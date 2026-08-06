import json

import pytest
from fastapi.testclient import TestClient

from app.core.auth import crear_token, hash_password
from app.core.db import get_connection, init_schema
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("ASR_PROVIDER", "stub")
    monkeypatch.setenv("STUB_INTERVAL_MS", "200")
    monkeypatch.setenv("SALA_TIMEOUT_MS", "100")

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
        "INSERT INTO termino (curso_id, lema, texto_visible, video_url, n_palabras) "
        "VALUES (1, 'derivado', 'derivada', '/v/derivada.mp4', 1)"
    )
    conn.commit()

    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_sala_estado_sin_sala(client):
    token = crear_token("11111111-1")
    resp = client.get("/api/salas/INF-221-SEC1/estado", headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["activa"] is False


def test_sala_estado_sin_token(client):
    resp = client.get("/api/salas/INF-221-SEC1/estado")
    assert resp.status_code == 401


def test_listener_sin_sala(client):
    token = crear_token("11111111-1")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=listener&token={token}") as ws:
        data = ws.receive_json()
        assert data["type"] == "error"


def test_fanout_y_finalizar(client):
    token = crear_token("11111111-1")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}") as em:
        with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=listener&token={token}") as lis:
            data = lis.receive_json()
            assert data["type"] == "segmento"
            em.send_text(json.dumps({"action": "finalizar", "titulo": "Clase de prueba"}))
            fin = lis.receive_json()
            assert fin["type"] == "clase_finalizada"
            assert fin["clase_id"] == 1

    conn = get_connection()
    row = conn.execute(
        "SELECT titulo, duracion_ms FROM clase WHERE id = 1"
    ).fetchone()
    assert row is not None
    assert row["titulo"] == "Clase de prueba"
    assert row["duracion_ms"] >= 0


def test_emisor_desconectado_guarda_parcial(client):
    token = crear_token("11111111-1")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}") as em:
        with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=listener&token={token}") as lis:
            assert lis.receive_json()["type"] == "segmento"
            em.close()
            aviso = lis.receive_json()
            assert aviso["type"] == "emisor_desconectado"
            fin = lis.receive_json()
            assert fin["type"] == "clase_finalizada"

    conn = get_connection()
    row = conn.execute(
        "SELECT titulo FROM clase WHERE room_id = 'INF-221-SEC1'"
    ).fetchone()
    assert row is not None
    assert row["titulo"] is None


def test_segundo_emisor_rechazado(client):
    token = crear_token("11111111-1")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}"):
        with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}") as em2:
            data = em2.receive_json()
            assert data["type"] == "error"
