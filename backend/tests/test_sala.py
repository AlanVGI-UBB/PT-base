import json
import logging
import time

import pytest
from fastapi.testclient import TestClient

from app.asr.base import ResultadoASR
from app.core.auth import crear_token, hash_password
from app.core.db import get_connection, init_schema
from app.main import app

TEST_JWT_SECRET = "test-secret-seguro-de-al-menos-32-bytes-009"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
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
    conn.execute("INSERT INTO curso (id, cod_ramo, nombre) VALUES (2, 'MAT-101', 'Álgebra Lineal')")
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("12345678-5", hash_password("test123"), "Juan", "Perez"),
    )
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("9876543-3", hash_password("test123"), "Maria", "Gonzalez"),
    )
    conn.execute(
        "INSERT INTO usuario (rut, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)",
        ("11111111-1", hash_password("test123"), "Pedro", "Soto"),
    )
    conn.execute(
        "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) "
        "VALUES ('12345678-5', 1, 'SEC1', 1)"
    )
    conn.execute(
        "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) "
        "VALUES ('9876543-3', 1, 'SEC1', 0)"
    )
    conn.execute(
        "INSERT INTO inscripcion (rut, curso_id, seccion, puede_capturar) "
        "VALUES ('11111111-1', 2, '3', 0)"
    )
    conn.execute(
        "INSERT INTO termino (curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
        "VALUES (1, 'lista enlazada', '[\"lista enlazada\", \"listas enlazadas\"]', '[]', 'lista_enlazada.mp4', 'ensayo')"
    )
    conn.execute(
        "INSERT INTO termino (curso_id, texto_visible, formas_json, bloqueos_json, video_url, estado) "
        "VALUES (1, 'memoria', '[\"memoria\"]', '[\"de memoria\"]', 'memoria.mp4', 'ensayo')"
    )
    conn.commit()

    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_sala_estado_sin_sala_incluye_permiso_y_omite_rut_emisor(client):
    token_em = crear_token("12345678-5")
    resp = client.get("/api/salas/INF-221-SEC1/estado", headers=auth(token_em))
    assert resp.status_code == 200
    data = resp.json()
    assert data["activa"] is False
    assert data["puede_capturar"] is True
    assert data["curso_id"] == 1
    assert "rut_emisor" not in data

    token_oy = crear_token("9876543-3")
    resp_oy = client.get("/api/salas/INF-221-SEC1/estado", headers=auth(token_oy))
    assert resp_oy.status_code == 200
    assert resp_oy.json()["puede_capturar"] is False


def test_sala_estado_sin_inscripcion_403(client):
    token_otro = crear_token("11111111-1")
    resp = client.get("/api/salas/INF-221-SEC1/estado", headers=auth(token_otro))
    assert resp.status_code == 403

    resp_inexistente = client.get("/api/salas/INF-221-999/estado", headers=auth(token_otro))
    assert resp_inexistente.status_code == 403


def test_sala_estado_sin_token(client):
    resp = client.get("/api/salas/INF-221-SEC1/estado")
    assert resp.status_code == 401


def test_listener_sin_sala(client):
    token = crear_token("9876543-3")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=listener&token={token}") as ws:
        data = ws.receive_json()
        assert data["type"] == "error"


def test_acceso_rechazado_no_inscrito_seccion_inexistente_y_sin_permiso(client):
    token_em = crear_token("12345678-5")
    token_oy = crear_token("9876543-3")
    token_otro = crear_token("11111111-1")

    # Emisor sin permiso de captura -> rechazado sin crear clase
    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token_oy}&condiciones=1"
    ) as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "permiso de captura" in err["mensaje"].lower()

    # Emisor sin confirmar condiciones -> rechazado sin crear clase
    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token_em}"
    ) as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "condiciones" in err["mensaje"].lower()

    # Usuario no inscrito intenta abrir sección inexistente -> rechazado sin crear clase
    with client.websocket_connect(
        f"/ws/sala/INF-221-999?rol=emitter&token={token_otro}&condiciones=1"
    ) as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["mensaje"] == "No tienes acceso a esta sala"

    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) FROM clase").fetchone()[0] == 0

    # Con una sala activa, oyente de otro curso es rechazado (CA01 completo)
    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token_em}&condiciones=1"
    ) as em:
        with client.websocket_connect(
            f"/ws/sala/INF-221-SEC1?rol=listener&token={token_otro}"
        ) as lis_otro:
            err = lis_otro.receive_json()
            assert err["type"] == "error"
            assert err["mensaje"] == "No tienes acceso a esta sala"

        assert client.get("/api/cursos/1/glosario", headers=auth(token_otro)).status_code == 403
        assert client.get("/api/cursos/1/senas/1/video", headers=auth(token_otro)).status_code == 403

        em.send_text(json.dumps({"action": "finalizar"}))


