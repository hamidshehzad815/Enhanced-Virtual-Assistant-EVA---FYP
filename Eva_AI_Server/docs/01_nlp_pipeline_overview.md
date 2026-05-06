# 📌 NLP Pipeline Overview — EVA AI Server

## What Is an NLP Pipeline?

A **Natural Language Processing (NLP) pipeline** is a sequence of processing steps that transforms raw human text into structured, machine-understandable data. Each step builds on the output of the previous one, progressively adding more meaning and structure.

In the EVA AI Server, a user message such as:
> *"Hey Eva, add physics exam on Friday at 3pm with high priority"*

…must pass through multiple stages before any action is taken. This document maps those stages end-to-end.

---

## EVA's Full NLP Pipeline at a Glance

```
User Message (raw text)
        │
        ▼
┌─────────────────────────┐
│  Phase 1: Context Check │  ← Is there a pending multi-turn conversation? (Redis)
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│  Phase 2: Preprocessing │  ← Lowercase, strip whitespace, remove salutations
└─────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│  Phase 3: Input-Type Clf     │  ← Classifier 1 (BERT-based, 5 classes)
│  command / general /         │
│  out_of_scope / confirmation │
│  / multiple_command          │
└──────────────────────────────┘
        │ (if "command")
        ▼
┌──────────────────────────────┐
│  Phase 4: Intent Clf         │  ← Classifier 2 (BERT-based, ~10 intents)
│  scheduling_add / delete /   │
│  update / show / learning_*  │
│  / behavioral                │
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│  Phase 5: NER Extraction     │  ← NER Model (token classification, BIO tagging)
│  task_name / date / time /   │
│  priority / collaborator …   │
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│  Phase 6: Entity Scoping     │  ← Filter entities by detected intent
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│  Phase 7: Date Resolution    │  ← Duckling: "Friday" → "2025-05-02"
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│  Phase 8: Routing & Handling │  ← Intent Router → Domain Handler → DB ops
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│  Phase 9: Response Gen       │  ← Gemini (LLM) generates natural language reply
└──────────────────────────────┘
```

---

## File-to-Pipeline Mapping

| Pipeline Phase           | File(s) Involved                                     |
|--------------------------|------------------------------------------------------|
| Context check            | `context/redis_client.py`, `context/context_manager.py` |
| Preprocessing            | `pipeline/preprocessor.py`                          |
| Input-type classification| `pipeline/classifier1.py`                           |
| Intent classification    | `pipeline/classifier2.py`                           |
| Named Entity Recognition | `pipeline/ner.py`                                   |
| Entity scoping/aliasing  | `pipeline/entity_scoper.py`                         |
| Date/time resolution     | `pipeline/date_resolver.py`, `services/duckling.py` |
| Deterministic fallback   | `pipeline/delete_entity_fallback.py`, `pipeline/update_entity_fallback.py` |
| Intent routing           | `handlers/router.py`                                |
| Response generation      | `services/gemini.py`                                |
| Orchestration            | `main.py`                                           |

---

## Key Design Decisions

### 1. Two-Stage Classification
EVA deliberately uses **two separate classifiers** instead of one:
- **Classifier 1** is a coarse gatekeeper ("is this even a command?")
- **Classifier 2** is a fine-grained classifier only invoked when Clf 1 says *command*

This keeps Classifier 2 focused and more accurate on its narrow task.

### 2. ML + Rule-Based Hybrid
The pipeline is **not purely ML**. Regex-based fallback extractors (`delete_entity_fallback.py`, `update_entity_fallback.py`) fill in entity gaps when the NER model fails. This hybrid approach improves robustness.

### 3. Multi-Turn Dialogue with Redis
The server is **stateless per request** but uses **Redis** as a shared key-value store to hold pending conversational context (e.g., "waiting for yes/no confirmation"). This enables multi-turn interactions without storing state in memory.

### 4. Separation of Classification and NER Texts
- **Classification** uses preprocessed (lowercased) text for model consistency
- **NER and Gemini** always receive original-cased text to preserve proper nouns and context

---

## Concept References

Each phase is documented in its own file:

| Concept | Documentation File |
|---|---|
| Transformers & BERT | `02_transformers_and_bert.md` |
| Sequence Classification | `03_sequence_classification.md` |
| Named Entity Recognition | `04_named_entity_recognition.md` |
| Duckling Date Parsing | `05_duckling_temporal_parsing.md` |
| Multi-Turn Dialogue | `06_multi_turn_dialogue_context.md` |
| Regex-Based Fallback | `07_regex_rule_based_extraction.md` |
| LLM Response Generation | `08_llm_response_generation.md` |
| Entity Normalization | `09_entity_normalization.md` |
