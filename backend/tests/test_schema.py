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
    c.execute("INSERT INTO curso (id, cod_ramo, nombre) VALUES (1, 'INF-221', 'Test')")
    c.commit()
    yield c
    c.close()


def test_insert_curso(conn):
    conn.execute("INSERT INTO curso (id, cod_ramo, nombre) VALUES (2, 'INF-222', 'Otro')")
    conn.commit()
    rows = conn.execute("SELECT * FROM curso").fetchall()
    assert len(rows) == 2


def test_insert_termino(conn):
    conn.execute(
        "INSERT INTO termino (curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
        "VALUES (1, 'lista enlazada', '[\"lista enlazada\"]', '[]', '/v/lista_enlazada.mp4', 'ensayo')"
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM termino WHERE texto_visible = 'lista enlazada'"
    ).fetchone()
    assert row["texto_visible"] == "lista enlazada"
    assert row["estado"] == "ensayo"


def test_schema_idempotent(db_path):
    c1 = sqlite3.connect(db_path)
    c1.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    c1.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    c1.close()


def test_tablas_obsoletas_eliminadas(conn):
    tablas = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "sesion" not in tablas
    assert "segmento" not in tablas
    assert "metrica_segmento" in tablas


def test_metrica_segmento_fk(conn):
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) "
        "VALUES ('11-1', 'hash', 'A', 'B')"
    )
    conn.execute(
        "INSERT INTO clase (id, room_id, curso_id, seccion, rut_emisor, fecha_inicio) "
        "VALUES (1, 'INF-221-SEC1', 1, 'SEC1', '11-1', '2026-01-01')"
    )
    conn.execute(
        "INSERT INTO metrica_segmento ("
        "clase_id, segmento_id, audio_inicio_ms, audio_fin_ms, "
        "llegada_fin_ms, asr_ms, nlp_ms, emitido_ms, receptores"
        ") VALUES (1, 3, 100, 1500, 1510, 80, 5, 1600, 4)"
    )
    conn.commit()
    row = conn.execute("SELECT * FROM metrica_segmento").fetchone()
    assert row["segmento_id"] == 3
    assert row["receptores"] == 4


def test_nuevas_tablas(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO curso (id, cod_ramo, nombre) VALUES (1, 'INF-221', 'Test')")
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) "
        "VALUES ('11-1', 'hash', 'A', 'B')"
    )
    conn.execute(
        "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) "
        "VALUES ('11-1', 1, 'SEC1', 1)"
    )
    conn.execute(
        "INSERT INTO clase (room_id, curso_id, seccion, rut_emisor, fecha_inicio, cierre, condiciones_confirmadas) "
        "VALUES ('INF-221-SEC1', 1, 'SEC1', '11-1', '2026-01-01', 'explicito', 1)"
    )
    conn.execute(
        "INSERT INTO evento_clase (clase_id, timestamp_ms, texto, estable, senas_json, abstenciones_json, tipo) "
        "VALUES (1, 0, 'test', 1, '[]', '[]', 'segmento')"
    )
    conn.commit()
    insc = conn.execute("SELECT puede_capturar FROM inscripcion WHERE rut = '11-1'").fetchone()
    clase = conn.execute("SELECT cierre, condiciones_confirmadas FROM clase WHERE id = 1").fetchone()
    ev = conn.execute("SELECT tipo FROM evento_clase WHERE clase_id = 1").fetchone()
    assert insc["puede_capturar"] == 1
    assert clase["cierre"] == "explicito"
    assert clase["condiciones_confirmadas"] == 1
    assert ev["tipo"] == "segmento"
    conn.close()
