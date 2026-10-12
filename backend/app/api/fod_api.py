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
)

router = APIRouter(prefix="/fod", tags=["FOD Debris Analysis Engine"])


@router.post("/upload", response_model=AnalysisJobCreateResponse)
async def upload_fod_media(file: UploadFile = File(...)):
    """Uploads video or image for FOD Debris analysis (FOD_Karhtikeyan.pt ONLY)."""
    ext = Path(file.filename or "").suffix.lower()
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty media file")

    if ext in video_exts:
        return analysis_service.create_video_job(
            filename=file.filename or "fod_video.mp4",
            file_bytes=file_bytes,
            analysis_type="FOD",
        )
    elif ext in image_exts:
        return analysis_service.create_image_job(
            filename=file.filename or "fod_image.jpg",
            file_bytes=file_bytes,
            analysis_type="FOD",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(video_exts | image_exts)}"
        )


@router.post("/{job_id}/start")
def start_fod_analysis(job_id: str):
    """Starts FOD model analysis."""
    try:
        return analysis_service.start_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {e}")


@router.post("/{job_id}/pause")
def pause_fod_analysis(job_id: str):
    """Pauses active FOD analysis."""
    try:
        return analysis_service.pause_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/resume")
def resume_fod_analysis(job_id: str):
    """Resumes paused FOD analysis."""
    try:
        return analysis_service.resume_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/cancel")
def cancel_fod_analysis(job_id: str):
    """Cancels FOD analysis."""
    try:
        return analysis_service.cancel_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history")
def get_fod_history(limit: int = Query(50)):
    """Returns FOD analysis job history."""
    return analysis_service.list_jobs(limit=limit, analysis_type="FOD")


@router.get("/{job_id}", response_model=AnalysisJobStatusResponse)
def get_fod_status(job_id: str):
    """Returns FOD analysis live status."""
    try:
        return analysis_service.get_job_status(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}/results", response_model=AnalysisJobResultsResponse)
def get_fod_results(job_id: str):
    """Returns FOD analysis final results."""
    try:
        return analysis_service.get_job_results(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}/video")
def get_fod_video(job_id: str):
    """Returns annotated FOD video."""
    results = analysis_service.get_job_results(job_id)
    path = results.get("annotated_media_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Analyzed video not found")
    return FileResponse(path, media_type="video/mp4", filename=Path(path).name)
