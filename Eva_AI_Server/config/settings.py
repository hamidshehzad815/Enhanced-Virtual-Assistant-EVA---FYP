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
    # Single model for every Gemini call site (replies, CLF1 classifier,
    # pending-reply fallback) — one env var, one source of truth. Model names
    # are env-configurable because Google retires them on a rolling basis:
    # gemini-2.5-flash is already blocked for new API keys and shuts down
    # 2026-10-16. Run testModels/list_gemini_models.py to see what a given key
    # can actually use, rather than hard-coding a name.
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    # EXPERIMENT (branch experiment/gemini-clf1): use Gemini instead of CLF1 to
    # classify input type and clean the text. Default OFF — CLF1 stays the
    # primary path and remains the fallback whenever Gemini fails. Uses
    # GEMINI_MODEL (see above) — no separate model setting.
    USE_GEMINI_CLF1: bool = _as_bool(os.getenv("USE_GEMINI_CLF1"), False)
    # Issue #73: Gemini fallback for natural replies to pending yes/no + list
    # prompts. Deterministic keyword/digit parsing always runs first; Gemini is
    # only consulted on a miss, and only when this flag is on. Uses
    # GEMINI_MODEL (see above) — no separate model setting.
    USE_GEMINI_PENDING_REPLY: bool = _as_bool(
        os.getenv("USE_GEMINI_PENDING_REPLY"),
        False,
    )
    GEMINI_PENDING_REPLY_MIN_CONFIDENCE: float = float(
        os.getenv("GEMINI_PENDING_REPLY_MIN_CONFIDENCE", "0.7"),
    )
    GEMINI_PENDING_REPLY_MIN_CONFIDENCE_DESTRUCTIVE: float = float(
        os.getenv("GEMINI_PENDING_REPLY_MIN_CONFIDENCE_DESTRUCTIVE", "0.85"),
    )
    GEMINI_TIMEOUT_SECONDS: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "4"))
    # Circuit breaker: pause Gemini after repeated failures instead of hammering
    # a clearly-broken API. This used to disable Gemini PERMANENTLY on the first
    # failure, so a single blip (or a 404 from a retired model name) silently
    # degraded every later reply to a canned string until the process restarted.
    # It now pauses for GEMINI_COOLDOWN_SECONDS and then retries.
    GEMINI_DISABLE_AFTER_FAILURE: bool = _as_bool(
        os.getenv("GEMINI_DISABLE_AFTER_FAILURE"),
        True,
    )
    GEMINI_FAILURE_THRESHOLD: int = int(os.getenv("GEMINI_FAILURE_THRESHOLD", "3"))
    GEMINI_COOLDOWN_SECONDS: float = float(os.getenv("GEMINI_COOLDOWN_SECONDS", "60"))

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

    # Model Paths (folders under Eva_AI_Server/models/)
    CLF1_MODEL_DIR: Path = BASE_DIR / os.getenv("CLF1_MODEL_DIR", "models/clf1_model")
    CLF2_MODEL_DIR: Path = BASE_DIR / os.getenv("CLF2_MODEL_DIR", "models/clf2_model")
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
