"""
List the Gemini models THIS API key can actually use.

Model availability differs per key/project and Google retires models on a
rolling basis (gemini-2.5-flash is blocked for new keys and shuts down
2026-10-16), so never hard-code a model name from a blog post — ask the API.

Run:
    python Eva_AI_Server/testModels/list_gemini_models.py
"""
import sys
from pathlib import Path

AI_SERVER_DIR = Path(__file__).resolve().parent.parent
if str(AI_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVER_DIR))

from config.settings import settings  # noqa: E402

try:
    import google.generativeai as genai
except ImportError:
    print("google-generativeai not installed:  pip install google-generativeai")
    sys.exit(1)


def main() -> None:
    if not settings.GEMINI_API_KEY:
        print("GEMINI_API_KEY is not set in .env")
        return

    genai.configure(api_key=settings.GEMINI_API_KEY)

    print("Models supporting generateContent (usable for EVA):\n")
    usable = []
    for model in genai.list_models():
        if "generateContent" in getattr(model, "supported_generation_methods", []):
            name = model.name.replace("models/", "")
            usable.append(name)
            print(f"  {name}")

    print(f"\n{len(usable)} usable model(s).")
    print(f"\nCurrently configured:")
    # One model for every call site (replies, CLF1 classifier, pending-reply
    # fallback) — see config/settings.py.
    print(f"  GEMINI_MODEL = {settings.GEMINI_MODEL}")

    if settings.GEMINI_MODEL not in usable:
        print(f"\n  WARNING: GEMINI_MODEL={settings.GEMINI_MODEL!r} is NOT in the usable list above.")
        print(f"           Set GEMINI_MODEL in .env to one of them.")


if __name__ == "__main__":
    main()
