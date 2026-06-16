"""Tests for Phase 4 augmentation utilities."""

import unittest

from augment_utils import (
    augment_example,
    augment_word_order_shuffle,
    chunks_to_example,
    load_hard_negatives,
    merge_datasets,
    split_into_chunks,
)


class ChunkTests(unittest.TestCase):
    def test_split_entity_span(self):
        tokens = ["delete", "my", "Python", "basics", "roadmap"]
        labels = ["O", "O", "B-topic", "B-subtopic", "O"]
        chunks = split_into_chunks(tokens, labels)
        self.assertEqual(len(chunks), 4)  # O, E(topic), E(subtopic), O
        ex = chunks_to_example(chunks, "learning_delete")
        self.assertEqual(ex["tokens"], tokens)
        self.assertEqual(ex["labels"], labels)


class AugmentTests(unittest.TestCase):
    def test_my_and_roadmap_stay_o_in_hard_negative(self):
        path = __import__("pathlib").Path(__file__).resolve().parent / "hard_negatives.json"
        items = load_hard_negatives(str(path), "learning")
        delete_my = next(x for x in items if x["text"] == "delete my Python roadmap")
        for tok, lbl in zip(delete_my["tokens"], delete_my["labels"]):
            if tok.lower() in ("my", "roadmap"):
                self.assertEqual(lbl, "O", f"{tok!r} should be O")

    def test_augment_produces_different_text(self):
        ex = {
            "text": "create python oop roadmap",
            "tokens": ["create", "python", "oop", "roadmap"],
            "labels": ["O", "B-topic", "B-subtopic", "O"],
            "intent": "learning_create",
        }
        cfg = {
            "probabilities": {
                "capitalization": 1.0,
                "typo": 0.0,
                "filler_prefix": 1.0,
                "filler_suffix": 0.0,
                "punctuation": 0.0,
                "abbreviation": 0.0,
                "word_order_shuffle": 0.0,
                "extra_spaces": 0.0,
            },
            "fillers_prefix": ["please"],
            "entity_typos": {},
            "o_token_typos": {},
            "protected_from_typo": ["my"],
        }
        import random

        rng = random.Random(0)
        aug = augment_example(ex, cfg, rng)
        self.assertIsNotNone(aug)
        self.assertNotEqual(aug["text"], ex["text"])
        self.assertEqual(len(aug["tokens"]), len(aug["labels"]))

    def test_word_order_shuffle_keeps_entity_labels(self):
        tokens = ["python", "oop", "roadmap", "create"]
        labels = ["B-topic", "B-subtopic", "O", "O"]
        import random

        rng = random.Random(1)
        new_toks, new_lbls = augment_word_order_shuffle(tokens, labels, rng)
        self.assertEqual(len(new_toks), len(new_lbls))
        merged = list(zip(new_toks, new_lbls))
        topic_labels = [lbl for tok, lbl in merged if lbl.endswith("topic") or lbl == "B-topic"]
        self.assertTrue(any(lbl.startswith("B-topic") for _, lbl in merged))


class MergeTests(unittest.TestCase):
    def test_dedupes_by_text(self):
        raw = [{"text": "a", "tokens": ["a"], "labels": ["O"], "intent": "x"}]
        aug = [{"text": "b", "tokens": ["b"], "labels": ["O"], "intent": "x"}]
        merged = merge_datasets(raw, aug, raw)
        self.assertEqual(len(merged), 2)


if __name__ == "__main__":
    unittest.main()