def test_fanout_y_finalizar(client):
    token_em = crear_token("12345678-5")
    token_oy = crear_token("9876543-3")
    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token_em}&condiciones=1"
    ) as em:
        with client.websocket_connect(
            f"/ws/sala/INF-221-SEC1?rol=listener&token={token_oy}"
        ) as lis:
            estado = lis.receive_json()
            assert estado["type"] == "estado_sesion"
            assert estado["estado"] == "activa"

            data = lis.receive_json()
            assert data["type"] == "segmento"
            em.send_text(json.dumps({"action": "finalizar", "titulo": "Clase de prueba"}))
            fin = lis.receive_json()
            assert fin["type"] == "clase_finalizada"
            assert fin["clase_id"] == 1

    conn = get_connection()
    row = conn.execute(
        "SELECT titulo, duracion_ms, cierre, condiciones_confirmadas FROM clase WHERE id = 1"
    ).fetchone()
    assert row is not None
    assert row["titulo"] == "Clase de prueba"
    assert row["duracion_ms"] >= 0
    assert row["cierre"] == "explicito"
    assert row["condiciones_confirmadas"] == 1


def test_emisor_desconectado_guarda_parcial_con_timeout_y_evento(client):
    token_em = crear_token("12345678-5")
    token_oy = crear_token("9876543-3")
    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token_em}&condiciones=1"
    ) as em:
        with client.websocket_connect(
            f"/ws/sala/INF-221-SEC1?rol=listener&token={token_oy}"
        ) as lis:
            assert lis.receive_json()["type"] == "estado_sesion"
            assert lis.receive_json()["type"] == "segmento"
            em.close()
            aviso = lis.receive_json()
            assert aviso["type"] == "emisor_desconectado"
            fin = lis.receive_json()
            assert fin["type"] == "clase_finalizada"

    conn = get_connection()
    row = conn.execute(
        "SELECT titulo, cierre FROM clase WHERE room_id = 'INF-221-SEC1'"
    ).fetchone()
    assert row is not None
    assert row["titulo"] is None
    assert row["cierre"] == "timeout"

    tipos = [
        r["tipo"]
        for r in conn.execute("SELECT tipo FROM evento_clase ORDER BY id").fetchall()
    ]
    assert "desconexion" in tipos


def test_segundo_emisor_rechazado(client):
    token = crear_token("12345678-5")
    with client.websocket_connect(f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}&condiciones=1"):
        with client.websocket_connect(
            f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}&condiciones=1"
        ) as em2:
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


def test_pausa_difunde_descarta_tramas_envia_estado_al_unirse_y_registra_discontinuidades(
    client, monkeypatch
):
    class _FakeProviderPausa:
        def __init__(self):
            self.tramas: list[bytes] = []

        async def transcribe_stream(self, audio_iter, lang="es", contexto=None):
            del lang, contexto
            seg_id = 0
            async for trama in audio_iter:
                self.tramas.append(trama)
                if len(trama) == 0:
                    # Señal de vaciado al pausar
                    seg_id += 1
                    yield ResultadoASR(
                        segmento_id=seg_id,
                        texto="segmento cerrado al pausar",
                        estable=True,
                        inicio_ms=0,
                        fin_ms=500,
                    )
                elif trama == b"\x03\x00" * 1600:
                    seg_id += 1
                    yield ResultadoASR(
                        segmento_id=seg_id,
                        texto="texto tras reanudar",
                        estable=True,
                        inicio_ms=1000,
                        fin_ms=1500,
                    )

    fake = _FakeProviderPausa()
    monkeypatch.setattr("app.main.get_asr_provider", lambda: fake)

    token_em = crear_token("12345678-5")
    token_oy = crear_token("9876543-3")

    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token_em}&condiciones=1"
    ) as em:
        with client.websocket_connect(
            f"/ws/sala/INF-221-SEC1?rol=listener&token={token_oy}"
        ) as lis1:
            assert lis1.receive_json()["estado"] == "activa"

            # Audio normal antes de pausar
            em.send_bytes(b"\x01\x00" * 1600)
            # Pausar: debe difundir estado pausada y cerrar segmento abierto
            em.send_text(json.dumps({"action": "pausar"}))

            recibidos_pausa = [lis1.receive_json(), lis1.receive_json()]
            tipos_recibidos = {m["type"] for m in recibidos_pausa}
            assert tipos_recibidos == {"estado_sesion", "segmento"}
            ev_estado = next(m for m in recibidos_pausa if m["type"] == "estado_sesion")
            assert ev_estado["estado"] == "pausada"
            assert isinstance(ev_estado["timestamp_ms"], int)

            # Audio enviado en pausa debe descartarse
            em.send_bytes(b"\x02\x00" * 1600)

            # Un segundo oyente que entra durante la pausa recibe estado pausada de inmediato
            with client.websocket_connect(
                f"/ws/sala/INF-221-SEC1?rol=listener&token={token_oy}"
            ) as lis2:
                estado_lis2 = lis2.receive_json()
                assert estado_lis2["type"] == "estado_sesion"
                assert estado_lis2["estado"] == "pausada"

                # Reanudar
                em.send_text(json.dumps({"action": "reanudar"}))
                assert lis1.receive_json()["estado"] == "activa"
                assert lis2.receive_json()["estado"] == "activa"

                # Audio tras reanudar vuelve a procesarse
                em.send_bytes(b"\x03\x00" * 1600)
                seg1 = lis1.receive_json()
                seg2 = lis2.receive_json()
                assert seg1["type"] == "segmento"
                assert seg1["texto"] == "texto tras reanudar"
                assert seg2["texto"] == "texto tras reanudar"

                em.send_text(json.dumps({"action": "finalizar"}))
                assert lis1.receive_json()["type"] == "clase_finalizada"
                assert lis2.receive_json()["type"] == "clase_finalizada"

    # La trama enviada durante pausa (b"\x02\x00" * 1600) nunca llegó al proveedor ASR
    assert b"\x02\x00" * 1600 not in fake.tramas
    assert fake.tramas == [b"\x01\x00" * 1600, b"", b"\x03\x00" * 1600]

    conn = get_connection()
    tipos = [
        r["tipo"]
        for r in conn.execute("SELECT tipo FROM evento_clase WHERE clase_id = 1 ORDER BY id").fetchall()
    ]
    assert "pausa" in tipos
    assert "reanudacion" in tipos
    assert tipos.count("segmento") == 2


