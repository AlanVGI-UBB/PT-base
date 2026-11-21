import json
import logging
import time

import pytest
from fastapi.testclient import TestClient

from app.asr.base import ResultadoASR
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

    from app.salas.manager import RoomManager
    RoomManager.limpiar()

    from app.glossary.indice import limpiar_cache_indices
    limpiar_cache_indices()

    init_schema()

    conn = get_connection()
    conn.execute("INSERT INTO curso (id, cod_ramo, nombre) VALUES (1, 'INF-221', 'Estructuras de Datos')")
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("11111111-1", hash_password("test123"), "Juan", "Perez"),
    )
    conn.execute("INSERT INTO inscripcion (rut, curso_id, seccion) VALUES ('11111111-1', 1, 'SEC1')")
    conn.execute(
        "INSERT INTO termino (curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
        "VALUES (1, 'lista enlazada', '[\"lista enlazada\", \"listas enlazadas\"]', '[]', '/v/lista.mp4', 'ensayo')"
    )
    conn.execute(
        "INSERT INTO termino (curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
        "VALUES (1, 'memoria', '[\"memoria\"]', '[\"de memoria\"]', '/v/memoria.mp4', 'ensayo')"
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


class _FakeProviderProvisionalYFinal:
    def __init__(self):
        self.contexto_recibido = None
        self.tramas_recibidas: list[bytes] = []

    async def transcribe_stream(self, audio_iter, lang="es", contexto=None):
        del lang
        self.contexto_recibido = contexto
        async for trama in audio_iter:
            self.tramas_recibidas.append(trama)
            if len(self.tramas_recibidas) == 1:
                yield ResultadoASR(
                    segmento_id=7,
                    texto="hoy vemos lista",
                    estable=False,
                    inicio_ms=0,
                    fin_ms=1000,
                )
            elif len(self.tramas_recibidas) == 2:
                yield ResultadoASR(
                    segmento_id=7,
                    texto="hoy vemos las listas enlazadas",
                    estable=True,
                    inicio_ms=0,
                    fin_ms=1600,
                )
        # Vaciado al finalizar (R13): emite un último segmento con bloqueo al cerrar audio_iter
        yield ResultadoASR(
            segmento_id=8,
            texto="no estudien de memoria",
            estable=True,
            inicio_ms=1600,
            fin_ms=2200,
        )


def test_handler_provisional_no_persiste_ni_matchea_y_vaciado_final(client, monkeypatch):
    fake = _FakeProviderProvisionalYFinal()
    monkeypatch.setattr("app.main.get_asr_provider", lambda: fake)

    token = crear_token("11111111-1")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}") as em:
        with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=listener&token={token}") as lis:
            time.sleep(0.05)
            em.send_bytes(b"\x01\x00" * 1600)
            ev_prov = lis.receive_json()
            assert ev_prov["type"] == "segmento"
            assert ev_prov["segment_id"] == 7
            assert ev_prov["final"] is False
            assert ev_prov["senas"] == []

            em.send_bytes(b"\x01\x00" * 1600)
            ev_fin = lis.receive_json()
            assert ev_fin["type"] == "segmento"
            assert ev_fin["segment_id"] == 7
            assert ev_fin["final"] is True
            assert isinstance(ev_fin["servidor_ms"], int)
            assert len(ev_fin["senas"]) == 1
            assert ev_fin["senas"][0]["texto_visible"] == "lista enlazada"
            assert ev_fin["senas"][0]["texto_detectado"] == "listas enlazadas"
            assert ev_fin["senas"][0]["estado"] == "ensayo"

            em.send_text(json.dumps({"action": "finalizar", "titulo": "Con vaciado"}))

            ev_flush = lis.receive_json()
            assert ev_flush["type"] == "segmento"
            assert ev_flush["segment_id"] == 8
            assert ev_flush["final"] is True
            assert ev_flush["texto"] == "no estudien de memoria"
            assert ev_flush["senas"] == []
            assert "abstenciones" not in ev_flush

            fin = lis.receive_json()
            assert fin["type"] == "clase_finalizada"

    assert fake.contexto_recibido == ["lista enlazada", "memoria"]
    assert len(fake.tramas_recibidas) == 2

    conn = get_connection()
    eventos = conn.execute(
        "SELECT texto, estable, abstenciones_json FROM evento_clase WHERE clase_id = 1 ORDER BY id"
    ).fetchall()
    assert len(eventos) == 2
    assert eventos[0]["texto"] == "hoy vemos las listas enlazadas"
    assert eventos[0]["estable"] == 1
    assert json.loads(eventos[0]["abstenciones_json"]) == []
    assert eventos[1]["texto"] == "no estudien de memoria"
    assert eventos[1]["estable"] == 1
    assert json.loads(eventos[1]["abstenciones_json"]) == [
        {"bloqueo": "de memoria", "texto_detectado": "de memoria"}
    ]

    metricas = conn.execute(
        "SELECT * FROM metrica_segmento WHERE clase_id = 1 ORDER BY id"
    ).fetchall()
    assert len(metricas) == 2
    assert metricas[0]["segmento_id"] == 7
    assert metricas[0]["audio_inicio_ms"] == 0
    assert metricas[0]["audio_fin_ms"] == 1600
    assert metricas[0]["receptores"] == 1
    assert metricas[0]["emitido_ms"] >= metricas[0]["llegada_fin_ms"]
    assert metricas[0]["nlp_ms"] >= 0
    assert metricas[1]["segmento_id"] == 8


def test_rechazo_tramas_fuera_de_contrato(client, monkeypatch, caplog):
    monkeypatch.setenv("ASR_MAX_TRAMA_BYTES", "6400")
    from app.core.config import get_settings

    get_settings.cache_clear()
    fake = _FakeProviderProvisionalYFinal()
    monkeypatch.setattr("app.main.get_asr_provider", lambda: fake)

    token = crear_token("11111111-1")
    with caplog.at_level(logging.WARNING, logger="puente_lsch"):
        with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}") as em:
            em.send_bytes(b"\x00\x01\x02")  # longitud impar
            em.send_bytes(b"\x00" * 7000)  # excede ASR_MAX_TRAMA_BYTES
            em.send_bytes(b"\x02\x00" * 1600)  # válida (3200 bytes)
            time.sleep(0.05)
            em.send_text(json.dumps({"action": "finalizar"}))

    assert fake.tramas_recibidas == [b"\x02\x00" * 1600]
    warnings_trama = [r for r in caplog.records if "trama de audio inválida" in r.message]
    assert len(warnings_trama) == 1


def test_prompt_glosario_desactivado_no_envia_contexto(client, monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    fake = _FakeProviderProvisionalYFinal()
    monkeypatch.setattr("app.main.get_asr_provider", lambda: fake)

    token = crear_token("11111111-1")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}") as em:
        em.send_text(json.dumps({"action": "finalizar"}))

    assert fake.contexto_recibido is None


def test_metricas_desactivadas_no_escribe_metrica_segmento(client, monkeypatch):
    monkeypatch.setenv("METRICAS", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    token = crear_token("11111111-1")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}") as em:
        with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=listener&token={token}") as lis:
            ev = lis.receive_json()
            assert ev["type"] == "segmento"
            assert isinstance(ev["servidor_ms"], int)
            em.send_text(json.dumps({"action": "finalizar"}))
            assert lis.receive_json()["type"] == "clase_finalizada"

    conn = get_connection()
    rows = conn.execute("SELECT * FROM metrica_segmento").fetchall()
    assert rows == []
