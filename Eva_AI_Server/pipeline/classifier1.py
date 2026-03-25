"""
Model 1 inference module.
Input type classifier with 5 classes:
command, general, out_of_scope, confirmation, multiple_command.
"""
import json
from pathlib import Path
from typing import Dict

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config.settings import settings


class Classifier1:
    """Loads and runs the Phase 4 input type classifier."""

    def __init__(self):
        self.model_dir: Path = settings.CLF1_MODEL_DIR
        self.tokenizer = None
        self.model = None
        self.id2label: Dict[int, str] = {}
        self.loaded = False

    def _load_id2label(self) -> Dict[int, str]:
        """Load label mapping from label_map.json or model config."""
        label_map_path = self.model_dir / "label_map.json"

        if label_map_path.exists():
            with open(label_map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            id2label = {
                int(label_id): label_name
                for label_id, label_name in data.get("id2label", {}).items()
            }
            if id2label:
                return id2label

        config_labels = getattr(self.model.config, "id2label", {}) if self.model else {}
        return {int(label_id): label_name for label_id, label_name in config_labels.items()}

    def load(self) -> bool:
        """Load model and tokenizer once at startup."""
        if self.loaded:
            return True

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
            self.model = AutoModelForSequenceClassification.from_pretrained(str(self.model_dir))
            self.model.eval()
            self.id2label = self._load_id2label()
            self.loaded = True
            print(f"[Model1] Loaded from {self.model_dir}")
            return True
        except Exception as e:
            print(f"[Model1] Load failed: {e}")
            self.loaded = False
            return False

    def predict(self, text: str) -> Dict[str, object]:
        """Predict input type label, confidence, and full probabilities."""
        if not self.loaded and not self.load():
            raise RuntimeError("Model1 is not loaded")

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=64,
        )

        with torch.no_grad():
            logits = self.model(**inputs).logits
            probabilities = torch.softmax(logits, dim=-1)[0]

        pred_id = int(torch.argmax(probabilities).item())
        label = self.id2label.get(pred_id, str(pred_id))

        all_probs: Dict[str, float] = {}
        for idx, prob in enumerate(probabilities.tolist()):
            all_probs[self.id2label.get(idx, str(idx))] = float(prob)

        return {
            "label": label,
            "confidence": float(probabilities[pred_id].item()),
            "all_probs": all_probs,
        }


# Singleton instance
classifier1 = Classifier1()
