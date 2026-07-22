from app.core.db import get_connection, init_schema


def ensure_schema() -> None:
    init_schema()


def list_cursos() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT id, nombre FROM curso ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def list_terminos(curso_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, curso_id, lema, texto_visible, video_url, n_palabras "
        "FROM termino WHERE curso_id = ? ORDER BY id",
        (curso_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_glosario_por_lema(curso_id: int) -> dict[str, dict]:
    terminos = list_terminos(curso_id)
    return {t["lema"]: t for t in terminos}


def insert_curso(curso_id: int, nombre: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO curso (id, nombre) VALUES (?, ?)",
        (curso_id, nombre),
    )
    conn.commit()


def insert_termino(
    curso_id: int,
    lema: str,
    texto_visible: str,
    video_url: str,
    n_palabras: int = 1,
) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO termino (curso_id, lema, texto_visible, video_url, n_palabras) "
        "VALUES (?, ?, ?, ?, ?)",
        (curso_id, lema, texto_visible, video_url, n_palabras),
    )
    conn.commit()
