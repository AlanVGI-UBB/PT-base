import sqlite3
from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "data" / "schema.sql"


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def conn(db_path):
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    c.execute("INSERT INTO curso (id, nombre) VALUES (1, 'Test')")
    c.commit()
    yield c
    c.close()


def test_insert_curso(conn):
    conn.execute("INSERT INTO curso (id, nombre) VALUES (2, 'Otro')")
    conn.commit()
    rows = conn.execute("SELECT * FROM curso").fetchall()
    assert len(rows) == 2


def test_insert_termino(conn):
    conn.execute(
        "INSERT INTO termino (curso_id, lema, texto_visible, video_url, n_palabras) "
        "VALUES (1, 'derivada', 'derivada', '/v/derivada.mp4', 1)"
    )
    conn.commit()
    row = conn.execute("SELECT * FROM termino WHERE lema = 'derivada'").fetchone()
    assert row["texto_visible"] == "derivada"
    assert row["n_palabras"] == 1


def test_schema_idempotent(db_path):
    c1 = sqlite3.connect(db_path)
    c1.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    c1.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    c1.close()


def test_segmento_fk(conn):
    conn.execute("INSERT INTO sesion (id, curso_id, inicio) VALUES (1, 1, '2026-01-01')")
    conn.execute(
        "INSERT INTO segmento (sesion_id, texto, estable) VALUES (1, 'hola', 1)"
    )
    conn.commit()
    row = conn.execute("SELECT * FROM segmento").fetchone()
    assert row["texto"] == "hola"
