import json
import base64
import time
import io
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.frame_processor import frame_processor
from backend.app.services.inference_service import inference_service
from backend.app.core.logging import logger

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        logger.info(f"WebSocket client connected for identifier: {client_id}")

    def disconnect(self, client_id: str, websocket: WebSocket):
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"WebSocket client disconnected for identifier: {client_id}")

    async def broadcast(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            msg_str = json.dumps(message)
            for connection in list(self.active_connections[client_id]):
                try:
                    await connection.send_text(msg_str)
                except Exception:
                    self.disconnect(client_id, connection)

    def get_total_clients(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

manager = ConnectionManager()

@router.websocket("/ws/v1/detection/{drone_id}")
async def websocket_detection_endpoint(websocket: WebSocket, drone_id: str):
    from backend.app.services.camera_service import camera_service
    # If target ID is an active camera or camera identifier, delegate to camera stream
    if drone_id in camera_service.active_streams or drone_id.lower().startswith("cam") or drone_id.lower().startswith("camera"):
        await websocket_camera_stream_endpoint(websocket, drone_id)
        return

    await manager.connect(drone_id, websocket)
    frame_counter = 0

    try:
        while True:
            data = await websocket.receive()
            frame_counter += 1
            conf_thresh = None

            image_bytes = None
            if "bytes" in data and data["bytes"]:
                image_bytes = data["bytes"]
            elif "text" in data and data["text"]:
                try:
                    payload = json.loads(data["text"])
                    if payload.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
                        continue

                    b64_str = payload.get("image") or payload.get("image_base64")
                    conf_thresh = payload.get("confidence_threshold") or payload.get("conf_thresh")
                    if b64_str:
                        if "," in b64_str:
                            b64_str = b64_str.split(",")[1]
                        image_bytes = base64.b64decode(b64_str)
                except Exception as e:
                    logger.error(f"Error parsing incoming frame JSON: {e}")

            if image_bytes:
                img_arr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
                if img_arr is None:
                    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                    img_arr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                h, w = img_arr.shape[:2]

                # Run through central FrameProcessor (PRD Section 7, 8, 10, 11, 12, 13, 18)
                proc_result = frame_processor.process_frame(
                    frame=img_arr,
                    frame_id=frame_counter,
                    camera_id=drone_id,
                    conf_thresh=conf_thresh
                )

                # Unified detection response payload
                response = {
                    "type": "detection",
                    "drone_id": drone_id,
                    "camera_id": drone_id,
                    "frame_id": frame_counter,
                    "timestamp": proc_result.get("timestamp", time.time()),
                    "inference_time_ms": proc_result.get("inference_ms", 0.0),
                    "inference_ms": proc_result.get("inference_ms", 0.0),
                    "width": w,
                    "height": h,
                    "detections": proc_result.get("detections", []),
                    "total_objects": proc_result.get("total_objects", len(proc_result.get("detections", []))),
                    "counts": proc_result.get("counts", {}),
                    "session_totals": proc_result.get("session_totals", {}),
                    "summary": {
                        "nav_count": proc_result.get("counts", {}).get("navigation", 0),
                        "fod_count": proc_result.get("counts", {}).get("fod", 0),
                        "light_on_count": proc_result.get("counts", {}).get("light_on", 0),
                        "light_off_count": proc_result.get("counts", {}).get("light_off", 0),
                        "confirmed_faults": proc_result.get("counts", {}).get("confirmed_faults", 0),
                        "total_detections": proc_result.get("total_objects", 0)
                    },
                    "performance": proc_result.get("performance", {}),
                    "average_confidence": proc_result.get("average_confidence", 0.0),
                    "alerts": proc_result.get("alerts", [])
                }

                await websocket.send_text(json.dumps(response))

    except WebSocketDisconnect:
        manager.disconnect(drone_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for drone {drone_id}: {e}")
        manager.disconnect(drone_id, websocket)

@router.websocket("/ws/v1/session/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for subscribers of video file analysis sessions (PRD Section 18)
    """
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            if req.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception:
        manager.disconnect(session_id, websocket)

@router.websocket("/ws/v1/telemetry/{drone_id}")
async def websocket_telemetry_endpoint(websocket: WebSocket, drone_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            if req.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "telemetry",
                    "drone_id": drone_id,
                    "latitude": 12.9012,
                    "longitude": 80.2273,
                    "altitude": 120.0,
                    "speed": 32.0,
                    "heading": 184.0,
                    "battery": 87.0,
                    "status": "ACTIVE"
                }))
    except WebSocketDisconnect:
        pass

@router.websocket("/ws/v1/detection/{camera_id}")
@router.websocket("/ws/v1/camera/{camera_id}/stream")
@router.websocket("/api/v1/camera/{camera_id}/stream")
async def websocket_camera_stream_endpoint(websocket: WebSocket, camera_id: str):
    import asyncio
    from backend.app.services.camera_service import camera_service

    await websocket.accept()
    logger.info(f"[WEBSOCKET] Client connected for live detection stream: {camera_id}")
    try:
        while True:
            info = camera_service.get_camera_status(camera_id)
            if not info or camera_id not in camera_service.active_streams:
                await websocket.send_text(json.dumps({
                    "type": "camera_frame",
                    "frame_id": 0,
                    "timestamp": time.time(),
                    "camera_id": camera_id,
                    "status": "DISCONNECTED",
                    "width": 1920,
                    "height": 1080,
                    "fps": 0.0,
                    "camera_fps": 0.0,
                    "inference_fps": 0.0,
                    "latency_ms": 0.0,
                    "brightness": None,
                    "sharpness": None,
                    "warnings": [],
                    "total_detections": 0,
                    "detections": [],
                    "counts": {"navigation": 0, "fod": 0, "light_on": 0, "light_off": 0, "confirmed_faults": 0},
                    "session_totals": {"navigation": 0, "fod": 0, "light_on": 0, "light_off": 0, "confirmed_faults": 0},
                    "message": f"Camera {camera_id} is disconnected"
                }))
                await asyncio.sleep(1.0)
                continue

            stream = camera_service.active_streams.get(camera_id)
            # Default to annotated frame if available for HUD visual confirmation (PRD Section 27)
            frame_bytes = stream.get_latest_jpeg(annotated=True) or (stream.get_latest_jpeg(annotated=False) if stream else None)

            counts = info.get("counts", {"navigation": 0, "fod": 0, "light_on": 0, "light_off": 0, "confirmed_faults": 0})
            session_totals = info.get("session_totals", counts)

            payload = {
                "type": "camera_frame",
                "frame_id": info.get("frame_id", 0),
                "timestamp": time.time(),
                "camera_id": camera_id,
                "status": info["status"],
                "width": info.get("width", 1920),
                "height": info.get("height", 1080),
                "fps": info.get("inference_fps") or info.get("fps", 0.0),
                "stream_fps": info.get("camera_fps", 30.0),
                "camera_fps": info.get("camera_fps", 0.0),
                "inference_fps": info.get("inference_fps", 0.0),
                "latency_ms": info.get("latency_ms", 0.0),
                "inference_ms": info.get("latency_ms", 0.0),
                "brightness": info.get("brightness"),
                "sharpness": info.get("sharpness"),
                "warnings": info.get("warnings", []),
                "total_detections": info.get("total_detections", 0),
                "detections": info.get("detections", []),
                "alerts": info.get("alerts", []),
                "counts": counts,
                "session_totals": session_totals,
                "average_confidence": info.get("average_confidence", 0.0),
                "summary": info.get("summary", {
                    "nav_count": counts.get("navigation", 0),
                    "fod_count": counts.get("fod", 0),
                    "light_on_count": counts.get("light_on", 0),
                    "light_off_count": counts.get("light_off", 0),
                    "confirmed_faults": counts.get("confirmed_faults", 0)
                }),
                "performance": {
                    "stream_fps": info.get("camera_fps", 30.0),
                    "inference_fps": info.get("inference_fps", 0.0),
                    "inference_ms": info.get("latency_ms", 0.0)
                },
                "model": info.get("model", "navigation_best.pt + FOD_Karhtikeyan.pt + runway_light_best.pt"),
                "error": info.get("error")
            }

            if frame_bytes:
                payload["image_base64"] = "data:image/jpeg;base64," + base64.b64encode(frame_bytes).decode("utf-8")

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.04)  # ~25 FPS transmission
    except WebSocketDisconnect:
        logger.info(f"[WEBSOCKET] Client disconnected from detection stream {camera_id}")
    except Exception as e:
        logger.error(f"[WEBSOCKET] Error in detection WS stream {camera_id}: {e}")
