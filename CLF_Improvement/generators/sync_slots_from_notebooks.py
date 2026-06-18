"""
Extract slot arrays from InshallahDataset notebooks into config/*.json.

Run from CLF_Improvement/generators:
  python3 sync_slots_from_notebooks.py
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
ADD_NB = WORKSPACE / "DataSets/InshallahDataset/addDatasetGeneration.ipynb"
LEARN_NB = WORKSPACE / "DataSets/InshallahDataset/learningDatasetGeneration.ipynb"


def _nb_source(path: Path) -> str:
    nb = json.loads(path.read_text(encoding="utf-8"))
    parts = []
    for cell in nb.get("cells", []):
        src = cell.get("source", "")
        parts.append(src if isinstance(src, str) else "".join(src))
    return "\n".join(parts)


def _extract(text: str, var_name: str) -> list:
    m = re.search(rf"{re.escape(var_name)}\s*=\s*\[", text)
    if not m:
        return []
    start = text.find("[", m.start())
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return ast.literal_eval(text[start : i + 1])
    return []


def main() -> None:
    add_src = _nb_source(ADD_NB)
    learn_src = _nb_source(LEARN_NB)

    sched = {
        "collaborators": _extract(add_src, "collaborators"),
        "task_names": _extract(add_src, "task_names"),
        "dates": _extract(add_src, "dates"),
        "times": _extract(add_src, "times"),
        "durations": _extract(add_src, "durations"),
        "priorities": _extract(add_src, "priorities"),
        "statuses": _extract(add_src, "statutes"),
        "days": _extract(add_src, "days"),
    }
    learn = {
        "topics": _extract(learn_src, "topics"),
        "subtopics": _extract(learn_src, "subtopics"),
        "durations": _extract(learn_src, "durations"),
        "start_dates": _extract(learn_src, "start_dates"),
        "persons": _extract(learn_src, "persons"),
    }

    cfg = ROOT / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "scheduling_slots.json").write_text(
        json.dumps(sched, ensure_ascii=False), encoding="utf-8"
    )
    (cfg / "learning_slots.json").write_text(
        json.dumps(learn, ensure_ascii=False), encoding="utf-8"
    )

    ner_cfg = WORKSPACE / "NER_Improvement" / "config"
    ner_cfg.mkdir(parents=True, exist_ok=True)
    (ner_cfg / "scheduling_slots.json").write_text(
        json.dumps(sched, ensure_ascii=False), encoding="utf-8"
    )
    (ner_cfg / "learning_slots.json").write_text(
        json.dumps(learn, ensure_ascii=False), encoding="utf-8"
    )

    print("[sync_slots] scheduling:", {k: len(v) for k, v in sched.items()})
    print("[sync_slots] learning:", {k: len(v) for k, v in learn.items()})


if __name__ == "__main__":
    main()
