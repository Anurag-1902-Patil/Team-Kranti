"""
LLM-based activity and entity extraction service — v2 ontology.

Consolidated single LLM call per message: extracts 25+ ontology attributes,
fine-grained linked entities (equipment, lines, chainages, contractors, blockers),
and per-field confidence + cited evidence.

Prompt version: prompts/extractor_v2.txt (versioned per project guidelines).
Model: Config-driven via NVIDIA NIM / OpenAI-compatible endpoint.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

PROMPT_V2_FILE = Path(__file__).resolve().parent.parent.parent.parent / "prompts" / "extractor_v2.txt"


class ExtractedEntityItem(BaseModel):
    """Granular entity extracted from text (equipment, contractor, blocker, etc.)."""

    entity_type: str = Field(..., description="equipment_tag, line_number, location, contractor, person, material, blocker")
    raw_text: str = Field(..., description="Exact substring from input")
    normalized_value: str | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    evidence: str | None = None


class ExtractedActivity(BaseModel):
    """Structured output from the LLM extractor covering full execution ontology."""

    activity_description: str = Field(..., description="Exact description of the activity as reported")
    activity_description_normalized: str | None = None
    discipline: str = Field(default="unknown", description="Civil, Structural, Piping, Mechanical, etc.")
    sub_discipline: str | None = None
    activity_type: str | None = None
    work_package: str | None = None
    wbs_code: str | None = None
    construction_phase: str | None = None
    execution_stage: str | None = None
    event_type: str = Field(default="partial_complete", description="'start', 'finish', or 'partial_complete'")
    status: str | None = "in_progress"
    actual_start: str | None = Field(None, description="ISO 8601 datetime or date string")
    actual_finish: str | None = Field(None, description="ISO 8601 datetime or date string")
    planned_start: str | None = None
    planned_finish: str | None = None
    planned_duration_days: float | None = None
    actual_duration_days: float | None = None
    remaining_duration_days: float | None = None
    percent_complete: float | None = Field(None, ge=0, le=100)
    quantity_completed: float | None = None
    quantity_unit: str | None = None
    location_reference: str | None = None
    location_area: str | None = None
    location_unit: str | None = None
    equipment_tag: str | None = None
    line_number: str | None = None
    tag_number: str | None = None
    drawing_reference: str | None = None
    material_reference: str | None = None
    contractor_name: str | None = None
    supervisor_name: str | None = None
    engineer_name: str | None = None
    crew_name: str | None = None
    delay_status: str | None = None
    delay_category: str | None = None
    delay_reason: str | None = None
    blocker_description: str | None = None
    priority: str | None = "medium"
    extraction_notes: str | None = None
    field_provenance: dict[str, Any] = Field(default_factory=dict)


class ExtractionError(Exception):
    """Raised when extraction fails on LLM call after retries."""
    pass


def _get_system_prompt_template() -> str:
    """Read prompts/extractor_v2.txt if present, or return fallback."""
    if PROMPT_V2_FILE.exists():
        try:
            return PROMPT_V2_FILE.read_text(encoding="utf-8")
        except Exception as exc:
            log.warning("llm_extractor.prompt_file_read_failed", error=str(exc))

    return """You are an AI assistant for an Oil India infrastructure project management system.
