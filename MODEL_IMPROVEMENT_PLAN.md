# EVA Model Improvement Plan — CLF1 / CLF2 / NER

Consolidated plan from the diagnosis sessions. **Phases are ordered by dependency.**
Doing them out of order wastes work — Phase 1 in particular gates everything after it.

---

## 0. The core diagnosis

Two findings explain why a year of template work didn't converge:

**A. The ruler is broken.** The generators do `rng.shuffle(all_examples)` then slice 90/10,
so the same template (and literal duplicate strings) land on both sides:

| | test size | exact duplicate of a train row | same structure seen in train |
|---|---|---|---|
| CLF1 | 996 | **42.7%** | **81.2%** |
| CLF2 | 2792 | **20.6%** | **91.2%** |

100% F1 is measuring **memorization**. It was pinned at the ceiling before any change was made,
so it could never signal whether a change helped. **A year was spent tuning against a number
that could not move.**

**B. A lot of the "data" is padding.** Classes are cycled to hit target counts:

| | total | unique | waste |
|---|---|---|---|
| CLF1 total | 8962 | 6542 | 27% |
| CLF1 `help` | 454 | **165** | 64% |
| CLF2 total | 25127 | 20783 | 17% |
| CLF2 `behavioral` | 2057 | **104** | **95%** |

Duplication adds zero information, inflates confidence, and is the mechanism of the leak above.

---

## 1. Evidence inventory (what we actually verified)

| # | Finding | Evidence | Type |
|---|---|---|---|
| 1 | `help` class has **no handler** | `help` appears nowhere in `main.py` / `router.py`; `general_handlers` has only general/oos/confirmation/multiple_command → falls to `unknown_input_type` | **Plumbing** |
| 2 | CLF1 is **right** on help | `where do i start`→help **0.974**, `guide me please`→**0.815**, `teach me how to use`→**0.970**, `what languages you support`→**0.951** | Model OK |
| 3 | `general` replies poor | Classification correct (`how are you?`→general **0.993**) — reply text comes from `handle_general` → Gemini prompt | **Prompt** |
| 4 | `road map` → wrong intent | `roadmap` in **1933** CLF2 rows, `road map` in **0** → `scheduling_add` @ **0.985** (confidently wrong) | Data gap |
| 5 | `how to add a roadmap` → `out_of_scope` @ **0.913** | help `"how to"` = **1** example; OOS `"how do i/how to"` = **22** (e.g. "how do i get rid of sore throat") → data teaches "how to…" = OOS | Data collision |
| 6 | NER subword split | `17july` → `date="17"`, `time=["ju","8am"]` — **FIXED** in commit `929f0858` | Fixed |
| 7 | NER exposes **no confidence** | `ner.py:274` uses `argmax`, discards the softmax | Gap |
| 8 | `moday` unresolvable | NER tags the slot correctly (`date="moday"`); Duckling can't parse the value | Preprocessing |
| 9 | Closed-class is deterministic | Duckling already parses `17july`/`5pm`/`next friday` with zero training | Architecture |

**Roughly 80% of the visible complaints are plumbing + prompts, not model quality.**
Items 4 and 5 are the genuine model gaps — and both are **confidently wrong**, which is why a
max-softmax confidence gate cannot be the primary fix.

---

## Phase 0 — Stop the bleeding (no model work)

Highest value per effort. Fixes most of what users actually hit. **Do this first.**

- [ ] **0.1 Add `handle_help`** — Gemini-backed, with a system prompt describing EVA's capabilities
      (scheduling add/show/update/delete, learning roadmaps, quiet hours, analytics, collaborators).
      CLF1 already predicts `help` correctly at 0.8–0.97; the pipeline just drops it.
      Answers open-ended help phrasings with **no training data**.
- [ ] **0.2 Fix the `general` reply prompt** — classification is already correct; only the
      generated text is bad (`how are you?`, `what's going on`).

**Exit criteria:** every message in the help screenshot returns a useful answer. No retraining.

---

## Phase 1 — Fix the measurement (gates everything else)

Nothing downstream is verifiable until this exists. **Do not skip or reorder.**

- [ ] **1.1 Dedupe every class.** Remove the cycling loops from the generators
      (`generate_clf1.py` `help` cycling → 438; `EXTRA_COMMAND_TEXTS` cycling → 300 *(added by us — same flaw)*;
      `generate_clf2.py` `behavioral`). Keep every **unique** example; delete only copies.
- [ ] **1.2 Template-disjoint split.** Split by **template**, not by row. Hold out whole templates
      *and* unseen slot values. Assert zero exact-duplicate overlap between train and test.
