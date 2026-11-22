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

    # Migracion: agregar puede_capturar si la tabla inscripcion no tiene la columna
    cursor = conn.execute("PRAGMA table_info(inscripcion)")
    columns = [row[1] for row in cursor.fetchall()]
    if "puede_capturar" not in columns and len(columns) > 0:
        conn.execute("ALTER TABLE inscripcion ADD COLUMN puede_capturar INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    # Migracion: agregar titulo, cierre y condiciones_confirmadas a clase si faltan
    cursor = conn.execute("PRAGMA table_info(clase)")
    columns = [row[1] for row in cursor.fetchall()]
    if len(columns) > 0:
        if "titulo" not in columns:
            conn.execute("ALTER TABLE clase ADD COLUMN titulo TEXT")
        if "cierre" not in columns:
            conn.execute("ALTER TABLE clase ADD COLUMN cierre TEXT")
        if "condiciones_confirmadas" not in columns:
            conn.execute(
                "ALTER TABLE clase ADD COLUMN condiciones_confirmadas INTEGER NOT NULL DEFAULT 0"
            )
        conn.commit()

    # Migracion: agregar abstenciones_json y tipo a evento_clase si faltan
    cursor = conn.execute("PRAGMA table_info(evento_clase)")
    columns = [row[1] for row in cursor.fetchall()]
    if len(columns) > 0:
        if "abstenciones_json" not in columns:
            conn.execute("ALTER TABLE evento_clase ADD COLUMN abstenciones_json TEXT")
        if "tipo" not in columns:
            conn.execute("ALTER TABLE evento_clase ADD COLUMN tipo TEXT NOT NULL DEFAULT 'segmento'")
        conn.commit()

    # Limpieza de tablas heredadas sin uso desde SPEC-004 (SPEC-008)
    conn.execute("DROP TABLE IF EXISTS segmento")
    conn.execute("DROP TABLE IF EXISTS sesion")
    conn.commit()
