import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import get_connection, init_schema
from app.glossary.repository import insert_curso, insert_termino


def main() -> None:
    init_schema()

    seed_path = Path(__file__).resolve().parent.parent / "data" / "seed_glosario.json"
    data = json.loads(seed_path.read_text(encoding="utf-8"))

    conn = get_connection()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DELETE FROM termino")
    conn.execute("DELETE FROM curso")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()

    for curso in data["cursos"]:
        insert_curso(curso["id"], curso["nombre"])
    for termino in data["terminos"]:
        insert_termino(
            termino["curso_id"],
            termino["lema"],
            termino["texto_visible"],
            termino["video_url"],
            termino.get("n_palabras", 1),
        )

    print(f"Sembrados {len(data['cursos'])} cursos y {len(data['terminos'])} terminos.")


if __name__ == "__main__":
    main()
