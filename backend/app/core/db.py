import sqlite3
from pathlib import Path

_conn = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        from app.core.config import get_settings

        db_path = Path(get_settings().DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def init_schema() -> None:
    conn = get_connection()
    schema_path = Path(__file__).resolve().parent.parent.parent / "data" / "schema.sql"

    # Migracion: reemplazar tabla termino heredada sin formas_json
    cursor = conn.execute("PRAGMA table_info(termino)")
    columns = [row[1] for row in cursor.fetchall()]
    if "formas_json" not in columns and len(columns) > 0:
        conn.execute("DROP TABLE termino")
        conn.commit()

    if schema_path.exists():
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.commit()

    # Migracion: agregar cod_ramo si la tabla curso existe pero no tiene la columna
    cursor = conn.execute("PRAGMA table_info(curso)")
    columns = [row[1] for row in cursor.fetchall()]
    if "cod_ramo" not in columns and len(columns) > 0:
        conn.execute("ALTER TABLE curso ADD COLUMN cod_ramo TEXT NOT NULL DEFAULT ''")
        conn.commit()

    # Migracion: agregar titulo si la tabla clase existe pero no tiene la columna
    cursor = conn.execute("PRAGMA table_info(clase)")
    columns = [row[1] for row in cursor.fetchall()]
    if "titulo" not in columns and len(columns) > 0:
        conn.execute("ALTER TABLE clase ADD COLUMN titulo TEXT")
        conn.commit()

    # Migracion: agregar abstenciones_json si la tabla evento_clase no tiene la columna
    cursor = conn.execute("PRAGMA table_info(evento_clase)")
    columns = [row[1] for row in cursor.fetchall()]
    if "abstenciones_json" not in columns and len(columns) > 0:
        conn.execute("ALTER TABLE evento_clase ADD COLUMN abstenciones_json TEXT")
        conn.commit()
