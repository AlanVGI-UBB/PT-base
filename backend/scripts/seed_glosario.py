import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import get_connection, init_schema


def hash_pass(password: str) -> str:
    return hashlib.sha256((password + "puente_lsch_salt").encode()).hexdigest()


def main() -> None:
    init_schema()

    seed_path = Path(__file__).resolve().parent.parent / "data" / "seed_glosario.json"
    data = json.loads(seed_path.read_text(encoding="utf-8"))

    conn = get_connection()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DELETE FROM evento_clase")
    conn.execute("DELETE FROM clase")
    conn.execute("DELETE FROM inscripcion")
    conn.execute("DELETE FROM segmento")
    conn.execute("DELETE FROM sesion")
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
        conn.execute(
            "INSERT INTO termino (curso_id, lema, texto_visible, video_url, n_palabras) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                termino["curso_id"],
                termino["lema"],
                termino["texto_visible"],
                termino["video_url"],
                termino.get("n_palabras", 1),
            ),
        )
    conn.commit()

    for usuario in data.get("usuarios", []):
        conn.execute(
            "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
            (usuario["rut"], hash_pass(usuario["password"]), usuario["nombre"], usuario["apellido"]),
        )
    conn.commit()

    for insc in data.get("inscripciones", []):
        conn.execute(
            "INSERT INTO inscripcion (rut, curso_id, seccion) VALUES (?, ?, ?)",
            (insc["rut"], insc["curso_id"], insc["seccion"]),
        )
    conn.commit()

    total_cursos = len(data["cursos"])
    total_terminos = len(data["terminos"])
    total_usuarios = len(data.get("usuarios", []))
    total_insc = len(data.get("inscripciones", []))
    print(f"Sembrados {total_cursos} cursos, {total_terminos} términos, {total_usuarios} usuarios, {total_insc} inscripciones.")


if __name__ == "__main__":
    main()
