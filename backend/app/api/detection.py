import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.detection import ImageDetectionResponse, VideoDetectionResponse, DetectionHistoryItem
from backend.app.services.inference_service import inference_service
from backend.app.services.detection_service import detection_service
from backend.app.core.logging import log_detection_event

router = APIRouter()

@router.post("/image", response_model=ImageDetectionResponse)
async def detect_image(
    file: UploadFile = File(...),
    drone_id: Optional[str] = Form(None),
    mission_id: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image format (JPEG/PNG)")
    
    contents = await file.read()
    detections, elapsed_ms, width, height = inference_service.predict_image(contents, conf_thresh=confidence)
    
    # Save results to database
    detection_service.save_detections(
        db=db,
        detections=detections,
        drone_id=drone_id,
        mission_id=mission_id,
        image_url=file.filename
    )

    log_detection_event(
        drone_id=drone_id or "DR-01",
        frame_id=file.filename or "frame_img",
        inference_ms=elapsed_ms,
        detections_count=len(detections),
        mission_id=mission_id
    )

    return {
        "success": True,
        "processing_time_ms": elapsed_ms,
        "detections": detections
    }

@router.post("/video", response_model=VideoDetectionResponse)
async def detect_video(
    file: UploadFile = File(...),
    drone_id: Optional[str] = Form(None),
    mission_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video format (MP4/AVI)")

    task_id = str(uuid.uuid4())
    # Asynchronous video processing stub
    return {
        "success": True,
        "task_id": task_id,
        "status": "PROCESSING",
        "message": f"Video {file.filename} queued for frame-by-frame YOLOv11 inference"
    }

@router.get("/history", response_model=List[DetectionHistoryItem])
def get_detection_history(
    drone_id: Optional[str] = None,
    mission_id: Optional[str] = None,
    class_name: Optional[str] = None,
    min_confidence: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    history = detection_service.get_history(
        db=db,
        drone_id=drone_id,
        mission_id=mission_id,
        class_name=class_name,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset
    )
    return history
