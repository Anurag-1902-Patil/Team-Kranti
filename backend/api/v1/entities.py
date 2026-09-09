"""
Entities API endpoints — master entities, extensible disciplines, and terminology aliases.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.db.models import (
    Contractor,
    Discipline,
    EntityAlias,
    Equipment,
    Location,
    Organization,
)

router = APIRouter()


class AliasCreateRequest(BaseModel):
    entity_type: str
    raw_alias: str
    canonical_value: str


@router.get("/disciplines")
async def list_disciplines(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all registered disciplines from the lookup table."""
    result = await db.execute(select(Discipline).order_by(Discipline.display_order))
    rows = result.scalars().all()
    return [
        {
            "code": r.code,
            "name": r.name,
            "category": r.category,
            "description": r.description,
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.get("/contractors")
async def list_contractors(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List project contractors."""
    result = await db.execute(select(Contractor).where(Contractor.is_active.is_(True)))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "trade_specialty": r.trade_specialty,
            "contact_person": r.contact_person,
            "phone": r.phone,
        }
        for r in rows
    ]


@router.get("/equipment")
async def list_equipment(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List tagged site equipment."""
    result = await db.execute(select(Equipment).order_by(Equipment.tag))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "tag": r.tag,
            "name": r.name,
            "equipment_type": r.equipment_type,
            "area": r.area,
            "status": r.status,
        }
        for r in rows
    ]


@router.get("/locations")
async def list_locations(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List site locations and chainages."""
    result = await db.execute(select(Location).order_by(Location.code))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "area": r.area,
            "grid_reference": r.grid_reference,
        }
        for r in rows
    ]


@router.get("/aliases")
async def list_aliases(
    status: str | None = Query(None, description="proposed, approved, or rejected"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List terminology aliases (for review queue or reference)."""
    stmt = select(EntityAlias)
    if status:
        stmt = stmt.where(EntityAlias.status == status)
    result = await db.execute(stmt.order_by(EntityAlias.created_at.desc()))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "entity_type": r.entity_type,
            "raw_alias": r.raw_alias,
            "canonical_value": r.canonical_value,
            "confidence": r.confidence,
            "status": r.status,
            "proposed_by": r.proposed_by,
            "approved_by": r.approved_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
