"""
LLM-based activity extraction service.

Primary: Local Ollama (qwen3:8b) — self-hosted, runs on single consumer GPU (~8-10GB VRAM at Q4).
Fallback: Groq API (qwen/qwen3-32b) — cloud reliability fallback for live-demo safety.

Model names are config-driven (LOCAL_LLM_MODEL, GROQ_MODEL_FALLBACK) — no code change
needed to swap models, just update .env.

The LLM receives raw text (from WhatsApp/OCR/ASR) and extracts structured
activity events per the §3.4 schema. Uses few-shot examples embedded in the
system prompt to guide format. Prompt versioned in prompts/extractor_v1.txt.

Output is a list of ExtractedActivity objects — validated before returning.
ExtractionError is raised on unrecoverable failures (triggers Celery retry).
"""

import json
from datetime import datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()


class ExtractedActivity(BaseModel):
    """Structured output from the LLM extractor."""

    activity_description: str = Field(..., description="Description of the activity as reported")
    event_type: str = Field(..., description="'start', 'finish', or 'partial_complete'")
    actual_start: str | None = Field(None, description="ISO 8601 datetime or date string")
    actual_finish: str | None = Field(None, description="ISO 8601 datetime or date string")
    percent_complete: float | None = Field(None, ge=0, le=100)
    quantity_completed: float | None = None
    quantity_unit: str | None = None
    location_reference: str | None = None
    discipline: str = Field(
        default="unknown",
        description="piping, civil, electrical, instrumentation, hse, structural, mechanical, or unknown",
    )
    extraction_notes: str | None = Field(
        None, description="Any ambiguities or assumptions made during extraction"
    )


class ExtractionError(Exception):
    """Raised when extraction fails on both primary and fallback LLM."""
    pass


SYSTEM_PROMPT = """You are an AI assistant for an Oil India infrastructure project management system.
Your job is to extract structured activity progress events from field supervisor messages.

Extract every activity mentioned and return a JSON object with key "activities" containing a list.
Each activity must have these fields:
- activity_description: exact description of the activity as the supervisor reported it
- event_type: one of "start", "finish", "partial_complete"
- actual_start: ISO 8601 datetime if a start time is mentioned (e.g. "2026-08-27T08:30:00+05:30"), or null
- actual_finish: ISO 8601 datetime if a finish/end time is mentioned, or null
- percent_complete: number 0-100 if progress percentage mentioned, or null
- quantity_completed: numeric quantity if mentioned (e.g. 120.5), or null
- quantity_unit: unit of quantity if mentioned (e.g. "meters", "welds", "joints"), or null
- location_reference: site location, grid reference, chainage, or area if mentioned, or null
- discipline: one of piping, civil, electrical, instrumentation, hse, structural, mechanical, unknown
- extraction_notes: any ambiguities or assumptions you made, or null

Today's date context: {today}
Project: Oil India infrastructure pipeline project
Discipline hint: {discipline_hint}

EXAMPLE INPUT: "Spool erection for Line 24\"-XX started at chainage 12+450, 09:30 AM. Estimated 3 days."
EXAMPLE OUTPUT:
{{
  "activities": [
    {{
      "activity_description": "Spool erection for Line 24\\"-XX",
      "event_type": "start",
      "actual_start": "{today}T09:30:00+05:30",
      "actual_finish": null,
      "percent_complete": null,
      "quantity_completed": null,
      "quantity_unit": null,
      "location_reference": "Chainage 12+450",
      "discipline": "piping",
      "extraction_notes": "Estimated duration 3 days noted but not extracted as a date field"
    }}
  ]
}}

EXAMPLE INPUT: "Civil team completed excavation for pump P-101 foundation (Area A, Grid 12-13). 100% done."
EXAMPLE OUTPUT:
{{
  "activities": [
    {{
      "activity_description": "Excavation for pump P-101 foundation",
      "event_type": "finish",
      "actual_start": null,
      "actual_finish": "{today}T00:00:00+05:30",
      "percent_complete": 100.0,
      "quantity_completed": null,
      "quantity_unit": null,
      "location_reference": "Area A, Grid 12-13",
      "discipline": "civil",
      "extraction_notes": "Actual finish time not specified; using report date"
    }}
  ]
}}

Return ONLY valid JSON. No explanations outside the JSON structure.
Important: Qwen3 thinking mode may produce <think>...</think> blocks — output ONLY the JSON after thinking."""


def _build_prompt(text: str, discipline_hint: str | None) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    hint = discipline_hint or "not specified — infer from content"
    return SYSTEM_PROMPT.format(today=today, discipline_hint=hint)


