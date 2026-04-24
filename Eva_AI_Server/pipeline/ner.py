"""
NER inference module for Phase 7.
Extracts entities from original text using token classification.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from config.settings import settings
from pipeline.delete_entity_fallback import extract_delete_entities_fallback
from pipeline.update_entity_fallback import extract_update_entities_fallback


class NERExtractor:
    """Loads and runs token-level NER model."""

    def __init__(self):
        self.model_dir: Path = settings.NER_MODEL_DIR
        self.tokenizer = None
        self.model = None
        self.id2label: Dict[int, str] = {}
        self.loaded = False
        self.loaded_from: Path = self.model_dir

    def load(self) -> bool:
        """Load model/tokenizer once at startup."""
        if self.loaded:
            return True

        candidates = self._candidate_model_dirs()
        load_errors: List[str] = []

        for candidate in candidates:
            tokenizer, tokenizer_mode = self._load_tokenizer(candidate)
            if tokenizer is None:
                load_errors.append(f"{candidate}: tokenizer load failed")
                continue

            try:
                model = AutoModelForTokenClassification.from_pretrained(str(candidate))
            except Exception as error:
                load_errors.append(f"{candidate}: model load failed: {error}")
                continue

            self.tokenizer = tokenizer
            self.model = model
            self.model.eval()
            self.loaded_from = candidate

            config_labels = getattr(self.model.config, "id2label", {})
            self.id2label = {
                int(label_id): label_name
                for label_id, label_name in config_labels.items()
            }

            self.loaded = True
            # print(f"[NER] Loaded from {candidate} (tokenizer={tokenizer_mode})")
            print(f"[NER] Loaded")
            return True

        print("[NER] Load failed for all candidates.")
        for err in load_errors:
            print(f"[NER]   - {err}")
        self.loaded = False
        return False

    def _candidate_model_dirs(self) -> List[Path]:
        """
        Try primary model dir first, then latest checkpoints.
        """
        candidates: List[Path] = [self.model_dir]
        checkpoint_dirs = list(self.model_dir.glob("checkpoint-*"))

        def _checkpoint_key(path: Path) -> int:
            try:
                return int(path.name.split("-")[-1])
            except Exception:
                return -1

        for checkpoint_dir in sorted(checkpoint_dirs, key=_checkpoint_key, reverse=True):
            if checkpoint_dir not in candidates:
                candidates.append(checkpoint_dir)

        return candidates

    @staticmethod
    def _ensure_roberta_slow_files(model_dir: Path) -> bool:
        """
        Build vocab.json + merges.txt from tokenizer.json for slow tokenizer fallback.
        """
        vocab_file = model_dir / "vocab.json"
        merges_file = model_dir / "merges.txt"

        if vocab_file.exists() and merges_file.exists():
            return True

        tokenizer_json = model_dir / "tokenizer.json"
        if not tokenizer_json.exists():
            return False

        try:
            with tokenizer_json.open("r", encoding="utf-8") as handle:
                tokenizer_data = json.load(handle)
        except Exception:
            return False

        model_data = tokenizer_data.get("model") or {}
        vocab = model_data.get("vocab")
        merges = model_data.get("merges")
        if not isinstance(vocab, dict) or not isinstance(merges, list):
            return False

        try:
            if not vocab_file.exists():
                with vocab_file.open("w", encoding="utf-8") as handle:
                    json.dump(vocab, handle, ensure_ascii=False)

            if not merges_file.exists():
                with merges_file.open("w", encoding="utf-8") as handle:
                    handle.write("#version: 0.2\n")
                    for merge in merges:
                        if isinstance(merge, (list, tuple)) and len(merge) >= 2:
                            handle.write(f"{merge[0]} {merge[1]}\n")
                        elif isinstance(merge, str):
                            handle.write(f"{merge}\n")
            return True
        except Exception:
            return False

    def _load_tokenizer(self, model_dir: Path):
        """
        Try fast tokenizer first; fallback to slow tokenizer derived from tokenizer.json.
        """
        try:
            tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            return tokenizer, "fast"
        except Exception as fast_error:
            print(f"[NER] Fast tokenizer load failed for {model_dir}: {fast_error}")

        if not self._ensure_roberta_slow_files(model_dir):
            return None, ""

        try:
            tokenizer = AutoTokenizer.from_pretrained(str(model_dir), use_fast=False)
            return tokenizer, "slow"
        except Exception as slow_error:
            print(f"[NER] Slow tokenizer load failed for {model_dir}: {slow_error}")
            return None, ""

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

        if intent_hint == "scheduling_update":
            fallback_entities = extract_update_entities_fallback(text)
            for key, value in fallback_entities.items():
                current_value = entities.get(key)
                if current_value in (None, "", [], {}):
                    entities[key] = value

        return entities


# Singleton instance
ner_extractor = NERExtractor()
