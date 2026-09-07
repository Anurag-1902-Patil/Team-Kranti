"""
Celery tasks — full pipeline orchestration per WhatsApp message.

process_whatsapp_message is the main task:
  1. Idempotency check (ON CONFLICT skip)
  2. Parse payload → Document record
  3. Branch by MIME type → raw text
  4. Discipline hint from sender_profiles
  5. LLM extraction → ExtractedActivity list
  6. Schema normalization → ProgressEvent records
  7. Fuzzy + semantic matching + LLM re-rank → confidence routing
  8. Postgres write (events + match candidates + audit trail)
  9. Schedule write-back (if matched)
  10. Qdrant indexing (if matched)

Retries: 3 attempts, exponential backoff (60s, 120s, 240s).
Failures: write processing_failed status to document row, log for manual triage.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from celery import Task
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.core.config import get_settings
from backend.db.models import (
    Document,
    Match,
    MatchStatusEnum,
    ProgressEvent,
    SenderProfile,
    SourceTypeEnum,
)
from backend.schemas.event import ProgressEventCreate
from backend.services.extraction.llm_extractor import ExtractionError, extract_activities
from backend.services.extraction.normalizer import normalize
from backend.services.ingestion.whatsapp import WAMessageType, parse_webhook_payload
from backend.services.matching.confidence import fuse_and_route
from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates
from backend.services.matching.semantic_matcher import get_semantic_candidates
from backend.workers.celery_app import celery_app

log = structlog.get_logger(__name__)
settings = get_settings()


def _run_async(coro):
    """Run a coroutine synchronously (for Celery task context)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _get_sync_session():
    """Return a synchronous SQLAlchemy session for Celery worker use."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def _get_source_type(mime_type: str | None, message_type: str) -> SourceTypeEnum:
    if message_type == "audio":
        return SourceTypeEnum.voice_log
    if message_type == "text":
        return SourceTypeEnum.free_text_dpr
    if mime_type:
        if "image" in mime_type:
            return SourceTypeEnum.scanned_diary
        if "spreadsheet" in mime_type or "excel" in mime_type or "csv" in mime_type:
            return SourceTypeEnum.spreadsheet
        if "pdf" in mime_type:
            return SourceTypeEnum.scanned_diary
    return SourceTypeEnum.unknown


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="workers.process_whatsapp_message",
)
def process_whatsapp_message(
    self: Task,
    message_id: str,
    sender_id: str,
    message_type: str,
    raw_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Main pipeline task — processes one WhatsApp message end-to-end.
    """
    log.info(
        "task.started",
        message_id=message_id,
        sender=sender_id,
        type=message_type,
        attempt=self.request.retries + 1,
    )

    session = _get_sync_session()

    try:
        # -----------------------------------------------------------------------
        # Step 1: Idempotency check
        # -----------------------------------------------------------------------
        existing = session.execute(
            select(Document).where(Document.message_id == message_id)
        ).scalar_one_or_none()

        if existing and existing.processing_status == "completed":
            log.info("task.idempotent_skip", message_id=message_id)
            return {"status": "skipped", "reason": "already_processed"}

        # -----------------------------------------------------------------------
        # Step 2: Create / update Document record
        # -----------------------------------------------------------------------
        messages = parse_webhook_payload(raw_payload)
        msg = next((m for m in messages if m.id == message_id), None)

        if msg is None:
            log.error("task.message_not_found_in_payload", message_id=message_id)
            return {"status": "error", "reason": "message_not_found"}

        if existing is None:
            doc = Document(
                message_id=message_id,
                sender_id=sender_id,
                source_type=_get_source_type(None, message_type),
                received_at=msg.received_at,
                processing_status="processing",
            )
            session.add(doc)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                log.info("task.idempotent_skip_db_conflict", message_id=message_id)
                return {"status": "skipped", "reason": "db_conflict"}
        else:
            doc = existing
            doc.processing_status = "processing"
            session.flush()

        # -----------------------------------------------------------------------
        # Step 3: Extract text from message content
        # -----------------------------------------------------------------------
        raw_text: str | None = None
        mime_type: str | None = None
        source_type = SourceTypeEnum.unknown
        is_handwritten = False

        if msg.type == WAMessageType.text:
            raw_text = msg.raw_text
            source_type = SourceTypeEnum.free_text_dpr

        elif msg.type == WAMessageType.audio:
            # Download audio → faster-whisper transcription
            source_type = SourceTypeEnum.voice_log
            if msg.audio and settings.whatsapp_access_token:
                try:
                    from backend.services.ingestion.media import (
                        download_media,
                        upload_to_minio,
                        upload_extracted_text,
                    )
                    from backend.services.extraction.asr import transcribe

                    audio_bytes, mime_type = asyncio.run(
                        download_media(msg.audio.id, settings.whatsapp_access_token)
                    )
                    s3_key = upload_to_minio(audio_bytes, message_id, f"{message_id}.ogg", mime_type or "audio/ogg")
                    doc.s3_key = s3_key

                    raw_text = transcribe(audio_bytes, mime_type or "audio/ogg")
                    doc.raw_text = raw_text
                    doc.extracted_text_s3_key = upload_extracted_text(raw_text, message_id, "transcript.txt")
                except Exception as exc:
                    log.error("task.asr_failed", message_id=message_id, error=str(exc))
                    raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

        elif msg.type in (WAMessageType.image, WAMessageType.document):
            media = msg.media
            if media and settings.whatsapp_access_token:
                try:
                    from backend.services.ingestion.media import (
                        download_media,
                        upload_to_minio,
                        upload_extracted_text,
                    )
                    from backend.services.extraction.ocr import (
                        extract_text_printed,
                        extract_text_handwritten,
                        extract_text_from_pdf,
                        extract_text_from_spreadsheet,
                    )

                    file_bytes, mime_type = asyncio.run(
                        download_media(
                            media.id,
                            settings.whatsapp_access_token,
                            filename=media.filename,
                        )
                    )

                    filename = media.filename or f"{message_id}.bin"
                    s3_key = upload_to_minio(file_bytes, message_id, filename, mime_type)
                    doc.s3_key = s3_key
                    doc.mime_type = mime_type

                    if "image" in (mime_type or ""):
                        # Heuristic: images sent as WAMessageType.image are typically
                        # handwritten diaries; typed content comes as documents.
                        is_handwritten = msg.type == WAMessageType.image
                        if is_handwritten:
                            # PP-OCRv5 — no groq client needed, CPU-only
                            raw_text = extract_text_handwritten(file_bytes)
                            source_type = SourceTypeEnum.scanned_diary
                        else:
                            raw_text = extract_text_printed(file_bytes)
                            source_type = SourceTypeEnum.image_annotation

                    elif "pdf" in (mime_type or ""):
                        raw_text = extract_text_from_pdf(file_bytes)
                        source_type = SourceTypeEnum.scanned_diary

                    elif any(x in (mime_type or "") for x in ["spreadsheet", "excel", "csv"]):
                        raw_text = extract_text_from_spreadsheet(file_bytes, filename)
                        source_type = SourceTypeEnum.spreadsheet

                    # Combine with any caption text
                    caption = msg.raw_text
                    if caption:
                        raw_text = f"{caption}\n\n{raw_text or ''}".strip()

                    if raw_text:
                        doc.extracted_text_s3_key = upload_extracted_text(raw_text, message_id, "extracted.txt")

                except Exception as exc:
                    log.error("task.media_extraction_failed", message_id=message_id, error=str(exc))
                    raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

        doc.raw_text = raw_text
        doc.source_type = source_type
        doc.mime_type = mime_type
        session.flush()

        if not raw_text:
            log.warning("task.no_text_extracted", message_id=message_id)
            doc.processing_status = "no_text"
            session.commit()
            return {"status": "ok", "events": 0, "reason": "no_text"}

        # -----------------------------------------------------------------------
        # Step 4: Discipline hint from sender_profiles
        # -----------------------------------------------------------------------
        profile = session.execute(
            select(SenderProfile).where(SenderProfile.sender_id == sender_id)
        ).scalar_one_or_none()
        discipline_hint: str | None = profile.discipline if profile else None

        log.info(
            "task.discipline_hint",
            message_id=message_id,
            hint=discipline_hint or "none_llm_will_infer",
        )

        # -----------------------------------------------------------------------
        # Step 5: LLM extraction
        # -----------------------------------------------------------------------
        try:
            extracted_activities, audit_trail = extract_activities(
                text=raw_text,
                discipline_hint=discipline_hint,
                source_label=source_type.value,
            )
        except ExtractionError as exc:
            log.error("task.extraction_failed", message_id=message_id, error=str(exc))
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

        if not extracted_activities:
            log.warning("task.no_activities_extracted", message_id=message_id)
            doc.processing_status = "no_activities"
            session.commit()
            return {"status": "ok", "events": 0, "reason": "no_activities_extracted"}

        # -----------------------------------------------------------------------
        # Step 6: Build activity index for matching
        # -----------------------------------------------------------------------
        from backend.services.matching.semantic_matcher import (
            _activity_ids,
            _embedding_matrix,
        )

        # Build sync activity index from DB
        from backend.db.models import PlanActivity

        plan_activities = session.execute(
            select(PlanActivity.activity_id, PlanActivity.activity_name)
        ).all()
        activity_index = {row.activity_id: row.activity_name for row in plan_activities}

        # Reload semantic embeddings if not loaded
        if _embedding_matrix is None and activity_index:
            from backend.services.matching.semantic_matcher import load_activity_embeddings
            load_activity_embeddings(activity_index)

        # -----------------------------------------------------------------------
        # Step 7–9: Normalize → Match → Write per extracted activity
        # -----------------------------------------------------------------------
        created_event_ids = []

        for extracted in extracted_activities:
            # Normalize to §3.4 schema
            event_create = normalize(
                extracted=extracted,
                document_id=doc.id,
                project_id=settings.project_id,
                source_type=source_type.value,
                source_document_id=doc.s3_key,
                audit_trail=audit_trail,
            )

            # Fuzzy + semantic matching
            fuzzy_candidates = get_fuzzy_candidates(
                description=extracted.activity_description,
                activity_index=activity_index,
                top_k=10,
            )
            semantic_candidates = get_semantic_candidates(
                description=extracted.activity_description,
                top_k=10,
            )

            match_result = fuse_and_route(
                description=extracted.activity_description,
                discipline=event_create.discipline.value,
                fuzzy_candidates=fuzzy_candidates,
                semantic_candidates=semantic_candidates,
            )

            # Resolve plan_activity_id FK
            plan_activity_id = None
            activity_name_plan = None
            if match_result.selected_activity_id:
                pa = session.execute(
                    select(PlanActivity).where(
                        PlanActivity.activity_id == match_result.selected_activity_id
                    )
                ).scalar_one_or_none()
                if pa:
                    plan_activity_id = pa.id
                    activity_name_plan = pa.activity_name

            # Create ProgressEvent
            event = ProgressEvent(
                project_id=event_create.project_id,
                document_id=doc.id,
                activity_id_plan=match_result.selected_activity_id,
                plan_activity_id=plan_activity_id,
                activity_name_plan=activity_name_plan,
                activity_description_extracted=event_create.activity_description_extracted,
                discipline=event_create.discipline,
                event_type=event_create.event_type,
                actual_start_datetime=event_create.actual_start_datetime,
                actual_finish_datetime=event_create.actual_finish_datetime,
                percent_complete=event_create.percent_complete,
                quantity_completed=event_create.quantity_completed,
                quantity_unit=event_create.quantity_unit,
                location_reference=event_create.location_reference,
                confidence_score=match_result.final_score,
                match_status=match_result.match_status,
                source_type=event_create.source_type,
                source_document_id=event_create.source_document_id,
                extracted_by=event_create.extracted_by,
                extraction_timestamp=event_create.extraction_timestamp,
                reviewed_by_planner=False,
                audit_trail={
                    **audit_trail,
                    "match_justification": match_result.llm_justification,
                    "match_status": match_result.match_status.value,
                },
            )
            session.add(event)
            session.flush()

            # Write match candidates to matches table
            for candidate in match_result.all_candidates[:10]:
                pa_id = None
                if candidate.activity_id in activity_index:
                    pa_row = session.execute(
                        select(PlanActivity.id).where(
                            PlanActivity.activity_id == candidate.activity_id
                        )
                    ).scalar_one_or_none()
                    pa_id = pa_row

                match_row = Match(
                    event_id=event.id,
                    candidate_activity_id=candidate.activity_id,
                    plan_activity_id=pa_id,
                    fuzzy_score=candidate.fuzzy_score,
                    semantic_score=candidate.semantic_score,
                    llm_score=candidate.llm_score,
                    final_score=candidate.final_score,
                    rank=candidate.rank,
                    was_selected=candidate.was_selected,
                )
                session.add(match_row)

            # Auto schedule write-back for high-confidence matches
            if match_result.match_status == MatchStatusEnum.matched and plan_activity_id:
                from backend.db.models import PlanActivity as PA

                session.execute(
                    select(PA).where(PA.id == plan_activity_id)
                )
                update_vals: dict = {}
                if event.actual_start_datetime:
                    update_vals["actual_start"] = event.actual_start_datetime
                if event.actual_finish_datetime:
                    update_vals["actual_finish"] = event.actual_finish_datetime
                if event.percent_complete:
                    update_vals["actual_percent_complete"] = event.percent_complete
                if update_vals:
                    from sqlalchemy import update as sa_update
                    session.execute(
                        sa_update(PlanActivity)
                        .where(PlanActivity.id == plan_activity_id)
                        .values(**update_vals)
                    )

            # Index to Qdrant if matched (institutional memory)
            if match_result.match_status == MatchStatusEnum.matched:
                try:
                    from backend.services.institutional_memory.qdrant_store import (
                        index_progress_event,
                    )

                    embedding_id = index_progress_event(
                        event_id=str(event.id),
                        activity_description=extracted.activity_description,
                        activity_name_plan=activity_name_plan,
                        discipline=event_create.discipline.value,
                        project_id=settings.project_id,
                        confidence_score=match_result.final_score,
                        actual_start=str(event.actual_start_datetime) if event.actual_start_datetime else None,
                        actual_finish=str(event.actual_finish_datetime) if event.actual_finish_datetime else None,
                    )
                    event.embedding_id = embedding_id
                except Exception as exc:
                    log.warning("task.chroma_index_failed", event_id=str(event.id), error=str(exc))

            created_event_ids.append(str(event.id))
            log.info(
                "task.event_created",
                event_id=str(event.id),
                match_status=match_result.match_status.value,
                confidence=round(match_result.final_score, 3),
                description=extracted.activity_description[:80],
            )

        # -----------------------------------------------------------------------
        # Finalize
        # -----------------------------------------------------------------------
        doc.processing_status = "completed"
        doc.processed_at = datetime.now(tz=timezone.utc)
        session.commit()

        log.info(
            "task.completed",
            message_id=message_id,
            events_created=len(created_event_ids),
        )

        return {
            "status": "ok",
            "events": len(created_event_ids),
            "event_ids": created_event_ids,
        }

    except Exception as exc:
        session.rollback()
        log.error("task.unhandled_error", message_id=message_id, error=str(exc))

        # Mark document as failed for manual triage
        try:
            session.execute(
                select(Document).where(Document.message_id == message_id)
            )
            from sqlalchemy import update as sa_update
            session.execute(
                sa_update(Document)
                .where(Document.message_id == message_id)
                .values(
                    processing_status="processing_failed",
                    processing_error=str(exc)[:1000],
                )
            )
            session.commit()
        except Exception:
            pass

        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    finally:
        session.close()
