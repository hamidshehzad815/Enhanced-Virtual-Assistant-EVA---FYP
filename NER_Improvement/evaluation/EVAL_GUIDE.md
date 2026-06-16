# Phase 8 — Evaluation Guide

## Quick adversarial run (automated)

From project root (uses `Eva_AI_Server` models + Phase 6 pipeline):

```bash
cd NER_Improvement/evaluation
python3 run_adversarial_eval.py
```

Outputs:
- `adversarial_report.json` — full pass/fail per case
- `errors/adversarial_failures.json` — failures grouped for template/augmentation feedback

Exit code `1` if any case fails (useful before/after retrain).

## Compare training F1 (after Colab)

```bash
python3 compare_f1.py baseline_f1_learning.json augmented_f1_learning.json
```

## Manual smoke tests (end-to-end `/process`)

Restart AI server, then try:

**Scheduling**
- `add physics exam on Monday at 5PM`
- `add physcis exam on munday at 5pm` (typos)
- `physics exam Monday 5PM add` (word order)
- `delete my morning standup`
- `when i am productive on tuesday`

**Learning**
- `create python oop roadmap`
- `delete my Python roadmap`
- `learn py begginer for 2 wks`
- `pause my Python oop roadmap`

Check `entities.raw` / `entities.scoped` in the response.

## When something fails

1. Read `errors/adversarial_failures.json`
2. Add hard negatives → `generators/hard_negatives.json`
3. Add targeted examples → `generators/targeted_examples.json`
4. Rebuild data: `augment_dataset.py` + `balance_dataset.py`
5. Retrain on Colab → deploy → re-run `run_adversarial_eval.py`
