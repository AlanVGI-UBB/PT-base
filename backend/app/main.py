import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app.asr.base import get_asr_provider
from app.evaluation.logging import crear_sesion, persistir_segmento
from app.glossary.matching import buscar_terminos
from app.glossary.repository import (
    ensure_schema,
    get_glosario_por_lema,
    list_cursos,
    list_terminos,
)

logger = logging.getLogger("puente_lsch")
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


@dataclass
class Sala:
    profesor: WebSocket | None = None
    alumnos: list[WebSocket] = field(default_factory=list)
    sesion_id: int | None = None


_salas: dict[int, Sala] = {}
_sala_lock = asyncio.Lock()


async def broadcast_alumnos(curso_id: int, payload: dict) -> None:
    sala = _salas.get(curso_id)
    if not sala:
        return
    texto = json.dumps(payload, ensure_ascii=False)
    muertos: list[WebSocket] = []
    for ws in sala.alumnos:
        try:
            await ws.send_text(texto)
        except Exception:
            muertos.append(ws)
    for ws in muertos:
        sala.alumnos.remove(ws)


async def get_or_create_sala(curso_id: int) -> Sala:
    async with _sala_lock:
        if curso_id not in _salas:
            _salas[curso_id] = Sala()
        return _salas[curso_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    yield


app = FastAPI(title="Puente LSCh API", version="0.2.0", lifespan=lifespan)

app.mount("/data/videos_senas", StaticFiles(directory=str(DATA_DIR / "videos_senas")), name="videos_senas")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/cursos")
async def api_list_cursos() -> list[dict]:
    return list_cursos()


@app.get("/api/cursos/{curso_id}/glosario")
async def api_glosario(curso_id: int) -> list[dict]:
    return list_terminos(curso_id)


@app.post("/api/sesiones")
async def api_crear_sesion(curso_id: int = Query(...)) -> dict:
    sesion_id = crear_sesion(curso_id)
    sala = await get_or_create_sala(curso_id)
    sala.sesion_id = sesion_id
    return {"sesion_id": sesion_id, "curso_id": curso_id}


@app.websocket("/ws/alumno/{curso_id}")
async def ws_alumno(ws: WebSocket, curso_id: int) -> None:
    await ws.accept()
    sala = await get_or_create_sala(curso_id)
    sala.alumnos.append(ws)
    logger.info("Alumno conectado a sala %s (%d alumnos)", curso_id, len(sala.alumnos))
    try:
        while True:
            data = await ws.receive_text()
            if data.strip() == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        if ws in sala.alumnos:
            sala.alumnos.remove(ws)
        logger.info("Alumno desconectado de sala %s", curso_id)


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


@app.websocket("/ws/profesor")
async def ws_profesor(ws: WebSocket, curso_id: int = Query(...)) -> None:
    await ws.accept()
    sala = await get_or_create_sala(curso_id)
    sala.profesor = ws
    if sala.sesion_id is None:
        sala.sesion_id = crear_sesion(curso_id)
    sesion_id = sala.sesion_id
    logger.info("Profesor conectado a sala %s (sesion %d)", curso_id, sesion_id)

    glosario = get_glosario_por_lema(curso_id)
    provider = get_asr_provider()
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
                if texto:
                    yield texto

    try:
        async for resultado in provider.transcribe_stream(_audio_gen()):
            if not resultado.texto.strip():
                continue
            senas = buscar_terminos(resultado.texto, glosario)
            segmento_idx += 1
            persistir_segmento(sesion_id, resultado.texto, resultado.estable, senas)
            evento = {
                "type": "segmento",
                "segment_id": segmento_idx,
                "texto": resultado.texto,
                "final": resultado.estable,
                "senas": senas,
                "t": datetime.now(timezone.utc).isoformat(),
            }
            await broadcast_alumnos(curso_id, evento)
    except WebSocketDisconnect:
        pass
    finally:
        if sala.profesor is ws:
            sala.profesor = None
        logger.info("Profesor desconectado de sala %s", curso_id)
