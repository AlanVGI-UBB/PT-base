import json

from app.core.db import get_connection, init_schema


def ensure_schema() -> None:
    init_schema()


def list_terminos(curso_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado "
        "FROM termino WHERE curso_id = ? ORDER BY id",
        (curso_id,),
    ).fetchall()
    resultado: list[dict] = []
    for r in rows:
        item = dict(r)
        formas = json.loads(item.pop("formas_json"))
        bloqueos = json.loads(item.pop("bloqueos_json") or "[]")
        item["formas"] = formas
        item["bloqueos"] = bloqueos
        item["video_url"] = f"/api/cursos/{item['curso_id']}/senas/{item['id']}/video"
        resultado.append(item)
    return resultado


def obtener_termino_video(curso_id: int, termino_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, curso_id, video_url, estado "
        "FROM termino WHERE id = ? AND curso_id = ?",
        (termino_id, curso_id),
    ).fetchone()
    return dict(row) if row else None
