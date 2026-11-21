import asyncio
import math
import struct
import wave
from types import SimpleNamespace

import pytest

from evaluar_asr import (
    _validar_y_leer_wav,
    calcular_cobertura_terminos_en_transcripcion,
    calcular_metricas_wer,
    evaluar_wav_con_provider,
)
from comun import asegurar_backend_en_path

asegurar_backend_en_path()

from app.asr.whisper_local import FasterWhisperProvider  # noqa: E402
from app.glossary.indice import construir_indice  # noqa: E402


def _escribir_wav_pcm(path, duracion_s: float = 0.8, freq_hz: int = 440, channels: int = 1, rate: int = 16000):
    n = int(duracion_s * rate)
    amp = int(32767 * 0.25)
    muestras = [int(amp * math.sin(2 * math.pi * freq_hz * i / rate)) for i in range(n)]
    data = struct.pack(f"<{n * channels}h", *(muestras * channels))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(data)


def test_validar_wav_rechaza_formato_invalido(tmp_path):
    wav_mal = tmp_path / "stereo.wav"
    _escribir_wav_pcm(wav_mal, channels=2)
    with pytest.raises(ValueError, match="WAV mono 16 bits PCM 16000 Hz"):
        _validar_y_leer_wav(wav_mal)


def test_metricas_wer_conteos_exactos():
    # ref: "un arreglo tiene cinco nodos" (5 palabras)
    # hyp: "un arreglo tiene nodos nuevos" -> 5 vs nodos(DEL), cinco->nodos(SUB), +nuevos(INS)?
    # Probamos caso inequívoco: "hola mundo cruel" vs "hola tierra" -> 1 sub ("mundo"->"tierra"), 1 del ("cruel") => S=1 D=1 I=0 N=3 WER=2/3
    res = calcular_metricas_wer("¡Hola, mundo cruel!", "Hola tierra.")
    assert res["palabras_referencia"] == 3
    assert res["sustituciones"] == 1
    assert res["eliminaciones"] == 1
    assert res["inserciones"] == 0
    assert res["wer"] == round(2 / 3, 4)


def test_cobertura_terminos_en_transcripcion_respeta_bloqueos():
    terminos = [
        {
            "id": 1,
            "curso_id": 1,
            "texto_visible": "nodo",
            "formas": ["nodo", "nodos"],
            "bloqueos": [],
            "video_url": "/v/nodo.mp4",
            "estado": "ensayo",
        },
        {
            "id": 2,
            "curso_id": 1,
            "texto_visible": "memoria",
            "formas": ["memoria"],
            "bloqueos": ["de memoria"],
            "video_url": "/v/memoria.mp4",
            "estado": "ensayo",
        },
    ]
    indice = construir_indice(terminos)
    res = calcular_cobertura_terminos_en_transcripcion(
        referencia="creamos dos nodos en memoria sin aprenderlo de memoria",
        hipotesis="creamos un nodo sin aprenderlo de memoria",
        indice=indice,
    )
    # Referencia tiene: nodo(1) + memoria(1); "de memoria" bloqueado => total_ref=2
    # Hipótesis tiene: nodo(1) => total_rec=1 => 0.5
    assert res["menciones_referencia"] == 2
    assert res["menciones_recuperadas"] == 1
    assert res["fraccion_recuperada"] == 0.5


class _FakeWhisperModelo:
    def __init__(self):
        self.llamadas = 0

    def transcribe(self, pcm, language="es", vad_filter=True, condition_on_previous_text=False, initial_prompt=None):
        del pcm, language, vad_filter, condition_on_previous_text, initial_prompt
        self.llamadas += 1
        return [SimpleNamespace(text="insertamos un nodo nuevo")], SimpleNamespace(language="es")


def test_evaluar_wav_con_provider_flujo_completo(tmp_path, monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    wav_ok = tmp_path / "ok.wav"
    _escribir_wav_pcm(wav_ok, duracion_s=0.4)
    pcm_bytes, duracion_ms = _validar_y_leer_wav(wav_ok)
    assert duracion_ms == 400

    indice = construir_indice(
        [
            {
                "id": 1,
                "curso_id": 1,
                "texto_visible": "nodo",
                "formas": ["nodo", "nodos"],
                "bloqueos": [],
                "video_url": "/v/nodo.mp4",
                "estado": "ensayo",
            }
        ]
    )
    provider = FasterWhisperProvider(
        modelo=_FakeWhisperModelo(),
        silencio_ms=300,
        max_segmento_ms=5000,
        parcial_ms=2000,
    )

    res = asyncio.run(
        evaluar_wav_con_provider(
            pcm_bytes=pcm_bytes,
            duracion_ms=duracion_ms,
            referencia_texto="insertamos un nodo nuevo",
            provider=provider,
            indice=indice,
            contexto=["nodo"],
            rapido=True,
            device_config="cpu",
        )
    )
    assert res["segmentos_finales"] == 1
    assert res["wer"]["wer"] == 0.0
    assert res["terminos_tecnicos"]["fraccion_recuperada"] == 1.0
    assert res["modo_rapido"] is True
    assert res["latencia_servidor_ms"]["n"] == 1
    assert res["memoria_proceso_max_mb"] > 0


def test_evaluar_wav_ritmo_real(tmp_path, monkeypatch):
    monkeypatch.setenv("ASR_PROMPT_GLOSARIO", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    wav_ok = tmp_path / "realtime.wav"
    _escribir_wav_pcm(wav_ok, duracion_s=0.3)
    pcm_bytes, duracion_ms = _validar_y_leer_wav(wav_ok)

    indice = construir_indice([])
    provider = FasterWhisperProvider(
        modelo=_FakeWhisperModelo(),
        silencio_ms=300,
        max_segmento_ms=5000,
        parcial_ms=2000,
    )

    res = asyncio.run(
        evaluar_wav_con_provider(
            pcm_bytes=pcm_bytes,
            duracion_ms=duracion_ms,
            referencia_texto="insertamos un nodo nuevo",
            provider=provider,
            indice=indice,
            contexto=None,
            rapido=False,
            device_config="cpu",
        )
    )
    assert res["modo_rapido"] is False
    assert res["wall_clock_ms"] >= 250
    assert "excluye" in res["latencia_servidor_ms"]
