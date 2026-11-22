from functools import lru_cache
import logging
from pathlib import Path
import secrets

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger("puente_lsch")


class Settings(BaseSettings):
    PORT: int = 8000
    ASR_PROVIDER: str = "stub"
    WHISPER_MODEL: str = "small"
    WHISPER_DEVICE: str = "auto"
    WHISPER_COMPUTE_TYPE: str = "auto"
    ASR_SILENCIO_MS: int = 600
    ASR_MAX_SEGMENTO_MS: int = 15000
    ASR_PARCIAL_MS: int = 1000
    ASR_FLUSH_TIMEOUT_MS: int = 5000
    ASR_MAX_TRAMA_BYTES: int = 64000
    ASR_PROMPT_GLOSARIO: bool = True
    SPACY_MODEL: str = "es_core_news_md"
    DB_PATH: str = str(BASE_DIR / "data" / "glosario.db")
    STUB_INTERVAL_MS: int = 1500
    JWT_SECRET: str = ""
    JWT_EXP_MIN: int = 480
    CORS_ORIGINS: str = "http://localhost:5173"
    SALA_TIMEOUT_MS: int = 30000
    METRICAS: bool = True

    model_config = {"env_file": str(BASE_DIR / ".env"), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.JWT_SECRET.strip():
        settings.JWT_SECRET = secrets.token_urlsafe(32)
        logger.warning(
            "JWT_SECRET está vacío; se generó un secreto aleatorio para este proceso. "
            "Las sesiones no sobrevivirán a un reinicio."
        )
    return settings
