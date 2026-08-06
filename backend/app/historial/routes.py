from fastapi import APIRouter, HTTPException, Request

from app.core.auth import obtener_rut
from app.historial.repository import (
    listar_clases,
    obtener_clase,
    obtener_eventos,
    usuario_participa,
)
from app.salas.manager import RoomManager

router = APIRouter(prefix="/api", tags=["historial"])


@router.get("/historial")
def api_historial(request: Request):
    rut = obtener_rut(request)
    clases = listar_clases(rut)
    return [
        {
            "id": c["id"],
            "room_id": c["room_id"],
            "curso_id": c["curso_id"],
            "curso_nombre": c["curso_nombre"],
            "cod_ramo": c["cod_ramo"],
            "seccion": c["seccion"],
            "fecha_inicio": c["fecha_inicio"],
            "fecha_fin": c["fecha_fin"],
            "duracion_ms": c["duracion_ms"],
            "titulo": c.get("titulo"),
            "palabras": c.get("palabras", 0),
            "preview": c.get("preview"),
        }
        for c in clases
    ]


@router.get("/historial/{clase_id}")
def api_historial_detalle(request: Request, clase_id: int):
    rut = obtener_rut(request)
    clase = obtener_clase(clase_id)
    if not clase:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    es_emisor = clase["rut_emisor"] == rut
    es_participante = usuario_participa(rut, clase["curso_id"], clase["seccion"])
    if not (es_emisor or es_participante):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta clase")
    eventos = obtener_eventos(clase_id)
    return {
        "clase": {
            "id": clase["id"],
            "room_id": clase["room_id"],
            "curso_nombre": clase.get("curso_nombre"),
            "cod_ramo": clase.get("cod_ramo"),
            "seccion": clase["seccion"],
            "fecha_inicio": clase["fecha_inicio"],
            "fecha_fin": clase["fecha_fin"],
            "duracion_ms": clase["duracion_ms"],
            "titulo": clase.get("titulo"),
        },
        "eventos": [
            {
                "timestamp_ms": e["timestamp_ms"],
                "texto": e["texto"],
                "estable": bool(e["estable"]),
                "senas": e["senas_json"],
            }
            for e in eventos
        ],
    }


@router.get("/salas/{room_id}/estado")
async def api_sala_estado(request: Request, room_id: str):
    obtener_rut(request)
    activa = await RoomManager.existe(room_id)
    sala = await RoomManager.obtener(room_id)
    rut_emisor = sala.rut_emisor if sala else None
    return {"room_id": room_id, "activa": activa, "rut_emisor": rut_emisor}