Extract structured activity progress events and linked entities from field messages.
Return JSON with keys "activities" and "linked_entities".
Today: {today}
Discipline hint: {discipline_hint}
Return ONLY valid JSON."""


def _build_prompt(text: str, discipline_hint: str | None) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    hint = discipline_hint or "not specified — infer from content"
    template = _get_system_prompt_template()
    try:
        return template.format(today=today, discipline_hint=hint)
    except Exception:
        return template.replace("{today}", today).replace("{discipline_hint}", hint)


def _parse_llm_response(
    raw_response: str, return_entities: bool = False
) -> list[ExtractedActivity] | tuple[list[ExtractedActivity], list[ExtractedEntityItem]]:
    """
    Parse and validate LLM JSON output → list of ExtractedActivity (and optionally ExtractedEntityItem).
    Handles thinking tags, markdown code blocks, and model discrepancies.
    """
    text = raw_response.strip()

    # Strip thinking blocks if present
    if "<think>" in text:
        end_think = text.rfind("</think>")
        if end_think != -1:
            text = text[end_think + len("</think>"):].strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        text = "\n".join(inner_lines).strip()

    data = json.loads(text)

    # Determine activities list and entities list
    if isinstance(data, list):
        activities_raw = data
        entities_raw = []
    else:
        activities_raw = data.get("activities", [])
        entities_raw = data.get("linked_entities", [])

    activities: list[ExtractedActivity] = []
    for item in activities_raw:
        try:
            if "activity" in item and "activity_description" not in item:
                item["activity_description"] = item.pop("activity")
            if not item.get("activity_description"):
                continue
            activities.append(ExtractedActivity.model_validate(item))
        except ValidationError as exc:
            log.warning("llm_extractor.activity_validation_failed", error=str(exc), item=item)
            continue

    entities: list[ExtractedEntityItem] = []
    for item in entities_raw:
        try:
            entities.append(ExtractedEntityItem.model_validate(item))
        except ValidationError as exc:
            log.warning("llm_extractor.entity_validation_failed", error=str(exc), item=item)
            continue

    if return_entities:
        return activities, entities
    return activities


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _call_nvidia_nim(system_prompt: str, user_text: str) -> str:
    """Call OpenAI-compatible endpoint (NVIDIA NIM, Groq, Ollama, etc.)."""
    from openai import OpenAI

    client = OpenAI(
        base_url=settings.nvidia_nim_base_url,
        api_key=settings.nvidia_api_key or "no-key-required",
    )
    response = client.chat.completions.create(
        model=settings.nvidia_nim_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0.2,   # lower temperature for high-precision extraction
        top_p=0.95,
        max_tokens=3000,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return response.choices[0].message.content


_call_llm_service = _call_nvidia_nim


def extract_activities(
    text: str,
    discipline_hint: str | None = None,
    source_label: str = "unknown",
) -> tuple[list[ExtractedActivity], dict[str, Any]]:
    """
    Extract structured activities and entities from raw text.

    Args:
        text: Raw field report or OCR transcript.
        discipline_hint: Inferred or sender-provided discipline hint.
        source_label: Source identifier for provenance.

    Returns:
        (activities, audit_dict) where audit_dict contains 'linked_entities'.
    """
    system_prompt = _build_prompt(text, discipline_hint)
    llm_used = f"nvidia-nim/{settings.nvidia_nim_model}"
    raw_response = None

    try:
        raw_response = _call_nvidia_nim(system_prompt, text)
        log.info("llm_extractor.success", model=settings.nvidia_nim_model, source=source_label)
    except Exception as exc:
        log.error("llm_extractor.call_failed", model=settings.nvidia_nim_model, error=str(exc), source=source_label)
        raise ExtractionError(f"LLM call failed for message from {source_label}: {exc}") from exc

    try:
        activities, entities = _parse_llm_response(raw_response, return_entities=True)
    except (json.JSONDecodeError, KeyError) as exc:
        log.error("llm_extractor.parse_failed", error=str(exc), raw_response=raw_response[:500] if raw_response else None)
        raise ExtractionError(f"LLM response parse failed: {exc}") from exc

    audit = {
        "original_text": text,
        "llm_prompt_system": system_prompt[:500] + "...",
        "llm_response": raw_response,
        "llm_used": llm_used,
        "model_version": settings.nvidia_nim_model,
        "discipline_hint_used": discipline_hint,
        "source_label": source_label,
        "activities_extracted": len(activities),
        "linked_entities": [e.model_dump() for e in entities],
    }

    log.info(
        "llm_extractor.done",
        activities=len(activities),
        entities=len(entities),
        source=source_label,
    )

    return activities, audit
