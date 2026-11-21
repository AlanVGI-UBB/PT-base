from app.core.config import get_settings
from app.core.db import get_connection


def registrar_segmento(
    clase_id: int,
    segmento_id: int,
    audio_inicio_ms: int,
    audio_fin_ms: int,
    llegada_fin_ms: int,
    asr_ms: int,
    nlp_ms: int,
    emitido_ms: int,
    receptores: int,
) -> int | None:
    """Registra métricas de latencia de un segmento final en SQLite si METRICAS está activa."""
    if not get_settings().METRICAS:
        return None
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO metrica_segmento ("
        "clase_id, segmento_id, audio_inicio_ms, audio_fin_ms, "
        "llegada_fin_ms, asr_ms, nlp_ms, emitido_ms, receptores"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            clase_id,
            segmento_id,
            audio_inicio_ms,
            audio_fin_ms,
            llegada_fin_ms,
            asr_ms,
            nlp_ms,
            emitido_ms,
            receptores,
        ),
    )
    conn.commit()
    return cur.lastrowid
