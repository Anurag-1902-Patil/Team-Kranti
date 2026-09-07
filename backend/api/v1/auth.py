"""
Simple named-token auth for the hackathon reviewer dashboard.

POST /auth/login  → {name: str, role: str} → {token: str, name: str, role: str}
POST /auth/logout → invalidate token

Tokens are stored in a module-level dict — process memory only. This is intentional
for a hackathon demo. On restart, everyone logs in again.

The token format is: f"{name}|{role}|{uuid4()}"
get_current_user() in deps.py accepts both:
  - Named tokens from this store (preferred)
  - The legacy REVIEWER_TOKEN env var (backward compat for tests)
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

router = APIRouter()

# In-memory token store: token_str → {name, role}
_token_store: dict[str, dict] = {}


class LoginRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Reviewer display name")
    role: str = Field(default="reviewer", description="reviewer | planner | admin")


class LoginResponse(BaseModel):
    token: str
    name: str
    role: str
    message: str


class LogoutRequest(BaseModel):
    token: str


def get_identity_from_token(token: str) -> dict | None:
    """Look up identity from named token store. Returns None if not found."""
    return _token_store.get(token)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(body: LoginRequest) -> LoginResponse:
    """
    Issue a named reviewer token.

    No password — this is a hackathon demo. The goal is audit trail realism:
    review_decisions rows will show who reviewed what, not just 'token_auth'.
    """
    valid_roles = {"reviewer", "planner", "admin"}
    role = body.role.lower()
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role must be one of: {', '.join(sorted(valid_roles))}",
        )

    token = f"{body.name}|{role}|{uuid.uuid4()}"
    _token_store[token] = {"name": body.name, "role": role}

    log.info("auth.login", name=body.name, role=role)

    return LoginResponse(
        token=token,
        name=body.name,
        role=role,
        message=f"Welcome, {body.name}! Your session token is active.",
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(body: LogoutRequest) -> dict:
    """Invalidate a named token."""
    if body.token in _token_store:
        identity = _token_store.pop(body.token)
        log.info("auth.logout", name=identity.get("name"))
        return {"status": "ok", "message": "Logged out."}
    return {"status": "ok", "message": "Token not found (already logged out or expired)."}


@router.get("/me", status_code=status.HTTP_200_OK)
async def me(token: str) -> dict:
    """Return identity for a token (for frontend to verify session)."""
    identity = _token_store.get(token)
    if not identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    return identity
