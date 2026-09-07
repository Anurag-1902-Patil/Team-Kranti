"""
Speech-to-text using faster-whisper.
Converts audio bytes → plain text transcript.

Model is loaded once per worker process (module-level singleton).
Supports WhatsApp audio formats: OGG/Opus (primary), MP3, WAV, M4A.
"""

import io
import tempfile
from pathlib import Path

import structlog

from backend.core.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

_whisper_model = None


def _get_model():
    """Lazy-load the faster-whisper model (singleton per process)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        log.info(
            "asr.loading_model",
            model=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        _whisper_model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        log.info("asr.model_ready")
    return _whisper_model


def transcribe(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Transcribe audio bytes to text.

    Args:
        audio_bytes: Raw audio bytes from WhatsApp/MinIO.
        mime_type: MIME type hint (used only for temp file extension).

    Returns:
        Transcribed text string.

    Raises:
        RuntimeError if transcription fails.
    """
    # Map MIME type to extension for temp file
    ext_map = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
        "audio/amr": ".amr",
    }
    ext = ext_map.get(mime_type.split(";")[0].strip(), ".audio")

    # faster-whisper needs a file path, not bytes
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = _get_model()
        segments, info = model.transcribe(
            tmp_path,
            beam_size=5,
            language="en",  # Primarily English; Hindi/mixed may need "hi" or None for auto
            vad_filter=True,  # Remove silence
        )

        transcript_parts = [seg.text.strip() for seg in segments]
        full_transcript = " ".join(transcript_parts).strip()

        log.info(
            "asr.transcribed",
            language=info.language,
            language_prob=round(info.language_probability, 2),
            duration_s=round(info.duration, 1),
            words=len(full_transcript.split()),
        )

        return full_transcript

    except Exception as exc:
        log.error("asr.transcription_failed", error=str(exc))
        raise RuntimeError(f"Transcription failed: {exc}") from exc

    finally:
        Path(tmp_path).unlink(missing_ok=True)
