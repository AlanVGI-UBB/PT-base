from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    PORT: int = 8000
    ASR_PROVIDER: str = "stub"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    SPACY_MODEL: str = "es_core_news_md"
    DB_PATH: str = str(BASE_DIR / "data" / "glosario.db")
    STUB_INTERVAL_MS: int = 1500

    model_config = {"env_file": str(BASE_DIR / ".env"), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
