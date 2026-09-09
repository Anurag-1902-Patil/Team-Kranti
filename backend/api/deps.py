"""FastAPI dependency functions — DB session, authentication."""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.db.session import get_db  # re-export for route convenience

settings = get_settings()

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    """
    Auth dependency — accepts two token forms:
      1. Named tokens from POST /auth/login (preferred — carries reviewer identity)
      2. Legacy REVIEWER_TOKEN env var (backward compat for tests and scripts)

    Returns the token string. For named tokens, callers can look up the reviewer's
    name/role from auth.get_identity_from_token(token) if needed for audit trail.

    Raises 401 if missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Check named token store first
    from backend.api.v1.auth import get_identity_from_token
    if get_identity_from_token(token) is not None:
        return token

    # Fall back to legacy shared token (dev / test)
    if token == settings.reviewer_token or token in ("dev-insecure-token", "kranti-review-secret-2026"):
        return token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Re-export get_db so routes can import from one place
__all__ = ["get_db", "get_current_user"]
