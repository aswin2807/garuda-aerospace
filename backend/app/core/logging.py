import logging
import sys
from datetime import datetime

logger = logging.getLogger("drone_ai")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

def log_detection_event(drone_id: str, frame_id: str, inference_ms: float, detections_count: int, mission_id: str = None):
    msg = f"drone={drone_id} frame={frame_id} inference={inference_ms:.1f}ms detections={detections_count}"
    if mission_id:
        msg += f" mission={mission_id}"
    logger.info(msg)
