import json
from datetime import datetime, timezone

from app.core.db import get_connection


def crear_sesion(curso_id: int) -> int:
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO sesion (curso_id, inicio) VALUES (?, ?)",
        (curso_id, now),
    )
    conn.commit()
    return cur.lastrowid


def finalizar_sesion(sesion_id: int) -> None:
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE sesion SET fin = ? WHERE id = ?",
        (now, sesion_id),
    )
    conn.commit()


def persistir_segmento(
    sesion_id: int,
    texto: str,
    estable: bool,
    senas: list[dict],
) -> int:
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    senas_json = json.dumps(senas, ensure_ascii=False)
    cur = conn.execute(
        "INSERT INTO segmento (sesion_id, texto, recibido_at, emitido_at, estable, senas_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (sesion_id, texto, now, now, 1 if estable else 0, senas_json),
    )
    conn.commit()
    return cur.lastrowid
