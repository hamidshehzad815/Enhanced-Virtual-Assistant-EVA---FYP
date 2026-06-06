"""
Model 2 inference module.
Intent classifier used after Model 1 identifies command input.
"""
import json
import pickle
from pathlib import Path
from typing import Dict

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config.settings import settings


class Classifier2:
    """Loads and runs the Phase 6 intent classifier."""

    def __init__(self):
        self.model_dir: Path = settings.CLF2_MODEL_DIR
        self.tokenizer = None
        self.model = None
        self.id2label: Dict[int, str] = {}
        self.loaded = False

    def _load_labels_from_label_map(self) -> Dict[int, str]:
        label_map_path = self.model_dir / "label_map.json"
        if not label_map_path.exists():
            return {}

        with open(label_map_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        id2label = {
            int(label_id): label_name
            for label_id, label_name in data.get("id2label", {}).items()
        }
        return id2label

    def _load_labels_from_label_encoder(self) -> Dict[int, str]:
        label_encoder_path = self.model_dir / "label_encoder.pkl"
        if not label_encoder_path.exists():
            return {}

        try:
            with open(label_encoder_path, "rb") as f:
                encoder = pickle.load(f)
            classes = list(getattr(encoder, "classes_", []))
            return {idx: str(label) for idx, label in enumerate(classes)}
        except Exception as e:
            print(f"[Model2] label_encoder load warning: {e}")
            return {}

    def _load_labels_from_model_config(self) -> Dict[int, str]:
        config_labels = getattr(self.model.config, "id2label", {}) if self.model else {}
        return {int(label_id): label_name for label_id, label_name in config_labels.items()}

    def _load_id2label(self) -> Dict[int, str]:
        for loader in (
            self._load_labels_from_label_map,
            self._load_labels_from_label_encoder,
            self._load_labels_from_model_config,
        ):
            id2label = loader()
            if id2label:
                return id2label
        return {}

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
            # print(f"[Model2] Loaded from {self.model_dir}")
            print(f"[Model2] Loaded")
            return True
        except Exception as e:
            print(f"[Model2] Load failed: {e}")
            self.loaded = False
            return False

    def predict(self, text: str) -> Dict[str, object]:
        """Predict intent label, confidence, and full probabilities."""
        if not self.loaded and not self.load():
            raise RuntimeError("Model2 is not loaded")

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
classifier2 = Classifier2()
