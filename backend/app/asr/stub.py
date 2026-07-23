import asyncio
from typing import AsyncIterator

from app.asr.base import ResultadoASR
from app.core.config import get_settings

FRASES = [
    "hola a todos",
    "bienvenidos a la clase",
    "hoy vamos a ver derivadas",
    "la función es continua",
    "calculamos la raíz cuadrada",
    "el teorema del valor medio",
    "reemplazamos en la ecuación",
    "el resultado es igual a cero",
    "alguien tiene alguna duda",
    "vamos con el siguiente ejercicio",
]


class StubAsrProvider:
    async def transcribe_stream(
        self,
        audio_iter: AsyncIterator[bytes],
        lang: str = "es-CL",
    ) -> AsyncIterator[ResultadoASR]:
        interval = get_settings().STUB_INTERVAL_MS / 1000.0
        idx = 0
        while True:
            frase = FRASES[idx % len(FRASES)]
            await asyncio.sleep(interval)
            yield ResultadoASR(
                texto=frase,
                estable=True,
                inicio_ms=0,
                fin_ms=int(interval * 1000),
            )
            idx += 1
