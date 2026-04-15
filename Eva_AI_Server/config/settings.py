"""
Settings module - loads environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from Eva_AI_Server directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _as_bool(raw_value, default=False):
    """Parse common truthy/falsey environment strings safely."""
    if raw_value is None:
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Application settings loaded from environment variables"""

    # Server
    PORT: int = int(os.getenv("PORT", "8080"))

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/eva_db")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

    # Duckling
    DUCKLING_URL: str = os.getenv("DUCKLING_URL", "http://localhost:8000")

    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_ENABLED: bool = _as_bool(os.getenv("GEMINI_ENABLED"), True)
    GEMINI_TIMEOUT_SECONDS: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "4"))
    GEMINI_DISABLE_AFTER_FAILURE: bool = _as_bool(
        os.getenv("GEMINI_DISABLE_AFTER_FAILURE"),
        True,
    )

    # YouTube API
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

    # Model Settings
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    # Temporary compatibility switch:
    # some NER versions emit weekday as `date` for behavioral intent.
    # When enabled, behavioral scope remaps weekday-like `date` -> `day`.
    BEHAVIORAL_DATE_AS_DAY_FALLBACK: bool = _as_bool(
        os.getenv("BEHAVIORAL_DATE_AS_DAY_FALLBACK"),
        True,
    )

    # Model Paths
    CLF1_MODEL_DIR: Path = BASE_DIR / os.getenv("CLF1_MODEL_DIR", "models/clf1")
    CLF2_MODEL_DIR: Path = BASE_DIR / os.getenv("CLF2_MODEL_DIR", "models/intent_classifier")
    NER_MODEL_DIR: Path = BASE_DIR / os.getenv("NER_MODEL_DIR", "models/ner_model")

    # Context Manager
    CONTEXT_TTL: int = int(os.getenv("CONTEXT_TTL", "300"))


# Singleton instance
settings = Settings()
