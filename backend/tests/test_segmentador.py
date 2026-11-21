import asyncio
import logging
import math
import struct
import time
from types import SimpleNamespace

import numpy as np
import pytest

from app.asr.base import AsrConfigError, get_asr_provider
from app.asr.segmentador import SAMPLE_RATE, Segmentador
from app.asr.whisper_local import FasterWhisperProvider, _cargar_whisper_model, _limpiar_cache_modelo


def _trama_silencio(duracion_ms: int = 100) -> bytes:
    n_muestras = SAMPLE_RATE * duracion_ms // 1000
    return b"\x00\x00" * n_muestras


def _trama_ruido_bajo(duracion_ms: int = 100, amplitud: float = 0.002) -> bytes:
    n_muestras = SAMPLE_RATE * duracion_ms // 1000
    amp = int(32767 * amplitud)
    muestras = [int(amp * math.sin(2 * math.pi * 220 * i / SAMPLE_RATE)) for i in range(n_muestras)]
    return struct.pack(f"<{n_muestras}h", *muestras)


def _trama_voz(duracion_ms: int = 100, amplitud: float = 0.25) -> bytes:
    n_muestras = SAMPLE_RATE * duracion_ms // 1000
    amp = int(32767 * amplitud)
    muestras = [int(amp * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)) for i in range(n_muestras)]
    return struct.pack(f"<{n_muestras}h", *muestras)


def test_segmentador_silencio_prolongado_no_emite():
    seg = Segmentador(silencio_ms=600, max_segmento_ms=15000, parcial_ms=1000)
    ventanas = []
    # 30 segundos de silencio y ruido bajo no deben emitir ventanas
    for i in range(300):
        trama = _trama_silencio(100) if i % 2 == 0 else _trama_ruido_bajo(100)
        ventanas.extend(seg.alimentar(trama))
    assert ventanas == []
    assert seg.cerrar() is None


def test_segmentador_provisional_y_final_mismo_id():
    seg = Segmentador(silencio_ms=600, max_segmento_ms=15000, parcial_ms=1000, pre_roll_ms=0)
    ventanas = []
    # 1.2 s de voz -> debe emitir al menos una provisional
    for _ in range(12):
        ventanas.extend(seg.alimentar(_trama_voz(100)))
    assert len(ventanas) >= 1
    assert all(not v.final for v in ventanas)
    seg_id = ventanas[0].segmento_id

    # 600 ms de silencio -> debe emitir final con el mismo segmento_id
    finales = []
    for _ in range(6):
        finales.extend(seg.alimentar(_trama_silencio(100)))
    assert len(finales) == 1
    assert finales[0].final is True
    assert finales[0].segmento_id == seg_id
    assert finales[0].inicio_ms == 0
    assert finales[0].fin_ms >= 1700
    assert finales[0].pcm.dtype == np.float32


def test_segmentador_corte_por_duracion_maxima():
    seg = Segmentador(silencio_ms=600, max_segmento_ms=1500, parcial_ms=600, pre_roll_ms=0)
    ventanas = []
    for _ in range(20):
        ventanas.extend(seg.alimentar(_trama_voz(100)))
    finales = [v for v in ventanas if v.final]
    assert len(finales) == 1
    assert finales[0].segmento_id == 1
    # El audio posterior abre un segundo segmento
    ultimo = seg.cerrar()
    assert ultimo is not None
    assert ultimo.final is True
    assert ultimo.segmento_id == 2


def test_segmentador_cerrar_vacia_segmento_abierto():
    seg = Segmentador(silencio_ms=600, max_segmento_ms=15000, parcial_ms=1000, pre_roll_ms=120)
    for _ in range(3):
        seg.alimentar(_trama_silencio(100))
    for _ in range(4):
        seg.alimentar(_trama_voz(100))
    v = seg.cerrar()
    assert v is not None
    assert v.final is True
    assert v.segmento_id == 1
    assert v.fin_ms == 700
    assert seg.cerrar() is None


def test_segmentador_trama_impar_falla():
    seg = Segmentador()
    with pytest.raises(ValueError):
        seg.alimentar(b"\x00\x01\x02")


class _FakeModeloWhisper:
    def __init__(self, respuestas=None, delay_s: float = 0.0):
        self.respuestas = list(respuestas) if respuestas is not None else ["hola mundo"]
        self.delay_s = delay_s
        self.llamadas: list[dict] = []
        self.activas = 0
        self.max_activas = 0

    def transcribe(
        self,
        pcm,
        language="es",
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=None,
    ):
        self.activas += 1
        self.max_activas = max(self.max_activas, self.activas)
        try:
            if self.delay_s:
                time.sleep(self.delay_s)
            self.llamadas.append(
                {
                    "muestras": len(pcm),
                    "language": language,
                    "vad_filter": vad_filter,
                    "condition_on_previous_text": condition_on_previous_text,
                    "initial_prompt": initial_prompt,
                }
            )
            texto = self.respuestas.pop(0) if self.respuestas else "ok"
            segs = [SimpleNamespace(text=texto)] if texto else []
            return segs, SimpleNamespace(language=language)
        finally:
            self.activas -= 1


