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

import uuid
from datetime import datetime, timezone

def sanitize_stream_url(url: str) -> str:
    """Masks credentials in RTSP / HTTP stream URLs to prevent leaking passwords in logs and UI."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":****@")
            return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except Exception:
        pass
    return url

class ActiveCameraStream:
    """
    Manages a single active IP/RTSP camera stream session:
    - Runs LatestFrameReader to prevent backlog and minimize latency
    - Executes YOLOv11 inference via FrameProcessor
    - Maintains flight session lifecycle (flight_id, flight_status, pre_landing_summary)
    - Maintains latest frame buffer, FPS counters, and image quality metrics
    """
    def __init__(
        self,
        camera_id: str,
        stream_url: str,
        camera_name: str = "IP Camera 01",
        is_simulated: bool = False,
        max_retries: int = 5,
        flight_id: Optional[str] = None
    ):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.stream_url = stream_url
        self.sanitized_url = sanitize_stream_url(stream_url)
        self.is_simulated = is_simulated or "demo://" in stream_url.lower() or "simulated" in stream_url.lower()
        self.max_retries = max_retries

        # Flight Lifecycle Tracking (FR-02, FR-04, FR-06)
        self.flight_id = flight_id or f"FLIGHT-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        self.flight_status = "FLYING"  # FLYING, ANALYSIS_ACTIVE, COMPLETED, ERROR
        self.flight_start_time = time.time()
        self.flight_end_time: Optional[float] = None
        self.frames_analyzed = 0
        self.first_detection_time: Optional[float] = None
        self.last_detection_time: Optional[float] = None
        self.latest_detected_object: Optional[str] = None
        self.latest_confidence: float = 0.0
        self.confidence_history: List[float] = []
        self.pre_landing_summary: Dict[str, Any] = {}

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
        with self._lock:
            self.status = "DISCONNECTED"
            if self.flight_status != "COMPLETED":
                self.flight_status = "COMPLETED"
                self.flight_end_time = time.time()
                self.pre_landing_summary = self._build_pre_landing_summary_locked()
        logger.info(f"[CAMERA] Stopped stream pipeline for {self.camera_id}")

    def complete_flight(self) -> Dict[str, Any]:
        """Finalizes flight session before landing and compiles the consolidated summary (FR-06)."""
        with self._lock:
            self.flight_status = "COMPLETED"
            self.flight_end_time = time.time()
            summary = self._build_pre_landing_summary_locked()
            self.pre_landing_summary = summary
        logger.info(f"[CAMERA] Completed flight {self.flight_id} for {self.camera_id}")
        return summary

    def _build_pre_landing_summary_locked(self) -> Dict[str, Any]:
        """Builds consolidated pre-landing summary while lock is held."""
        min_conf = round(float(min(self.confidence_history)), 3) if self.confidence_history else 0.0
        max_conf = round(float(max(self.confidence_history)), 3) if self.confidence_history else 0.0
        avg_conf = (
            round(float(np.mean(self.confidence_history)), 3)
            if self.confidence_history
            else round(self.average_confidence, 3)
        )
        duration = (
            round(time.time() - self.flight_start_time, 1)
            if not self.flight_end_time
            else round(self.flight_end_time - self.flight_start_time, 1)
        )

        first_det_iso = (
            datetime.fromtimestamp(self.first_detection_time, tz=timezone.utc).isoformat()
            if self.first_detection_time
            else None
        )
        last_det_iso = (
            datetime.fromtimestamp(self.last_detection_time, tz=timezone.utc).isoformat()
            if self.last_detection_time
            else None
        )

        # Summary status: READY once frames have been analyzed, or PENDING if aborted/ended before processing
        summary_status = "READY" if self.frames_analyzed > 0 else "PENDING"
        if self.flight_status == "COMPLETED" and self.frames_analyzed == 0:
            summary_status = "PENDING"

        total_unique = self.latest_session_totals.get("total_unique", 0)
        if total_unique == 0 and (self.latest_counts.get("light_on", 0) > 0 or self.latest_counts.get("light_off", 0) > 0):
            total_unique = self.latest_counts.get("light_on", 0) + self.latest_counts.get("light_off", 0)

        return {
            "flight_id": self.flight_id,
            "camera_id": self.camera_id,
            "flight_status": self.flight_status,
            "camera_status": self.status,
            "summary_status": summary_status,
            "total_unique_objects": total_unique,
            "light_on_count": self.latest_session_totals.get("light_on", self.latest_counts.get("light_on", 0)),
            "light_off_count": self.latest_session_totals.get("light_off", self.latest_counts.get("light_off", 0)),
            "min_confidence": min_conf,
            "avg_confidence": avg_conf,
            "max_confidence": max_conf,
            "frames_analyzed": self.frames_analyzed,
            "flight_duration_sec": duration,
            "first_detection_time": first_det_iso,
            "last_detection_time": last_det_iso,
            "latest_detected_object": self.latest_detected_object,
            "latest_confidence": round(self.latest_confidence, 3),
            "model": "runway_light_best.pt"
        }

    def get_pre_landing_summary(self) -> Dict[str, Any]:
        with self._lock:
            return self._build_pre_landing_summary_locked()

    def _run_inference_worker(self):
        logger.info(f"[CAMERA] Initializing LatestFrameReader for {self.camera_id}: {self.sanitized_url}")
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
                raise RuntimeError(f"Connected to RTSP but no video frame received from {self.sanitized_url}")

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
                self.flight_status = "ERROR"
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

                # Encode annotated frame with color-coded boxes & labels
                annotated = inference_service.draw_detections(frame, res.get("detections", []))
                ret_ann, ann_jpeg = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                ann_jpeg_bytes = ann_jpeg.tobytes() if ret_ann else clean_jpeg_bytes

                counts = res.get("counts", {})
                session_totals = res.get("session_totals", {})

                with self._lock:
                    self.status = "CONNECTED"
                    if self.flight_status == "FLYING":
                        self.flight_status = "ANALYSIS_ACTIVE"
                    self.frames_analyzed += 1
                    self.latest_detections = res.get("detections", [])
                    self.total_detections = res.get("total_objects", len(self.latest_detections))

                    if self.latest_detections:
                        now_det = time.time()
                        if self.first_detection_time is None:
                            self.first_detection_time = now_det
                        self.last_detection_time = now_det
                        primary_det = self.latest_detections[0]
                        self.latest_detected_object = str(primary_det.get("class_name", "UNKNOWN")).upper()
                        self.latest_confidence = float(primary_det.get("confidence", 0.0))
                        for d in self.latest_detections:
                            conf = float(d.get("confidence", 0.0))
                            if conf > 0:
                                self.confidence_history.append(conf)

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
                    self.pre_landing_summary = self._build_pre_landing_summary_locked()

            except Exception as e:
                logger.error(f"[INFERENCE] Error in frame worker for {self.camera_id}: {e}")

        with self._lock:
            self.status = "DISCONNECTED"

    def get_latest_data(self) -> Dict[str, Any]:
        with self._lock:
            last_det_str = (
                datetime.fromtimestamp(self.last_detection_time, tz=timezone.utc).isoformat()
                if self.last_detection_time
                else None
            )
            return {
                "camera_id": self.camera_id,
                "camera_name": self.camera_name,
                "flight_id": self.flight_id,
                "flight_status": self.flight_status,
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
                "latest_detected_object": self.latest_detected_object,
                "latest_confidence": self.latest_confidence,
                "last_detection_time": last_det_str,
                "frames_analyzed": self.frames_analyzed,
                "summary": dict(self.latest_summary),
                "pre_landing_summary": self._build_pre_landing_summary_locked(),
                "model": "runway_light_best.pt",
                "frame_id": self.latest_frame_id,
                "stream_url": self.sanitized_url,
                "error": self.error
            }

    def get_latest_jpeg(self, annotated: bool = False) -> Optional[bytes]:
        with self._lock:
            return self.latest_annotated_jpeg if annotated else self.latest_frame_jpeg


class CameraService:
    def __init__(self):
        self.active_streams: Dict[str, ActiveCameraStream] = {}
        self.recent_flight_summaries: Dict[str, Dict[str, Any]] = {}

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
            return False, f"Camera cannot be reached: Connection timed out reaching {sanitize_stream_url(stream_url)} (timeout={timeout}s)"
        except ConnectionRefusedError:
            return False, f"Camera cannot be reached: Connection refused on port {port}. Verify camera RTSP server is active."
        except Exception as e:
            return False, f"Camera cannot be reached: Network check failed ({str(e)})"

    def connect_camera(
        self,
        camera_id: str,
        stream_url: str,
        camera_name: str = "IP Camera 01",
        is_simulated: bool = False,
        flight_id: Optional[str] = None
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
            is_simulated=is_simulated,
            flight_id=flight_id
        )
        self.active_streams[camera_id] = stream
        stream.start()

        # Persist in DB
        try:
            db = SessionLocal()
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            sanitized_url = sanitize_stream_url(stream_url)
            parsed = urllib.parse.urlparse(stream_url)

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

        # Check recent flight summaries if camera disconnected
        if camera_id in self.recent_flight_summaries:
            recent = self.recent_flight_summaries[camera_id]
            return {
                "camera_id": camera_id,
                "camera_name": "Drone Camera",
                "flight_id": recent.get("flight_id"),
                "flight_status": recent.get("flight_status", "COMPLETED"),
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
                "total_detections": recent.get("total_unique_objects", 0),
                "detections": [],
                "alerts": [],
                "summary": None,
                "latest_detected_object": recent.get("latest_detected_object"),
                "latest_confidence": recent.get("latest_confidence"),
                "last_detection_time": recent.get("last_detection_time"),
                "frames_analyzed": recent.get("frames_analyzed", 0),
                "pre_landing_summary": recent,
                "model": "runway_light_best.pt",
                "stream_url": "",
                "error": None
            }

        # Check DB
        try:
            db = SessionLocal()
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            db.close()
            if cam:
                return {
                    "camera_id": cam.camera_id,
                    "camera_name": cam.camera_name,
                    "flight_id": None,
                    "flight_status": "COMPLETED",
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
                    "alerts": [],
                    "summary": None,
                    "latest_detected_object": None,
                    "latest_confidence": None,
                    "last_detection_time": None,
                    "frames_analyzed": 0,
                    "pre_landing_summary": None,
                    "model": "runway_light_best.pt",
                    "stream_url": cam.stream_url,
                    "error": None
                }
        except Exception:
            pass

        return None

    def complete_flight(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Completes the flight session and finalizes the pre-landing summary (FR-06)."""
        stream = self.active_streams.get(camera_id)
        if stream:
            summary = stream.complete_flight()
            self.recent_flight_summaries[camera_id] = summary
            return summary
        return self.recent_flight_summaries.get(camera_id)

    def get_flight_summary(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves current or final pre-landing flight summary."""
        stream = self.active_streams.get(camera_id)
        if stream:
            return stream.get_pre_landing_summary()
        return self.recent_flight_summaries.get(camera_id)

    def disconnect_camera(self, camera_id: str) -> bool:
        stream = self.active_streams.pop(camera_id, None)
        if stream:
            summary = stream.complete_flight()
            self.recent_flight_summaries[camera_id] = summary
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
