"""
Settings module - loads environment variables
"""
import os
from pathlib import Path

# Load .env file from Eva_AI_Server directory
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BASE_DIR.parent

try:
    from dotenv import load_dotenv

    # Use override=True so local .env values are not shadowed by stale exported
    # shell variables during development/testing runs.
    load_dotenv(BASE_DIR / ".env", override=True)
except ImportError:
    # Notebooks / minimal test envs may omit python-dotenv; defaults still apply.
    pass


def get_roadmaps_json_path() -> Path:
    """
    Path to the roadmap structure JSON used for seeding and learning_utils.

    Resolution order:
      1. ``ROADMAPS_JSON_PATH`` env (absolute, or relative to workspace root)
      2. ``<workspace>/Roadmaps/roadmaps.json`` if that file exists
      3. ``Eva_AI_Server/data/roadmaps.json`` (legacy default)
    """
    raw = (os.getenv("ROADMAPS_JSON_PATH") or "").strip()
    if raw:
        p = Path(raw)
        if p.is_absolute():
            return p
        return (WORKSPACE_ROOT / p).resolve()

    preferred = WORKSPACE_ROOT / "Roadmaps" / "roadmaps.json"
    if preferred.is_file():
        return preferred

    return BASE_DIR / "data" / "roadmaps.json"


def _as_bool(raw_value, default=False):
    """Parse common truthy/falsey environment strings safely."""
    if raw_value is None:
        return default

    normalized = str(raw_value).strip()
    if (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in {'"', "'"}
    ):
        normalized = normalized[1:-1].strip()
    normalized = normalized.lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


class Settings:
    """Application settings loaded from environment variables"""

    BASE_DIR: Path = BASE_DIR
    WORKSPACE_ROOT: Path = WORKSPACE_ROOT

    # Server
    PORT: int = int(os.getenv("PORT", "8080"))

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/eva_db")

    # Redis — use REDIS_URL (Upstash TCP string) or host/port/password fields.
    REDIS_URL: str = os.getenv("REDIS_URL", "").strip()
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_USERNAME: str = os.getenv("REDIS_USERNAME", "")
    # Upstash and other cloud Redis providers require TLS (set REDIS_SSL=true).
    REDIS_SSL: bool = _as_bool(os.getenv("REDIS_SSL"), False)

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

    # Google Calendar OAuth (token refresh for calendar sync)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # YouTube API
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    RESOURCE_FETCH_DELAY_SECONDS: float = float(
        os.getenv("RESOURCE_FETCH_DELAY_SECONDS", "0.5"),
    )
    RESOURCE_REFRESH_ENABLED: bool = _as_bool(
        os.getenv("RESOURCE_REFRESH_ENABLED"),
        True,
    )
    RESOURCE_REFRESH_INTERVAL_DAYS: int = int(
        os.getenv("RESOURCE_REFRESH_INTERVAL_DAYS", "30"),
    )

    # Learning: map user subtopic text to a roadmap track; fuzzy score must reach this (0–1).
    SUBTOPIC_MATCH_THRESHOLD: float = float(os.getenv("SUBTOPIC_MATCH_THRESHOLD", "0.56"))
    # Learning: typo-tolerant match against SUBTOPIC_ALIAS_MAP keys (e.g. begginers → beginners).
    SUBTOPIC_ALIAS_FUZZY_THRESHOLD: float = float(
        os.getenv("SUBTOPIC_ALIAS_FUZZY_THRESHOLD", "0.85"),
    )

    # Model Settings
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

    # Model Paths
    CLF1_MODEL_DIR: Path = BASE_DIR / os.getenv("CLF1_MODEL_DIR", "models/clf1_model")
    CLF2_MODEL_DIR: Path = BASE_DIR / os.getenv("CLF2_MODEL_DIR", "models/clf1_model")
    NER_MODEL_DIR: Path = BASE_DIR / os.getenv("NER_MODEL_DIR", "models/ner1_model")
    LEARNING_NER_MODEL_DIR: Path = BASE_DIR / os.getenv(
        "LEARNING_NER_MODEL_DIR",
        "models/ner2_model",
    )

    # Context Manager
    CONTEXT_TTL: int = int(os.getenv("CONTEXT_TTL", "300"))

    # Behavioral NER fallback:
    # When True, behavioral entity scoping can interpret weekday-like `date`
    # as `day` for legacy NER outputs.
    BEHAVIORAL_DATE_AS_DAY_FALLBACK: bool = _as_bool(
        os.getenv("BEHAVIORAL_DATE_AS_DAY_FALLBACK"),
        True,
    )


# Singleton instance
settings = Settings()
