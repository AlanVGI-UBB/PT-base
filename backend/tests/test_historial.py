import pytest
from fastapi.testclient import TestClient

from app.core.auth import hash_password
from app.core.db import get_connection, init_schema
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.core import db as db_mod
    db_mod._conn = None

    init_schema()

    conn = get_connection()
    conn.execute("INSERT INTO curso (id, cod_ramo, nombre) VALUES (1, 'INF-221', 'Calculo I')")
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("11111111-1", hash_password("test123"), "Juan", "Perez"),
    )
    conn.execute("INSERT INTO inscripcion (rut, curso_id, seccion) VALUES ('11111111-1', 1, 'SEC1')")
    conn.execute(
        "INSERT INTO clase (id, room_id, curso_id, seccion, rut_emisor, fecha_inicio) "
        "VALUES (1, 'INF-221-SEC1', 1, 'SEC1', '11111111-1', '2026-07-23T10:00:00')"
    )
    conn.execute(
        "INSERT INTO evento_clase (clase_id, timestamp_ms, texto, estable, senas_json) "
        "VALUES (1, 0, 'hola', 1, '[]')"
    )
    conn.execute(
        "INSERT INTO evento_clase (clase_id, timestamp_ms, texto, estable, senas_json) "
        "VALUES (1, 2000, 'derivada', 1, '[{\"lema\": \"derivado\"}]')"
    )
    conn.commit()

    with TestClient(app) as c:
        yield c


def test_historial_lista(client):
    resp = client.get("/api/historial?rut=11111111-1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["curso_nombre"] == "Calculo I"


def test_historial_detalle(client):
    resp = client.get("/api/historial/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["clase"]["id"] == 1
    assert len(data["eventos"]) == 2
    assert data["eventos"][0]["texto"] == "hola"


def test_historial_no_encontrado(client):
    resp = client.get("/api/historial/999")
    assert resp.status_code == 404
