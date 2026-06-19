"""
Build synthetic datasets for EVA text classifiers (CLF1 + CLF2).
"""

from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from slot_fillers import build_clf_slot_pools
from template_library import CLF1_TEMPLATES, CLF2_TEMPLATES


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "datasets"
HARD_NEG_PATH = Path(__file__).resolve().parent / "hard_negatives.json"


def _compact_spaces(s: str) -> str:
    return " ".join(str(s).strip().split())


def _norm_key(text: str, label: str) -> Tuple[str, str]:
    return _compact_spaces(text).lower(), label


def _choice(rng: random.Random, values: List[str]) -> str:
    if not values:
        return ""
    return rng.choice(values)


def _render(template: str, slots: Dict[str, List[str]], rng: random.Random) -> str:
    text = template
    for _ in range(30):
        start = text.find("{")
        if start < 0:
            break
        end = text.find("}", start + 1)
        if end < 0:
            break
        key = text[start + 1 : end].strip()
        if key in slots and slots[key]:
            rep = _choice(rng, slots[key])
            text = text[:start] + rep + text[end + 1 :]
        else:
            break
    return _compact_spaces(text)


def _maybe_style(text: str, rng: random.Random) -> str:
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
        "kindly",
    ]
    suffixes = ["", "", "", "please", "thanks", "pls", "now"]
    punct = ["", "", ".", "?", "!"]

    out = text
    pre = rng.choice(prefixes)
    suf = rng.choice(suffixes)
    p = rng.choice(punct)

    if pre:
        out = f"{pre} {out}"
    if suf:
        out = f"{out} {suf}"
    out = _compact_spaces(out)

    roll = rng.random()
    if roll < 0.08:
        out = out.upper()
    elif roll < 0.22:
        out = out.capitalize()

    if p and not out.endswith((".", "?", "!", "…")):
        out = out + p

    if rng.random() < 0.10:
        out = out.replace(" ", "  ")

    return _compact_spaces(out)


def _typo(text: str, rng: random.Random) -> str:
    if len(text) < 6:
        return text
    out = text
    if rng.random() < 0.05:
        out = out.replace("learn ", "learning ", 1)
    if rng.random() < 0.05:
        out = out.replace("schedule ", "scheduel ", 1)
    if rng.random() < 0.06 and len(out) > 8:
        i = rng.randrange(1, len(out) - 2)
        if out[i].isalpha() and out[i + 1].isalpha():
            out = out[:i] + out[i + 1] + out[i] + out[i + 2 :]
    return out


def _drop_filler_words(text: str, rng: random.Random) -> str:
    if rng.random() > 0.12:
        return text
    return re.sub(r"\b(please|pls|hey eva|eva)\b", "", text, flags=re.I).strip()


@dataclass(frozen=True)
class BuildSpec:
    name: str
    labels: Dict[str, List[str]]
    out_path: Path
    per_template: int
    seed: int


def _load_hard_negatives() -> List[Dict[str, str]]:
    if not HARD_NEG_PATH.exists():
        return []
    with HARD_NEG_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return list(data) if isinstance(data, list) else []


def _build_one(spec: BuildSpec, slots: Dict[str, List[str]]) -> Tuple[int, Dict[str, int]]:
    rng = random.Random(spec.seed)
    augment_per_row = int(os.getenv("AUGMENT_PER_ROW", "2"))
    allowed_labels = set(spec.labels.keys())
    seen: Set[Tuple[str, str]] = set()
    rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}

    for label, templates in spec.labels.items():
        for t_idx, template in enumerate(templates):
            for _ in range(spec.per_template):
                base = _render(template, slots, rng)
                if not base:
                    continue
                variants = {base}
                for _ in range(max(0, augment_per_row)):
                    v = _drop_filler_words(_maybe_style(base, rng), rng)
                    v = _typo(v, rng)
                    variants.add(_compact_spaces(v))

                for v in variants:
                    key = _norm_key(v, label)
                    if key in seen:
                        continue
                    seen.add(key)
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

    if spec.name == "clf2":
        for hn in _load_hard_negatives():
            label = str(hn.get("label") or "").strip()
            text = _compact_spaces(str(hn.get("text") or ""))
            if not label or not text or label not in allowed_labels:
                continue
            variants = {text, _maybe_style(text, rng), _typo(text, rng)}
            for v in variants:
                key = _norm_key(v, label)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "text": v,
                        "label": label,
                        "meta": {"source": "hard_negative", "dataset": spec.name},
                    }
                )
                counts[label] = counts.get(label, 0) + 1

    rng.shuffle(rows)
    spec.out_path.parent.mkdir(parents=True, exist_ok=True)
    with spec.out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(rows), counts


def main() -> None:
    per_template = int(os.getenv("PER_TEMPLATE", "120"))
    seed = int(os.getenv("SEED", "1337"))
    slots = build_clf_slot_pools()

    specs = [
        BuildSpec(
            name="clf1",
            labels=CLF1_TEMPLATES,
            out_path=OUT_DIR / "clf1" / "final" / "clf1.jsonl",
            per_template=per_template,
            seed=seed,
        ),
        BuildSpec(
            name="clf2",
            labels=CLF2_TEMPLATES,
            out_path=OUT_DIR / "clf2" / "final" / "clf2.jsonl",
            per_template=per_template,
            seed=seed + 1,
        ),
    ]

    print("[build_dataset] ROOT:", ROOT)
    print("[build_dataset] PER_TEMPLATE:", per_template)
    print("[build_dataset] AUGMENT_PER_ROW:", int(os.getenv("AUGMENT_PER_ROW", "2")))
    print("[build_dataset] slot counts:", {k: len(v) for k, v in slots.items() if v})

    for spec in specs:
        total, counts = _build_one(spec, slots)
        print(f"[build_dataset] Wrote {spec.name}: {total} rows -> {spec.out_path}")
        for k in sorted(counts.keys()):
            print(f"  - {k}: {counts[k]}")


if __name__ == "__main__":
    main()
