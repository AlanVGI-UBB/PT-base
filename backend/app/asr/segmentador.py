from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 16000
SUBTRAMA_MS = 30
SUBTRAMA_MUESTRAS = SAMPLE_RATE * SUBTRAMA_MS // 1000  # 480 muestras


@dataclass
class Ventana:
    segmento_id: int
    pcm: np.ndarray  # float32 mono 16 kHz
    inicio_ms: int
    fin_ms: int
    final: bool


class Segmentador:
    """Acumula tramas PCM s16le mono 16 kHz y emite ventanas por detección de energía."""

    def __init__(
        self,
        silencio_ms: int = 600,
        max_segmento_ms: int = 15000,
        parcial_ms: int = 1000,
        umbral_rms: float = 0.01,
        pre_roll_ms: int = 240,
    ) -> None:
        self.silencio_ms = silencio_ms
        self.max_segmento_ms = max_segmento_ms
        self.parcial_ms = parcial_ms
        self.umbral_rms = umbral_rms
        max_pre_roll = max(0, pre_roll_ms // SUBTRAMA_MS)
        self._pre_roll: deque[tuple[int, np.ndarray]] = deque(maxlen=max_pre_roll)

        self._residuo = np.empty(0, dtype=np.float32)
        self._muestras_procesadas = 0
        self._siguiente_segmento_id = 1

        self._en_segmento = False
        self._segmento_id = 0
        self._seg_inicio_ms = 0
        self._seg_chunks: list[np.ndarray] = []
        self._seg_muestras = 0
        self._silencio_acumulado_ms = 0
        self._ultimo_parcial_ms = 0

    @property
    def en_segmento(self) -> bool:
        return self._en_segmento

    def _limpiar_segmento(self) -> None:
        self._en_segmento = False
        self._seg_chunks = []
        self._seg_muestras = 0
        self._silencio_acumulado_ms = 0

    def alimentar(self, trama: bytes) -> list[Ventana]:
        if len(trama) % 2 != 0:
            raise ValueError("La trama PCM s16le debe tener longitud par")
        if not trama:
            return []

        muestras = np.frombuffer(trama, dtype="<i2").astype(np.float32) / 32768.0
        if len(self._residuo) > 0:
            datos = np.concatenate([self._residuo, muestras])
        else:
            datos = muestras

        ventanas: list[Ventana] = []
        offset = 0
        total = len(datos)

        while offset + SUBTRAMA_MUESTRAS <= total:
            sub = datos[offset : offset + SUBTRAMA_MUESTRAS]
            offset += SUBTRAMA_MUESTRAS

            sub_inicio_ms = (self._muestras_procesadas * 1000) // SAMPLE_RATE
            self._muestras_procesadas += SUBTRAMA_MUESTRAS
            sub_fin_ms = (self._muestras_procesadas * 1000) // SAMPLE_RATE

            rms = float(np.sqrt(np.mean(sub * sub)))
            es_voz = rms >= self.umbral_rms

            if not self._en_segmento:
                if es_voz:
                    self._en_segmento = True
                    self._segmento_id = self._siguiente_segmento_id
                    self._siguiente_segmento_id += 1
                    if self._pre_roll:
                        self._seg_inicio_ms = self._pre_roll[0][0]
                        self._seg_chunks = [chunk for _, chunk in self._pre_roll]
                        self._pre_roll.clear()
                    else:
                        self._seg_inicio_ms = sub_inicio_ms
                        self._seg_chunks = []
                    self._seg_chunks.append(sub)
                    self._seg_muestras = sum(len(c) for c in self._seg_chunks)
                    self._silencio_acumulado_ms = 0
                    self._ultimo_parcial_ms = sub_inicio_ms
                else:
                    self._pre_roll.append((sub_inicio_ms, sub))
                continue

            self._seg_chunks.append(sub)
            self._seg_muestras += len(sub)

            if es_voz:
                self._silencio_acumulado_ms = 0
            else:
                self._silencio_acumulado_ms += SUBTRAMA_MS

            duracion_seg_ms = (self._seg_muestras * 1000) // SAMPLE_RATE
            if (
                self._silencio_acumulado_ms >= self.silencio_ms
                or duracion_seg_ms >= self.max_segmento_ms
            ):
                ventanas.append(
                    Ventana(
                        segmento_id=self._segmento_id,
                        pcm=np.concatenate(self._seg_chunks),
                        inicio_ms=self._seg_inicio_ms,
                        fin_ms=sub_fin_ms,
                        final=True,
                    )
                )
                self._limpiar_segmento()
            elif (sub_fin_ms - self._ultimo_parcial_ms) >= self.parcial_ms:
                ventanas.append(
                    Ventana(
                        segmento_id=self._segmento_id,
                        pcm=np.concatenate(self._seg_chunks),
                        inicio_ms=self._seg_inicio_ms,
                        fin_ms=sub_fin_ms,
                        final=False,
                    )
                )
                self._ultimo_parcial_ms = sub_fin_ms

        self._residuo = datos[offset:].copy()
        return ventanas

    def cerrar(self) -> Ventana | None:
        self._pre_roll.clear()
        if not self._en_segmento:
            if len(self._residuo) > 0:
                self._muestras_procesadas += len(self._residuo)
                self._residuo = np.empty(0, dtype=np.float32)
            return None

        if len(self._residuo) > 0:
            self._seg_chunks.append(self._residuo)
            self._muestras_procesadas += len(self._residuo)
            self._residuo = np.empty(0, dtype=np.float32)

        fin_ms = (self._muestras_procesadas * 1000) // SAMPLE_RATE
        ventana = Ventana(
            segmento_id=self._segmento_id,
            pcm=np.concatenate(self._seg_chunks),
            inicio_ms=self._seg_inicio_ms,
            fin_ms=fin_ms,
            final=True,
        )
        self._limpiar_segmento()
        return ventana
