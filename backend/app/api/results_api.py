from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession

from backend.app.db.database import get_db
from backend.app.schemas.results import (
    AnalysisResultCreate,
    AnalysisResultUpdate,
    AnalysisResultResponse,
    AnalysisResultDetailResponse,
    PaginatedResultsResponse,
    ResultsSummaryResponse,
    DetectionEventCreate,
    DetectionEventResponse,
    MediaAssetCreate,
    MediaAssetResponse,
    SurveillanceSessionCreate,
    SurveillanceSessionResponse
)
from backend.app.services.central_results_service import central_results_service

router = APIRouter(tags=["Centralized Results Management"])


# ==============================================================================
# 1. ANALYSIS RESULTS ENDPOINTS (FR-01 to FR-10)
# ==============================================================================

@router.post("/results", status_code=status.HTTP_201_CREATED)
def create_result(data: AnalysisResultCreate, db: DBSession = Depends(get_db)):
    """
    Creates a new analysis result record in the centralized database (FR-01).
    Validates input and ensures idempotent creation.
    """
    try:
        res = central_results_service.create_result(data, db=db)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create result: {str(e)}")


@router.get("/results/summary")
def get_results_summary(db: DBSession = Depends(get_db)):
    """
    Retrieves dashboard summary statistics across all five modules (FR-07).
    """
    return central_results_service.get_summary(db=db)


@router.get("/results")
def list_results(
    module_type: Optional[str] = Query(None, description="Filter by module: navigation, rod_debris, runway_lights, live_surveillance, offline_surveillance"),
    status: Optional[str] = Query(None, description="Filter by status: queued, processing, completed, failed"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    search: Optional[str] = Query(None, description="Search term for ID, session ID, or title"),
    detection_class: Optional[str] = Query(None, description="Filter by detected class name"),
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: DBSession = Depends(get_db)
):
    """
    Retrieves paginated and filtered results from the centralized database (FR-07, FR-08).
    """
    return central_results_service.list_results(
        module_type=module_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        search=search,
        detection_class=detection_class,
        camera_id=camera_id,
        page=page,
        page_size=page_size,
        db=db
    )


@router.get("/results/{id}")
def get_result_details(id: str, db: DBSession = Depends(get_db)):
    """
    Retrieves complete stored details, detection events, and media assets for a result (FR-09).
    """
    res = central_results_service.get_result(id, db=db)
    if not res:
        # Check if it exists in analysis_jobs and sync on-the-fly
        synced = central_results_service.sync_analysis_job_to_central_result(id, db=db)
        if synced:
            res = central_results_service.get_result(id, db=db)
    if not res:
        raise HTTPException(status_code=404, detail=f"Analysis result {id} not found")
    return res


@router.patch("/results/{id}")
def update_result(id: str, data: AnalysisResultUpdate, db: DBSession = Depends(get_db)):
    """
    Updates processing status, summary, or error information for a result (FR-10).
    """
    res = central_results_service.update_result(id, data, db=db)
    if not res:
        raise HTTPException(status_code=404, detail=f"Analysis result {id} not found")
    return res


@router.get("/results/{id}/events")
def get_result_events(
    id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    event_type: Optional[str] = None,
    class_name: Optional[str] = None,
    db: DBSession = Depends(get_db)
):
    """
    Retrieves detection events associated with a specific analysis result.
    """
    from backend.app.db.models import DetectionEvent
    res = central_results_service.get_result(id, db=db)
    if not res:
        raise HTTPException(status_code=404, detail=f"Analysis result {id} not found")

    query = db.query(DetectionEvent).filter(DetectionEvent.analysis_result_id == id)
    if event_type:
        query = query.filter(DetectionEvent.event_type.ilike(f"%{event_type}%"))
    if class_name:
        query = query.filter(DetectionEvent.class_name.ilike(f"%{class_name}%"))

    total = query.count()
    offset = max(0, (page - 1) * page_size)
    events = query.order_by(DetectionEvent.timestamp.asc()).offset(offset).limit(page_size).all()

    return {
        "analysis_result_id": id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [central_results_service._event_to_dict(e) for e in events]
    }


@router.get("/results/{id}/media")
def get_result_media(id: str, db: DBSession = Depends(get_db)):
    """
    Retrieves media metadata and authorized access links for a result.
    """
    res = central_results_service.get_result(id, db=db)
    if not res:
        raise HTTPException(status_code=404, detail=f"Analysis result {id} not found")

    return {
        "analysis_result_id": id,
        "media_assets": res.get("media_assets", [])
    }


# ==============================================================================
# 2. SURVEILLANCE SESSIONS ENDPOINTS (FR-05, FR-06)
# ==============================================================================

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(data: SurveillanceSessionCreate, db: DBSession = Depends(get_db)):
    """
    Creates a new surveillance session record (live or offline).
    """
    return central_results_service.create_surveillance_session(data, db=db)


@router.get("/sessions")
def list_sessions(
    mode: Optional[str] = Query(None, description="Filter by mode: live, offline"),
    status: Optional[str] = Query(None, description="Filter by status: active, completed, stopped, error"),
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: DBSession = Depends(get_db)
):
    """
    Searches surveillance and analysis sessions.
    """
    from backend.app.db.models import SurveillanceSessionRecord
    query = db.query(SurveillanceSessionRecord)
    if mode:
        query = query.filter(SurveillanceSessionRecord.mode == mode.lower())
    if status:
        query = query.filter(SurveillanceSessionRecord.status == status.lower())
    if camera_id:
        query = query.filter(SurveillanceSessionRecord.camera_id == camera_id)

    total = query.count()
    offset = max(0, (page - 1) * page_size)
    items = query.order_by(SurveillanceSessionRecord.started_at.desc()).offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": s.id,
                "mode": s.mode,
                "camera_id": s.camera_id,
                "source_reference": s.source_reference,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "status": s.status,
                "metadata_json": s.metadata_json or {}
            }
            for s in items
        ]
    }


@router.get("/sessions/{id}")
def get_session(id: str, db: DBSession = Depends(get_db)):
    """
    Retrieves surveillance session details by ID.
    """
    sess = central_results_service.get_surveillance_session(id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Surveillance session {id} not found")
    return sess


@router.post("/results/sync/backfill")
def trigger_backfill(db: DBSession = Depends(get_db)):
    """
    Synchronizes and backfills all historical analysis jobs into the centralized database.
    """
    synced_count = central_results_service.backfill_all_historical_jobs()
    return {
        "success": True,
        "synced_count": synced_count,
        "message": f"Successfully backfilled {synced_count} historical analysis jobs into centralized results database."
    }
