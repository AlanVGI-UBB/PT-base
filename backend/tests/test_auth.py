import logging
from pathlib import Path
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.auth import crear_token, hash_password, verificar_password
from app.core.config import Settings, get_settings
from app.core.db import get_connection, init_schema
from app.main import app

TEST_JWT_SECRET = "test-secret-seguro-de-al-menos-32-bytes-009"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("ASR_PROVIDER", "stub")

    get_settings.cache_clear()
    from app.core import db as db_mod
    db_mod._conn = None

    init_schema()

    conn = get_connection()
    conn.execute("INSERT INTO curso (id, cod_ramo, nombre) VALUES (1, 'INF-221', 'Estructuras de Datos')")
    conn.execute("INSERT INTO curso (id, cod_ramo, nombre) VALUES (2, 'MAT-101', 'Álgebra Lineal')")
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("12345678-5", hash_password("test123"), "Juan", "Pérez"),
    )
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("9876543-3", hash_password("test123"), "María", "González"),
    )
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("11111111-1", hash_password("test123"), "Pedro", "Soto"),
    )
    conn.execute(
        "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) "
        "VALUES ('12345678-5', 1, '1', 1)"
    )
    conn.execute(
        "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) "
        "VALUES ('9876543-3', 1, '1', 0)"
    )
    conn.execute(
        "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) "
        "VALUES ('11111111-1', 2, '3', 0)"
    )
    conn.execute(
        "INSERT INTO termino (id, curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
        "VALUES (1, 1, 'arreglo', '[\"arreglo\"]', '[]', 'arreglo.mp4', 'ensayo')"
    )
    conn.execute(
        "INSERT INTO termino (id, curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
        "VALUES (2, 1, 'obsoleto', '[\"obsoleto\"]', '[]', 'arreglo.mp4', 'retirado')"
    )
    conn.commit()

    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_scrypt_hash_distinto_y_verificacion():
    h1 = hash_password("test123")
    h2 = hash_password("test123")
    assert h1 != h2
    assert h1.startswith("scrypt$16384$8$1$")
    assert verificar_password("test123", h1) is True
    assert verificar_password("test123", h2) is True
    assert verificar_password("otra", h1) is False
    assert verificar_password("test123", "sha256_legacy_invalido") is False


def test_jwt_secret_vacio_genera_aleatorio_y_advierte(monkeypatch, caplog):
    monkeypatch.setenv("JWT_SECRET", "")
    get_settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="puente_lsch"):
            s = get_settings()
        assert len(s.JWT_SECRET) >= 32
        assert any("JWT_SECRET está vacío" in r.message for r in caplog.records)
    finally:
        get_settings.cache_clear()


def test_token_vigencia_jornada_clases(client):
    token = crear_token("12345678-5")
    payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
    vigencia_seg = payload["exp"] - int(time.time())
    assert vigencia_seg > 90 * 60
    assert vigencia_seg <= 480 * 60 + 5


def test_env_example_sincronizado_con_settings():
    env_example = Path(__file__).resolve().parent.parent / ".env.example"
    claves = {
        linea.split("=", 1)[0].strip()
        for linea in env_example.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    }
    assert claves == set(Settings.model_fields.keys())


def test_login_valido(client):
    resp = client.post("/api/auth/login", json={"rut": "12345678-5", "password": "test123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["rut"] == "12345678-5"


def test_login_invalido(client):
    resp = client.post("/api/auth/login", json={"rut": "12345678-5", "password": "mala"})
    assert resp.status_code == 401


def test_usuario_me(client):
    token = crear_token("12345678-5")
    resp = client.get("/api/auth/usuario/me", headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["rut"] == "12345678-5"
    assert data["nombre"] == "Juan"
    assert len(data["inscripciones"]) == 1
    assert data["inscripciones"][0]["puede_capturar"] is True


def test_cursos_con_token_incluye_puede_capturar(client):
    token_emisor = crear_token("12345678-5")
    resp = client.get("/api/cursos", headers=auth(token_emisor))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["cod_ramo"] == "INF-221"
    assert data[0]["puede_capturar"] is True

    token_oyente = crear_token("9876543-3")
    resp_oy = client.get("/api/cursos", headers=auth(token_oyente))
    assert resp_oy.status_code == 200
    assert resp_oy.json()[0]["puede_capturar"] is False


def test_cursos_sin_token(client):
    resp = client.get("/api/cursos")
    assert resp.status_code == 401


def test_usuario_me_sin_token(client):
    resp = client.get("/api/auth/usuario/me")
    assert resp.status_code == 401


def test_glosario_exige_inscripcion_y_devuelve_ruta_protegida(client):
    token_inscrito = crear_token("9876543-3")
    resp_ok = client.get("/api/cursos/1/glosario", headers=auth(token_inscrito))
    assert resp_ok.status_code == 200
    items = resp_ok.json()
    assert items[0]["video_url"] == "/api/cursos/1/senas/1/video"

    token_otro_curso = crear_token("11111111-1")
    resp_403 = client.get("/api/cursos/1/glosario", headers=auth(token_otro_curso))
    assert resp_403.status_code == 403


def test_clip_protegido_401_403_404_y_200(client):
    # Sin token -> 401
    resp_401 = client.get("/api/cursos/1/senas/1/video")
    assert resp_401.status_code == 401

    # Usuario de otro curso -> 403
    token_otro = crear_token("11111111-1")
    resp_403 = client.get("/api/cursos/1/senas/1/video", headers=auth(token_otro))
    assert resp_403.status_code == 403

    # Usuario inscrito, término retirado -> 404
    token_inscrito = crear_token("9876543-3")
    resp_retirado = client.get("/api/cursos/1/senas/2/video", headers=auth(token_inscrito))
    assert resp_retirado.status_code == 404

    # Usuario inscrito, término activo -> 200 video/mp4
    resp_ok = client.get("/api/cursos/1/senas/1/video", headers=auth(token_inscrito))
    assert resp_ok.status_code == 200
    assert resp_ok.headers["content-type"].startswith("video/mp4")
    assert len(resp_ok.content) > 1024

    # Montaje estático antiguo eliminado -> 404
    resp_estatico = client.get("/data/videos_senas/arreglo.mp4")
    assert resp_estatico.status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
