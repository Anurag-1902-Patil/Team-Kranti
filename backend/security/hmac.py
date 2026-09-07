"""
HMAC-SHA256 signature verification for Meta WhatsApp webhook.
Uses constant-time comparison to prevent timing attacks.
"""

import hashlib
import hmac

import structlog

log = structlog.get_logger(__name__)


def verify_whatsapp_signature(
    payload_bytes: bytes,
    x_hub_signature_256: str | None,
    app_secret: str,
) -> bool:
    """
    Verify that a webhook payload came from Meta.

    Meta sends X-Hub-Signature-256: sha256=<hex_digest>.
    We compute HMAC-SHA256(app_secret, payload_bytes) and compare
    using hmac.compare_digest (constant-time) to prevent timing attacks.

    Args:
        payload_bytes: The raw request body bytes.
        x_hub_signature_256: The value of the X-Hub-Signature-256 header.
        app_secret: The WhatsApp App Secret from Meta Developer Console.

    Returns:
        True if valid, False otherwise.
    """
    if not x_hub_signature_256:
        log.warning("webhook.signature_missing")
        return False

    if not x_hub_signature_256.startswith("sha256="):
        log.warning("webhook.signature_malformed", header=x_hub_signature_256[:20])
        return False

    expected_hex = x_hub_signature_256[len("sha256="):]

    computed = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(computed, expected_hex)

    if not is_valid:
        log.warning(
            "webhook.signature_invalid",
            expected_prefix=expected_hex[:8] + "...",
            computed_prefix=computed[:8] + "...",
        )

    return is_valid