def test_handler_provisional_no_persiste_ni_matchea_y_vaciado_final(client, monkeypatch):
    fake = _FakeProviderProvisionalYFinal()
    monkeypatch.setattr("app.main.get_asr_provider", lambda: fake)

    token_em = crear_token("12345678-5")
    token_oy = crear_token("9876543-3")
    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token_em}&condiciones=1"
    ) as em:
        with client.websocket_connect(
            f"/ws/sala/INF-221-SEC1?rol=listener&token={token_oy}"
        ) as lis:
            assert lis.receive_json()["type"] == "estado_sesion"
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
            assert ev_fin["senas"][0]["video_url"] == "/api/cursos/1/senas/1/video"

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
        "SELECT texto, estable, abstenciones_json, tipo FROM evento_clase WHERE clase_id = 1 ORDER BY id"
    ).fetchall()
    assert len(eventos) == 2
    assert eventos[0]["texto"] == "hoy vemos las listas enlazadas"
    assert eventos[0]["estable"] == 1
    assert eventos[0]["tipo"] == "segmento"
    assert json.loads(eventos[0]["abstenciones_json"]) == []
    assert eventos[1]["texto"] == "no estudien de memoria"
    assert eventos[1]["estable"] == 1
    assert eventos[1]["tipo"] == "segmento"
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

    token = crear_token("12345678-5")
    with caplog.at_level(logging.WARNING, logger="puente_lsch"):
        with client.websocket_connect(
            f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}&condiciones=1"
        ) as em:
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

    token = crear_token("12345678-5")
    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token}&condiciones=1"
    ) as em:
        em.send_text(json.dumps({"action": "finalizar"}))

    assert fake.contexto_recibido is None


def test_metricas_desactivadas_no_escribe_metrica_segmento(client, monkeypatch):
    monkeypatch.setenv("METRICAS", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    token_em = crear_token("12345678-5")
    token_oy = crear_token("9876543-3")
    with client.websocket_connect(
        f"/ws/sala/INF-221-SEC1?rol=emitter&token={token_em}&condiciones=1"
    ) as em:
        with client.websocket_connect(
            f"/ws/sala/INF-221-SEC1?rol=listener&token={token_oy}"
        ) as lis:
            assert lis.receive_json()["type"] == "estado_sesion"
            ev = lis.receive_json()
            assert ev["type"] == "segmento"
            assert isinstance(ev["servidor_ms"], int)
            em.send_text(json.dumps({"action": "finalizar"}))
            assert lis.receive_json()["type"] == "clase_finalizada"

    conn = get_connection()
    rows = conn.execute("SELECT * FROM metrica_segmento").fetchall()
    assert rows == []


def test_ws_echo_eliminado(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/echo"):
            pass
