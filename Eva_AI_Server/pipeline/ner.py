"""
NER inference module for Phase 7.
Extracts entities from original text using token classification.
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from config.settings import settings
from pipeline.delete_entity_fallback import extract_delete_entities_fallback


class NERExtractor:
    """Loads and runs token-level NER model."""

    def __init__(self):
        self.model_dir: Path = settings.NER_MODEL_DIR
        self.tokenizer = None
        self.model = None
        self.id2label: Dict[int, str] = {}
        self.loaded = False

    def load(self) -> bool:
        """Load model/tokenizer once at startup."""
        if self.loaded:
            return True

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
            self.model = AutoModelForTokenClassification.from_pretrained(str(self.model_dir))
            self.model.eval()

            config_labels = getattr(self.model.config, "id2label", {})
            self.id2label = {
                int(label_id): label_name
                for label_id, label_name in config_labels.items()
            }

            self.loaded = True
            print(f"[NER] Loaded from {self.model_dir}")
            return True
        except Exception as e:
            print(f"[NER] Load failed: {e}")
            self.loaded = False
            return False

    @staticmethod
    def _parse_tag(tag: str) -> Tuple[str, str]:
        """Split BIO tag into (prefix, entity_type)."""
        if tag == "O" or "-" not in tag:
            return "O", ""
        prefix, entity_type = tag.split("-", 1)
        return prefix, entity_type

    @staticmethod
    def _finalize(entities: Dict[str, List[str]], entity_type: str, text: str):
        if entity_type and text.strip():
            entities.setdefault(entity_type, []).append(text.strip())

    def _aggregate_entities(self, text: str, tags_with_offsets: List[Tuple[str, int, int]]) -> Dict[str, Any]:
        """
        Convert BIO token predictions into merged entity strings.
        Returns dict[str, str|list[str]].
        """
        grouped: Dict[str, List[str]] = {}
        current_type = ""
        current_start = -1
        current_end = -1

        for tag, start, end in tags_with_offsets:
            prefix, entity_type = self._parse_tag(tag)

            if prefix == "O":
                if current_type:
                    self._finalize(grouped, current_type, text[current_start:current_end])
                    current_type = ""
                    current_start = -1
                    current_end = -1
                continue

            gap_text = ""
            if current_type and current_end >= 0 and start >= current_end:
                gap_text = text[current_end:start]

            # Some model outputs emit B- tags on subword/adjacent tokens of the same
            # entity (e.g., "F" + "aisal"). Treat those as continuation.
            b_should_split = prefix == "B" and not (
                current_type
                and entity_type == current_type
                and start <= current_end + 1
                and (not gap_text.strip())
            )

            if (
                b_should_split
                or not current_type
                or entity_type != current_type
                or start > current_end + 1
            ):
                if current_type:
                    self._finalize(grouped, current_type, text[current_start:current_end])
                current_type = entity_type
                current_start = start
                current_end = end
            else:
                current_end = end

        if current_type:
            self._finalize(grouped, current_type, text[current_start:current_end])

        result: Dict[str, Any] = {}
        for key, values in grouped.items():
            if not values:
                continue
            result[key] = values[0] if len(values) == 1 else values

        return result

    def extract(self, text: str, intent_hint: str = "") -> Dict[str, Any]:
        """Extract entities from original text."""
        if not self.loaded and not self.load():
            raise RuntimeError("NER model is not loaded")

        if not text:
            return {}

        encoded = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            return_offsets_mapping=True,
        )

        offsets = encoded.pop("offset_mapping")[0].tolist()

        with torch.no_grad():
            logits = self.model(**encoded).logits
            pred_ids = torch.argmax(logits, dim=-1)[0].tolist()

        tags_with_offsets: List[Tuple[str, int, int]] = []
        for pred_id, (start, end) in zip(pred_ids, offsets):
            if start == end:
                continue

            tag = self.id2label.get(pred_id, "O")
            tags_with_offsets.append((tag, int(start), int(end)))

        entities = self._aggregate_entities(text, tags_with_offsets)

        if intent_hint == "scheduling_delete":
            fallback_entities = extract_delete_entities_fallback(text)
            for key, value in fallback_entities.items():
                current_value = entities.get(key)
                if current_value in (None, "", [], {}):
                    entities[key] = value

        return entities


# Singleton instance
ner_extractor = NERExtractor()
