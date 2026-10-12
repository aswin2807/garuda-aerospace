import time
import glob
import threading
from typing import Optional, Tuple
import cv2
import numpy as np

from backend.app.core.logging import logger

class LatestFrameReader:
    """
    Continuously grabs RTSP / video frames in a dedicated thread and exposes only the newest frame.
    This prevents inference from processing an ever-growing backlog when YOLO is slower than the camera frame rate.
    """
    def __init__(self, url: str, is_simulated: bool = False):
        self.url = url
        self.is_simulated = is_simulated or "demo://" in url.lower() or "simulated" in url.lower()
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame: Optional[np.ndarray] = None
        self.frame_id: int = 0
        self.running: bool = False
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None

        # Stream resolution and reported FPS
        self.width: int = 0
        self.height: int = 0
        self.fps: float = 25.0

        # Simulated frame files for demo/offline operation
        self._simulated_files = []
        if self.is_simulated:
            test_imgs = sorted(glob.glob("test/images/*.jpg") or glob.glob("../test/images/*.jpg"))
            if not test_imgs:
                test_imgs = sorted(glob.glob("train/images/*.jpg") or glob.glob("../train/images/*.jpg"))
            self._simulated_files = test_imgs[:60] if test_imgs else []

    def _open(self) -> cv2.VideoCapture:
        # Use CAP_FFMPEG where available
        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            # Fallback without CAP_FFMPEG flag if platform requires default backend
            cap = cv2.VideoCapture(self.url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def start(self) -> "LatestFrameReader":
        if self.is_simulated and self._simulated_files:
            sample = cv2.imread(self._simulated_files[0])
            if sample is not None:
                self.height, self.width = sample.shape[:2]
                self.fps = 25.0
            self.running = True
            self.thread = threading.Thread(target=self._simulated_loop, daemon=True)
            self.thread.start()
            logger.info(f"[CAMERA] Started simulated RTSP reader for {self.url} ({self.width}x{self.height} @ {self.fps}fps)")
            return self

        self.cap = self._open()
        if not self.cap.isOpened():
            logger.error(f"[CAMERA] Cannot open RTSP stream: {self.url}")
            raise RuntimeError(f"Cannot open RTSP stream: {self.url}")

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = cap_fps if (cap_fps > 0 and cap_fps <= 120) else 25.0

        self.running = True
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()
        logger.info(f"[CAMERA] Started RTSP reader for {self.url} ({self.width}x{self.height} @ {self.fps}fps)")
        return self

    def _reader_loop(self):
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                time.sleep(0.5)
                try:
                    self.cap = self._open()
                except Exception:
                    pass
                continue

            ok, frame = self.cap.read()
            if ok and frame is not None:
                with self.lock:
                    self.frame = frame
                    self.frame_id += 1
                    if self.width <= 0 or self.height <= 0:
                        self.height, self.width = frame.shape[:2]
            else:
                logger.warning(f"[CAMERA] RTSP frame lost for {self.url}. Reconnecting...")
                try:
                    if self.cap:
                        self.cap.release()
                except Exception:
                    pass
                time.sleep(0.5)
                try:
                    self.cap = self._open()
                except Exception as e:
                    logger.error(f"[CAMERA] Reconnect attempt failed: {e}")

    def _simulated_loop(self):
        idx = 0
        total = len(self._simulated_files)
        while self.running and total > 0:
            frame_path = self._simulated_files[idx % total]
            idx += 1
            frame = cv2.imread(frame_path)
            if frame is not None:
                with self.lock:
                    self.frame = frame
                    self.frame_id += 1
                    self.height, self.width = frame.shape[:2]
            time.sleep(1.0 / max(1.0, self.fps))

    def read_latest(self) -> Tuple[bool, Optional[np.ndarray], int]:
        with self.lock:
            if self.frame is None:
                return False, None, self.frame_id
            return True, self.frame.copy(), self.frame_id

    def get_properties(self) -> Tuple[int, int, float]:
        with self.lock:
            return self.width, self.height, self.fps

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        logger.info(f"[CAMERA] Stopped RTSP reader for {self.url}")
