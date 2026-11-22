import asyncio
import contextlib
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.asr.base import AsrConfigError, get_asr_provider
from app.asr.stub import StubAsrProvider
from app.auth.routes import router as auth_router
from app.core.auth import obtener_rut, verificar_token
from app.core.config import get_settings
from app.core.db import get_connection
from app.core.permisos import exigir_inscripcion_curso, inscripcion, resolver_sala
from app.evaluation.metricas import registrar_segmento
from app.glossary.indice import obtener_indice_curso
from app.glossary.matching import buscar_terminos
from app.glossary.repository import ensure_schema, list_terminos, obtener_termino_video
from app.historial.repository import crear_clase, finalizar_clase, guardar_evento
from app.historial.routes import router as historial_router
from app.salas.manager import RoomManager

logger = logging.getLogger("puente_lsch")
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    if get_settings().ASR_PROVIDER == "whisper":
        get_asr_provider()
    try:
        yield
    finally:
        RoomManager.limpiar()


app = FastAPI(title="Puente LSCh API", version="0.4.0", lifespan=lifespan)

_cors_origins = [
    origin.strip()
    for origin in get_settings().CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(historial_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/cursos")
def api_cursos(request: Request):
    rut = obtener_rut(request)
    conn = get_connection()
    rows = conn.execute(
        "SELECT c.id, c.cod_ramo, c.nombre, i.seccion, i.puede_capturar "
        "FROM inscripcion i "
        "JOIN curso c ON c.id = i.curso_id "
        "WHERE i.rut = ? ORDER BY c.id, i.seccion",
        (rut,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "cod_ramo": r["cod_ramo"],
            "nombre": r["nombre"],
            "seccion": r["seccion"],
            "puede_capturar": bool(r["puede_capturar"]),
        }
        for r in rows
    ]


@app.get("/api/cursos/{curso_id}/glosario")
async def api_glosario(request: Request, curso_id: int) -> list[dict]:
    rut = obtener_rut(request)
    exigir_inscripcion_curso(rut, curso_id)
    return list_terminos(curso_id)


@app.get("/api/cursos/{curso_id}/senas/{termino_id}/video")
def video_sena(request: Request, curso_id: int, termino_id: int) -> FileResponse:
    rut = obtener_rut(request)
    exigir_inscripcion_curso(rut, curso_id)
    termino = obtener_termino_video(curso_id, termino_id)
    if not termino or termino.get("estado") == "retirado":
        raise HTTPException(status_code=404, detail="Clip no disponible")
    videos_dir = (DATA_DIR / "videos_senas").resolve()
    nombre_archivo = Path(termino["video_url"]).name
    ruta = (videos_dir / nombre_archivo).resolve()
    if ruta.parent != videos_dir or not ruta.is_file():
        raise HTTPException(status_code=404, detail="Archivo de video no encontrado")
    return FileResponse(str(ruta), media_type="video/mp4")


@app.websocket("/ws/sala/{room_id}")
async def ws_sala(
    ws: WebSocket,
    room_id: str,
    rol: str = Query("listener"),
    token: str = Query(""),
    condiciones: str = Query("0"),
):
    rut = verificar_token(token)
    if not rut:
        await ws.accept()
        await ws.send_json({"type": "error", "mensaje": "Token inválido o expirado"})
        await ws.close()
        return

    resuelta = resolver_sala(room_id)
    if not resuelta:
        await ws.accept()
        await ws.send_json({"type": "error", "mensaje": "No tienes acceso a esta sala"})
        await ws.close()
        return
    curso_id, seccion = resuelta

    insc = inscripcion(rut, curso_id, seccion)
    if not insc:
        await ws.accept()
        await ws.send_json({"type": "error", "mensaje": "No tienes acceso a esta sala"})
        await ws.close()
        return

    await ws.accept()

    if rol == "emitter":
        if not insc["puede_capturar"]:
            await ws.send_json({"type": "error", "mensaje": "No tienes permiso de captura en esta sala"})
            await ws.close()
            return

        if condiciones != "1":
            await ws.send_json(
                {
                    "type": "error",
                    "mensaje": "Debes confirmar las condiciones de registro antes de capturar",
                }
            )
            await ws.close()
            return

        if await RoomManager.existe(room_id):
            await ws.send_json({"type": "error", "mensaje": "Ya existe una transmisión activa en esta sala"})
            await ws.close()
            return

        try:
            provider = get_asr_provider()
        except AsrConfigError as exc:
            await ws.send_json({"type": "error", "mensaje": str(exc)})
            await ws.close()
            return

        settings = get_settings()
        max_trama_bytes = settings.ASR_MAX_TRAMA_BYTES
        flush_timeout_s = settings.ASR_FLUSH_TIMEOUT_MS / 1000.0
        indice = obtener_indice_curso(curso_id)
        terminos_activos = [
            t for t in list_terminos(curso_id) if t.get("estado", "ensayo") != "retirado"
        ]
        contexto = (
            [t["texto_visible"] for t in terminos_activos]
            if settings.ASR_PROMPT_GLOSARIO
            else None
        )

        sala = await RoomManager.crear(room_id, curso_id, seccion, rut, ws, indice)
        inicio_iso = datetime.now(timezone.utc).isoformat()
        clase_id_db = crear_clase(
            room_id,
            curso_id,
            seccion,
            rut,
            inicio_iso,
            condiciones_confirmadas=True,
        )
        sala.clase_id = clase_id_db

        logger.info("Sala %s creada por %s (clase %d)", room_id, rut, clase_id_db)

        t_inicio = int(time.time() * 1000)
        t_mono_inicio_ns = time.monotonic_ns()
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        stop_event = asyncio.Event()
        session_state: dict = {
            "titulo": None,
            "finalizar": False,
            "disconectado": False,
            "trama_invalida_registrada": False,
        }

        async def _receiver():
            try:
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        session_state["disconectado"] = True
                        stop_event.set()
                        return
                    trama = msg.get("bytes")
                    if trama is not None:
                        if sala.estado == "pausada":
                            continue
                        if len(trama) % 2 != 0 or len(trama) > max_trama_bytes:
                            if not session_state["trama_invalida_registrada"]:
                                logger.warning(
                                    "Sala %s: trama de audio inválida (%d bytes); descartando",
                                    room_id,
                                    len(trama),
                                )
                                session_state["trama_invalida_registrada"] = True
                            continue
                        if len(trama) == 0:
                            continue
                        await audio_queue.put(trama)
                    elif msg.get("text") is not None:
                        try:
                            data = json.loads(msg["text"])
                            action = data.get("action")
                            if action == "pausar" and sala.estado != "pausada":
                                ts_ms = int(time.time() * 1000) - t_inicio
                                await RoomManager.set_estado(room_id, "pausada", ts_ms)
                                await audio_queue.put(b"")
                                guardar_evento(
                                    clase_id_db,
                                    ts_ms,
                                    None,
                                    True,
                                    "[]",
                                    "[]",
                                    tipo="pausa",
                                )
                                await RoomManager.broadcast(
                                    room_id,
                                    {
                                        "type": "estado_sesion",
                                        "estado": "pausada",
                                        "timestamp_ms": ts_ms,
                                    },
                                )
                            elif action == "reanudar" and sala.estado != "activa":
                                ts_ms = int(time.time() * 1000) - t_inicio
                                await RoomManager.set_estado(room_id, "activa", ts_ms)
                                guardar_evento(
                                    clase_id_db,
                                    ts_ms,
                                    None,
                                    True,
                                    "[]",
                                    "[]",
                                    tipo="reanudacion",
                                )
                                await RoomManager.broadcast(
                                    room_id,
                                    {
                                        "type": "estado_sesion",
                                        "estado": "activa",
                                        "timestamp_ms": ts_ms,
                                    },
                                )
                            elif action == "finalizar":
                                session_state["titulo"] = data.get("titulo")
                                session_state["finalizar"] = True
                                await audio_queue.put(None)
                                return
                        except (json.JSONDecodeError, TypeError):
                            pass
            except (WebSocketDisconnect, RuntimeError):
                session_state["disconectado"] = True
                stop_event.set()

        async def _audio_gen():
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    return
                yield chunk

        async def _transcribir():
            es_stub = isinstance(provider, StubAsrProvider)
            async for resultado in provider.transcribe_stream(
                _audio_gen(),
                contexto=contexto,
            ):
                if stop_event.is_set():
                    break
                if es_stub and sala.estado == "pausada":
                    continue
                if not resultado.texto.strip():
                    continue
                ts_ms = int(time.time() * 1000) - t_inicio
                nlp_ms = 0
                if resultado.estable:
                    nlp_ini_ns = time.monotonic_ns()
                    coincidencias = buscar_terminos(resultado.texto, sala.indice)
                    nlp_ms = (time.monotonic_ns() - nlp_ini_ns) // 1_000_000
                    senas = coincidencias.senas
                    senas_json = json.dumps(senas, ensure_ascii=False)
                    abstenciones_json = json.dumps(
                        coincidencias.abstenciones,
                        ensure_ascii=False,
                    )
                    guardar_evento(
                        clase_id_db,
                        ts_ms,
                        resultado.texto,
                        True,
                        senas_json,
                        abstenciones_json,
                        tipo="segmento",
                    )
                else:
                    senas = []

                emitido_ms = (time.monotonic_ns() - t_mono_inicio_ns) // 1_000_000
                servidor_ms = time.time_ns() // 1_000_000
                evento = {
                    "type": "segmento",
                    "segment_id": resultado.segmento_id,
                    "texto": resultado.texto,
                    "final": resultado.estable,
                    "senas": senas,
                    "timestamp_ms": ts_ms,
                    "servidor_ms": servidor_ms,
                }
                receptores = await RoomManager.broadcast(room_id, evento)
                if resultado.estable:
                    registrar_segmento(
                        clase_id=clase_id_db,
                        segmento_id=resultado.segmento_id,
                        audio_inicio_ms=resultado.inicio_ms,
                        audio_fin_ms=resultado.fin_ms,
                        llegada_fin_ms=resultado.llegada_fin_ms,
                        asr_ms=resultado.asr_ms,
                        nlp_ms=nlp_ms,
                        emitido_ms=emitido_ms,
                        receptores=receptores,
                    )

        async def _cerrar_listeners(evento: dict) -> None:
            await RoomManager.broadcast(room_id, evento)
            sala_actual = await RoomManager.obtener(room_id)
            if not sala_actual:
                return
            for ws_listener in list(sala_actual.listeners):
                try:
                    await ws_listener.close()
                except Exception:
                    pass
            sala_actual.listeners.clear()

        receiver_task = asyncio.create_task(_receiver())
        transcribe_task = asyncio.create_task(_transcribir())

        try:
            await asyncio.wait(
                {receiver_task, transcribe_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if session_state["finalizar"] and not transcribe_task.done():
                try:
                    await asyncio.wait_for(transcribe_task, timeout=flush_timeout_s)
                except asyncio.TimeoutError:
                    logger.warning(
                        "Sala %s: vaciado final superó %d ms; abandonando transcripción pendiente",
                        room_id,
                        settings.ASR_FLUSH_TIMEOUT_MS,
                    )
                except Exception as exc:
                    logger.error("Error en vaciado de sala %s: %s", room_id, exc)
            if transcribe_task.done() and not transcribe_task.cancelled():
                exc = transcribe_task.exception()
                if exc:
                    logger.error("Error en transcripción de sala %s: %s", room_id, exc)
        except BaseException:
            pass
        finally:
            try:
                stop_event.set()
                for t in (transcribe_task, receiver_task):
                    if not t.done():
                        t.cancel()
                for t in (transcribe_task, receiver_task):
                    with contextlib.suppress(BaseException):
                        await t

                cierre = "explicito" if session_state["finalizar"] else "timeout"
                if not session_state["finalizar"]:
                    ts_desc = int(time.time() * 1000) - t_inicio
                    guardar_evento(
                        clase_id_db,
                        ts_desc,
                        None,
                        True,
                        "[]",
                        "[]",
                        tipo="desconexion",
                    )

                if session_state["disconectado"] and not session_state["finalizar"]:
                    timeout_ms = settings.SALA_TIMEOUT_MS
                    logger.info(
                        "Sala %s: emisor desconectado sin finalizar; cierre en %d ms",
                        room_id,
                        timeout_ms,
                    )
                    await RoomManager.broadcast(
                        room_id,
                        {
                            "type": "emisor_desconectado",
                            "mensaje": "El emisor se desconectó. La clase se guardará automáticamente.",
                        },
                    )
                    await asyncio.sleep(timeout_ms / 1000)

                fin_iso = datetime.now(timezone.utc).isoformat()
                duracion = int(time.time() * 1000) - t_inicio
                titulo = session_state["titulo"]
                if titulo is not None:
                    titulo = titulo.strip() or None
                finalizar_clase(clase_id_db, fin_iso, duracion, titulo, cierre=cierre)
                await _cerrar_listeners({"type": "clase_finalizada", "clase_id": clase_id_db})
                logger.info(
                    "Sala %s finalizada (clase %d, %d ms, cierre=%s, titulo=%r)",
                    room_id,
                    clase_id_db,
                    duracion,
                    cierre,
                    titulo,
                )
            finally:
                await RoomManager.eliminar(room_id)
                with contextlib.suppress(Exception):
                    await ws.close()

    elif rol == "listener":
        estado_info = await RoomManager.agregar_listener(room_id, ws)
        if estado_info is None:
            await ws.send_json({"type": "error", "mensaje": "No hay transmisión activa en esta sala"})
            await ws.close()
            return
        estado_actual, estado_ts_ms = estado_info
        await ws.send_json(
            {
                "type": "estado_sesion",
                "estado": estado_actual,
                "timestamp_ms": estado_ts_ms,
            }
        )
        logger.info("Listener conectado a sala %s (estado=%s)", room_id, estado_actual)
        try:
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            await RoomManager.quitar_listener(room_id, ws)
            logger.info("Listener desconectado de sala %s", room_id)
    else:
        await ws.send_json({"type": "error", "mensaje": "Rol inválido. Usar emitter o listener"})
        await ws.close()
