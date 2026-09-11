"""
Grounded Natural-Language Search API endpoint.
Reference: SIH26122 §2.3.
"""

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.services.search.nl_search import execute_grounded_search

router = APIRouter()


class NLSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language search query")


@router.post("/natural")
async def natural_search_endpoint(
    request: NLSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Search project activities, field events, and equipment using grounded natural language.
    Safe by construction — translates to a structured filter object and runs parameterized SQL.
    """
    def _run_sync(session):
        return execute_grounded_search(request.query, session)

    return await db.run_sync(_run_sync)


@router.post("/parse-filter")
async def parse_filter_endpoint(
    request: NLSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Part C #4: Search filter-parsing endpoint.
    Takes free text, returns the parsed structured filter object (entity type, discipline, status,
    location, flags) from the parser/LLM, keeping the raw filter inspectable/debuggable
    before submission, and suggests navigation route.
    """
    from backend.services.search.nl_search import parse_query_to_filters

    filters = parse_query_to_filters(request.query)

    # Build human explanation
    parts = []
    if filters.discipline:
        parts.append(f"Discipline = '{filters.discipline}'")
    if filters.location:
        parts.append(f"Location = '{filters.location}'")
    if filters.status:
        parts.append(f"Status = '{filters.status}'")
    if filters.is_delayed:
        parts.append("Delayed only")
    if filters.is_critical:
        parts.append("Critical Path only")
    if filters.has_blocker:
        parts.append("With active blockers")
    if filters.equipment_tag:
        parts.append(f"Equipment = '{filters.equipment_tag}'")
    if filters.keyword:
        parts.append(f"Keyword = '{filters.keyword}'")

    explanation = f"Searching {filters.target_type}s with: " + (", ".join(parts) if parts else "free text search")

    # Suggested route
    route = "/schedule"
    query_params = []
    if filters.discipline:
        query_params.append(f"discipline={filters.discipline}")
    if filters.status:
        query_params.append(f"status={filters.status}")
    if filters.is_critical:
        query_params.append("critical_only=true")
    if filters.keyword:
        query_params.append(f"search={filters.keyword}")

    if filters.target_type == "event":
        route = "/review"
    elif query_params:
        route += "?" + "&".join(query_params)

    # Preview results
    def _run_sync(session):
        return execute_grounded_search(request.query, session)

    search_res = await db.run_sync(_run_sync)

    return {
        "query": request.query,
        "filters": filters.model_dump(),
        "explanation": explanation,
        "suggested_route": route,
        "results_preview": (search_res.get("results") or [])[:6],
        "total_matches": len(search_res.get("results") or []),
    }
