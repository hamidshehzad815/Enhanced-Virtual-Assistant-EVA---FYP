# 📚 EVA AI Server — NLP/AI/ML Concepts Documentation Index

A complete reference for the NLP, AI, and ML concepts used in the **EVA AI Server**.

## Documents

| # | File | Topics Covered |
|---|---|---|
| 1 | [01_nlp_pipeline_overview.md](./01_nlp_pipeline_overview.md) | End-to-end NLU pipeline, all phases, file mapping, design decisions |
| 2 | [02_transformers_and_bert.md](./02_transformers_and_bert.md) | Transformer architecture, BERT, tokenization, softmax, inference |
| 3 | [03_sequence_classification.md](./03_sequence_classification.md) | Text classification, two-stage design, [CLS] token, label maps |
| 4 | [04_named_entity_recognition.md](./04_named_entity_recognition.md) | NER, BIO tagging, token classification, offset mapping, aggregation |
| 5 | [05_duckling_temporal_parsing.md](./05_duckling_temporal_parsing.md) | Temporal parsing, Duckling, timezone handling, date ranges, UTC |
| 6 | [06_multi_turn_dialogue_context.md](./06_multi_turn_dialogue_context.md) | Multi-turn dialogue, Redis, TTL, expected_response, context flows |
| 7 | [07_regex_rule_based_extraction.md](./07_regex_rule_based_extraction.md) | Regex patterns, fallback extraction, stopwords, salutation stripping |
| 8 | [08_llm_response_generation.md](./08_llm_response_generation.md) | Gemini LLM, prompt engineering, grounding, action context, history |
| 9 | [09_entity_normalization.md](./09_entity_normalization.md) | Entity scoping, aliasing, value canonicalization, duration parsing |

---

## Concept Map

```
                        User Message
                             │
         ┌───────────────────▼────────────────────┐
         │           Multi-Turn Context?           │
         │         Redis (concept: #6)             │
         └────────────────────────────────────────-┘
                 │ No pending             │ Yes
                 ▼                        ▼
         ┌───────────────┐       Handle pending reply
         │ Preprocessing │       (yes/no, number, free_text)
         │  (concept: #7)│
         └───────────────┘
                 │
                 ▼
         ┌────────────────────────────────┐
         │       Classifier 1             │
         │  Input Type (5 classes)        │
         │  BERT + Softmax (concept: #2,3)│
         └────────────────────────────────┘
                 │ command
                 ▼
         ┌────────────────────────────────┐
         │       Classifier 2             │
         │  Intent (~10 classes)          │
         │  BERT + Softmax (concept: #2,3)│
         └────────────────────────────────┘
                 │
                 ▼
         ┌────────────────────────────────┐
         │         NER Model              │
         │  Token Classification          │
         │  BIO Tagging (concept: #4)     │
         └────────────────────────────────┘
                 │                 │ gaps
                 ▼                 ▼
         ┌──────────┐     ┌─────────────────┐
         │ ML output │     │ Regex Fallback  │
         │           │     │ (concept: #7)   │
         └──────────-┘     └─────────────────┘
                 │ merged
                 ▼
         ┌────────────────────────────────┐
         │     Entity Scoping             │
         │   + Aliasing (concept: #9)     │
         └────────────────────────────────┘
                 │
                 ▼
         ┌────────────────────────────────┐
         │     Date/Time Resolution       │
         │     Duckling (concept: #5)     │
         └────────────────────────────────┘
                 │
                 ▼
         ┌────────────────────────────────┐
         │     Value Normalization        │
         │   priority/status (concept: #9)│
         └────────────────────────────────┘
                 │
                 ▼
         ┌────────────────────────────────┐
         │     Intent Handler             │
         │     DB operations              │
         └────────────────────────────────┘
                 │
                 ▼
         ┌────────────────────────────────┐
         │     Gemini LLM                 │
         │  Response Generation (concept: │
         │       #8)                      │
         └────────────────────────────────┘
                 │
                 ▼
             Natural Language Response
```

---

## Key Technologies

| Technology | Version / Source | Purpose |
|---|---|---|
| Python | 3.10+ | Server language |
| FastAPI | Latest | HTTP server framework |
| PyTorch | Latest | ML tensor operations |
| HuggingFace Transformers | Latest | BERT model loading and inference |
| Duckling | Meta OSS (HTTP service) | Temporal expression parsing |
| Redis | In-memory DB | Multi-turn context storage |
| Google Gemini | `google-generativeai` SDK | LLM response generation |
| MongoDB | via `motor` (async) | Task and user data storage |
| `re` (Python stdlib) | Built-in | Regex-based fallback extraction |

---

## Quick Reference: Which Concept Does Which?

| "EVA, what does X?" | Relevant Concept Doc |
|---|---|
| How does EVA know if I said a command? | #3 Sequence Classification |
| How does EVA know I want to *add* a task? | #3 Sequence Classification |
| How does EVA extract "physics exam" from a sentence? | #4 Named Entity Recognition |
| How does "Friday" become a real date? | #5 Duckling Temporal Parsing |
| How does EVA remember my pending delete confirmation? | #6 Multi-Turn Dialogue |
| How does BERT read and understand text? | #2 Transformers & BERT |
| What is "urgent" normalized to in the database? | #9 Entity Normalization |
| How does EVA reply in natural language? | #8 LLM Response Generation |
| What happens if the NER model misses an entity? | #7 Regex Fallback |
