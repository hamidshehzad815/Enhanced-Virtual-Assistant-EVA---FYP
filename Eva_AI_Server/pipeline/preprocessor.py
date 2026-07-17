"""
Message preprocessing utilities used before model inference.
"""
import re
from typing import Dict


def to_lowercase(text: str) -> str:
    """Lowercase and strip input text."""
    return text.lower().strip()


def is_too_short(text: str, min_chars: int = 2) -> bool:
    """
    Return True only when the input carries no usable content.

    This used to require at least 2 *words*, which silently rejected every
    single-word message before it ever reached the classifiers: "help", "hi",
    "yes", "cancel", "thanks". Those are among the most common things a user
    types, and "help" in particular is the clearest help request there is — the
    models classify it correctly, they just never got the chance.

    The gate exists to drop genuinely empty/meaningless input ("", "?", "a"),
    so it counts alphanumeric characters instead of words.
    """
    meaningful = re.sub(r"[^a-z0-9]", "", (text or "").lower())
    return len(meaningful) < min_chars


def preprocess(text: str) -> Dict[str, str]:
		"""
		Run preprocessing pipeline.
		Lowercasing only.

		Returns both original and processed text.
		Original is always preserved for NER and Gemini.
		Processed is used only for model classification.
		"""
		original = text.strip() if text else ""
		processed = to_lowercase(original)

		return {
				"original": original,
				"processed": processed,
		}

