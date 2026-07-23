import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import WebSocket


logger = logging.getLogger("puente_lsch")


@dataclass
class RoomState:
    room_id: str
    curso_id: int
    seccion: str
    rut_emisor: str
    emitter_ws: WebSocket | None = None
    listeners: set[WebSocket] = field(default_factory=set)
    glosario_por_lema: dict = field(default_factory=dict)
    timeline: list[dict] = field(default_factory=list)
    inicio_ms: int = 0
    clase_id: int | None = None


class RoomManager:
    _salas: dict[str, RoomState] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def existe(cls, room_id: str) -> bool:
        async with cls._lock:
            return room_id in cls._salas

    @classmethod
    async def crear(
        cls,
        room_id: str,
        curso_id: int,
        seccion: str,
        rut_emisor: str,
        emitter_ws: WebSocket,
        glosario: dict,
    ) -> RoomState:
        async with cls._lock:
            if room_id in cls._salas:
                raise ValueError(f"La sala {room_id} ya existe")
            sala = RoomState(
                room_id=room_id,
                curso_id=curso_id,
                seccion=seccion,
                rut_emisor=rut_emisor,
                emitter_ws=emitter_ws,
                glosario_por_lema=glosario,
                inicio_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
            )
            cls._salas[room_id] = sala
            return sala

    @classmethod
    async def obtener(cls, room_id: str) -> RoomState | None:
        async with cls._lock:
            return cls._salas.get(room_id)

    @classmethod
    async def agregar_listener(cls, room_id: str, ws: WebSocket) -> bool:
        async with cls._lock:
            sala = cls._salas.get(room_id)
            if not sala:
                return False
            sala.listeners.add(ws)
            return True

    @classmethod
    async def quitar_listener(cls, room_id: str, ws: WebSocket) -> None:
        async with cls._lock:
            sala = cls._salas.get(room_id)
            if sala and ws in sala.listeners:
                sala.listeners.discard(ws)

    @classmethod
    async def broadcast(cls, room_id: str, evento: dict) -> None:
        async with cls._lock:
            sala = cls._salas.get(room_id)
            if not sala:
                return
        text = json.dumps(evento, ensure_ascii=False)
        targets: list[WebSocket] = []
        async with cls._lock:
            if sala.emitter_ws:
                targets.append(sala.emitter_ws)
            targets.extend(sala.listeners)
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:
                pass

    @classmethod
    async def eliminar(cls, room_id: str) -> RoomState | None:
        async with cls._lock:
            return cls._salas.pop(room_id, None)
