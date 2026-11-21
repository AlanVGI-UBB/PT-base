from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time
from typing import Any, AsyncIterator
from weakref import WeakKeyDictionary

import numpy as np

from app.asr.base import AsrConfigError, ResultadoASR
from app.asr.segmentador import SAMPLE_RATE, Segmentador, Ventana
from app.core.config import get_settings

logger = logging.getLogger("puente_lsch")

_FIN = object()
_MODELO_LOCK = threading.Lock()
_MODELO_CACHE: dict[tuple[str, str, str], Any] = {}
_ASYNC_LOCKS: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = WeakKeyDictionary()


def _get_async_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _ASYNC_LOCKS.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _ASYNC_LOCKS[loop] = lock
    return lock


def _resolver_compute_type(device: str, compute_type: str) -> str:
    if compute_type != "auto":
        return compute_type
    return "float16" if device == "cuda" else "int8"


def _cargar_whisper_model(model_name: str, device: str, compute_type: str) -> Any:
    key = (model_name, device, compute_type)
    with _MODELO_LOCK:
        if key in _MODELO_CACHE:
            return _MODELO_CACHE[key]

        try:
            import ctranslate2
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise AsrConfigError(
                "El paquete faster-whisper no está instalado. "
                "Instálalo con: pip install faster-whisper, o cambia ASR_PROVIDER a 'stub'."
            ) from exc

        if device not in {"auto", "cuda", "cpu"}:
            raise AsrConfigError(
                f"WHISPER_DEVICE inválido: {device!r}. Opciones válidas: auto | cuda | cpu"
            )

        modelo = None
        if device == "auto":
            cuda_count = 0
            try:
                cuda_count = ctranslate2.get_cuda_device_count()
            except Exception:
                cuda_count = 0

            if cuda_count > 0:
                ct_cuda = _resolver_compute_type("cuda", compute_type)
                try:
                    modelo = WhisperModel(model_name, device="cuda", compute_type=ct_cuda)
                except Exception as exc:
                    logger.warning(
                        "No se pudo inicializar Whisper en GPU (%s); usando CPU.",
                        exc,
                    )
            else:
                logger.warning("GPU CUDA no disponible para Whisper; usando CPU.")

            if modelo is None:
                ct_cpu = _resolver_compute_type("cpu", compute_type)
                try:
                    modelo = WhisperModel(model_name, device="cpu", compute_type=ct_cpu)
                except Exception as exc:
                    raise AsrConfigError(
                        f"No se pudo cargar el modelo Whisper '{model_name}' en CPU ({exc}). "
                        "Verifica la instalación y el nombre del modelo, o cambia ASR_PROVIDER a 'stub'."
                    ) from exc
        else:
            ct = _resolver_compute_type(device, compute_type)
            try:
                modelo = WhisperModel(model_name, device=device, compute_type=ct)
            except Exception as exc:
                raise AsrConfigError(
                    f"No se pudo cargar el modelo Whisper '{model_name}' en {device} ({exc}). "
                    "Verifica CUDA/cuDNN o cambia WHISPER_DEVICE a 'cpu' o ASR_PROVIDER a 'stub'."
                ) from exc

        _MODELO_CACHE[key] = modelo
        return modelo


def _limpiar_cache_modelo() -> None:
    with _MODELO_LOCK:
        _MODELO_CACHE.clear()


def _normalizar_idioma(lang: str) -> str:
    base = (lang or "es").split("-")[0].strip().lower()
    return base or "es"


def _construir_prompt(contexto: list[str] | None) -> str | None:
    if not contexto:
        return None
    vistos: list[str] = []
    for item in contexto:
        limpio = (item or "").strip()
        if limpio and limpio not in vistos:
            vistos.append(limpio)
    if not vistos:
        return None
    return ", ".join(vistos) + "."


