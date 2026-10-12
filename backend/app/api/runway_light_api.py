import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.services.analysis_service import analysis_service
from backend.app.schemas.analysis import (
    AnalysisJobCreateResponse,
    AnalysisJobStatusResponse,
    AnalysisJobResultsResponse,
    RunwayLightSummaryResponse,
)

router = APIRouter(prefix="/runway-light", tags=["Runway Light Fault Analysis Engine"])


@router.post("/upload", response_model=AnalysisJobCreateResponse)
async def upload_runway_light_media(file: UploadFile = File(...)):
    """Uploads video or image for Runway Light Fault analysis (runway_light_best.pt ONLY)."""
    ext = Path(file.filename or "").suffix.lower()
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty media file")

    if ext in video_exts:
        return analysis_service.create_video_job(
            filename=file.filename or "runway_light_video.mp4",
            file_bytes=file_bytes,
            analysis_type="RUNWAY_LIGHT",
        )
    elif ext in image_exts:
        return analysis_service.create_image_job(
            filename=file.filename or "runway_light_image.jpg",
            file_bytes=file_bytes,
            analysis_type="RUNWAY_LIGHT",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(video_exts | image_exts)}"
        )


@router.post("/{job_id}/start")
def start_runway_light_analysis(job_id: str):
    """Starts Runway Light model analysis."""
    try:
        return analysis_service.start_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {e}")


@router.post("/{job_id}/pause")
def pause_runway_light_analysis(job_id: str):
    """Pauses active Runway Light analysis."""
    try:
        return analysis_service.pause_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/resume")
def resume_runway_light_analysis(job_id: str):
    """Resumes paused Runway Light analysis."""
    try:
        return analysis_service.resume_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/cancel")
def cancel_runway_light_analysis(job_id: str):
    """Cancels Runway Light analysis."""
    try:
        return analysis_service.cancel_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history")
def get_runway_light_history(limit: int = Query(50)):
    """Returns Runway Light analysis job history."""
    return analysis_service.list_jobs(limit=limit, analysis_type="RUNWAY_LIGHT")


@router.get("/{job_id}", response_model=AnalysisJobStatusResponse)
def get_runway_light_status(job_id: str):
    """Returns Runway Light analysis live status."""
    try:
        return analysis_service.get_job_status(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}/results", response_model=AnalysisJobResultsResponse)
def get_runway_light_results(job_id: str):
    """Returns Runway Light analysis final results including row-by-row table and grid matrix."""
    try:
        return analysis_service.get_job_results(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}/summary", response_model=RunwayLightSummaryResponse)
def get_runway_light_summary(job_id: str):
    """Returns dedicated Runway Light summary including visual matrix grid, ON/OFF counts, and faults."""
    try:
        return analysis_service.get_runway_summary(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch runway summary: {e}")


@router.get("/{job_id}/video")
def get_runway_light_video(job_id: str):
    """Returns annotated Runway Light video."""
    results = analysis_service.get_job_results(job_id)
    path = results.get("annotated_media_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Analyzed video not found")
    return FileResponse(path, media_type="video/mp4", filename=Path(path).name)
