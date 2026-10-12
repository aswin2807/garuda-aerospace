import os
import re
import time
import socket
import threading
import ipaddress
import urllib.parse
from typing import Dict, Optional, Tuple, Any, List
import cv2
import numpy as np

from backend.app.core.logging import logger
from backend.app.services.inference_service import inference_service
from backend.app.services.rtsp_service import LatestFrameReader
from backend.app.db.database import SessionLocal
from backend.app.db.models import Camera

from backend.app.services.frame_processor import frame_processor

class ActiveCameraStream:
    """
    Manages a single active IP/RTSP camera stream session:
    - Runs LatestFrameReader to prevent backlog and minimize latency
    - Executes YOLOv11 tri-model inference via FrameProcessor
    - Maintains latest frame buffer, FPS counters, and image quality metrics
    """
    def __init__(
        self,
        camera_id: str,
        stream_url: str,
        camera_name: str = "IP Camera 01",
        is_simulated: bool = False,
        max_retries: int = 5
    ):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.stream_url = stream_url
        self.is_simulated = is_simulated or "demo://" in stream_url.lower() or "simulated" in stream_url.lower()
        self.max_retries = max_retries

        self.status = "CONNECTING"  # CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING, ERROR
        self.error: Optional[str] = None
        self.width: int = 1920
        self.height: int = 1080
        self.fps: float = 0.0          # Reported/camera FPS
        self.camera_fps: float = 0.0
        self.inference_fps: float = 0.0
        self.latency_ms: float = 0.0
        self.total_detections: int = 0
        self.latest_detections: List[Dict[str, Any]] = []
        self.quality: Dict[str, Any] = {"brightness": 0.0, "sharpness": 0.0, "warnings": []}
        self.latest_frame_jpeg: Optional[bytes] = None
        self.latest_annotated_jpeg: Optional[bytes] = None
        self.latest_frame_id: int = 0
        self.latest_alerts: List[Dict[str, Any]] = []
        self.latest_counts: Dict[str, int] = {"navigation": 0, "fod": 0, "light_on": 0, "light_off": 0, "confirmed_faults": 0}
        self.latest_session_totals: Dict[str, int] = {"navigation": 0, "fod": 0, "light_on": 0, "light_off": 0, "confirmed_faults": 0}
        self.average_confidence: float = 0.0
        self.latest_summary: Dict[str, Any] = {"nav_count": 0, "fod_count": 0, "light_on_count": 0, "light_off_count": 0}

        self.reader: Optional[LatestFrameReader] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._retry_count = 0

    def start(self):
        self._stop_event.clear()
        self.status = "CONNECTING"
        self._thread = threading.Thread(target=self._run_inference_worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self.reader:
            self.reader.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.status = "DISCONNECTED"
        logger.info(f"[CAMERA] Stopped stream pipeline for {self.camera_id}")

    def _run_inference_worker(self):
        logger.info(f"[CAMERA] Initializing LatestFrameReader for {self.camera_id}: {self.stream_url}")
        try:
            self.reader = LatestFrameReader(self.stream_url, is_simulated=self.is_simulated).start()
            # Wait briefly for first frame
            start_wait = time.time()
            first_frame = None
            while time.time() - start_wait < 5.0 and not self._stop_event.is_set():
                ok, frame, _ = self.reader.read_latest()
                if ok and frame is not None:
                    first_frame = frame
                    break
                time.sleep(0.05)

            if first_frame is None and not self.is_simulated:
                raise RuntimeError(f"Connected to RTSP but no video frame received from {self.stream_url}")

            w, h, reported_fps = self.reader.get_properties()
            with self._lock:
                self.width = w if w > 0 else (first_frame.shape[1] if first_frame is not None else 1920)
                self.height = h if h > 0 else (first_frame.shape[0] if first_frame is not None else 1080)
                self.fps = reported_fps
                self.camera_fps = reported_fps
                self.status = "CONNECTED"
                self.error = None

            logger.info(f"[CAMERA] Connected: {self.camera_id} ({self.width}x{self.height} @ {reported_fps:.1f}fps)")
        except Exception as e:
            logger.error(f"[CAMERA] Failed to connect to stream {self.camera_id}: {e}")
            with self._lock:
                self.status = "ERROR"
                self.error = str(e)
            return

        last_frame_id = -1
        prev_inf_time = time.perf_counter()

        while not self._stop_event.is_set():
            ok, frame, frame_id = self.reader.read_latest()
            if not ok or frame is None:
                with self._lock:
                    if self.status == "CONNECTED":
                        self.status = "RECONNECTING"
                time.sleep(0.01)
                continue

            if frame_id == last_frame_id:
                time.sleep(0.002)
                continue
            last_frame_id = frame_id

            try:
                # Run complete tri-model scheduled pipeline
                res = frame_processor.process_frame(
                    frame=frame,
                    frame_id=frame_id,
                    camera_id=self.camera_id,
                    stream_fps=self.camera_fps
                )

                now = time.perf_counter()
                dt = now - prev_inf_time
                prev_inf_time = now
                calc_inf_fps = round(1.0 / dt, 1) if dt > 0 else 0.0

                # Encode clean frame
                ret, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                clean_jpeg_bytes = jpeg.tobytes() if ret else None

                # Encode annotated frame with color-coded boxes & labels per PRD Section 26
                annotated = inference_service.draw_detections(frame, res.get("detections", []))
                ret_ann, ann_jpeg = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                ann_jpeg_bytes = ann_jpeg.tobytes() if ret_ann else clean_jpeg_bytes

                counts = res.get("counts", {})
                session_totals = res.get("session_totals", {})

                with self._lock:
                    self.status = "CONNECTED"
                    self.latest_detections = res.get("detections", [])
                    self.total_detections = res.get("total_objects", len(self.latest_detections))
                    self.alerts = res.get("alerts", [])
                    self.latest_alerts = res.get("alerts", [])
                    self.latest_counts = counts
                    self.latest_session_totals = session_totals
                    self.average_confidence = res.get("average_confidence", 0.0)
                    self.latest_summary = {
                        "nav_count": counts.get("navigation", 0),
                        "fod_count": counts.get("fod", 0),
                        "light_on_count": counts.get("light_on", 0),
                        "light_off_count": counts.get("light_off", 0),
                        "confirmed_faults": counts.get("confirmed_faults", 0)
                    }
                    self.latency_ms = res.get("inference_ms", 0.0)
                    self.inference_fps = calc_inf_fps
                    self.latest_frame_id = frame_id
                    self.latest_frame_jpeg = clean_jpeg_bytes
                    self.latest_annotated_jpeg = ann_jpeg_bytes

            except Exception as e:
                logger.error(f"[INFERENCE] Error in frame worker for {self.camera_id}: {e}")

        with self._lock:
            self.status = "DISCONNECTED"

    def get_latest_data(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "camera_id": self.camera_id,
                "camera_name": self.camera_name,
                "status": self.status,
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
                "camera_fps": self.camera_fps,
                "inference_fps": self.inference_fps,
                "latency_ms": self.latency_ms,
                "brightness": self.quality.get("brightness"),
                "sharpness": self.quality.get("sharpness"),
                "warnings": self.quality.get("warnings", []),
                "total_detections": self.total_detections,
                "detections": list(self.latest_detections),
                "alerts": list(self.latest_alerts),
                "counts": dict(self.latest_counts),
                "session_totals": dict(self.latest_session_totals),
                "average_confidence": self.average_confidence,
                "summary": dict(self.latest_summary),
                "model": "navigation_best.pt + FOD_Karhtikeyan.pt + runway_light_best.pt",
                "frame_id": self.latest_frame_id,
                "stream_url": self.stream_url,
                "error": self.error
            }

    def get_latest_jpeg(self, annotated: bool = False) -> Optional[bytes]:
        with self._lock:
            return self.latest_annotated_jpeg if annotated else self.latest_frame_jpeg


class CameraService:
    def __init__(self):
        self.active_streams: Dict[str, ActiveCameraStream] = {}

    def validate_input(
        self,
        stream_url: Optional[str] = None,
        rtsp_url: Optional[str] = None,
        ip: Optional[str] = None,
        port: int = 554,
        protocol: str = "RTSP",
        path: str = "/stream",
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validates IP address, port, and stream URL.
        Returns: (is_valid, resolved_url, error_message)
        """
        target_url = rtsp_url or stream_url

        if target_url and target_url.strip():
            url = target_url.strip()
            # Demo/simulated shortcut
            if url.startswith("demo://") or "simulated" in url.lower():
                return True, url, None

            # Check supported protocols
            if not any(url.lower().startswith(p) for p in ["rtsp://", "http://", "https://"]):
                return False, "", "Stream URL must start with rtsp://, http://, or https://"

            return True, url, None

        if ip and ip.strip():
            ip_str = ip.strip()
            if ip_str.lower() != "localhost":
                try:
                    ipaddress.ip_address(ip_str)
                except ValueError:
                    return False, "", f"Invalid IP address format: '{ip_str}'"

            if port < 1 or port > 65535:
                return False, "", f"Port must be between 1 and 65535 (received: {port})"

            proto_lower = (protocol or "RTSP").lower()
            if proto_lower not in ["rtsp", "http", "https", "mjpeg"]:
                return False, "", f"Unsupported protocol '{protocol}'"

            clean_path = path if path.startswith("/") else f"/{path}"
            creds = ""
            if username and username.strip():
                u_enc = urllib.parse.quote(username.strip())
                p_enc = urllib.parse.quote(password) if password else ""
                creds = f"{u_enc}:{p_enc}@"

            assembled_url = f"{proto_lower}://{creds}{ip_str}:{port}{clean_path}"
            return True, assembled_url, None

        return False, "", "Must provide either an IP address or a stream URL."

    def check_reachability(self, stream_url: str, timeout: float = 2.5) -> Tuple[bool, str]:
        """
        Non-blocking TCP socket connection check to diagnose connectivity.
        """
        if stream_url.startswith("demo://") or "simulated" in stream_url.lower():
            return True, "Simulated stream ready"

        try:
            parsed = urllib.parse.urlparse(stream_url)
            host = parsed.hostname
            port = parsed.port or (554 if parsed.scheme == "rtsp" else 80)

            if not host:
                return False, "Camera cannot be reached: Could not resolve hostname from stream URL"

            with socket.create_connection((host, port), timeout=timeout):
                return True, f"Host {host}:{port} reachable"
        except socket.timeout:
            return False, f"Camera cannot be reached: Connection timed out reaching {stream_url} (timeout={timeout}s)"
        except ConnectionRefusedError:
            return False, f"Camera cannot be reached: Connection refused on port {port}. Verify camera RTSP server is active."
        except Exception as e:
            return False, f"Camera cannot be reached: Network check failed ({str(e)})"

    def connect_camera(
        self,
        camera_id: str,
        stream_url: str,
        camera_name: str = "IP Camera 01",
        is_simulated: bool = False
    ) -> ActiveCameraStream:
        """
        Connects to a camera stream and registers it in the database and active memory.
        """
        if camera_id in self.active_streams:
            self.active_streams[camera_id].stop()

        stream = ActiveCameraStream(
            camera_id=camera_id,
            stream_url=stream_url,
            camera_name=camera_name,
            is_simulated=is_simulated
        )
        self.active_streams[camera_id] = stream
        stream.start()

        # Persist in DB
        try:
            db = SessionLocal()
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            parsed = urllib.parse.urlparse(stream_url)
            sanitized_url = stream_url
            if parsed.password:
                sanitized_url = stream_url.replace(f":{parsed.password}@", ":****@")

            if not cam:
                cam = Camera(
                    camera_id=camera_id,
                    camera_name=camera_name,
                    ip_address=parsed.hostname or "127.0.0.1",
                    port=parsed.port or (554 if parsed.scheme == "rtsp" else 80),
                    protocol=parsed.scheme.upper() if parsed.scheme else "RTSP",
                    stream_path=parsed.path or "/stream",
                    stream_url=sanitized_url,
                    status="CONNECTED"
                )
                db.add(cam)
            else:
                cam.camera_name = camera_name
                cam.stream_url = sanitized_url
                cam.status = "CONNECTED"
            db.commit()
            db.close()
        except Exception as e:
            logger.warning(f"Failed to persist camera {camera_id} in DB: {e}")

        return stream

    def get_camera_status(self, camera_id: str) -> Optional[Dict[str, Any]]:
        if camera_id in self.active_streams:
            return self.active_streams[camera_id].get_latest_data()

        # Check DB
        try:
            db = SessionLocal()
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            db.close()
            if cam:
                return {
                    "camera_id": cam.camera_id,
                    "camera_name": cam.camera_name,
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
                    "stream_url": cam.stream_url,
                    "error": None
                }
        except Exception:
            pass

        return None

    def disconnect_camera(self, camera_id: str) -> bool:
        stream = self.active_streams.pop(camera_id, None)
        if stream:
            stream.stop()

        try:
            db = SessionLocal()
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            if cam:
                cam.status = "DISCONNECTED"
                db.commit()
            db.close()
        except Exception as e:
            logger.warning(f"Failed to update camera status in DB: {e}")

        logger.info(f"[CAMERA] Disconnected camera: {camera_id}")
        return True

    def mjpeg_generator(self, camera_id: str, annotated: bool = False):
        """
        Yields multipart JPEG frames for web streaming.
        """
        while True:
            if camera_id not in self.active_streams:
                break
            stream = self.active_streams[camera_id]
            frame_bytes = stream.get_latest_jpeg(annotated=annotated)
            if frame_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            time.sleep(0.04)

camera_service = CameraService()
