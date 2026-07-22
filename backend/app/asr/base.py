from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass
class ResultadoASR:
    texto: str
    estable: bool
    inicio_ms: int
    fin_ms: int


class StreamingASRProvider(Protocol):
    async def transcribe_stream(
        self,
        audio_iter: AsyncIterator[bytes],
        lang: str = "es-CL",
    ) -> AsyncIterator[ResultadoASR]: ...


class AsrConfigError(RuntimeError):
    pass


def get_asr_provider(provider: str | None = None) -> StreamingASRProvider:
    from app.core.config import get_settings

    name = provider or get_settings().ASR_PROVIDER

    if name == "google":
        from app.asr.google_streaming import GoogleStreamingProvider

        return GoogleStreamingProvider()
    if name == "stub":
        from app.asr.stub import StubAsrProvider

        return StubAsrProvider()

    raise AsrConfigError(
        f"ASR_PROVIDER desconocido: {name!r}. "
        "Opciones válidas: google | stub | webspeech | faster_whisper"
    )
