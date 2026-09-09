"""
Analysis API endpoints — schedule health, delay & bottleneck intelligence,
resource allocation (Observed/Inferred/Unknown), and deterministic predictions.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.core.config import get_settings
from backend.services.analytics.delay_intelligence import get_delay_analytics
from backend.services.analytics.prediction_engine import compute_activity_prediction
from backend.services.analytics.resource_intelligence import get_resource_intelligence
from backend.services.analytics.schedule_intelligence import get_schedule_health

router = APIRouter()
settings = get_settings()


@router.get("/schedule-health")
async def schedule_health_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get project schedule health, variance metrics, milestone tracking, and critical path."""
    def _run_sync(session):
        return get_schedule_health(session)

    return await db.run_sync(_run_sync)


@router.get("/delays")
async def delay_analytics_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get delay classification across 12 categories, recurring blockers, and bottleneck locations."""
    def _run_sync(session):
        return get_delay_analytics(session)

    return await db.run_sync(_run_sync)


@router.get("/resources")
async def resource_intelligence_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get manpower and crew analysis explicitly segregating Observed vs Inferred vs Unknown."""
    def _run_sync(session):
        return get_resource_intelligence(session)

    return await db.run_sync(_run_sync)


@router.get("/predictions/{activity_id}")
async def activity_prediction_endpoint(
    activity_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get deterministic completion date forecast and delay risk for a specific activity.
    All numbers are computed from historical data; factors and evidence are cited.
    """
    def _run_sync(session):
        try:
            return compute_activity_prediction(activity_id, session)
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))

    return await db.run_sync(_run_sync)
