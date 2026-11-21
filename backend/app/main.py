import asyncio
import contextlib
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.asr.base import AsrConfigError, get_asr_provider
from app.auth.routes import router as auth_router
from app.core.auth import obtener_rut, verificar_token
from app.core.config import get_settings
from app.core.db import get_connection
from app.evaluation.metricas import registrar_segmento
from app.glossary.indice import obtener_indice_curso
from app.glossary.matching import buscar_terminos
from app.glossary.repository import ensure_schema, list_terminos
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


app = FastAPI(title="Puente LSCh API", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/data/videos_senas", StaticFiles(directory=str(DATA_DIR / "videos_senas")), name="videos_senas")

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
        "SELECT c.id, c.cod_ramo, c.nombre, i.seccion "
        "FROM inscripcion i "
        "JOIN curso c ON c.id = i.curso_id "
        "WHERE i.rut = ? ORDER BY c.id, i.seccion",
        (rut,),
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/cursos/{curso_id}/glosario")
async def api_glosario(request: Request, curso_id: int) -> list[dict]:
    obtener_rut(request)
    return list_terminos(curso_id)


@app.websocket("/ws/echo")
async def ws_echo(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_text()
            await ws.send_json(
                {
                    "type": "echo",
                    "text": payload,
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "echoed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except WebSocketDisconnect:
        return


@app.websocket("/ws/sala/{room_id}")
async def ws_sala(ws: WebSocket, room_id: str, rol: str = Query("listener"), token: str = Query("")):
    rut = verificar_token(token)
    if not rut:
        await ws.accept()
        await ws.send_json({"type": "error", "mensaje": "Token inválido o expirado"})
        await ws.close()
        return

    partes = room_id.rsplit("-", 1)
    if len(partes) != 2:
        await ws.accept()
        await ws.send_json({"type": "error", "mensaje": "Formato de room_id inválido. Usar COD_RAMO-SECCION"})
        await ws.close()
        return
    cod_ramo, seccion = partes

    conn = get_connection()
    curso_row = conn.execute(
        "SELECT id, nombre FROM curso WHERE cod_ramo = ?", (cod_ramo,)
    ).fetchone()
    if not curso_row:
        await ws.accept()
        await ws.send_json({"type": "error", "mensaje": f"Curso {cod_ramo} no encontrado"})
        await ws.close()
        return
    curso_id = curso_row["id"]

    await ws.accept()

    if rol == "emitter":
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
        clase_id_db = crear_clase(room_id, curso_id, seccion, rut, inicio_iso)
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
                            if data.get("action") == "finalizar":
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
            async for resultado in provider.transcribe_stream(
                _audio_gen(),
                contexto=contexto,
            ):
                if stop_event.is_set():
                    break
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
                finalizar_clase(clase_id_db, fin_iso, duracion, titulo)
                await _cerrar_listeners({"type": "clase_finalizada", "clase_id": clase_id_db})
                logger.info("Sala %s finalizada (clase %d, %d ms, titulo=%r)", room_id, clase_id_db, duracion, titulo)
            finally:
                await RoomManager.eliminar(room_id)
                with contextlib.suppress(Exception):
                    await ws.close()

    elif rol == "listener":
        if not await RoomManager.existe(room_id):
            await ws.send_json({"type": "error", "mensaje": "No hay transmisión activa en esta sala"})
            await ws.close()
            return

        await RoomManager.agregar_listener(room_id, ws)
        logger.info("Listener conectado a sala %s", room_id)
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
