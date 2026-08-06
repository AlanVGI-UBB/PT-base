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
    conn.commit()

    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_valido(client):
    resp = client.post("/api/auth/login", json={"rut": "11111111-1", "password": "test123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["rut"] == "11111111-1"


def test_login_invalido(client):
    resp = client.post("/api/auth/login", json={"rut": "11111111-1", "password": "mala"})
    assert resp.status_code == 401


def test_usuario_me(client):
    token = crear_token("11111111-1")
    resp = client.get("/api/auth/usuario/me", headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["rut"] == "11111111-1"
    assert data["nombre"] == "Juan"
    assert len(data["inscripciones"]) == 1


def test_cursos_con_token(client):
    token = crear_token("11111111-1")
    resp = client.get("/api/cursos", headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["cod_ramo"] == "INF-221"


def test_cursos_sin_token(client):
    resp = client.get("/api/cursos")
    assert resp.status_code == 401


def test_usuario_me_sin_token(client):
    resp = client.get("/api/auth/usuario/me")
    assert resp.status_code == 401


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
