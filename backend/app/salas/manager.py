import asyncio
import json
import logging
from dataclasses import dataclass, field
from weakref import WeakKeyDictionary

from fastapi import WebSocket

from app.glossary.indice import Indice

logger = logging.getLogger("puente_lsch")


@dataclass
class RoomState:
    room_id: str
    curso_id: int
    seccion: str
    rut_emisor: str
    emitter_ws: WebSocket | None = None
    listeners: set[WebSocket] = field(default_factory=set)
    indice: Indice = field(default_factory=lambda: Indice(entradas={}, max_ngrama=0))
    clase_id: int | None = None
    estado: str = "activa"
    estado_ts_ms: int = 0


class RoomManager:
    _salas: dict[str, RoomState] = {}
    _locks: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = WeakKeyDictionary()

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        lock = cls._locks.get(loop)
        if lock is None:
            lock = asyncio.Lock()
            cls._locks[loop] = lock
        return lock

    @classmethod
    def limpiar(cls) -> None:
        cls._salas.clear()

    @classmethod
    async def existe(cls, room_id: str) -> bool:
        async with cls._get_lock():
            return room_id in cls._salas

    @classmethod
    async def crear(
        cls,
        room_id: str,
        curso_id: int,
        seccion: str,
        rut_emisor: str,
        emitter_ws: WebSocket,
        indice: Indice,
    ) -> RoomState:
        async with cls._get_lock():
            if room_id in cls._salas:
                raise ValueError(f"La sala {room_id} ya existe")
            sala = RoomState(
                room_id=room_id,
                curso_id=curso_id,
                seccion=seccion,
                rut_emisor=rut_emisor,
                emitter_ws=emitter_ws,
                indice=indice,
            )
            cls._salas[room_id] = sala
            return sala

    @classmethod
    async def obtener(cls, room_id: str) -> RoomState | None:
        async with cls._get_lock():
            return cls._salas.get(room_id)

    @classmethod
    async def set_estado(cls, room_id: str, estado: str, timestamp_ms: int) -> bool:
        async with cls._get_lock():
            sala = cls._salas.get(room_id)
            if not sala:
                return False
            sala.estado = estado
            sala.estado_ts_ms = timestamp_ms
            return True

    @classmethod
    async def agregar_listener(cls, room_id: str, ws: WebSocket) -> tuple[str, int] | None:
        async with cls._get_lock():
            sala = cls._salas.get(room_id)
            if not sala:
                return None
            sala.listeners.add(ws)
            return sala.estado, sala.estado_ts_ms

    @classmethod
    async def quitar_listener(cls, room_id: str, ws: WebSocket) -> None:
        async with cls._get_lock():
            sala = cls._salas.get(room_id)
            if sala and ws in sala.listeners:
                sala.listeners.discard(ws)

    @classmethod
    async def broadcast(cls, room_id: str, evento: dict) -> int:
        async with cls._get_lock():
            sala = cls._salas.get(room_id)
            if not sala:
                return 0
            receptores = len(sala.listeners)
            targets: list[WebSocket] = []
            if sala.emitter_ws:
                targets.append(sala.emitter_ws)
            targets.extend(sala.listeners)
        text = json.dumps(evento, ensure_ascii=False)
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:
                pass
        return receptores

    @classmethod
    async def eliminar(cls, room_id: str) -> RoomState | None:
        async with cls._get_lock():
            return cls._salas.pop(room_id, None)
