import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.core.logging import logger
from backend.app.services.analysis_service import analysis_service

router = APIRouter(tags=["Analysis WebSocket"])


class AnalysisConnectionManager:
    """Manages WebSocket connections for analysis jobs."""
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"[ANALYSIS_WS] Client connected to job {job_id}")

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"[ANALYSIS_WS] Client disconnected from job {job_id}")

    async def broadcast(self, job_id: str, message: dict):
        if job_id not in self.active_connections:
            return
        payload = json.dumps(message)
        dead_conns = []
        for ws in list(self.active_connections[job_id]):
            try:
                await ws.send_text(payload)
            except Exception:
                dead_conns.append(ws)
        for dead in dead_conns:
            self.disconnect(job_id, dead)


manager = AnalysisConnectionManager()
# Link manager with analysis_service
analysis_service.set_ws_manager(manager)


@router.websocket("/ws/v1/analysis/{job_id}")
async def analysis_websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    Real-time progress WebSocket for analysis job (PRD Section 39).
    Emits continuous updates: status, processed_frames, total_frames, progress, processing_fps,
    elapsed_seconds, remaining_seconds, estimated_finish_time.
    """
    await manager.connect(job_id, websocket)

    # Send initial status
    try:
        initial_status = analysis_service.get_job_status(job_id)
        await websocket.send_text(json.dumps({
            "type": "analysis_progress",
            **initial_status,
        }))
    except Exception as e:
        logger.debug(f"[ANALYSIS_WS] Could not send initial status for job {job_id}: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
    except Exception as e:
        logger.error(f"[ANALYSIS_WS] Error in socket for job {job_id}: {e}")
        manager.disconnect(job_id, websocket)
