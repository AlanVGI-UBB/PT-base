from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


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
    JWT_SECRET: str = "cambiar-en-produccion"
    SALA_TIMEOUT_MS: int = 30000
    AUTH_PROVIDER: str = "local"
    METRICAS: bool = True

    model_config = {"env_file": str(BASE_DIR / ".env"), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
