import os
import uuid
from typing import Optional, Dict, Any, List
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from backend.app.services.camera_service import camera_service
from backend.app.services.analysis_service import analysis_service
from backend.app.api.analysis import send_media_with_range_support

router = APIRouter(prefix="/surveillance", tags=["Surveillance Engine"])


class LiveSurveillanceStartRequest(BaseModel):
    stream_url: Optional[str] = None
    rtsp_url: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = "RTSP"
    camera_id: Optional[str] = None
    camera_name: Optional[str] = "Surveillance Camera"
    model_type: Optional[str] = "NAVIGATION"
    model: Optional[str] = None
    is_simulated: Optional[bool] = False


class LiveSurveillanceStopRequest(BaseModel):
    session_id: Optional[str] = None
    camera_id: Optional[str] = None


@router.post("/live/start")
def start_live_surveillance(req: LiveSurveillanceStartRequest):
    """
    Connects to a live RTSP / IP camera feed and initiates real-time surveillance.
    Validates network reachability before connecting.
    """
    target_url = req.stream_url or req.rtsp_url or req.source_url
    if not target_url:
        raise HTTPException(status_code=400, detail="Missing required stream_url or rtsp_url")

    selected_model = req.model or req.model_type or "NAVIGATION"
    cam_id = req.camera_id or f"cam_{uuid.uuid4().hex[:6]}"
    is_sim = req.is_simulated or target_url.startswith("demo://") or target_url in ("0", "webcam") or (req.source_type and req.source_type.upper() == "WEBCAM")
    if is_sim and not target_url.startswith("demo://"):
        target_url = "demo://webcam"

    if not is_sim:
        reachable, reach_err = camera_service.check_reachability(target_url)
        if not reachable:
            raise HTTPException(status_code=504, detail=reach_err or f"Stream unreachable: {target_url}")

    stream = camera_service.connect_camera(
        camera_id=cam_id,
        stream_url=target_url,
        camera_name=req.camera_name or "Live Surveillance",
        is_simulated=is_sim
    )

    try:
        from datetime import datetime, timezone
        from backend.app.services.central_results_service import central_results_service
        from backend.app.schemas.results import SurveillanceSessionCreate, AnalysisResultCreate
        central_results_service.create_surveillance_session(SurveillanceSessionCreate(
            id=cam_id,
            mode="live",
            camera_id=cam_id,
            source_reference=target_url,
            status="active",
            metadata_json={"model_type": selected_model, "is_simulated": is_sim}
        ))
        live_res_id = f"live_{cam_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        central_results_service.create_result(AnalysisResultCreate(
            id=live_res_id,
            module_type="live_surveillance",
            session_id=cam_id,
            title=f"Live Surveillance: {req.camera_name or cam_id}",
            status="processing",
            summary=f"Active real-time surveillance feed via {selected_model} model.",
            media_reference=target_url,
            result_data={"camera_id": cam_id, "model_type": selected_model, "is_simulated": is_sim}
        ))
    except Exception as e:
        pass

    return {
        "success": True,
        "session_id": cam_id,
        "camera_id": cam_id,
        "status": stream.status,
        "model_type": selected_model,
        "stream_url": target_url,
        "fps": stream.fps,
        "message": f"Connected to live surveillance stream: {target_url}"
    }


@router.post("/live/stop")
def stop_live_surveillance(req: LiveSurveillanceStopRequest):
    """
    Stops live surveillance and releases stream resources.
    """
    target_id = req.session_id or req.camera_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Missing session_id or camera_id")

    success = camera_service.disconnect_camera(target_id)
    try:
        from backend.app.db.database import SessionLocal
        from backend.app.db.models import AnalysisResult, SurveillanceSessionRecord, get_utc_now
        with SessionLocal() as db:
            sess = db.query(SurveillanceSessionRecord).filter(SurveillanceSessionRecord.id == target_id).first()
            if sess:
                sess.status = "completed"
                sess.ended_at = get_utc_now()
            results = db.query(AnalysisResult).filter(
                AnalysisResult.session_id == target_id,
                AnalysisResult.status == "processing"
            ).all()
            for r in results:
                r.status = "completed"
                r.completed_at = get_utc_now()
                r.summary = f"Live surveillance session {target_id} ended."
            db.commit()
    except Exception:
        pass

    return {
        "success": success,
        "session_id": target_id,
        "status": "DISCONNECTED",
        "message": "Live surveillance stopped successfully"
    }


