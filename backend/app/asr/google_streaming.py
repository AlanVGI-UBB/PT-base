import asyncio
import logging
from typing import AsyncIterator

from app.asr.base import AsrConfigError, ResultadoASR
from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from google.cloud import speech

    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False


class GoogleStreamingProvider:
    def __init__(self) -> None:
        if not _GOOGLE_AVAILABLE:
            raise AsrConfigError(
                "El paquete google-cloud-speech no está instalado. "
                "Instálalo con: pip install google-cloud-speech"
            )
        creds = get_settings().GOOGLE_APPLICATION_CREDENTIALS
        if not creds:
            raise AsrConfigError(
                "GOOGLE_APPLICATION_CREDENTIALS no está configurada. "
                "Define la variable de entorno con la ruta al archivo de "
                "credenciales de servicio de Google Cloud, o cambia "
                "ASR_PROVIDER a 'stub' para desarrollo sin credenciales."
            )
        self._client = speech.SpeechClient()
        self._config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code="es-CL",
            enable_automatic_punctuation=True,
            model="latest_short",
        )
        self._streaming_config = speech.StreamingRecognitionConfig(
            config=self._config,
            interim_results=True,
            single_utterance=False,
        )

    async def transcribe_stream(
        self,
        audio_iter: AsyncIterator[bytes],
        lang: str = "es-CL",
    ) -> AsyncIterator[ResultadoASR]:
        queue: asyncio.Queue[ResultadoASR | None] = asyncio.Queue()

        async def _audio_chunks():
            async for chunk in audio_iter:
                yield chunk

        def _request_gen():
            config_req = speech.StreamingRecognizeRequest(
                streaming_config=self._streaming_config,
            )
            yield config_req
            for chunk_bytes in _audio_chunks_sync:
                yield speech.StreamingRecognizeRequest(audio_content=chunk_bytes)

        _audio_chunks_sync: list[bytes] = []

        async def _collect_chunks():
            async for chunk in audio_iter:
                _audio_chunks_sync.append(chunk)

        def _run_stream():
            try:
                for response in self._client.streaming_recognize(_request_gen()):
                    for result in response.results:
                        alt = result.alternatives[0]
                        queue.put_nowait(
                            ResultadoASR(
                                texto=alt.transcript.strip(),
                                estable=result.is_final,
                                inicio_ms=0,
                                fin_ms=0,
                            )
                        )
            except Exception as e:
                logger.error("Error en streaming Google: %s", e)
            finally:
                queue.put_nowait(None)

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _run_stream)

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
