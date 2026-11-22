import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.auth import hash_password
from app.core.db import get_connection, init_schema
from app.glossary.indice import construir_indice, limpiar_cache_indices
from app.glossary.repository import list_terminos


def _resolver_archivo_video(video: str) -> str:
    return Path(video).name


def main() -> None:
    init_schema()

    seed_path = Path(__file__).resolve().parent.parent / "data" / "seed_glosario.json"
    data = json.loads(seed_path.read_text(encoding="utf-8"))

    conn = get_connection()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DELETE FROM metrica_segmento")
    conn.execute("DELETE FROM evento_clase")
    conn.execute("DELETE FROM clase")
    conn.execute("DELETE FROM inscripcion")
    conn.execute("DELETE FROM usuario")
    conn.execute("DELETE FROM termino")
    conn.execute("DELETE FROM curso")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()

    for curso in data["cursos"]:
        conn.execute(
            "INSERT INTO curso (id, cod_ramo, nombre) VALUES (?, ?, ?)",
            (curso["id"], curso["cod_ramo"], curso["nombre"]),
        )
    conn.commit()

    for termino in data["terminos"]:
        video = termino.get("video") or termino["video_url"]
        conn.execute(
            "INSERT INTO termino (curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                termino["curso_id"],
                termino["concepto"],
                json.dumps(termino["formas"], ensure_ascii=False),
                json.dumps(termino.get("bloqueos", []), ensure_ascii=False),
                _resolver_archivo_video(video),
                termino.get("estado", "ensayo"),
            ),
        )
    conn.commit()

    for usuario in data.get("usuarios", []):
        conn.execute(
            "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
            (
                usuario["rut"],
                hash_password(usuario["password"]),
                usuario["nombre"],
                usuario["apellido"],
            ),
        )
    conn.commit()

    for insc in data.get("inscripciones", []):
        conn.execute(
            "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) VALUES (?, ?, ?, ?)",
            (
                insc["rut"],
                insc["curso_id"],
                insc["seccion"],
                1 if insc.get("puede_capturar") else 0,
            ),
        )
    conn.commit()

    for curso in data["cursos"]:
        construir_indice(list_terminos(curso["id"]))
    limpiar_cache_indices()

    total_cursos = len(data["cursos"])
    total_terminos = len(data["terminos"])
    total_usuarios = len(data.get("usuarios", []))
    total_insc = len(data.get("inscripciones", []))
    print(
        f"Sembrados {total_cursos} cursos, {total_terminos} términos, "
        f"{total_usuarios} usuarios, {total_insc} inscripciones."
    )


if __name__ == "__main__":
    main()