- [ ] **1.3 Real eval set.** Hand-label **300–500 real messages** from `conversation_history` in Mongo
      (a year of real testing traffic). This is the *measurement* set — it does not need to be training data.
- [ ] **1.4 Re-score the current models** on 1.2 + 1.3 to get the honest baseline.

**Expect F1 to crash from 100% to roughly 50–70%. That crash is the deliverable** — it is the first
number that responds to change.

**Exit criteria:** a metric that moves when the data changes, and a documented baseline.

---

## Phase 2 — Shrink the problem (architecture)

Less for the models to learn = less to overfit, and it deletes an unlearnable boundary.

- [ ] **2.1 Collapse `help` / `general` / `out_of_scope` into one Gemini "chat" branch.**
      All three terminate in "Gemini generates text" anyway — the classification buys nothing.
      CLF1 becomes: `command` / `multiple_command` / `confirmation` / **chat**.
      - Kills the help-vs-OOS boundary (finding #5), which is **unlearnable from templates**:
        `how to add a roadmap` vs `how to cook pasta` differ only by **domain knowledge**, not grammar,
        and the phrasing space is unbounded.
      - Subsumes Phase 0.1/0.2 as the permanent design.
      - CLF1 keeps only the decision it is genuinely strong at (`command` @ 1.000 in every observed sample).
- [ ] **2.2 Take closed-class entities off NER.**
      `date`, `time`, `priority`, `status`, `duration` → Duckling + lexicons (already generalize perfectly).
      NER keeps only the open-class spans: `task_name`, `topic`, `subtopic`.

**Exit criteria:** CLF2 + NER (the FYP contribution) remain the command path; the chat path needs no training data.

---

## Phase 3 — Deterministic preprocessing (no model, µs latency)

- [ ] **3.1 Domain-constrained spell correction.** Replace the hardcoded 25-entry map in
      `pipeline/spell_correction.py` with a lexicon **auto-derived from `SlotArrays/` + templates**
      (so it never drifts). Correct only out-of-vocabulary tokens, rank by **Jaro-Winkler**
      (prefix-weighted), optionally position-aware (after `on`/`from`/`starting` → date candidates only).
      - Fixes `moday`→`monday`: plain edit distance ties `monday`/`today`; the prefix bonus breaks it correctly.
      - Scope is ~60 closed-class words. **Open-class task names do not need spelling correction.**
- [ ] **3.2 Compound normalization.** `road map` / `road-map` → `roadmap` before classification.
      Note: `road map` is **valid English** — no spell checker (or LLM "fix spelling") would ever touch it.
- [ ] **3.3 Fuzzy task-name matching** in delete/show/update against the user's own tasks,
      instead of correcting titles.

---

## Phase 4 — Model quality (now measurable)

- [ ] **4.1 Diversity, not volume.** Fix `behavioral` (104 unique) and `help`/chat coverage.
      Add real phrasing variety + typo/keyboard-noise augmentation (~20% of rows).
      Add the `road map` class of surface variants.
- [ ] **4.2 Training hygiene.** Label smoothing (stops softmax saturation), early stopping against the
      **real** validation set, lower LR, fewer epochs.
- [ ] **4.3 Calibration.** Temperature scaling — fit one scalar `T` on held-out real data, divide logits by `T`.
      Preserves accuracy exactly; fixes over-confidence.
      *Only meaningful once Phase 1 exists — calibrating on leaked templates calibrates to a fiction.*
- [ ] **4.4 Re-measure** against the Phase 1 baseline.

---

## Phase 5 — Gemini fallback on CLF1 + CLF2 (only after Phases 1–4)

**Design:** when a classifier is unsure, Gemini **decides the route _and_ cleans the input**.
Entity extraction **stays with NER** — Gemini never returns entities.

```
input → CLF1 / CLF2
          conf ok   → normal path (models: fast, free, deterministic)
          conf bad  → Gemini → { input_type, intent, cleaned_text }
                              → cleaned_text → NER → handler
```

**Why this shape:** the models are trained on clean, well-formed template text; real input is messy.
Gemini's job is to **map off-distribution input onto the distribution the models were trained on** —
messy in → clean in → models work. Extraction stays with NER, so there is no hallucinated-entity path
(see PR #54/#55 — "Stop delete fallback inventing fake task_name" — that failure mode is already proven here).

- [ ] **5.1 Trigger = calibrated confidence **OR** OOD score.** Not raw max-softmax.
      **Justification:** `road map` @ **0.985** and `how to add a roadmap` @ **0.913** were both
      *confidently wrong* — a raw `< 0.7` gate fires on **neither**, i.e. it would miss exactly the cases
      that motivated this work. Requires Phase 4.3 (temperature scaling) + an OOD score
      (energy, or k-NN / Mahalanobis distance in embedding space).
- [ ] **5.2 Gemini fallback call** returning a strict schema: `{ input_type, intent, cleaned_text }`.
      Validate `input_type`/`intent` against the known label sets; reject and fall back to the model
      output if invalid.
- [ ] **5.3 Rewrite guardrail (hard requirement).** The prompt must constrain to:
      *fix spelling/grammar only; preserve every content word verbatim; add nothing; remove nothing.*
      Otherwise `add physcis exam on moday` → *"Add the physics examination on Monday"* and NER extracts a
      task title the user never typed — invention through the back door.
- [ ] **5.4 Duckling still owns date/time resolution.** Gemini may normalize a span
      (`moday` → `monday`) but must never emit a resolved date. Otherwise timezone correctness is lost
      and dates get hallucinated.
- [ ] **5.5 One combined call, not three.** A single fallback returning input_type + intent + cleaned_text.
      Three independent fallbacks = up to 3 sequential Gemini calls + the reply call = 4 round-trips/turn.
- [ ] **5.6 Defined degradation path.** Today a Gemini outage only degrades *wording* (it runs after the work).
      Putting it in NLU makes correctness depend on it — the same shape as the Duckling hard-dependency bug
      (fixed in `929f0858`). On Gemini failure/timeout: use the model's original prediction; never hard-fail.
- [ ] **5.7 Expose NER confidence** — `softmax` the logits (`ner.py:274` currently `argmax`s them away),
      aggregate per entity (min/mean over its tokens). Used for telemetry + the "required entity missing"
      re-prompt, **not** for swapping in Gemini extraction.

---

## Phase 6 — Only if Phases 1–5 leave the real number short

- [ ] **SetFit** (few-shot classification over sentence-transformer embeddings) and/or **GLiNER** (few/zero-shot NER).
      These lean on pretrained semantics instead of memorizing templates, so they generalize from ~50–100 real
      examples per class. Directly addresses "templates are limited" by removing the need for template volume.

---

## Rejected approaches (and why)

| Proposal | Why rejected |
|---|---|
| **LLM API on every input** | Would have fixed **none** of the three help failures — the model was already right; the pipeline dropped the answer. Pays latency + cost + non-determinism to change nothing. |
| **Replace NER with LLM + rule-based extraction** | Discards the FYP's core contribution; inverts difficulty (LLM does the hard part non-deterministically, rules do the easy part); breaks the entity contract the handlers + test suite are built on. |
| **Gemini fallback that returns *entities*** | Hallucination lands directly on the destructive path (delete/update). Already burned by this: PR #54/#55 "Stop delete fallback inventing fake task_name". Phase 5 keeps extraction with NER and gives Gemini only route + cleaned text. |
| **Reduce unique examples so confidence drops** | Overconfidence comes from data being **trivially separable**, not from volume. 650 templates are as separable as 6500 → same ~1.0 confidence on a strictly worse model. *(Deleting duplicates is different — and is Phase 1.1.)* |
| **Max-softmax confidence gate as the primary fix** | Miscalibrated: 0.985 and 0.913 confidently wrong. |
| **General spell-check libraries (TextBlob/PySpellChecker)** | Optimize for general-English frequency → `moday`→`today`. And they cannot fix `road map` (nothing is misspelled). |

---

## Measurement discipline

1. Every change is scored on the **Phase 1** split + real eval set. No exceptions.
2. Report **per-class** F1, not just macro — `help`/`behavioral` will hide behind `command`'s mass.
3. Track **calibration (ECE)** alongside F1, not just accuracy.
4. Any change that doesn't move the real number gets **reverted**, not kept "just in case".

## Related GitHub issues

- #57 — `don't do it` classified as YES (data loss)
- #58 — time-only delete ignores the time filter
- #62 — learning_create duration gate → counter-offer
- #63 — "See roadmap" action after plan creation
- #64 — multiple learning sessions per day
- *(to file)* — missing `help` handler; `general` reply quality; help/general/OOS collapse

## Suggested order

**Phase 0 → 1 → 2 → 3 → 4 → 5 → (6)**

Phase 0 buys immediate user-visible wins with zero model risk.
Phase 1 is the prerequisite for judging literally everything else.
Phases 2–3 remove work from the models rather than adding data to them.
