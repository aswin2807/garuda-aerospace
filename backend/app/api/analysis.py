import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from backend.app.services.analysis_service import analysis_service
from backend.app.schemas.analysis import (
    AnalysisJobCreateResponse,
    AnalysisJobStatusResponse,
    AnalysisJobResultsResponse,
    ImageAnalysisResponse,
)

router = APIRouter(prefix="/analysis", tags=["Media Analysis Engine"])


@router.post("/upload", response_model=AnalysisJobCreateResponse)
async def upload_media(
    file: UploadFile = File(...),
    analysis_type: str = Form("NAVIGATION"),
):
    """
    Universal media upload endpoint (PRD Section 6, 7, 38).
    Accepts video or image and creates a queued analysis job.
    """
    ext = Path(file.filename or "").suffix.lower()
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    if ext in video_exts:
        return await upload_video(file, analysis_type=analysis_type)
    elif ext in image_exts:
        return await upload_image(file, analysis_type=analysis_type)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported media format '{ext}'. Allowed videos: {', '.join(video_exts)}, images: {', '.join(image_exts)}"
        )


@router.post("/videos", response_model=AnalysisJobCreateResponse)
async def upload_video(
    file: UploadFile = File(...),
    analysis_type: str = Form("NAVIGATION"),
):
    """
    Uploads a video for AI analysis (PRD Section 6, 7, 38).
    Creates an analysis job with video PAUSED on upload.
    User must call POST /analysis/{job_id}/start to begin processing.
    """
    allowed_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{ext}'. Allowed: {', '.join(allowed_exts)}"
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty video file")

    res = analysis_service.create_video_job(
        filename=file.filename or "uploaded_video.mp4",
        file_bytes=file_bytes,
        analysis_type=analysis_type,
    )
    return res


@router.post("/images", response_model=AnalysisJobCreateResponse)
async def upload_image(
    file: UploadFile = File(...),
    analysis_type: str = Form("NAVIGATION"),
):
    """
    Uploads an image for AI analysis (PRD Section 5, 34, 38).
    Supports .jpg, .jpeg, .png, .webp, .bmp.
    """
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format '{ext}'. Allowed: {', '.join(allowed_exts)}"
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty image file")

    res = analysis_service.create_image_job(
        filename=file.filename or "uploaded_image.jpg",
        file_bytes=file_bytes,
        analysis_type=analysis_type,
    )
    return res


@router.post("/{job_id}/start")
def start_analysis(job_id: str):
    """
    Starts offline AI analysis on the uploaded video or image (PRD Section 8, 38).
    Processes every frame sequentially with real YOLO models in background.
    """
    try:
        return analysis_service.start_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {e}")


@router.post("/{job_id}/pause")
def pause_analysis(job_id: str):
    """
    Pauses active video analysis process (PRD Section 13, 38).
    """
    try:
        return analysis_service.pause_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/resume")
def resume_analysis(job_id: str):
    """
    Resumes paused video analysis process (PRD Section 13, 38).
    """
    try:
        return analysis_service.resume_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/cancel")
def cancel_analysis(job_id: str):
    """
    Cancels video analysis process cleanly (PRD Section 14, 38).
    """
    try:
        return analysis_service.cancel_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}", response_model=AnalysisJobStatusResponse)
def get_analysis_status(job_id: str):
    """
    Returns live progress, processing FPS, and dynamic ETA (PRD Section 9, 10, 12, 38).
    """
    try:
        return analysis_service.get_job_status(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}/results", response_model=AnalysisJobResultsResponse)
def get_analysis_results(job_id: str):
    """
    Returns complete post-analysis results, real counts, unique tracked objects,
    and confirmed runway faults (PRD Section 29, 31, 32, 38).
    """
    try:
        return analysis_service.get_job_results(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


import re
from fastapi import Request, Response
from fastapi.responses import FileResponse, StreamingResponse

def send_media_with_range_support(request: Request, path: str, media_type: str, filename: str):
    file_size = os.path.getsize(path)
    range_header = request.headers.get("range")
    if not range_header or not media_type.startswith("video/"):
        return FileResponse(path, media_type=media_type, filename=filename, headers={"Accept-Ranges": "bytes"})

    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        return FileResponse(path, media_type=media_type, filename=filename, headers={"Accept-Ranges": "bytes"})

    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    chunk_size = end - start + 1

    def file_iterator():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                chunk = f.read(min(remaining, 1024 * 512))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": media_type,
    }
    return StreamingResponse(file_iterator(), status_code=206, headers=headers)


@router.get("/{job_id}/video")
def get_analyzed_video(job_id: str, request: Request):
    """
    Streams or downloads the analyzed video/image with overlaid YOLO detection boxes (PRD Section 33, 38).
    Supports HTTP 206 Partial Content byte ranges for smooth browser playback.
    """
    results = analysis_service.get_job_results(job_id)
    path = results.get("annotated_media_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Analyzed media not yet generated or not found")

    ext = Path(path).suffix.lower()
    media_map = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = media_map.get(ext, "application/octet-stream")
    return send_media_with_range_support(request, path, media_type, Path(path).name)


@router.get("/{job_id}/original")
def get_original_media(job_id: str, request: Request):
    """
    Returns original uploaded media file if retained (PRD Section 5).
    Supports HTTP 206 Partial Content byte ranges for smooth browser playback.
    """
    results = analysis_service.get_job_results(job_id)
    path = results.get("file_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Original media not retained or not found")

    ext = Path(path).suffix.lower()
    media_map = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = media_map.get(ext, "application/octet-stream")
    return send_media_with_range_support(request, path, media_type, Path(path).name)


@router.get("/{job_id}/report")
def get_analysis_report(job_id: str, format: str = "csv"):
    """
    Downloads CSV detection records or JSON summary report (PRD Section 38).
    """
    results = analysis_service.get_job_results(job_id)
    if format.lower() == "csv":
        path = results.get("report_csv_path")
        media = "text/csv"
    else:
        path = results.get("report_json_path")
        media = "application/json"

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Report file ({format}) not found")
    return FileResponse(path, media_type=media, filename=Path(path).name)


@router.get("/jobs/all")
def list_analysis_jobs(
    limit: int = 50,
    analysis_type: Optional[str] = None,
):
    """
    Lists recent analysis jobs (PRD Section 36), optionally filtered by analysis_type.
    """
    return analysis_service.list_jobs(limit=limit, analysis_type=analysis_type)
