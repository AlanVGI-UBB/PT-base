from app.core.db import get_connection


def crear_clase(
    room_id: str,
    curso_id: int,
    seccion: str,
    rut_emisor: str,
    inicio: str,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO clase (room_id, curso_id, seccion, rut_emisor, fecha_inicio) "
        "VALUES (?, ?, ?, ?, ?)",
        (room_id, curso_id, seccion, rut_emisor, inicio),
    )
    conn.commit()
    return cur.lastrowid


def finalizar_clase(clase_id: int, fin: str, duracion_ms: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE clase SET fecha_fin = ?, duracion_ms = ? WHERE id = ?",
        (fin, duracion_ms, clase_id),
    )
    conn.commit()


def guardar_evento(
    clase_id: int,
    timestamp_ms: int,
    texto: str,
    estable: bool,
    senas_json: str,
) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO evento_clase (clase_id, timestamp_ms, texto, estable, senas_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (clase_id, timestamp_ms, texto, 1 if estable else 0, senas_json),
    )
    conn.commit()


def listar_clases(rut: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT c.id, c.room_id, c.curso_id, co.nombre as curso_nombre, "
        "co.cod_ramo, c.seccion, c.rut_emisor, c.fecha_inicio, c.fecha_fin, "
        "c.duracion_ms "
        "FROM clase c "
        "JOIN curso co ON co.id = c.curso_id "
        "JOIN inscripcion i ON i.curso_id = c.curso_id AND i.seccion = c.seccion "
        "WHERE i.rut = ? "
        "ORDER BY c.fecha_inicio DESC",
        (rut,),
    ).fetchall()
    return [dict(r) for r in rows]


def obtener_clase(clase_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT c.*, co.nombre as curso_nombre, co.cod_ramo "
        "FROM clase c "
        "JOIN curso co ON co.id = c.curso_id "
        "WHERE c.id = ?",
        (clase_id,),
    ).fetchone()
    if not row:
        return None
    return dict(row)


def obtener_eventos(clase_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, clase_id, timestamp_ms, texto, estable, senas_json "
        "FROM evento_clase WHERE clase_id = ? ORDER BY timestamp_ms",
        (clase_id,),
    ).fetchall()
    return [dict(r) for r in rows]
