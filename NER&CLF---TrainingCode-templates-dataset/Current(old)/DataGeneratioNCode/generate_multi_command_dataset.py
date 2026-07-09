#!/usr/bin/env python3
"""Generate a multi-command dataset by pairing scheduling command samples
with learning command samples.

Source files in this folder:
- !LearningNER.json  -> scheduling intents:
                        add, delete, show, update, behavioral
- LearningNER.json   -> learning intents:
                        learning_create, learning_delete, learning_update

The script samples N examples from each intent in both groups,
then pairs one scheduling command with one learning command to
create multi_command examples.

Each output row is:
{
  "text": "<scheduling_command> and also <learning_command>",
  "intent": "multi_command"
}

The connector is rotated across natural variants so the dataset
is not repetitive.
"""

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────

SCHEDULING_INTENTS = ["add", "delete", "show", "update", "behavioral"]

LEARNING_INTENTS = ["learning_create", "learning_delete", "learning_update"]

OUTPUT_INTENT = "multi_command"

SCHEDULING_SOURCE_FILE = "!LearningNER.json"
LEARNING_SOURCE_FILE   = "LearningNER.json"

# Samples to take per intent
SCHEDULING_SAMPLES_PER_INTENT = 200   # 200 × 5 = 1000 scheduling samples
LEARNING_SAMPLES_PER_INTENT   = 333   # 333 × 3 = 999 ≈ 1000 learning samples

CONNECTORS = [
    " and then ",
    " and ",
    " then ",
    " then also ",
    " plus ",
    " after that, ",
    " followed by ",
    " as well as ",
    " later, ",
    " afterward, ",
    " next, ",
    ", and also ",
    ", then ",
]


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def extract_text(item: Any) -> Optional[str]:
    if isinstance(item, str):
        cleaned = item.strip()
        return cleaned or None

    if isinstance(item, dict):
        for key in ("text", "Text", "sentence", "utterance", "content", "message"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for value in item.values():
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def load_intent_texts(path: Path, intent_name: str) -> List[str]:
    """Load all unique texts for a specific intent from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}")

    texts: List[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item_intent = str(item.get("intent", "")).strip()
        if item_intent != intent_name:
            continue
        text = extract_text(item)
        if text:
            texts.append(text)

    # Deduplicate while preserving order
    seen = set()
    unique: List[str] = []
    for text in texts:
        if text not in seen:
            seen.add(text)
            unique.append(text)

    return unique


def sample_texts(texts: Sequence[str], count: int, label: str) -> List[str]:
    """Sample `count` texts. Use replacement if pool is smaller than count."""
    if count <= 0:
        return []
    pool = list(texts)
    if not pool:
        raise ValueError(f"No texts available for intent: {label}")

    if len(pool) >= count:
        return random.sample(pool, count)

    print(
        f"  Warning: '{label}' has only {len(pool)} unique texts. "
        f"Sampling with replacement to reach {count}."
    )
    return [random.choice(pool) for _ in range(count)]


def load_all_intents(
    path: Path,
    intents: List[str],
    samples_per_intent: int
) -> List[str]:
    """
    Load and sample texts from multiple intents in one file.
    Returns a flat shuffled list of all sampled texts.
    """
    all_texts: List[str] = []
    for intent in intents:
        texts = load_intent_texts(path, intent)
        print(f"  {intent}: {len(texts)} unique texts available")
        sampled = sample_texts(texts, samples_per_intent, intent)
        all_texts.extend(sampled)

    random.shuffle(all_texts)
    return all_texts


# ──────────────────────────────────────────────────────────────────────────────
# PAIR BUILDER
# ──────────────────────────────────────────────────────────────────────────────

def build_pairs(
    scheduling_pool: List[str],
    learning_pool: List[str],
) -> List[Dict[str, str]]:
    """
    Pair each scheduling command with a learning command.
    If pools are different sizes, trim to the smaller one.
    """
    min_len = min(len(scheduling_pool), len(learning_pool))

    if len(scheduling_pool) != len(learning_pool):
        print(
            f"  Pool size mismatch: {len(scheduling_pool)} scheduling vs "
            f"{len(learning_pool)} learning. Trimming to {min_len}."
        )
        scheduling_pool = scheduling_pool[:min_len]
        learning_pool   = learning_pool[:min_len]

    rows: List[Dict[str, str]] = []
    for index, (sched_text, learn_text) in enumerate(
        zip(scheduling_pool, learning_pool)
    ):
        connector   = CONNECTORS[index % len(CONNECTORS)]
        merged_text = f"{sched_text}{connector}{learn_text}"
        rows.append({"text": merged_text, "intent": OUTPUT_INTENT})

    random.shuffle(rows)
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--folder",
        default=".",
        help="Folder containing !LearningNER.json and LearningNER.json"
    )
    parser.add_argument(
        "--scheduling-per-intent",
        type=int,
        default=SCHEDULING_SAMPLES_PER_INTENT,
        help=f"Samples per scheduling intent (default: {SCHEDULING_SAMPLES_PER_INTENT})"
    )
    parser.add_argument(
        "--learning-per-intent",
        type=int,
        default=LEARNING_SAMPLES_PER_INTENT,
        help=f"Samples per learning intent (default: {LEARNING_SAMPLES_PER_INTENT})"
    )
    args, _unknown = parser.parse_known_args()

    folder           = Path(args.folder).resolve()
    scheduling_path  = folder / SCHEDULING_SOURCE_FILE
    learning_path    = folder / LEARNING_SOURCE_FILE

    # ── Load scheduling intents ──────────────────────────────────────────────
    print(f"\nLoading scheduling intents from: {scheduling_path}")
    scheduling_pool = load_all_intents(
        scheduling_path,
        SCHEDULING_INTENTS,
        args.scheduling_per_intent
    )
    print(f"  Total scheduling samples: {len(scheduling_pool)}")

    # ── Load learning intents ────────────────────────────────────────────────
    print(f"\nLoading learning intents from: {learning_path}")
    learning_pool = load_all_intents(
        learning_path,
        LEARNING_INTENTS,
        args.learning_per_intent
    )
    print(f"  Total learning samples: {len(learning_pool)}")

    # ── Build pairs ──────────────────────────────────────────────────────────
    print("\nBuilding multi_command pairs...")
    rows = build_pairs(scheduling_pool, learning_pool)
    print(f"  Total pairs generated: {len(rows)}")

    # ── Save output ──────────────────────────────────────────────────────────
    out_path = folder / "multiCommandDataset.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(rows)} multi_command rows to: {out_path}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\nSummary:")
    print(f"  Scheduling intents  : {SCHEDULING_INTENTS}")
    print(f"  Learning intents    : {LEARNING_INTENTS}")
    print(f"  Samples per scheduling intent : {args.scheduling_per_intent}")
    print(f"  Samples per learning intent   : {args.learning_per_intent}")
    print(f"  Total output rows   : {len(rows)}")


if __name__ == "__main__":
    main()