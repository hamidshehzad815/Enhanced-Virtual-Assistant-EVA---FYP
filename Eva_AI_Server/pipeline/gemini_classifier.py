"""
EXPERIMENT (branch: experiment/gemini-clf1)

Gemini-backed replacement for CLF1. Does two jobs in one call:

  1. classify the input type (the CLF1 label set)
  2. return a spelling/grammar-cleaned version of the text for the
     downstream CLF2 + NER models

Enable with USE_GEMINI_CLF1=true in .env (default off, so `main` behaviour is
unchanged). Requires GEMINI_API_KEY.

Design notes
------------
* Drop-in: `predict()` returns the same shape as Classifier1.predict()
  ({label, confidence, all_probs}) plus `cleaned_text` and `source`.
* Never hard-fails. On any error/timeout/invalid output the caller is expected
  to fall back to the real CLF1 (see `main.py`). Gemini sitting in front of the
  whole pipeline must not be able to take EVA down.
* The cleanup prompt is deliberately restrictive. An unconstrained "improve the
  grammar" instruction will happily turn "add physcis exam on moday" into
  "Add the physics examination on Monday", and NER would then extract a task
  title the user never typed. Content words must survive verbatim.
* Gemini must NOT resolve dates. "moday" -> "monday" is fine; "moday" ->
  "2026-07-20" is not: Duckling owns resolution (it is timezone-aware and
  deterministic).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from config.settings import settings

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


# Must stay identical to the CLF1 label set, or routing in main.py breaks.
VALID_LABELS = [
    "command",
    "confirmation",
    "general",
    "help",
    "multiple_command",
    "out_of_scope",
]

_PROMPT = """You are the input router for EVA, a friendly academic assistant.
The user's name is {user_name}.

WHAT EVA CAN DO (never claim anything else):
1. Scheduling — add / show / update / reschedule / delete tasks, with date,
   time, priority (low/medium/high), status (pending/ongoing/complete),
   reminders, collaborators, and Google Calendar sync.
   Example: "add physics exam on monday at 5pm"
2. Learning — create / update / delete a learning roadmap for a topic. EVA
   supports programming topics and languages (python, java, javascript, c++,
   sql, and similar). A roadmap schedules study sessions on the user's chosen
   learning days.
   Example: "create a python roadmap from monday"
3. Insights — most productive hours, most productive days, completion rate,
   productivity report.
   Example: "when am i most productive"
4. Settings exist (quiet hours, learning schedules, default task duration and
   priority, notifications) but are changed on the Settings SCREEN, not by
   chat. EVA has NO chat command for settings.

TASK 1 — classify the message into exactly ONE label:
- "command": asks EVA to DO one thing from capabilities 1-3 (add/show/update/
  delete a task, create or change a roadmap, or ask for insights). Even vague
  ones like "add a task".
- "multiple_command": asks for TWO OR MORE actions in one message.
- "confirmation": a bare yes/no/cancel reply ("yes", "go ahead", "no",
  "don't do it", "cancel"). A refusal like "don't do it" is STILL "confirmation".
