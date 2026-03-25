"""
Message preprocessing utilities used before model inference.
"""
from typing import Dict


def to_lowercase(text: str) -> str:
    """Lowercase and strip input text."""
    return text.lower().strip()


def is_too_short(text: str, min_len: int = 2) -> bool:
    """Return True when text has fewer than min_len meaningful tokens."""
    return len(text.split()) < min_len


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

