"""
Build synthetic datasets for EVA text classifiers (CLF1 + CLF2).

Outputs:
  datasets/clf1/final/clf1.jsonl
  datasets/clf2/final/clf2.jsonl

JSONL format:
  {"text": "...", "label": "...", "meta": {...}}
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
OUT_DIR = ROOT / "datasets"


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _compact_spaces(s: str) -> str:
    return " ".join(str(s).strip().split())


def _choice(rng: random.Random, values: List[str]) -> str:
    if not values:
        return ""
    return rng.choice(values)


def _render(template: str, slots: Dict[str, List[str]], rng: random.Random) -> str:
    # simple "{slot}" replacement; unknown slots are left as-is
    text = template
    for _ in range(20):  # cap replacements if template repeats placeholders
        start = text.find("{")
        if start < 0:
            break
        end = text.find("}", start + 1)
        if end < 0:
            break
        key = text[start + 1 : end].strip()
        if key and key in slots:
            rep = _choice(rng, slots[key])
            text = text[:start] + rep + text[end + 1 :]
        else:
            # skip unknown placeholder
            text = text[:start] + text[start : end + 1] + text[end + 1 :]
            break
    return _compact_spaces(text)


def _maybe_style(text: str, rng: random.Random) -> str:
    """
    Light text augmentation for classifiers (keeps meaning, adds realism).
    """
    prefixes = [
        "",
        "hey eva,",
        "eva,",
        "please",
        "pls",
        "can you",
        "could you",
        "i want to",
        "i need to",
    ]
    suffixes = ["", "", "", "please", "thanks", "pls", "now"]
    punct = ["", "", ".", "?", "!", "…"]

    out = text
    pre = rng.choice(prefixes)
    suf = rng.choice(suffixes)
    p = rng.choice(punct)

    if pre:
        out = f"{pre} {out}"
    if suf:
        out = f"{out} {suf}"
    out = _compact_spaces(out)

    # random casing
    roll = rng.random()
    if roll < 0.10:
        out = out.upper()
    elif roll < 0.25:
        out = out.capitalize()

    # add punctuation at end
    if p and not out.endswith((".", "?", "!", "…")):
        out = out + p

    # occasional double spaces/newlines (preprocessor will normalize)
    if rng.random() < 0.08:
        out = out.replace(" ", "  ")
    if rng.random() < 0.02:
        out = out.replace(" ", "\n", 1)

    return _compact_spaces(out)


def _typo(text: str, rng: random.Random) -> str:
    """
    Very small typo injection (safe). Example: 'schedule' -> 'scheduel'.
    """
    if len(text) < 8 or rng.random() > 0.06:
        return text
    i = rng.randrange(1, len(text) - 2)
    if not text[i].isalpha() or not text[i + 1].isalpha():
        return text
    # swap two adjacent letters
    return text[:i] + text[i + 1] + text[i] + text[i + 2 :]


@dataclass(frozen=True)
class BuildSpec:
    name: str
    template_path: Path
    out_path: Path
    per_template: int
    seed: int


def _build_one(spec: BuildSpec) -> Tuple[int, Dict[str, int]]:
    data = _load_json(spec.template_path)
    labels: Dict[str, List[str]] = data.get("labels") or {}
    slots: Dict[str, List[str]] = data.get("slots") or {}

    rng = random.Random(spec.seed)
    rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    augment_per_row = int(os.getenv("AUGMENT_PER_ROW", "3"))

    for label, templates in labels.items():
        for t_idx, template in enumerate(templates):
            for i in range(spec.per_template):
                base = _render(template, slots, rng)
                if not base:
                    continue

                variants = [base]
                for _ in range(max(0, augment_per_row)):
                    v = _maybe_style(base, rng)
                    v = _typo(v, rng)
                    variants.append(v)

                for v in variants:
                    v = _compact_spaces(v)
                    if not v:
                        continue
                    rows.append(
                        {
                            "text": v,
                            "label": label,
                            "meta": {
                                "source": "template",
                                "template_id": f"{label}__t{t_idx}",
                                "dataset": spec.name,
                            },
                        }
                    )
                    counts[label] = counts.get(label, 0) + 1

    rng.shuffle(rows)
    _ensure_parent(spec.out_path)
    with spec.out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(rows), counts


def main() -> None:
    per_template = int(os.getenv("PER_TEMPLATE", "250"))  # scale data size here
    seed = int(os.getenv("SEED", "1337"))

    specs = [
        BuildSpec(
            name="clf1",
            template_path=TEMPLATES_DIR / "clf1" / "templates.json",
            out_path=OUT_DIR / "clf1" / "final" / "clf1.jsonl",
            per_template=per_template,
            seed=seed,
        ),
        BuildSpec(
            name="clf2",
            template_path=TEMPLATES_DIR / "clf2" / "templates.json",
            out_path=OUT_DIR / "clf2" / "final" / "clf2.jsonl",
            per_template=per_template,
            seed=seed + 1,
        ),
    ]

    print("[build_dataset] ROOT:", ROOT)
    print("[build_dataset] PER_TEMPLATE:", per_template)
    print("[build_dataset] SEED:", seed)
    print("[build_dataset] AUGMENT_PER_ROW:", int(os.getenv("AUGMENT_PER_ROW", "3")))

    for spec in specs:
        total, counts = _build_one(spec)
        print(f"[build_dataset] Wrote {spec.name}: {total} rows -> {spec.out_path}")
        for k in sorted(counts.keys()):
            print(f"  - {k}: {counts[k]}")


if __name__ == "__main__":
    main()

