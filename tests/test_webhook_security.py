"""
Tests for webhook HMAC signature validation.

These tests verify the actual security logic — not just that a mock was called.
"""

import hashlib
import hmac as hmac_lib
import json

import pytest


class TestHMACValidation:
    """Tests for backend/security/hmac.py"""

    def _compute_valid_sig(self, payload: bytes, secret: str) -> str:
        digest = hmac_lib.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def test_valid_signature_accepted(self):
        """Correct HMAC signature returns True."""
        from backend.security.hmac import verify_whatsapp_signature

        secret = "test-app-secret"
        payload = b'{"object": "whatsapp_business_account"}'
        sig = self._compute_valid_sig(payload, secret)

        assert verify_whatsapp_signature(payload, sig, secret) is True

    def test_invalid_signature_rejected(self):
        """Tampered payload signature returns False."""
        from backend.security.hmac import verify_whatsapp_signature

        secret = "test-app-secret"
        original_payload = b'{"object": "whatsapp_business_account"}'
        sig = self._compute_valid_sig(original_payload, secret)

        tampered_payload = b'{"object": "TAMPERED"}'
        assert verify_whatsapp_signature(tampered_payload, sig, secret) is False

    def test_missing_signature_rejected(self):
        """None signature header returns False."""
        from backend.security.hmac import verify_whatsapp_signature

        assert verify_whatsapp_signature(b"payload", None, "secret") is False

    def test_signature_without_prefix_rejected(self):
        """Signature missing 'sha256=' prefix is rejected."""
        from backend.security.hmac import verify_whatsapp_signature

        payload = b"test"
        raw_hex = hmac_lib.new(b"secret", payload, hashlib.sha256).hexdigest()
        # No 'sha256=' prefix
        assert verify_whatsapp_signature(payload, raw_hex, "secret") is False

    def test_wrong_secret_rejected(self):
        """Signature computed with different secret returns False."""
        from backend.security.hmac import verify_whatsapp_signature

        payload = b"test payload"
        sig = self._compute_valid_sig(payload, "correct-secret")

        assert verify_whatsapp_signature(payload, sig, "wrong-secret") is False

    def test_empty_payload_valid_signature(self):
        """Empty payload with matching signature is accepted."""
        from backend.security.hmac import verify_whatsapp_signature

        secret = "secret"
        payload = b""
        sig = self._compute_valid_sig(payload, secret)

        assert verify_whatsapp_signature(payload, sig, secret) is True


class TestWebhookEndpoint:
    """Integration tests for the /webhooks/whatsapp endpoint."""

    def _make_payload(self, message_type="text", message_id="TEST-001"):
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "TEST_BUSINESS",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"display_phone_number": "1234", "phone_number_id": "ID"},
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": message_id,
                                        "timestamp": "1756281600",
                                        "type": message_type,
                                        "text": {"body": "Test message"} if message_type == "text" else None,
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

    def test_verification_challenge(self, test_client):
        """GET webhook with correct verify token returns challenge."""
        resp = test_client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == 12345

    def test_verification_wrong_token(self, test_client):
        """GET webhook with wrong verify token returns 403."""
        resp = test_client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "WRONG-TOKEN",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 403

    def _make_signed_request(self, test_client, payload: dict):
        """Send a POST request with a valid X-Hub-Signature-256 header."""
        import json as json_mod
        import hmac as hmac_mod
        import hashlib
        body = json_mod.dumps(payload).encode()
        sig = hmac_mod.new(b"test-secret", body, hashlib.sha256).hexdigest()
        return test_client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={sig}",
            },
        )

    def test_webhook_returns_200_immediately(self, test_client, mocker):
        """
        POST webhook must return 200 before processing (fire-and-forget).
        The Celery task enqueue is mocked so tests don't need a live Redis.
        """
        mocker.patch(
            "backend.workers.tasks.process_whatsapp_message.delay",
            return_value=None,
        )
        payload = self._make_payload()
        resp = self._make_signed_request(test_client, payload)
        # Should return 200 regardless (Celery task is enqueued, not waited on)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_webhook_status_update_payload_returns_200(self, test_client):
        """Status update payloads (no messages) return 200 silently."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "TEST_BUSINESS",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "statuses": [{"id": "MSG_ID", "status": "delivered"}],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }
        resp = self._make_signed_request(test_client, payload)
        assert resp.status_code == 200