@pytest.mark.asyncio
async def test_whisper_provider_parametros_prompt_y_descarte_vacios(monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    fake = _FakeModeloWhisper(respuestas=["", "derivada parcial", "derivada final"])
    provider = FasterWhisperProvider(
        modelo=fake,
        silencio_ms=300,
        max_segmento_ms=5000,
        parcial_ms=400,
    )

    async def audio():
        for _ in range(9):
            yield _trama_voz(100)
            await asyncio.sleep(0.03)
        for _ in range(4):
            yield _trama_silencio(100)
            await asyncio.sleep(0.03)

    resultados = [
        r
        async for r in provider.transcribe_stream(
            audio(),
            lang="es-CL",
            contexto=["derivada", "integral"],
        )
    ]
    assert [r.texto for r in resultados] == ["derivada parcial", "derivada final"]
    assert resultados[0].estable is False
    assert resultados[1].estable is True
    assert resultados[0].segmento_id == resultados[1].segmento_id
    assert resultados[1].inicio_ms >= 0 and resultados[1].fin_ms > resultados[1].inicio_ms
    assert fake.llamadas[0]["language"] == "es"
    assert fake.llamadas[0]["vad_filter"] is True
    assert fake.llamadas[0]["condition_on_previous_text"] is False
    assert fake.llamadas[0]["initial_prompt"] == "derivada, integral."


@pytest.mark.asyncio
async def test_whisper_provider_prompt_desactivado(monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    fake = _FakeModeloWhisper(respuestas=["texto"])
    provider = FasterWhisperProvider(modelo=fake, silencio_ms=300, parcial_ms=1000)

    async def audio():
        for _ in range(4):
            yield _trama_voz(100)

    resultados = [
        r async for r in provider.transcribe_stream(audio(), contexto=["derivada"])
    ]
    assert len(resultados) == 1
    assert fake.llamadas[0]["initial_prompt"] is None


@pytest.mark.asyncio
async def test_whisper_provider_cierra_por_falta_de_tramas(monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    fake = _FakeModeloWhisper(respuestas=["frase por timeout"])
    provider = FasterWhisperProvider(modelo=fake, silencio_ms=120, parcial_ms=1000)

    async def audio():
        for _ in range(3):
            yield _trama_voz(100)
        # Deja de enviar tramas pero mantiene el stream abierto > silencio_ms
        await asyncio.sleep(0.25)

    resultados = [r async for r in provider.transcribe_stream(audio())]
    assert len(resultados) == 1
    assert resultados[0].estable is True
    assert resultados[0].texto == "frase por timeout"


@pytest.mark.asyncio
async def test_whisper_provider_omite_provisionales_si_hay_atraso(monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    # Primera inferencia lenta (0.35 s) hace que se acumulen > parcial_ms (200 ms)
    fake = _FakeModeloWhisper(
        respuestas=["primera", "segunda final"],
        delay_s=0.35,
    )
    provider = FasterWhisperProvider(modelo=fake, silencio_ms=300, parcial_ms=200)

    async def audio():
        # Primer bloque dispara una provisional tras ~210 ms
        for _ in range(3):
            yield _trama_voz(100)
            await asyncio.sleep(0.01)
        # Mientras corre la primera inferencia lenta, llegan 400 ms más de voz y luego silencio
        await asyncio.sleep(0.05)
        for _ in range(4):
            yield _trama_voz(100)
        for _ in range(4):
            yield _trama_silencio(100)

    resultados = [r async for r in provider.transcribe_stream(audio())]
    finales = [r for r in resultados if r.estable]
    provisionales = [r for r in resultados if not r.estable]
    assert len(finales) == 1
    assert len(provisionales) <= 1


@pytest.mark.asyncio
async def test_whisper_provider_concurrencia_exclusiva(monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    fake = _FakeModeloWhisper(respuestas=["sala a", "sala b"], delay_s=0.05)
    p1 = FasterWhisperProvider(modelo=fake, silencio_ms=200, parcial_ms=1000)
    p2 = FasterWhisperProvider(modelo=fake, silencio_ms=200, parcial_ms=1000)

    async def audio():
        for _ in range(3):
            yield _trama_voz(100)

    async def consumir(p):
        return [r async for r in p.transcribe_stream(audio())]

    r1, r2 = await asyncio.gather(consumir(p1), consumir(p2))
    assert len(r1) == 1 and len(r2) == 1
    assert fake.max_activas == 1


def test_proveedor_desconocido_solo_lista_whisper_y_stub():
    with pytest.raises(AsrConfigError) as exc:
        get_asr_provider("google")
    msg = str(exc.value)
    assert "whisper | stub" in msg
    assert "google" not in msg.split("Opciones válidas:")[1]


def test_whisper_auto_fallback_cpu_con_warning(monkeypatch, caplog):
    _limpiar_cache_modelo()

    class _FakeWhisperModel:
        def __init__(self, model_name, device, compute_type):
            self.args = (model_name, device, compute_type)
            if device == "cuda":
                raise RuntimeError("CUDA no disponible")

    import ctranslate2
    import faster_whisper

    monkeypatch.setattr(ctranslate2, "get_cuda_device_count", lambda: 1)
    monkeypatch.setattr(faster_whisper, "WhisperModel", _FakeWhisperModel)

    with caplog.at_level(logging.WARNING, logger="puente_lsch"):
        modelo = _cargar_whisper_model("small", "auto", "auto")

    assert modelo.args == ("small", "cpu", "int8")
    assert any("usando CPU" in rec.message for rec in caplog.records)
    _limpiar_cache_modelo()


def test_whisper_error_config_en_espanol_si_falla_carga(monkeypatch):
    _limpiar_cache_modelo()
    import faster_whisper

    def _fallar(*args, **kwargs):
        raise RuntimeError("modelo inexistente")

    monkeypatch.setattr(faster_whisper, "WhisperModel", _fallar)
    with pytest.raises(AsrConfigError) as exc:
        _cargar_whisper_model("no-existe", "cpu", "int8")
    msg = str(exc.value)
    assert "stub" in msg
    assert "no-existe" in msg
    _limpiar_cache_modelo()


@pytest.mark.modelo
@pytest.mark.asyncio
async def test_humo_modelo_real_whisper(monkeypatch):
    _limpiar_cache_modelo()
    monkeypatch.setenv("ASR_PROVIDER", "whisper")
    monkeypatch.setenv("WHISPER_MODEL", "tiny")
    monkeypatch.setenv("WHISPER_DEVICE", "auto")
    monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "auto")
    from app.core.config import get_settings

    get_settings.cache_clear()
    provider = get_asr_provider("whisper")

    async def silencio():
        for _ in range(10):
            yield _trama_silencio(100)

    resultados = [r async for r in provider.transcribe_stream(silencio())]
    assert resultados == []
    _limpiar_cache_modelo()


def test_segmentador_registra_llegada_fin_ms():
    seg = Segmentador(silencio_ms=300, max_segmento_ms=15000, parcial_ms=1000, pre_roll_ms=0)
    seg.alimentar(_trama_voz(100), llegada_ms=100)
    seg.alimentar(_trama_voz(100), llegada_ms=200)
    ventanas = []
    for t_ms in (300, 400, 500, 600):
        ventanas.extend(seg.alimentar(_trama_silencio(100), llegada_ms=t_ms))
    assert len(ventanas) == 1
    assert ventanas[0].final is True
    assert ventanas[0].llegada_fin_ms == 600

    seg.alimentar(_trama_voz(100), llegada_ms=900)
    cerrada = seg.cerrar(llegada_ms=950)
    assert cerrada is not None
    assert cerrada.llegada_fin_ms == 950


@pytest.mark.asyncio
async def test_whisper_provider_mide_asr_ms_y_llegada_fin_ms(monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    fake = _FakeModeloWhisper(respuestas=["lista enlazada"], delay_s=0.05)
    provider = FasterWhisperProvider(modelo=fake, silencio_ms=300, parcial_ms=2000)

    async def audio():
        for _ in range(3):
            yield _trama_voz(100)
            await asyncio.sleep(0.02)
        for _ in range(3):
            yield _trama_silencio(100)
            await asyncio.sleep(0.02)

    resultados = [r async for r in provider.transcribe_stream(audio())]
    assert len(resultados) == 1
    assert resultados[0].asr_ms >= 40
    assert resultados[0].llegada_fin_ms >= 50


@pytest.mark.asyncio
async def test_stub_provider_entrega_metricas_en_cero(monkeypatch):
    monkeypatch.setenv("STUB_INTERVAL_MS", "20")
    from app.asr.stub import StubAsrProvider
    from app.core.config import get_settings

    get_settings.cache_clear()
    provider = StubAsrProvider()

    async def audio():
        await asyncio.sleep(0.08)
        yield _trama_silencio(100)

    resultados = [r async for r in provider.transcribe_stream(audio())]
    assert len(resultados) >= 1
    assert all(r.llegada_fin_ms == 0 and r.asr_ms == 0 for r in resultados)
