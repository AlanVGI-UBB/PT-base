import pytest
from fastapi.testclient import TestClient

from app.core.auth import crear_token, hash_password
from app.core.db import get_connection, init_schema
from app.main import app

TEST_JWT_SECRET = "test-secret-seguro-de-al-menos-32-bytes-009"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)

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
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("22222222-2", hash_password("otro123"), "Ana", "Lopez"),
    )
    conn.execute(
        "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) "
        "VALUES ('11111111-1', 1, 'SEC1', 1)"
    )
    conn.execute(
        "INSERT INTO clase (id, room_id, curso_id, seccion, rut_emisor, fecha_inicio, cierre, condiciones_confirmadas) "
        "VALUES (1, 'INF-221-SEC1', 1, 'SEC1', '11111111-1', '2026-07-23T10:00:00', 'timeout', 1)"
    )
    conn.execute(
        "INSERT INTO evento_clase (clase_id, timestamp_ms, texto, estable, senas_json, tipo) "
        "VALUES (1, 0, NULL, 1, '[]', 'pausa')"
    )
    conn.execute(
        "INSERT INTO evento_clase (clase_id, timestamp_ms, texto, estable, senas_json, tipo) "
        "VALUES (1, 500, 'hola', 1, '[]', 'segmento')"
    )
    conn.execute(
        "INSERT INTO evento_clase (clase_id, timestamp_ms, texto, estable, senas_json, tipo) "
        "VALUES (1, 1500, 'no debe contarse', 1, '[]', 'reanudacion')"
    )
    conn.execute(
        "INSERT INTO evento_clase (clase_id, timestamp_ms, texto, estable, senas_json, tipo) "
        "VALUES (1, 2000, 'lista enlazada', 1, "
        "'[{\"termino_id\": 1, \"texto_visible\": \"lista enlazada\", \"estado\": \"ensayo\", \"texto_detectado\": \"lista enlazada\"}]', "
        "'segmento')"
    )
    conn.commit()

    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_historial_lista_incluye_cierre_y_filtra_discontinuidades(client):
    token = crear_token("11111111-1")
    resp = client.get("/api/historial", headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["curso_nombre"] == "Calculo I"
    assert data[0]["cierre"] == "timeout"
    assert data[0]["palabras"] == 3  # 'hola' (1) + 'lista enlazada' (2)
    assert data[0]["preview"] == "hola"


def test_historial_sin_token(client):
    resp = client.get("/api/historial")
    assert resp.status_code == 401


def test_historial_detalle_incluye_cierre_y_tipos(client):
    token = crear_token("11111111-1")
    resp = client.get("/api/historial/1", headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["clase"]["id"] == 1
    assert data["clase"]["cierre"] == "timeout"
    assert [e["tipo"] for e in data["eventos"]] == ["pausa", "segmento", "reanudacion", "segmento"]
    assert data["eventos"][1]["texto"] == "hola"


def test_historial_no_encontrado(client):
    token = crear_token("11111111-1")
    resp = client.get("/api/historial/999", headers=auth(token))
    assert resp.status_code == 404


def test_historial_detalle_sin_inscripcion(client):
    token = crear_token("22222222-2")
    resp = client.get("/api/historial/1", headers=auth(token))
    assert resp.status_code == 403
