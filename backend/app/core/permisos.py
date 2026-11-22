from fastapi import HTTPException

from app.core.db import get_connection


def resolver_sala(room_id: str) -> tuple[int, str] | None:
    partes = room_id.rsplit("-", 1)
    if len(partes) != 2 or not partes[0] or not partes[1]:
        return None
    cod_ramo, seccion = partes
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM curso WHERE cod_ramo = ?",
        (cod_ramo,),
    ).fetchone()
    if not row:
        return None
    return row["id"], seccion


def inscripcion(rut: str, curso_id: int, seccion: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT rut, curso_id, seccion, puede_capturar "
        "FROM inscripcion WHERE rut = ? AND curso_id = ? AND seccion = ?",
        (rut, curso_id, seccion),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["puede_capturar"] = bool(data["puede_capturar"])
    return data


def inscripcion_en_curso(rut: str, curso_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT rut, curso_id, seccion, puede_capturar "
        "FROM inscripcion WHERE rut = ? AND curso_id = ? LIMIT 1",
        (rut, curso_id),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["puede_capturar"] = bool(data["puede_capturar"])
    return data


def exigir_inscripcion(rut: str, curso_id: int, seccion: str) -> dict:
    insc = inscripcion(rut, curso_id, seccion)
    if not insc:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta sala")
    return insc


def exigir_inscripcion_curso(rut: str, curso_id: int) -> dict:
    insc = inscripcion_en_curso(rut, curso_id)
    if not insc:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")
    return insc
