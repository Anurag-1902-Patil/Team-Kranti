"""Institutional memory API — semantic query and dataset export."""

from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from backend.api.deps import get_current_user, get_db
from backend.core.config import get_settings
from backend.services.institutional_memory.qdrant_store import (
    get_events_collection_count,
    query_institutional_memory,
)

router = APIRouter()
log = structlog.get_logger(__name__)
settings = get_settings()


@router.get("/query")
async def query_memory(
    q: str = Query(..., description="Natural language query"),
    discipline: str | None = Query(None),
    n: int = Query(10, ge=1, le=50),
    _: str = Depends(get_current_user),
) -> dict:
    """
    Semantic search over finalized progress events.
    Example: "piping spool erection duration delays"
    """
    results = query_institutional_memory(
        query_text=q,
        discipline=discipline,
        n_results=n,
    )

    return {
        "query": q,
        "discipline_filter": discipline,
        "result_count": len(results),
        "total_indexed": get_events_collection_count(),
        "results": results,
    }


@router.get("/export")
async def export_dataset(
    _: str = Depends(get_current_user),
):
    """
    Export the institutional memory dataset as Parquet + CSV + SCHEMA.md.
    Returns a ZIP archive for download.

    Per §7 of project context: this is an explicit required deliverable.
    """
    import io
    import zipfile
    import tempfile
    from fastapi.responses import StreamingResponse

    from backend.services.institutional_memory.exporter import export_dataset

    with tempfile.TemporaryDirectory() as tmpdir:
        result = export_dataset(
            output_dir=tmpdir,
            db_url_sync=settings.database_url_sync,
        )

        if result["event_count"] == 0:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No finalized events to export yet. Process some messages first.",
            )

        # Zip the output
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in result["files"]:
                path = Path(file_path)
                if path.exists():
                    zf.write(path, arcname=path.name)

        zip_buffer.seek(0)
        log.info("memory.export_served", event_count=result["event_count"])

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=sih26122_institutional_memory.zip"
            },
        )


@router.get("/stats")
async def memory_stats(
    _: str = Depends(get_current_user),
) -> dict:
    """Return counts for indexed events and activities."""
    from backend.services.institutional_memory.qdrant_store import (
        get_activity_collection_count,
    )

    return {
        "indexed_events": get_events_collection_count(),
        "indexed_activities": get_activity_collection_count(),
    }
