from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass
class ResultadoASR:
    segmento_id: int
    texto: str
    estable: bool
    inicio_ms: int
    fin_ms: int
    llegada_fin_ms: int = 0
    asr_ms: int = 0


class StreamingASRProvider(Protocol):
    def transcribe_stream(
        self,
        audio_iter: AsyncIterator[bytes],
        lang: str = "es",
        contexto: list[str] | None = None,
    ) -> AsyncIterator[ResultadoASR]: ...


class AsrConfigError(RuntimeError):
    pass


def get_asr_provider(provider: str | None = None) -> StreamingASRProvider:
    from app.core.config import get_settings

    name = provider or get_settings().ASR_PROVIDER

    if name == "whisper":
        from app.asr.whisper_local import FasterWhisperProvider

        return FasterWhisperProvider()
    if name == "stub":
        from app.asr.stub import StubAsrProvider

        return StubAsrProvider()

    raise AsrConfigError(
        f"ASR_PROVIDER desconocido: {name!r}. "
        "Opciones válidas: whisper | stub"
    )