def _parse_llm_response(raw_response: str) -> list[ExtractedActivity]:
    """
    Parse and validate LLM JSON output → list of ExtractedActivity.

    Handles:
    - Markdown code fences (```json ... ```)
    - Qwen3 <think>...</think> reasoning blocks (stripped before parse)
    - Bare JSON without wrapper
    """
    text = raw_response.strip()

    # Strip Qwen3 thinking blocks if present
    if "<think>" in text:
        # Find the last </think> and take everything after
        end_think = text.rfind("</think>")
        if end_think != -1:
            text = text[end_think + len("</think>"):].strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        text = "\n".join(inner_lines).strip()

    data = json.loads(text)

    # Handle both {"activities": [...]} and bare [...]
    if isinstance(data, list):
        activities_raw = data
    else:
        activities_raw = data.get("activities", [])

    activities = []
    for item in activities_raw:
        try:
            # Qwen may return "activity" instead of the required
            # "activity_description". Normalize before validation.
            if "activity" in item and "activity_description" not in item:
                item["activity_description"] = item.pop("activity")

            activities.append(ExtractedActivity.model_validate(item))
        except ValidationError as exc:
            log.warning("llm_extractor.activity_validation_failed", error=str(exc), item=item)
            continue

    return activities


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _call_local_llm(system_prompt: str, user_text: str) -> str:
    """
    Call local Ollama (Qwen3-8B) as the PRIMARY extractor.
    Model name from config: settings.local_llm_model
    """
    import ollama

    full_prompt = f"{system_prompt}\n\nUser message:\n{user_text}"
    response = ollama.generate(
        model=settings.local_llm_model,
        prompt=full_prompt,
        options={"temperature": 0.1},
    )
    return response["response"]


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _call_groq_fallback(system_prompt: str, user_text: str) -> str:
    """
    Call Groq (qwen/qwen3-32b) as the FALLBACK extractor.
    Model name from config: settings.groq_model_fallback
    Invoked only when local Ollama fails or is unavailable.
    """
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model=settings.groq_model_fallback,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=2000,
    )
    return response.choices[0].message.content


def extract_activities(
    text: str,
    discipline_hint: str | None = None,
    source_label: str = "unknown",
) -> tuple[list[ExtractedActivity], dict[str, Any]]:
    """
    Extract structured activity events from raw text.

    Order: local Qwen3-8B (Ollama) → Groq qwen/qwen3-32b (fallback).

    Args:
        text: Raw text to extract from (WhatsApp message, OCR output, etc.)
        discipline_hint: Discipline from sender_profiles (may be None).
        source_label: For logging/audit trail.

    Returns:
        (list[ExtractedActivity], audit_dict)

    Raises:
        ExtractionError if both backends fail.
    """
    system_prompt = _build_prompt(text, discipline_hint)
    llm_used = None
    raw_response = None

    # --- Primary: Local Qwen3-8B via Ollama ---
    try:
        raw_response = _call_local_llm(system_prompt, text)
        llm_used = f"ollama/{settings.local_llm_model}"
        log.info("llm_extractor.local_llm_success", model=settings.local_llm_model, source=source_label)
    except Exception as local_exc:
        log.warning(
            "llm_extractor.local_llm_failed",
            model=settings.local_llm_model,
            error=str(local_exc),
            source=source_label,
        )

    # --- Fallback: Groq qwen/qwen3-32b ---
    if raw_response is None:
        if not settings.groq_api_key:
            raise ExtractionError(
                f"Local LLM failed and no GROQ_API_KEY configured — cannot process {source_label}"
            )
        try:
            raw_response = _call_groq_fallback(system_prompt, text)
            llm_used = f"groq/{settings.groq_model_fallback}"
            log.info("llm_extractor.groq_fallback_success", model=settings.groq_model_fallback, source=source_label)
        except Exception as groq_exc:
            log.error(
                "llm_extractor.all_llm_failed",
                local_error="already logged",
                groq_error=str(groq_exc),
            )
            raise ExtractionError(
                f"All LLM backends failed for message from {source_label}"
            ) from groq_exc

    # --- Parse and validate ---
    try:
        activities = _parse_llm_response(raw_response)
    except (json.JSONDecodeError, KeyError) as exc:
        log.error(
            "llm_extractor.parse_failed",
            error=str(exc),
            raw_response=raw_response[:500] if raw_response else None,
        )
        raise ExtractionError(f"LLM response parse failed: {exc}") from exc

    audit = {
        "original_text": text,
        "llm_prompt_system": system_prompt[:500] + "...",
        "llm_response": raw_response,
        "llm_used": llm_used,
        "discipline_hint_used": discipline_hint,
        "source_label": source_label,
        "activities_extracted": len(activities),
    }

    log.info(
        "llm_extractor.done",
        llm=llm_used,
        activities=len(activities),
        source=source_label,
    )

    return activities, audit
