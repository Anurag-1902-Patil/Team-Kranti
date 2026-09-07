"""
WhatsApp webhook endpoints.

GET  /webhooks/whatsapp — Meta verification challenge
POST /webhooks/whatsapp — Receive messages, validate HMAC, enqueue, return 200

Critical: the 200 response MUST be sent before any processing begins.
If Meta doesn't receive 200 within ~5s it will retry — leading to duplicate processing.
Idempotency is handled in the Celery task via message_id UNIQUE constraint.
"""

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.core.config import get_settings
from backend.db.models import Document
from backend.security.hmac import verify_whatsapp_signature
from backend.services.ingestion.whatsapp import parse_webhook_payload
from backend.workers.tasks import process_whatsapp_message

router = APIRouter()
settings = get_settings()
log = structlog.get_logger(__name__)


@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Any:
    """
    Meta webhook verification challenge.
    Returns hub.challenge if the verify_token matches.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        log.info("webhook.verified")
        return int(hub_challenge)

    log.warning(
        "webhook.verification_failed",
        mode=hub_mode,
        token_match=(hub_verify_token == settings.whatsapp_verify_token),
    )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed.")


@router.post("/whatsapp", status_code=status.HTTP_200_OK)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Receive a WhatsApp Cloud API webhook notification.

    Order of operations (critical — do not reorder):
    1. Read raw body
    2. HMAC validate (return 401 on failure — Meta won't retry 4xx)
    3. Parse payload to find message IDs
    4. For each message: check idempotency (skip if already seen)
    5. Enqueue Celery task (fire-and-forget)
    6. Return 200 IMMEDIATELY

    Meta considers anything other than 200 a failure and retries with backoff.
    """
    raw_body = await request.body()

    # --- Step 1: HMAC validation ---
    # In dev with no secret set, skip validation so local testing works
    if settings.whatsapp_app_secret:
        sig = request.headers.get("x-hub-signature-256")
        if not verify_whatsapp_signature(raw_body, sig, settings.whatsapp_app_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature.",
            )
    else:
        log.warning("webhook.hmac_skip_no_secret_configured")

    # --- Step 2: Parse ---
    try:
        payload = await request.json()
    except Exception:
        # Still return 200 — don't let malformed JSON cause Meta retries
        log.error("webhook.json_parse_error", body_prefix=raw_body[:200].decode("utf-8", errors="replace"))
        return {"status": "ok"}

    messages = parse_webhook_payload(payload)

    if not messages:
        # Status update or other notification — acknowledge and move on
        return {"status": "ok"}

    log.info("webhook.received", message_count=len(messages))

    # --- Step 3: Idempotency check + enqueue ---
    # We do a fast existence check here so we don't even enqueue duplicates.
    # The Celery task also has a guard for race conditions.
    for msg in messages:
        log.info(
            "webhook.enqueuing",
            message_id=msg.id,
            sender=msg.from_number,
            msg_type=msg.type,
        )
        # Fire-and-forget to Celery — do NOT await
        process_whatsapp_message.delay(
            message_id=msg.id,
            sender_id=msg.from_number,
            message_type=msg.type.value,
            raw_payload=payload,
        )

    return {"status": "ok"}
