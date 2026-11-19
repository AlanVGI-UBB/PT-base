import json

from app.core.db import get_connection, init_schema


def ensure_schema() -> None:
    init_schema()


def list_cursos() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT id, cod_ramo, nombre FROM curso ORDER BY id").fetchall()
    return [dict(r) for r in rows]


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
        resultado.append(item)
    return resultado


def insert_curso(curso_id: int, nombre: str, cod_ramo: str = "") -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO curso (id, cod_ramo, nombre) VALUES (?, ?, ?)",
        (curso_id, cod_ramo, nombre),
    )
    conn.commit()


def insert_termino(
    curso_id: int,
    texto_visible: str,
    formas: list[str],
    video_url: str,
    bloqueos: list[str] | None = None,
    estado: str = "ensayo",
) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO termino (curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            curso_id,
            texto_visible,
            json.dumps(formas, ensure_ascii=False),
            json.dumps(bloqueos or [], ensure_ascii=False),
            video_url,
            estado,
        ),
    )
    conn.commit()