- "help": asks what EVA can do, or HOW to do something in EVA. This includes
  questions ABOUT settings ("what are the quiet hours", "how do i change my
  learning days") because settings are not chat commands. It also includes
  questions about what EVA supports ("what languages do you support").
- "general": small talk ("hi", "how are you", "thanks", "bye").
- "out_of_scope": something EVA cannot do (order pizza, weather, play music,
  translate, general knowledge).

Key distinctions:
- "how to add a roadmap" -> help (roadmaps ARE EVA's job; the user is asking HOW).
- "add a roadmap for python" -> command (the user is asking EVA to DO it).
- "how to cook pasta" -> out_of_scope (cooking is not EVA's job).
- "what are the quiet hours" -> help (a settings question, not a chat command).

TASK 2 — clean the message for a downstream parser. STRICT RULES:
- Fix ONLY spelling and obvious grammar ("moday" -> "monday",
  "physcis" -> "physics", "road map" -> "roadmap").
- Preserve EVERY content word verbatim. Do NOT add, remove, reorder, expand or
  rephrase. "physcis exam" -> "physics exam", NEVER "physics examination".
- Do NOT resolve dates or times. "moday" -> "monday", NEVER a calendar date.
  Leave "5pm", "tomorrow", "17july" as written (fix spelling only).
- If nothing is misspelled, return the message unchanged.

TASK 3 — the reply.
- If input_type is "command": return response_text as an EMPTY STRING "". EVA's
  own scheduling/learning engine handles commands; do NOT answer it yourself and
  do NOT invent confirmations like "I've added it".
- Otherwise ("help", "general", "out_of_scope", "multiple_command",
  "confirmation") WRITE the reply EVA should say. Rules:
  * Warm, natural, conversational. Use the user's name sometimes, not every time.
  * help: answer their SPECIFIC question and include one example command they
    can copy. Up to 4 short lines. Only describe capabilities 1-4 above — never
    invent a feature.
  * general: actually answer the small talk (if asked how you are, say how you
    are), then offer one concrete next step. 1-2 sentences.
  * out_of_scope: briefly say you cannot do it, then point to the nearest thing
    you CAN do. 1-2 sentences.
  * multiple_command: ask them to send one request at a time. 1 sentence.
  * confirmation: they replied yes/no but nothing is pending — say so lightly
    and ask what they would like to do. 1 sentence.
  * Never mention internals: no "intent", "classifier", "NER", "confidence".

Return ONLY raw JSON, no markdown fence:
{{"input_type": "<one label>", "cleaned_text": "<cleaned message>", "response_text": "<reply or empty string>"}}

Message: {message}"""


def _strip_fence(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _content_words(text: str) -> list:
    """Alphabetic tokens only — punctuation/casing changes are allowed."""
    return re.findall(r"[a-z]+", (text or "").lower())


class GeminiInputClassifier:
    """CLF1-shaped classifier backed by Gemini."""

    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = getattr(settings, "GEMINI_CLF1_MODEL", "gemini-2.5-flash")
        self.enabled = bool(
            getattr(settings, "USE_GEMINI_CLF1", False) and self.api_key and genai
        )
        self.model = None

        if self.enabled:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                print(f"[GeminiCLF1] Enabled ({self.model_name})")
            except Exception as error:
                print(f"[GeminiCLF1] Init failed, disabled: {error}")
                self.enabled = False
                self.model = None

    def _validate_cleaned(self, original: str, cleaned: str) -> str:
        """
        Reject rewrites that add or drop content.

        Spelling fixes keep the word count identical; hallucinated expansions do
        not. If the model wandered, keep the original text — a typo downstream is
        far cheaper than a task titled something the user never said.
        """
        if not cleaned or not cleaned.strip():
            return original

        orig_words = _content_words(original)
        new_words = _content_words(cleaned)

        # "road map" -> "roadmap" legitimately drops one token, so allow -1..0.
        if not (len(orig_words) - 1 <= len(new_words) <= len(orig_words)):
            print(
                f"[GeminiCLF1] Rejected rewrite (word count {len(orig_words)}"
                f"->{len(new_words)}): {cleaned!r}"
            )
            return original

        # Guard against date resolution sneaking in.
        if re.search(r"\b\d{4}-\d{2}-\d{2}\b", cleaned) and not re.search(
            r"\b\d{4}-\d{2}-\d{2}\b", original
        ):
            print(f"[GeminiCLF1] Rejected rewrite (resolved a date): {cleaned!r}")
            return original

        return cleaned.strip()

    def predict(self, text: str, user_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Return {label, confidence, all_probs, cleaned_text, response_text, source}
        or None.

        None means "could not classify" — the caller must fall back to CLF1.

        `response_text` is populated for the non-command labels, so a chat turn
        costs ONE Gemini call instead of two (classify, then generate a reply).
        For commands it is empty: EVA's own handlers own that path, and letting
        the model invent "I've added it" would be a lie.
        """
        if not self.enabled or not self.model or not text or not text.strip():
            return None

        try:
            response = self.model.generate_content(
                _PROMPT.format(message=text, user_name=user_name or "the user"),
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 20000,
                    "response_mime_type": "application/json",
                },
                request_options={"timeout": float(settings.GEMINI_TIMEOUT_SECONDS)},
            )
            payload = json.loads(_strip_fence(response.text))
        except Exception as error:
            print(f"[GeminiCLF1] Call failed, falling back to CLF1: {error}")
            return None

        label = str(payload.get("input_type") or "").strip().lower()
        if label not in VALID_LABELS:
            print(f"[GeminiCLF1] Invalid label {label!r}, falling back to CLF1")
            return None

        cleaned = self._validate_cleaned(text, str(payload.get("cleaned_text") or ""))

        # Never let a generated reply through on the command path: the handlers
        # own that, and an invented "I've added it" would be a lie to the user.
        reply = "" if label == "command" else str(payload.get("response_text") or "").strip()

        # Gemini gives no calibrated score. Report 1.0 so downstream threshold
        # checks pass, but `source` marks it so it is never mistaken for a real
        # model confidence in evaluation.
        return {
            "label": label,
            "confidence": 1.0,
            "all_probs": {name: (1.0 if name == label else 0.0) for name in VALID_LABELS},
            "cleaned_text": cleaned,
            "response_text": reply,
            "source": "gemini",
        }


gemini_input_classifier = GeminiInputClassifier()
