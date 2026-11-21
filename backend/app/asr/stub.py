import asyncio
import contextlib
from typing import AsyncIterator

from app.asr.base import ResultadoASR
from app.core.config import get_settings

FRASES = [
    "hola a todos, hoy continuamos con estructuras de datos",
    "un arreglo permite acceso directo en memoria contigua",
    "las listas enlazadas conectan cada nodo con un puntero",
    "hoy repasamos pila, cola y árbol binario",
    "no se aprendan la fórmula de memoria sin entenderla",
    "una tabla hash reduce la complejidad de búsqueda",
    "el algoritmo de ordenamiento facilita la búsqueda binaria",
    "la recursión y los grafos quedan para la próxima clase",
]


class StubAsrProvider:
    """Proveedor ASR de desarrollo sin credenciales ni modelo."""

    async def transcribe_stream(
        self,
        audio_iter: AsyncIterator[bytes],
        lang: str = "es",
        contexto: list[str] | None = None,
    ) -> AsyncIterator[ResultadoASR]:
        del lang, contexto
        interval_ms = get_settings().STUB_INTERVAL_MS
        interval = interval_ms / 1000.0
        fin = asyncio.Event()

        async def _watch_audio() -> None:
            try:
                async for _ in audio_iter:
                    pass
            finally:
                fin.set()

        watcher = asyncio.create_task(_watch_audio())
        idx = 0
        try:
            while not fin.is_set():
                try:
                    await asyncio.wait_for(fin.wait(), timeout=interval)
                    break
                except asyncio.TimeoutError:
                    pass
                frase = FRASES[idx % len(FRASES)]
                yield ResultadoASR(
                    segmento_id=idx + 1,
                    texto=frase,
                    estable=True,
                    inicio_ms=idx * interval_ms,
                    fin_ms=(idx + 1) * interval_ms,
                    llegada_fin_ms=0,
                    asr_ms=0,
                )
                idx += 1
        finally:
            watcher.cancel()
            with contextlib.suppress(BaseException):
                await watcher
