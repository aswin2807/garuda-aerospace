from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

from backend.app.services.database_service import database_service
from backend.app.services.frame_processor import frame_processor
from backend.app.services.export_service import export_service
from backend.app.schemas.session import SessionStatsResponse, SessionDetectionsResponse

router = APIRouter(prefix="/session", tags=["Analysis Sessions"])

@router.get("/{session_id}")
def get_session_details(session_id: str):
    """
    Retrieves session metadata per PRD Section 30
    """
    res = database_service.get_session(session_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return res

@router.get("/{session_id}/detections")
def get_session_detections(session_id: str, limit: int = Query(default=100, ge=1, le=1000)):
    """
    Retrieves recorded detections for session per PRD Section 30
    """
    dets = database_service.get_session_detections(session_id, limit=limit)
    return {
        "session_id": session_id,
        "count": len(dets),
        "detections": dets
    }

@router.get("/{session_id}/statistics", response_model=SessionStatsResponse)
def get_session_statistics(session_id: str):
    """
    Retrieves aggregated summary statistics for session per PRD Section 30 & 42
    """
    stats = database_service.get_session_statistics(session_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return stats

@router.post("/{session_id}/reset")
def reset_session(session_id: str):
    """
    Resets current session metrics, tracking IDs, and counters (PRD Section 40)
    """
    frame_processor.reset_pipeline(session_id=session_id)
    return {
        "session_id": session_id,
        "status": "RESET",
        "message": f"Session {session_id} counters and tracks reset"
    }

@router.get("/{session_id}/export")
def export_session_data(session_id: str):
    """
    Exports session detections to CSV and summary statistics to JSON (PRD Section 22).
    """
    try:
        paths = export_service.export_all(session_id)
        return {
            "session_id": session_id,
            "status": "EXPORTED",
            "files": paths
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