@router.post("/live/{session_id}/stop")
def stop_live_surveillance_by_id(session_id: str):
    """
    Stops live surveillance by path session_id.
    """
    return stop_live_surveillance(LiveSurveillanceStopRequest(session_id=session_id))


@router.get("/live/{session_id}/status")
def get_live_surveillance_status(session_id: str):
    """
    Retrieves real-time status, FPS, and detection summary for live surveillance stream.
    """
    info = camera_service.get_camera_status(session_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Surveillance session {session_id} not active or not found")
    info["session_id"] = session_id
    return info


@router.get("/live/{session_id}/feed")
def get_live_surveillance_feed(session_id: str, annotated: bool = True):
    """
    Native MJPEG video stream accessible directly by web browser <img> or player.
    Provides live real-time YOLO detections overlay when annotated=True.
    """
    if session_id not in camera_service.active_streams:
        raise HTTPException(status_code=404, detail=f"Live surveillance stream {session_id} is not active")

    return StreamingResponse(
        camera_service.mjpeg_generator(session_id, annotated=annotated),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/live/sessions")
def list_live_surveillance_sessions():
    """
    Lists all currently active live surveillance sessions.
    """
    sessions = []
    for sid, stream in camera_service.active_streams.items():
        sessions.append({
            "session_id": sid,
            "camera_name": stream.camera_name,
            "status": stream.status,
            "stream_url": stream.stream_url,
            "fps": stream.fps,
            "inference_fps": stream.inference_fps,
            "total_detections": stream.total_detections,
        })
    return sessions


@router.post("/offline/upload")
async def upload_offline_media(
    file: UploadFile = File(...),
    analysis_type: str = Form("NAVIGATION"),
):
    """
    Uploads a video or image for offline surveillance analysis.
    """
    ext = Path(file.filename or "").suffix.lower()
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    safe_name = file.filename or "uploaded_media"
    atype = (analysis_type or "NAVIGATION").upper()

    if ext in video_exts:
        return analysis_service.create_video_job(
            filename=safe_name,
            file_bytes=file_bytes,
            analysis_type=atype
        )
    elif ext in image_exts:
        return analysis_service.create_image_job(
            filename=safe_name,
            file_bytes=file_bytes,
            analysis_type=atype
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed videos: {', '.join(video_exts)}, images: {', '.join(image_exts)}"
        )


@router.post("/offline/{job_id}/start")
def start_offline_analysis(job_id: str):
    """
    Begins model inference on the uploaded offline media file.
    """
    try:
        return analysis_service.start_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start offline analysis: {e}")


@router.post("/offline/{job_id}/pause")
def pause_offline_analysis(job_id: str):
    """Pauses active offline surveillance analysis."""
    try:
        return analysis_service.pause_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/offline/{job_id}/resume")
def resume_offline_analysis(job_id: str):
    """Resumes paused offline surveillance analysis."""
    try:
        return analysis_service.resume_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/offline/{job_id}/cancel")
def cancel_offline_analysis(job_id: str):
    """Cancels offline surveillance analysis."""
    try:
        return analysis_service.cancel_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/offline/{job_id}/status")
def get_offline_analysis_status(job_id: str):
    """
    Returns progress, processing FPS, and dynamic ETA for offline surveillance job.
    """
    try:
        return analysis_service.get_job_status(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/offline/{job_id}/results")
def get_offline_analysis_results(job_id: str):
    """
    Returns completed offline analysis results, real counts, and detections.
    """
    try:
        return analysis_service.get_job_results(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/offline/{job_id}/video")
def get_offline_analyzed_video(job_id: str, request: Request):
    """
    Streams browser-playable annotated video with HTTP 206 Partial Content byte ranges.
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
    }
    media_type = media_map.get(ext, "application/octet-stream")
    return send_media_with_range_support(request, path, media_type, Path(path).name)


@router.get("/offline/{job_id}/original")
def get_offline_original_media(job_id: str, request: Request):
    """
    Streams original uploaded media file with HTTP 206 Partial Content byte ranges.
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
    }
    media_type = media_map.get(ext, "application/octet-stream")
    return send_media_with_range_support(request, path, media_type, Path(path).name)


@router.get("/offline/{job_id}/report")
def get_offline_report(job_id: str, format: str = "csv"):
    """
    Downloads CSV or JSON summary audit report for offline surveillance job.
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


@router.get("/offline/jobs")
def list_offline_jobs(limit: int = 50, analysis_type: Optional[str] = None):
    """
    Lists recent offline surveillance jobs.
    """
    return analysis_service.list_jobs(limit=limit, analysis_type=analysis_type)
