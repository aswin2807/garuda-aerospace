import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from backend.app.schemas.video import VideoStartRequest, VideoStartResponse, VideoStopResponse
from backend.app.services.video_service import video_service
from backend.app.core.logging import logger

router = APIRouter(prefix="/video", tags=["Video Analysis"])

@router.post("/start", response_model=VideoStartResponse)
def start_video_analysis(req: VideoStartRequest):
    """
    Starts sequential frame-by-frame video file inference per PRD Section 6 & 30
    """
    try:
        res = video_service.start_session(
            source_path=req.source,
            loop=req.loop,
            session_id=req.session_id
        )
        return res
    except Exception as e:
        logger.error(f"Error starting video analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/stop", response_model=VideoStopResponse)
def stop_video_analysis(session_id: str):
    """
    Stops video analysis session and returns final summary statistics (PRD Section 41, 42)
    """
    try:
        res = video_service.stop_session(session_id)
        return res
    except Exception as e:
        logger.error(f"Error stopping video session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/status")
def get_video_session_status(session_id: str):
    """
    Returns live progress and latest detections for an active video session
    """
    res = video_service.get_session_status(session_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return res

@router.post("/upload")
async def upload_video_file(file: UploadFile = File(...)):
    """
    Uploads a video file (.mp4, .mov, .avi) to data/videos/ for server-side processing
    """
    os.makedirs("data/videos", exist_ok=True)
    file_path = os.path.join("data/videos", file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "success": True,
            "filename": file.filename,
            "path": file_path,
            "message": f"Saved video to {file_path}"
        }
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")
