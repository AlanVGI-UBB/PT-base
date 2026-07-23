import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.asr.base import get_asr_provider
from app.auth.routes import router as auth_router
from app.core.auth import verificar_token
from app.core.db import get_connection
from app.glossary.matching import buscar_terminos
from app.glossary.repository import ensure_schema, get_glosario_por_lema, list_cursos, list_terminos
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
    yield


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
def api_cursos(rut: str = Query("")):
    conn = get_connection()
    if rut:
        rows = conn.execute(
            "SELECT c.id, c.cod_ramo, c.nombre, i.seccion "
            "FROM inscripcion i "
            "JOIN curso c ON c.id = i.curso_id "
            "WHERE i.rut = ? ORDER BY c.id, i.seccion",
            (rut,),
        ).fetchall()
        return [dict(r) for r in rows]
    return list_cursos()


@app.get("/api/cursos/{curso_id}/glosario")
async def api_glosario(curso_id: int) -> list[dict]:
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

        glosario = get_glosario_por_lema(curso_id)
        sala = await RoomManager.crear(room_id, curso_id, seccion, rut, ws, glosario)
        inicio_iso = datetime.now(timezone.utc).isoformat()
        clase_id_db = crear_clase(room_id, curso_id, seccion, rut, inicio_iso)
        sala.clase_id = clase_id_db

        logger.info("Sala %s creada por %s (clase %d)", room_id, rut, clase_id_db)

        provider = get_asr_provider()
        t_inicio = int(time.time() * 1000)
        segmento_idx = 0

        async def _audio_gen():
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    return
                if "bytes" in msg:
                    yield msg["bytes"]
                elif "text" in msg:
                    texto = msg["text"].strip()
                    if texto == '{"action":"finalizar"}':
                        return

        try:
            async for resultado in provider.transcribe_stream(_audio_gen()):
                if not resultado.texto.strip():
                    continue
                segmento_idx += 1
                ts_ms = int(time.time() * 1000) - t_inicio
                senas = buscar_terminos(resultado.texto, sala.glosario_por_lema)
                senas_json = json.dumps(senas, ensure_ascii=False)
                guardar_evento(clase_id_db, ts_ms, resultado.texto, resultado.estable, senas_json)

                evento = {
                    "type": "segmento",
                    "segment_id": segmento_idx,
                    "texto": resultado.texto,
                    "final": resultado.estable,
                    "senas": senas,
                    "timestamp_ms": ts_ms,
                }
                await RoomManager.broadcast(room_id, evento)
        except WebSocketDisconnect:
            pass
        finally:
            fin_iso = datetime.now(timezone.utc).isoformat()
            duracion = int(time.time() * 1000) - t_inicio
            finalizar_clase(clase_id_db, fin_iso, duracion)
            await RoomManager.broadcast(room_id, {"type": "clase_finalizada", "clase_id": clase_id_db})
            await RoomManager.eliminar(room_id)
            logger.info("Sala %s finalizada (clase %d, %d ms)", room_id, clase_id_db, duracion)

    elif rol == "listener":
        if not await RoomManager.existe(room_id):
            await ws.send_json({"type": "error", "mensaje": "No hay transmisión activa en esta sala"})
            await ws.close()
            return

        await RoomManager.agregar_listener(room_id, ws)
        logger.info("Listener conectado a sala %s", room_id)
        try:
            while True:
                await asyncio.wait_for(ws.receive_text(), timeout=30)
        except (WebSocketDisconnect, asyncio.TimeoutError):
            pass
        finally:
            await RoomManager.quitar_listener(room_id, ws)
            logger.info("Listener desconectado de sala %s", room_id)
    else:
        await ws.send_json({"type": "error", "mensaje": "Rol inválido. Usar emitter o listener"})
        await ws.close()
