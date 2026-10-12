import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Camera
from backend.app.schemas.camera import (
    CameraConnectRequest,
    CameraConnectResponse,
    CameraStatusResponse,
    CameraDisconnectResponse,
    CameraListItem,
)
from backend.app.services.camera_service import camera_service

router = APIRouter()

@router.post("/connect", response_model=CameraConnectResponse)
def connect_camera(request: CameraConnectRequest, db: Session = Depends(get_db)):
    # Phase 1: Input Validation
    is_valid, stream_url, val_err = camera_service.validate_input(
        stream_url=request.stream_url,
        rtsp_url=request.rtsp_url,
        ip=request.ip,
        port=request.port or 554,
        protocol=request.protocol or "RTSP",
        path=request.path or "/stream",
        username=request.username,
        password=request.password,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=val_err or "Invalid camera IP address or RTSP/stream URL."
        )

    camera_id = request.camera_id or f"camera_{uuid.uuid4().hex[:6]}"
    is_simulated = request.is_simulated or stream_url.startswith("demo://")

    # Phase 2: Network Reachability Test (skip for demo/simulated feeds)
    if not is_simulated:
        reachable, reach_msg = camera_service.check_reachability(stream_url)
        if not reachable:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=reach_msg
            )

    # Phase 3: Connect Stream
    stream = camera_service.connect_camera(
        camera_id=camera_id,
        stream_url=stream_url,
        camera_name=request.camera_name or "IP Camera 01",
        is_simulated=is_simulated
    )

    return {
        "success": True,
        "camera_id": camera_id,
        "status": stream.status,
        "message": f"Connected to camera stream: {stream_url}",
        "stream_url": stream_url,
        "fps": stream.fps,
        "latency_ms": stream.latency_ms,
    }

@router.get("/{camera_id}/status", response_model=CameraStatusResponse)
def get_camera_status(camera_id: str):
    info = camera_service.get_camera_status(camera_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return info

@router.post("/{camera_id}/disconnect", response_model=CameraDisconnectResponse)
def disconnect_camera(camera_id: str):
    success = camera_service.disconnect_camera(camera_id)
    return {
        "success": success,
        "camera_id": camera_id,
        "status": "DISCONNECTED",
        "message": "Camera disconnected successfully" if success else "Camera was not active",
    }

@router.get("/{camera_id}/feed")
def get_camera_feed(camera_id: str, annotated: bool = False):
    """Native MJPEG video stream accessible directly by web browser <img> or <video>"""
    return StreamingResponse(
        camera_service.mjpeg_generator(camera_id, annotated=annotated),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/list", response_model=List[CameraListItem])
def list_cameras(db: Session = Depends(get_db)):
    cameras = db.query(Camera).all()
    # Update statuses from active memory if currently running
    result = []
    for cam in cameras:
        active = camera_service.get_camera_status(cam.camera_id)
        current_status = active["status"] if active else cam.status
        result.append({
            "camera_id": cam.camera_id,
            "camera_name": cam.camera_name,
            "ip_address": cam.ip_address,
            "port": cam.port or 554,
            "protocol": cam.protocol or "RTSP",
            "stream_url": cam.stream_url,
            "status": current_status,
            "created_at": cam.created_at,
        })
    return result
