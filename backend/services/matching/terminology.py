"""
Terminology Normalization & Controlled Vocabulary Service.
Reference: SIH26122 §1.6.

Handles:
1. Deterministic normalization (case/whitespace/hyphen-insensitive matching)
2. Controlled vocabulary lookups against approved entity_aliases
3. Human-gated proposals for new vocabulary: genuinely new terminology is queued
   with status='proposed' and NEVER silently auto-promoted until a planner approves it.
"""

import re
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import EntityAlias


def clean_alias_key(text: str) -> str:
    """Normalize string for robust alias matching (lowercase, alphanumeric only)."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def normalize_term(
    raw_text: str,
    entity_type: str,
    session: Session,
    suggested_canonical: str | None = None,
) -> tuple[str, bool, str]:
    """
    Look up or propose an alias mapping.

    Args:
        raw_text: Raw term from supervisor update (e.g., "pump P101", "NE PetroWorks")
        entity_type: equipment, contractor, location, material, or discipline
        session: Active SQLAlchemy DB session
        suggested_canonical: Optional AI suggested canonical target

    Returns:
        (canonical_value, is_approved, resolution_status)
    """
    if not raw_text or not raw_text.strip():
        return raw_text, True, "empty"

    raw_clean = raw_text.strip()
    clean_key = clean_alias_key(raw_clean)

    # 1. Check approved aliases in database
    existing_aliases = session.execute(
        select(EntityAlias).where(
            EntityAlias.entity_type == entity_type,
            EntityAlias.status == "approved",
        )
    ).scalars().all()

    for alias in existing_aliases:
        if clean_alias_key(alias.raw_alias) == clean_key:
            return alias.canonical_value, True, "approved_alias_match"

    # 2. Check built-in common deterministic equipment/contractor patterns
    common_aliases: dict[str, dict[str, str]] = {
        "equipment": {
            "p101": "P-101",
            "pumpp101": "P-101",
            "p101pump": "P-101",
            "ft501": "FT-501",
            "transmitterft501": "FT-501",
            "mcc1": "MCC-1",
        },
        "contractor": {
            "nepetroworks": "NorthEast PetroWorks",
            "northeastpetro": "NorthEast PetroWorks",
            "brahmaputrainfra": "Brahmaputra Infratech",
            "brahmaputratech": "Brahmaputra Infratech",
            "assampiping": "Assam Piping Fabrication Ltd",
        },
        "location": {
            "areaa": "Area A",
            "areab": "Area B",
            "ch12450": "Chainage 12+450",
            "chainage12450": "Chainage 12+450",
        },
    }

    type_patterns = common_aliases.get(entity_type, {})
    if clean_key in type_patterns:
        canonical = type_patterns[clean_key]
        # Auto-create approved alias if not already in DB
        alias_record = EntityAlias(
            entity_type=entity_type,
            raw_alias=raw_clean,
            canonical_value=canonical,
            confidence=0.98,
            status="approved",
            proposed_by="rule_engine",
            approved_by="system",
            reviewed_at=datetime.now(tz=timezone.utc),
        )
        session.add(alias_record)
        session.flush()
        return canonical, True, "rule_engine_match"

    # 3. If unrecognized, create a PROPOSED alias in the review queue
    # Check if this proposal was already logged
    existing_proposal = session.execute(
        select(EntityAlias).where(
            EntityAlias.entity_type == entity_type,
            EntityAlias.raw_alias == raw_clean,
        )
    ).scalar_one_or_none()

    canonical_proposal = suggested_canonical or raw_clean.title()

    if not existing_proposal:
        new_proposal = EntityAlias(
            entity_type=entity_type,
            raw_alias=raw_clean,
            canonical_value=canonical_proposal,
            confidence=0.72,
            status="proposed",
            proposed_by="ai_proposal",
            reviewed_at=None,
        )
        session.add(new_proposal)
        session.flush()

    # Crucial guarantee: Return raw text and is_approved=False until approved by planner!
    return raw_clean, False, "proposed_gated_review"
