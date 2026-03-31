"""
Gemini client for natural response generation.
Phase 8: integrates action-aware prompting with graceful fallback responses.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
from typing import Any, Dict, List, Optional

from config.settings import settings

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - guarded runtime import
    genai = None


_SYSTEM_INSTRUCTION = (
    "You are EVA, a friendly and intelligent academic assistant. "
    "Generate a short, warm, natural reply based ONLY on the provided action context. "
    "Use the user's name when available. "
    "Keep responses specific and conversational, not robotic. "
    "Never expose internal system details. "
    "Prefer 1-2 sentences."
)

_ACTION_GUIDANCE: Dict[str, str] = {
    "task_added": "Confirm the task was added with task name/date/time and any useful reminder context.",
    "task_deleted": "Confirm deletion naturally and reassure user politely.",
    "delete_bulk_completed": "Confirm multiple tasks were deleted and mention count naturally.",
    "delete_cancel_single": "Confirm deletion was cancelled and that the single task is unchanged.",
    "delete_cancel_bulk": "Confirm bulk deletion was cancelled and tasks were left unchanged.",
    "delete_missing_entities": "Ask which task to delete and suggest name, date, or priority.",
    "delete_invalid_date": "Ask user to re-enter date in a clear way after parse failure.",
    "delete_not_found": "Explain no matching tasks were found and suggest refining filters.",
    "delete_single_confirm": "Ask for yes/no confirmation to delete one specific task.",
    "delete_multi_list": "Introduce that multiple tasks were found and ask user to choose one or all.",
    "delete_too_broad": "Ask user to narrow delete request because too many tasks matched.",
    "task_updated": "Mention what changed and keep it concise.",
    "tasks_shown": "Summarize visible tasks in a helpful conversational way.",
    "show_results": "Introduce shown tasks naturally and keep the tone concise and helpful.",
    "show_not_found": "Explain that no tasks matched the requested show filters.",
    "missing_task_name": "Ask for task name naturally.",
    "missing_date": "Ask for date naturally.",
    "missing_time": "Ask for time naturally.",
    "duplicate_found": "Explain that a task with the same name is already scheduled on the given date and time, then ask the user to reply yes or no.",
    "task_time_conflict": "Explain that the requested task overlaps an existing task window and confirm that it was not scheduled.",
    "quiet_hours_conflict": "Explain that the requested time falls inside the user's quiet hours and ask whether to schedule anyway.",
    "quiet_hours_alternative_time": "Acknowledge the quiet-hours conflict and ask for another time outside those quiet hours.",
    "cancelled": "Acknowledge cancellation warmly.",
    "general_greeting": "Reply like a friendly assistant greeting/chat response.",
    "out_of_scope": "Politely state scope limitation and redirect to supported capabilities.",
    "validation_error": "Explain input was unclear and suggest a simple valid format.",
    "multiple_command": "Ask user to provide one command at a time.",
    "confirmation_unexpected": "State that no confirmation is currently needed.",
    "empty_input": "Ask the user to send a real message and keep it warm.",
    "too_short_input": "Ask for a little more detail in a natural way.",
    "pending_cancelled": "Confirm the pending flow was cancelled.",
    "pending_waiting_reply": "Explain that we are still waiting for the expected reply.",
    "pending_yes_no_prompt": "Ask the user to reply yes or no.",
    "pending_number_prompt": "Ask the user to reply with the expected number options.",
    "pending_free_text_captured": "Acknowledge that free-text reply was captured.",
    "pending_yes_no_processed": "Acknowledge that yes/no choice was captured.",
    "pending_number_processed": "Acknowledge that number choice was captured.",
    "unknown_input_type": "Handle unknown classification safely and ask user to rephrase.",
    "model_unavailable": "Politely explain the assistant is temporarily unavailable and ask user to retry.",
    "intent_not_implemented": "Explain this command type is recognized but not implemented yet, then redirect to available capabilities.",
    "system_error": "Give a friendly recovery message after an internal error without exposing stack traces.",
}

_FALLBACK_RESPONSES: Dict[str, List[str]] = {
    "general_greeting": [
        "Hi {name}! I am here and ready to help with your schedule or learning plan.",
        "Hey {name}, tell me what you want to plan or study next.",
        "Hello {name}! Share a task or topic and I will help you organize it.",
        "Hi {name}, I can help with tasks, roadmaps, and productivity guidance.",
        "Great to hear from you, {name}. What should we work on right now?",
    ],
    "out_of_scope": [
        "I cannot help with that directly, {name}, but I can help with tasks, study plans, and progress tracking.",
        "That is outside my current scope, {name}. I can still assist with scheduling and learning roadmaps.",
        "I am focused on academic planning right now, {name}. Try asking about tasks or study goals.",
    ],
    "multiple_command": [
        "I caught multiple requests, {name}. Please send one command at a time.",
        "Let us do this step by step, {name}. Start with one command.",
        "Please send a single request first, {name}, and I will handle it immediately.",
    ],
    "confirmation_unexpected": [
        "Thanks {name}, but I am not waiting for a confirmation right now.",
        "Noted {name}. I currently need a command or specific detail, not a confirmation.",
        "I got your confirmation, {name}, but there is no pending yes/no step at the moment.",
    ],
    "missing_task_name": [
        "What should I call this task, {name}?",
        "Got it, {name}. What is the task name?",
        "Please share the task title, {name}.",
    ],
    "missing_date": [
        "When should I schedule it, {name}?",
        "What date should I use, {name}?",
        "Tell me the date for this task, {name}.",
    ],
    "missing_time": [
        "What time works best for you, {name}?",
        "Please share the time, {name}.",
        "When exactly should I set it, {name}?",
    ],
    "duplicate_found": [
        "{task_name} is already scheduled on {existing_date} at {existing_time}, {name}. Should I add another one? Reply yes or no.",
        "I already have {task_name} scheduled on {existing_date} at {existing_time}, {name}. Do you still want me to add it? Reply yes or no.",
        "{task_name} is already on your schedule for {existing_date} at {existing_time}, {name}. Should I add it anyway? Reply yes or no.",
    ],
    "task_time_conflict": [
        "I did not schedule {task_name}{date_time_suffix}, {name}, because it overlaps with {conflicting_task_name} around {conflicting_time}.",
        "{task_name}{date_time_suffix} clashes with {conflicting_task_name} around {conflicting_time}, {name}, so I left it unscheduled.",
        "I stopped that, {name}. {task_name}{date_time_suffix} would overlap with {conflicting_task_name} around {conflicting_time}.",
    ],
    "quiet_hours_conflict": [
        "That time falls in your {quiet_hours}, {name}. Do you want me to schedule {task_name}{date_time_suffix} anyway?",
        "{task_name}{date_time_suffix} lands in your {quiet_hours}, {name}. Should I keep it there?",
        "That matches your {quiet_hours}, {name}. Do you still want {task_name} scheduled{date_time_suffix}?",
    ],
    "quiet_hours_alternative_time": [
        "No problem, {name}. What time should I use instead outside your quiet hours?",
        "Alright {name}, give me another time that works better than your quiet hours.",
        "Sure {name}, what time would you prefer outside your quiet hours?",
    ],
    "cancelled": [
        "No problem {name}, I cancelled that.",
        "Done {name}, I have stopped that flow.",
        "Alright {name}, nothing else will be changed.",
    ],
    "validation_error": [
        "I could not parse that clearly, {name}. Please try a simpler format.",
        "That input was unclear, {name}. Try wording it like date and time explicitly.",
        "I did not catch that fully, {name}. Could you rephrase it?",
    ],
    "task_added": [
        "Done {name}! {task_name} is added{date_time_suffix}.",
        "Great, {name}. I have scheduled {task_name}{date_time_suffix}.",
        "All set {name}, {task_name} is now on your plan{date_time_suffix}.",
    ],
    "task_deleted": [
        "Done {name}, I removed {task_name}.",
        "{task_name} has been deleted, {name}.",
        "Removed successfully, {name}. {task_name} is off your schedule now.",
    ],
    "delete_bulk_completed": [
        "Done {name}, I deleted {count} tasks: {task_names}.",
        "All set {name}. I removed {count} tasks ({task_names}).",
        "Cleared, {name}. {count} tasks were deleted, including {task_names}.",
    ],
    "delete_cancel_single": [
        "No problem {name}, I left {task_name} as it is.",
        "Alright {name}, I did not delete {task_name}.",
        "Understood {name}, {task_name} is still there.",
    ],
    "delete_cancel_bulk": [
        "No problem {name}, I left those {count} tasks unchanged.",
        "Alright {name}, I did not delete any of those tasks.",
        "Understood {name}, those tasks were kept as they are.",
    ],
    "delete_missing_entities": [
        "Which task should I delete, {name}? You can tell me the name, date, or priority.",
        "I can do that, {name}. Which task do you want to remove?",
        "Tell me what to delete, {name}. A task name, date, or priority is enough.",
    ],
    "delete_invalid_date": [
        "I could not understand that date, {name}. Please share it again in another way.",
        "That date did not parse correctly, {name}. Can you re-enter it?",
        "Please give me the date again, {name}, so I can match the right task.",
    ],
    "delete_not_found": [
        "I could not find any tasks matching {filters_summary}, {name}. Try refining the name or date.",
        "No matching tasks found for {filters_summary}, {name}. Want to try a different filter?",
        "I did not find tasks for {filters_summary}, {name}. Please narrow it down and try again.",
    ],
    "delete_single_confirm": [
        "I found {task_name} on {due_datetime}, {name}. Should I delete it? Reply yes or no.",
        "{name}, do you want me to delete {task_name} on {due_datetime}? Reply yes or no.",
        "Ready to delete {task_name} on {due_datetime}, {name}. Confirm with yes or no.",
    ],
    "delete_multi_list": [
        "I found {count} matching tasks, {name}.",
        "There are {count} tasks matching that request, {name}.",
        "I found several matches ({count}), {name}.",
    ],
    "delete_too_broad": [
        "That matches too many tasks, {name}. Please narrow it by name, date, or priority.",
        "I found a lot of tasks for that, {name}. Add a filter like date or task name.",
        "This delete request is broad, {name}. Can you narrow it down a little?",
    ],
    "task_updated": [
        "Updated, {name}. Your task changes are saved.",
        "Done {name}, I applied the update.",
        "All set {name}, that task is updated now.",
    ],
    "tasks_shown": [
        "Here is what I found, {name}.",
        "These are your matching tasks, {name}.",
        "I pulled your requested tasks, {name}.",
    ],
    "show_results": [
        "Here is your schedule snapshot, {name}.",
        "I found these matching tasks for you, {name}.",
        "This is what is coming up based on your filters, {name}.",
    ],
    "show_not_found": [
        "I could not find any tasks for {filters_summary}, {name}.",
        "No tasks matched {filters_summary}, {name}.",
        "Nothing is scheduled for {filters_summary}, {name}.",
    ],
    "empty_input": [
        "I did not catch any message, {name}. Please type what you want me to do.",
        "Your message looks empty, {name}. Send me a task or question and I will help.",
        "I am ready, {name}, but I need a real message to continue.",
    ],
    "too_short_input": [
        "Could you add a little more detail, {name}, so I can help properly?",
        "I need a bit more context, {name}. Try phrasing it as a full request.",
        "That is too short for me to act on, {name}. Please expand it a little.",
    ],
    "pending_cancelled": [
        "No problem {name}, I cancelled that pending flow.",
        "Done {name}, that in-progress step has been cancelled.",
        "Alright {name}, I stopped the pending action.",
    ],
    "pending_waiting_reply": [
        "I am still waiting for your pending reply, {name}. You can also say cancel.",
        "We are mid-flow right now, {name}. Please finish the pending step or say cancel.",
        "I still need the expected reply for the current step, {name}.",
    ],
    "pending_yes_no_prompt": [
        "Please reply with yes or no, {name}.",
        "A yes or no answer will do here, {name}.",
        "I just need yes or no to continue, {name}.",
    ],
    "pending_number_prompt": [
        "Please choose by replying with 1 or 2, {name}.",
        "I need a numeric choice here, {name}. Reply 1 or 2.",
        "Reply with one of the listed numbers, {name} (1 or 2).",
    ],
    "pending_free_text_captured": [
        "Got it {name}, I captured your reply and I am continuing.",
        "Thanks {name}, I have your answer and will proceed.",
        "Perfect {name}, your response is saved for this step.",
    ],
    "pending_yes_no_processed": [
        "Thanks {name}, I processed your yes/no response.",
        "Understood {name}, your confirmation choice is captured.",
        "Got it {name}, I have your yes/no answer.",
    ],
    "pending_number_processed": [
        "Choice received {name}, I processed that option.",
        "Thanks {name}, your number selection is captured.",
        "Done {name}, I recorded your selected option.",
    ],
    "unknown_input_type": [
        "I could not confidently classify that input, {name}. Please rephrase it.",
        "That input was unclear for routing, {name}. Try a more direct request.",
        "I did not parse that reliably, {name}. Please say it in another way.",
    ],
    "model_unavailable": [
        "I am temporarily unable to process that right now, {name}. Please try again in a moment.",
        "Some processing components are unavailable at the moment, {name}. Try again shortly.",
        "I cannot complete that request right now, {name}. Please retry in a bit.",
    ],
    "intent_not_implemented": [
        "I understand that request type ({intent_name}), {name}, but it is not fully implemented yet. I can help with task creation right now.",
        "That command path ({intent_name}) is recognized but not ready yet, {name}. Please try an add-task request for now.",
        "I can identify {intent_name}, {name}, but this operation is still pending implementation. Try scheduling a new task.",
    ],
    "system_error": [
        "Something went wrong on my side, {name}, but I am still here. Please try again.",
        "I hit an internal issue while processing that, {name}. Could you resend your request?",
        "I could not complete that due to a system hiccup, {name}. Please retry in a moment.",
    ],
}

_DEFAULT_FALLBACK = [
    "I am here to help, {name}.",
    "Tell me what you want to do next, {name}.",
]


class GeminiService:
    """Action-aware Gemini response generator with deterministic fallback variety."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.timeout_seconds = max(0.5, float(settings.GEMINI_TIMEOUT_SECONDS))
        self.disable_after_failure = bool(settings.GEMINI_DISABLE_AFTER_FAILURE)
        self.enabled = bool(settings.GEMINI_ENABLED and self.api_key and genai)
        self.model = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._action_counts: Dict[str, int] = {}
        self._last_response_by_action: Dict[str, str] = {}

        if self.enabled:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
            except Exception as e:
                print(f"[Gemini] Initialization failed, fallback mode enabled: {e}")
                self.enabled = False
                self.model = None

    @staticmethod
    def _compact_history(conversation_history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
        if not conversation_history:
            return []

        compact: List[Dict[str, str]] = []
        for item in conversation_history[:6]:
            compact.append(
                {
                    "role": str(item.get("role", "")),
                    "content": str(item.get("content", ""))[:240],
                }
            )
        return compact

    def _build_prompt(
        self,
        action_context: Dict[str, Any],
        user_name: Optional[str],
        conversation_history: Optional[List[Dict[str, Any]]],
    ) -> str:
        action = str(action_context.get("action", "general_greeting"))
        guidance = _ACTION_GUIDANCE.get(action, "Respond naturally based on action context.")
        payload = {
            "action": action,
            "user_name": user_name,
            "action_context": action_context,
            "recent_history": self._compact_history(conversation_history),
        }

        return (
            f"{_SYSTEM_INSTRUCTION}\n\n"
            f"Action guidance: {guidance}\n"
            "Return plain text only.\n"
            f"Context JSON:\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
        )

    def _pick_fallback(self, action_context: Dict[str, Any], user_name: Optional[str]) -> str:
        action = str(action_context.get("action", "general_greeting"))
        options = _FALLBACK_RESPONSES.get(action, _DEFAULT_FALLBACK)

        count = self._action_counts.get(action, 0)
        template = options[count % len(options)]
        self._action_counts[action] = count + 1

        name = user_name or "there"
        task_name = str(action_context.get("task_name") or "your task")
        date = str(action_context.get("date") or "")
        time = str(action_context.get("time") or "")
        due_datetime = str(action_context.get("due_datetime") or "the scheduled time")
        priority = str(action_context.get("priority") or "")
        filters_summary = str(action_context.get("filters_summary") or "those filters")
        task_names = str(action_context.get("task_names") or "those tasks")
        try:
            count = int(action_context.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        quiet_hours = str(action_context.get("quiet_hours") or "quiet hours")
        conflicting_task_name = str(
            action_context.get("conflicting_task_name") or "another task"
        )
        conflicting_time = str(
            action_context.get("conflicting_time") or "that time"
        )
        existing_date = str(action_context.get("existing_date") or date or "that date")
        existing_time = str(action_context.get("existing_time") or time or "that time")
        intent_name = str(action_context.get("intent_name") or "this command")

        date_time_suffix = ""
        if date and time:
            date_time_suffix = f" for {date} at {time}"
        elif date:
            date_time_suffix = f" for {date}"
        elif time:
            date_time_suffix = f" at {time}"

        return template.format(
            name=name,
            task_name=task_name,
            due_datetime=due_datetime,
            priority=priority,
            filters_summary=filters_summary,
            task_names=task_names,
            count=count,
            date=date,
            date_time_suffix=date_time_suffix,
            quiet_hours=quiet_hours,
            conflicting_task_name=conflicting_task_name,
            conflicting_time=conflicting_time,
            existing_date=existing_date,
            existing_time=existing_time,
            intent_name=intent_name,
        ).strip()

    def generate_reply(
        self,
        action_context: Dict[str, Any],
        user_name: Optional[str],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate a natural language reply.
        Falls back to local varied templates if Gemini is unavailable or fails.
        """
        action = str(action_context.get("action", "general_greeting"))

        if self.enabled and self.model is not None:
            try:
                prompt = self._build_prompt(action_context, user_name, conversation_history)
                future = self._executor.submit(
                    self.model.generate_content,
                    prompt,
                    request_options={"timeout": self.timeout_seconds},
                )
                response = future.result(timeout=self.timeout_seconds + 0.25)
                text = (getattr(response, "text", "") or "").strip()

                # Enforce variation even if model repeats exactly.
                if text:
                    if self._last_response_by_action.get(action) == text:
                        text = self._pick_fallback(action_context, user_name)
                    self._last_response_by_action[action] = text
                    return text
            except FuturesTimeoutError:
                print(
                    "[Gemini] generate_reply timed out, using fallback."
                )
                if self.disable_after_failure:
                    self.enabled = False
                    self.model = None
            except Exception as e:
                print(f"[Gemini] generate_reply failed, using fallback: {e}")
                if self.disable_after_failure:
                    self.enabled = False
                    self.model = None

        fallback = self._pick_fallback(action_context, user_name)
        self._last_response_by_action[action] = fallback
        return fallback


# Singleton instance
gemini_service = GeminiService()
