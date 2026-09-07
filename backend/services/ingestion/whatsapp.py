"""
WhatsApp Cloud API webhook payload parsing.
Converts Meta's JSON webhook structure into typed Python models.
Handles: text, audio, image, document, and mixed (caption+attachment) messages.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WAMessageType(str, Enum):
    text = "text"
    audio = "audio"
    image = "image"
    document = "document"
    video = "video"
    sticker = "sticker"
    interactive = "interactive"
    unknown = "unknown"


class WATextBody(BaseModel):
    body: str


class WAMedia(BaseModel):
    """Common structure for image/audio/document/video."""
    id: str                         # Media ID — use to download
    mime_type: str | None = None
    sha256: str | None = None
    filename: str | None = None     # Present for documents
    caption: str | None = None      # Optional caption on image/document


class WAMessage(BaseModel):
    id: str
    from_number: str = Field(alias="from")
    timestamp: str
    type: WAMessageType = WAMessageType.unknown
    text: WATextBody | None = None
    audio: WAMedia | None = None
    image: WAMedia | None = None
    document: WAMedia | None = None
    video: WAMedia | None = None

    model_config = {"populate_by_name": True}

    @property
    def received_at(self) -> datetime:
        try:
            ts = int(self.timestamp)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OSError):
            return datetime.now(tz=timezone.utc)

    @property
    def raw_text(self) -> str | None:
        """Best-effort plain text from any message type."""
        if self.text:
            return self.text.body
        # Caption on media acts as text
        for media_field in (self.image, self.document, self.audio, self.video):
            if media_field and media_field.caption:
                return media_field.caption
        return None

    @property
    def media(self) -> WAMedia | None:
        """The first non-None media attachment."""
        return self.image or self.audio or self.document or self.video


def parse_webhook_payload(payload: dict[str, Any]) -> list[WAMessage]:
    """
    Extract all WAMessage objects from a Meta webhook payload.
    Meta batches multiple messages in one webhook call.
    Returns an empty list for status-update-only payloads.
    """
    messages: list[WAMessage] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg_data in value.get("messages", []):
                try:
                    msg = WAMessage.model_validate(msg_data)
                    messages.append(msg)
                except Exception:
                    # Never crash on a malformed message — log and skip
                    import structlog
                    structlog.get_logger(__name__).warning(
                        "whatsapp.parse_error",
                        raw=str(msg_data)[:200],
                    )

    return messages
