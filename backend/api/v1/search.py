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