class FasterWhisperProvider:
    """Proveedor ASR local por streaming simulado con faster-whisper."""

    def __init__(
        self,
        modelo: Any | None = None,
        silencio_ms: int | None = None,
        max_segmento_ms: int | None = None,
        parcial_ms: int | None = None,
        umbral_rms: float = 0.01,
    ) -> None:
        settings = get_settings()
        self._modelo = (
            modelo
            if modelo is not None
            else _cargar_whisper_model(
                settings.WHISPER_MODEL,
                settings.WHISPER_DEVICE,
                settings.WHISPER_COMPUTE_TYPE,
            )
        )
        self._silencio_ms = (
            silencio_ms if silencio_ms is not None else settings.ASR_SILENCIO_MS
        )
        self._max_segmento_ms = (
            max_segmento_ms
            if max_segmento_ms is not None
            else settings.ASR_MAX_SEGMENTO_MS
        )
        self._parcial_ms = (
            parcial_ms if parcial_ms is not None else settings.ASR_PARCIAL_MS
        )
        self._umbral_rms = umbral_rms
        self._prompt_habilitado = settings.ASR_PROMPT_GLOSARIO
        self._inst_lock = threading.Lock() if modelo is not None else _MODELO_LOCK

    def _transcribir_sync(
        self,
        pcm: np.ndarray,
        idioma: str,
        prompt: str | None,
    ) -> str:
        with self._inst_lock:
            segments, _ = self._modelo.transcribe(
                pcm,
                language=idioma,
                vad_filter=True,
                condition_on_previous_text=False,
                initial_prompt=prompt,
            )
            partes = [s.text.strip() for s in segments if getattr(s, "text", "").strip()]
        return " ".join(partes)

    async def _transcribir_ventana(
        self,
        ventana: Ventana,
        idioma: str,
        prompt: str | None,
    ) -> ResultadoASR | None:
        async with _get_async_lock():
            t_ini = time.monotonic_ns()
            texto = await asyncio.to_thread(
                self._transcribir_sync,
                ventana.pcm,
                idioma,
                prompt,
            )
            asr_ms = (time.monotonic_ns() - t_ini) // 1_000_000
        texto = texto.strip()
        if not texto:
            return None
        return ResultadoASR(
            segmento_id=ventana.segmento_id,
            texto=texto,
            estable=ventana.final,
            inicio_ms=ventana.inicio_ms,
            fin_ms=ventana.fin_ms,
            llegada_fin_ms=ventana.llegada_fin_ms,
            asr_ms=asr_ms,
        )

    @staticmethod
    def _filtrar_ventanas(
        ventanas: list[Ventana],
        omitir_provisionales: bool,
    ) -> list[Ventana]:
        if not ventanas:
            return []
        resultado: list[Ventana] = []
        ultima_provisional: Ventana | None = None
        for v in ventanas:
            if v.final:
                ultima_provisional = None
                resultado.append(v)
            elif not omitir_provisionales:
                ultima_provisional = v
        if ultima_provisional is not None:
            resultado.append(ultima_provisional)
        return resultado

    async def transcribe_stream(
        self,
        audio_iter: AsyncIterator[bytes],
        lang: str = "es",
        contexto: list[str] | None = None,
    ) -> AsyncIterator[ResultadoASR]:
        t0_ns = time.monotonic_ns()
        segmentador = Segmentador(
            silencio_ms=self._silencio_ms,
            max_segmento_ms=self._max_segmento_ms,
            parcial_ms=self._parcial_ms,
            umbral_rms=self._umbral_rms,
        )
        idioma = _normalizar_idioma(lang)
        prompt = _construir_prompt(contexto) if self._prompt_habilitado else None

        pcm_queue: asyncio.Queue[tuple[bytes | object, int]] = asyncio.Queue()
        queued_bytes = 0

        async def _pump() -> None:
            nonlocal queued_bytes
            try:
                async for trama in audio_iter:
                    llegada_ms = (time.monotonic_ns() - t0_ns) // 1_000_000
                    queued_bytes += len(trama)
                    await pcm_queue.put((trama, llegada_ms))
            finally:
                fin_ms = (time.monotonic_ns() - t0_ns) // 1_000_000
                await pcm_queue.put((_FIN, fin_ms))

        pump_task = asyncio.create_task(_pump())
        terminado = False
        fin_llegada_ms: int | None = None
        try:
            while not terminado:
                tramas: list[tuple[bytes, int]] = []
                try:
                    payload, ts_ms = await asyncio.wait_for(
                        pcm_queue.get(),
                        timeout=self._silencio_ms / 1000.0,
                    )
                except asyncio.TimeoutError:
                    timeout_ms = (time.monotonic_ns() - t0_ns) // 1_000_000
                    v_timeout = segmentador.cerrar(llegada_ms=timeout_ms)
                    if v_timeout is not None:
                        res = await self._transcribir_ventana(v_timeout, idioma, prompt)
                        if res is not None:
                            yield res
                    continue

                if payload is _FIN:
                    terminado = True
                    fin_llegada_ms = ts_ms
                else:
                    queued_bytes -= len(payload)  # type: ignore[arg-type]
                    tramas.append((payload, ts_ms))  # type: ignore[arg-type]

                while not pcm_queue.empty():
                    nxt_payload, nxt_ts_ms = pcm_queue.get_nowait()
                    if nxt_payload is _FIN:
                        terminado = True
                        fin_llegada_ms = nxt_ts_ms
                        break
                    queued_bytes -= len(nxt_payload)  # type: ignore[arg-type]
                    tramas.append((nxt_payload, nxt_ts_ms))  # type: ignore[arg-type]

                total_bytes = sum(len(t) for t, _ in tramas)
                pendiente_ms = (total_bytes // 2) * 1000 // SAMPLE_RATE

                ventanas: list[Ventana] = []
                for trama, llegada_ms in tramas:
                    ventanas.extend(segmentador.alimentar(trama, llegada_ms=llegada_ms))
                if terminado:
                    v_fin = segmentador.cerrar(llegada_ms=fin_llegada_ms)
                    if v_fin is not None:
                        ventanas.append(v_fin)

                a_transcribir = self._filtrar_ventanas(
                    ventanas,
                    omitir_provisionales=(pendiente_ms > self._parcial_ms and not terminado),
                )
                for v in a_transcribir:
                    if not v.final:
                        cola_ms = (queued_bytes // 2) * 1000 // SAMPLE_RATE
                        if cola_ms > self._parcial_ms:
                            continue
                    res = await self._transcribir_ventana(v, idioma, prompt)
                    if res is not None:
                        yield res
        finally:
            pump_task.cancel()
            with contextlib.suppress(BaseException):
                await pump_task
