import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from backend.app.db.database import SessionLocal
from backend.app.db.models import Session, FrameRecord, Detection, TrackRecord, RunwayFaultRecord, Alert, RunwayLightResult, RunwayLightSummary
from backend.app.core.logging import logger

def get_utc_now():
    return datetime.now(timezone.utc)

class DatabaseService:
    """
    Central database persistence layer for AI video sessions, frame metrics,
    object detections, tracks, runway faults, and alerts.
    Implements PRD Section 15, 16, 17, 39, 42.
    """

    def create_session(self, source: str, source_type: str = "VIDEO_FILE", session_id: Optional[str] = None) -> str:
        db: DBSession = SessionLocal()
        try:
            if not session_id:
                now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
                session_id = f"SESSION-{now_str}"

            # Check if session exists
            existing = db.query(Session).filter(Session.session_id == session_id).first()
            if existing:
                return existing.session_id

            session = Session(
                session_id=session_id,
                source=source,
                source_type=source_type,
                status="RUNNING",
                start_time=get_utc_now()
            )
            db.add(session)
            db.commit()
            logger.info(f"[DB] Created session {session_id} for source {source}")
            return session_id
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error creating session: {e}")
            return session_id or "SESSION-FALLBACK"
        finally:
            db.close()

    def update_session(self, session_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        db: DBSession = SessionLocal()
        try:
            sess = db.query(Session).filter(Session.session_id == session_id).first()
            if not sess:
                return None

            for key, val in kwargs.items():
                if hasattr(sess, key):
                    setattr(sess, key, val)

            db.commit()
            db.refresh(sess)
            return {
                "session_id": sess.session_id,
                "status": sess.status,
                "total_frames": sess.total_frames,
                "processed_frames": sess.processed_frames,
                "nav_count": sess.nav_count,
                "fod_count": sess.fod_count,
                "light_on_count": sess.light_on_count,
                "light_off_count": sess.light_off_count,
                "confirmed_faults": sess.confirmed_faults,
                "avg_confidence": sess.avg_confidence,
                "avg_inference_ms": sess.avg_inference_ms,
            }
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error updating session {session_id}: {e}")
            return None
        finally:
            db.close()

    def complete_session(self, session_id: str, final_stats: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        db: DBSession = SessionLocal()
        try:
            sess = db.query(Session).filter(Session.session_id == session_id).first()
            if not sess:
                return None

            sess.status = "COMPLETED"
            sess.end_time = get_utc_now()

            if final_stats:
                if "total_frames" in final_stats:
                    sess.total_frames = final_stats["total_frames"]
                if "processed_frames" in final_stats:
                    sess.processed_frames = final_stats["processed_frames"]
                if "nav_count" in final_stats:
                    sess.nav_count = final_stats["nav_count"]
                if "fod_count" in final_stats:
                    sess.fod_count = final_stats["fod_count"]
                if "light_on_count" in final_stats:
                    sess.light_on_count = final_stats["light_on_count"]
                if "light_off_count" in final_stats:
                    sess.light_off_count = final_stats["light_off_count"]
                if "confirmed_faults" in final_stats:
                    sess.confirmed_faults = final_stats["confirmed_faults"]
                if "avg_confidence" in final_stats:
                    sess.avg_confidence = float(final_stats["avg_confidence"])
                if "avg_inference_ms" in final_stats:
                    sess.avg_inference_ms = float(final_stats["avg_inference_ms"])

            db.commit()
            logger.info(f"[DB] Session {session_id} marked as COMPLETED")
            return self.get_session(session_id)
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error completing session {session_id}: {e}")
            return None
        finally:
            db.close()

    def record_frame(
        self,
        session_id: str,
        frame_number: int,
        stream_fps: float,
        inference_ms: float,
        counts: Dict[str, int]
    ):
        db: DBSession = SessionLocal()
        try:
            record = FrameRecord(
                session_id=session_id,
                frame_number=frame_number,
                timestamp=get_utc_now(),
                stream_fps=float(stream_fps),
                inference_ms=float(inference_ms),
                nav_count=counts.get("navigation", counts.get("nav_count", 0)),
                fod_count=counts.get("fod", counts.get("fod_count", 0)),
                light_on_count=counts.get("light_on", counts.get("light_on_count", 0)),
                light_off_count=counts.get("light_off", counts.get("light_off_count", 0))
            )
            db.add(record)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error recording frame #{frame_number} for {session_id}: {e}")
        finally:
            db.close()

    def save_detections(
        self,
        session_id: str,
        frame_id: int,
        detections: List[Dict[str, Any]],
        camera_id: Optional[str] = None
    ):
        """
        Persists detections per PRD Section 16 & 39.
        """
        if not detections:
            return

        db: DBSession = SessionLocal()
        try:
            records = []
            for d in detections:
                bbox = d.get("bbox", {})
                if isinstance(bbox, dict):
                    x1 = float(bbox.get("x1", 0))
                    y1 = float(bbox.get("y1", 0))
                    x2 = float(bbox.get("x2", 0))
                    y2 = float(bbox.get("y2", 0))
                elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                    x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                else:
                    x1 = y1 = x2 = y2 = 0.0

                w = max(0.0, x2 - x1)
                h = max(0.0, y2 - y1)
                cls_name = str(d.get("class_name", "UNKNOWN"))
                conf = float(d.get("confidence", 0.0))
                model_name = str(d.get("model", ""))
                track_id = d.get("track_id")

                rec = Detection(
                    job_id=session_id,
                    session_id=session_id,
                    camera_id=camera_id,
                    model_name=model_name,
                    class_name=cls_name,
                    class_id=int(d.get("class_id", 0)),
                    confidence=conf,
                    x=x1,
                    y=y1,
                    width=w,
                    height=h,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    track_id=int(track_id) if track_id is not None else None,
                    frame_number=frame_id,
                    timestamp=get_utc_now()
                )
                records.append(rec)

            db.add_all(records)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error saving {len(detections)} detections: {e}")
        finally:
            db.close()

    def save_detections_batch(
        self,
        session_id: str,
        batched_items: List[Any],
        camera_id: Optional[str] = None
    ):
        """
        Batch-persists detections across multiple frames in a single database transaction.
        Significantly reduces SQLite commit overhead during video analysis.
        """
        if not batched_items:
            return

        db: DBSession = SessionLocal()
        try:
            records = []
            now = get_utc_now()
            for frame_id, d in batched_items:
                bbox = d.get("bbox", {})
                if isinstance(bbox, dict):
                    x1 = float(bbox.get("x1", 0))
                    y1 = float(bbox.get("y1", 0))
                    x2 = float(bbox.get("x2", 0))
                    y2 = float(bbox.get("y2", 0))
                elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                    x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                else:
                    x1 = y1 = x2 = y2 = 0.0

                w = max(0.0, x2 - x1)
                h = max(0.0, y2 - y1)
                cls_name = str(d.get("class_name", "UNKNOWN"))
                conf = float(d.get("confidence", 0.0))
                model_name = str(d.get("model", ""))
                track_id = d.get("track_id")

                rec = Detection(
                    job_id=session_id,
                    session_id=session_id,
                    camera_id=camera_id,
                    model_name=model_name,
                    class_name=cls_name,
                    class_id=int(d.get("class_id", 0)),
                    confidence=conf,
                    x=x1,
                    y=y1,
                    width=w,
                    height=h,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    track_id=int(track_id) if track_id is not None else None,
                    frame_number=frame_id,
                    timestamp=now
                )
                records.append(rec)

            db.add_all(records)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error batch-saving {len(batched_items)} detections: {e}")
        finally:
            db.close()

    def save_alert(self, session_id: Optional[str], alert_data: Dict[str, Any], camera_id: Optional[str] = None):
        db: DBSession = SessionLocal()
        try:
            alert = Alert(
                session_id=session_id,
                camera_id=camera_id,
                type=alert_data.get("event_type", "HAZARD_ALERT"),
                severity=alert_data.get("severity", "WARNING"),
                message=alert_data.get("message", "Alert detected"),
                timestamp=get_utc_now()
            )
            db.add(alert)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error saving alert: {e}")
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        db: DBSession = SessionLocal()
        try:
            sess = db.query(Session).filter(Session.session_id == session_id).first()
            if not sess:
                return None
            return {
                "session_id": sess.session_id,
                "source": sess.source,
                "source_type": sess.source_type,
                "status": sess.status,
                "start_time": sess.start_time.isoformat() if sess.start_time else None,
                "end_time": sess.end_time.isoformat() if sess.end_time else None,
                "total_frames": sess.total_frames,
                "processed_frames": sess.processed_frames,
                "nav_count": sess.nav_count,
                "fod_count": sess.fod_count,
                "light_on_count": sess.light_on_count,
                "light_off_count": sess.light_off_count,
                "confirmed_faults": sess.confirmed_faults,
                "avg_confidence": sess.avg_confidence,
                "avg_inference_ms": sess.avg_inference_ms,
                "created_at": sess.created_at.isoformat() if sess.created_at else None,
            }
        finally:
            db.close()

    def get_session_detections(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        db: DBSession = SessionLocal()
        try:
            rows = (
                db.query(Detection)
                .filter(Detection.session_id == session_id)
                .order_by(Detection.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "frame_id": r.frame_number,
                    "model": r.model_name,
                    "class_name": r.class_name,
                    "confidence": r.confidence,
                    "bbox": {
                        "x1": r.x1 or r.x,
                        "y1": r.y1 or r.y,
                        "x2": r.x2 or (r.x + r.width),
                        "y2": r.y2 or (r.y + r.height)
                    },
                    "track_id": r.track_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None
                }
                for r in rows
            ]
        finally:
            db.close()

    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        db: DBSession = SessionLocal()
        try:
            sess = db.query(Session).filter(Session.session_id == session_id).first()
            if not sess:
                return {}

            total_dets = db.query(func.count(Detection.id)).filter(Detection.session_id == session_id).scalar() or 0
            avg_conf = db.query(func.avg(Detection.confidence)).filter(Detection.session_id == session_id).scalar() or 0.0

            # Count unique tracks per model
            unique_tracks = (
                db.query(Detection.model_name, func.count(func.distinct(Detection.track_id)))
                .filter(Detection.session_id == session_id, Detection.track_id.isnot(None))
                .group_by(Detection.model_name)
                .all()
            )
            track_counts = {m or "general": c for m, c in unique_tracks}

            return {
                "session_id": session_id,
                "status": sess.status,
                "start_time": sess.start_time.isoformat() if sess.start_time else None,
                "end_time": sess.end_time.isoformat() if sess.end_time else None,
                "total_frames": sess.total_frames,
                "processed_frames": sess.processed_frames,
                "total_detections": total_dets,
                "average_confidence": round(float(avg_conf), 3),
                "average_inference_ms": sess.avg_inference_ms,
                "counts": {
                    "navigation": sess.nav_count,
                    "fod": sess.fod_count,
                    "light_on": sess.light_on_count,
                    "light_off": sess.light_off_count,
                    "confirmed_faults": sess.confirmed_faults
                },
                "unique_tracks": track_counts
            }
        finally:
            db.close()

    def get_db_stats(self) -> Dict[str, int]:
        db: DBSession = SessionLocal()
        try:
            total_sessions = db.query(func.count(Session.session_id)).scalar() or 0
            total_frames = db.query(func.count(FrameRecord.id)).scalar() or 0
            total_detections = db.query(func.count(Detection.id)).scalar() or 0
            total_alerts = db.query(func.count(Alert.id)).scalar() or 0
            return {
                "total_sessions": total_sessions,
                "total_frames": total_frames,
                "total_detections": total_detections,
                "total_alerts": total_alerts
            }
        except Exception:
            return {"total_sessions": 0, "total_frames": 0, "total_detections": 0, "total_alerts": 0}
        finally:
            db.close()

    def save_runway_light_results(self, job_id: str, frame_id: int, detections: List[Dict[str, Any]], timestamp: float = 0.0) -> int:
        db: DBSession = SessionLocal()
        try:
            saved_count = 0
            for d in detections:
                bbox = d.get("bbox") or [0, 0, 0, 0]
                if isinstance(bbox, dict):
                    x1 = float(bbox.get("x1", 0))
                    y1 = float(bbox.get("y1", 0))
                    x2 = float(bbox.get("x2", 0))
                    y2 = float(bbox.get("y2", 0))
                elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                    x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
                else:
                    x1, y1, x2, y2 = 0.0, 0.0, 0.0, 0.0

                record = RunwayLightResult(
                    job_id=job_id,
                    light_id=d.get("light_id", "R1-C1"),
                    row_id=int(d.get("row_id", 1)),
                    column_id=int(d.get("column_id", 1)),
                    frame_id=frame_id,
                    timestamp=timestamp,
                    class_name=d.get("class_name", "LIGHT ON"),
                    status=d.get("slot_status", d.get("state", "UNKNOWN")),
                    confidence=float(d.get("confidence", 0.0)),
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    track_id=d.get("track_id"),
                    is_confirmed=bool(d.get("is_confirmed", False))
                )
                db.add(record)
                saved_count += 1
            db.commit()
            return saved_count
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error saving runway light results: {e}")
            return 0
        finally:
            db.close()

    def save_runway_light_summary(self, job_id: str, summary_data: Dict[str, Any]) -> Optional[RunwayLightSummary]:
        import json
        db: DBSession = SessionLocal()
        try:
            summary = db.query(RunwayLightSummary).filter(RunwayLightSummary.job_id == job_id).first()
            if not summary:
                summary = RunwayLightSummary(job_id=job_id)
                db.add(summary)

            summary.total_lights = summary_data.get("total_lights", 0)
            summary.lights_on = summary_data.get("lights_on", 0)
            summary.lights_off = summary_data.get("lights_off", 0)
            summary.lights_unknown = summary_data.get("lights_unknown", 0)
            summary.confirmed_faults = summary_data.get("confirmed_faults", 0)
            summary.total_rows = summary_data.get("total_rows", 0)
            summary.total_columns = summary_data.get("total_columns", 0)
            summary.average_confidence = float(summary_data.get("average_confidence", 0.0))
            summary.processed_frames = summary_data.get("processed_frames", 0)
            summary.analysis_duration = float(summary_data.get("analysis_duration", 0.0))

            matrix = summary_data.get("matrix", [])
            summary.matrix_json = json.dumps(matrix) if isinstance(matrix, list) else str(matrix)

            faults = summary_data.get("faults", [])
            summary.faults_json = json.dumps(faults) if isinstance(faults, list) else str(faults)

            db.commit()
            db.refresh(summary)
            return summary
        except Exception as e:
            db.rollback()
            logger.error(f"[DB] Error saving runway light summary: {e}")
            return None
        finally:
            db.close()

    def get_runway_light_summary(self, job_id: str) -> Optional[Dict[str, Any]]:
        import json
        db: DBSession = SessionLocal()
        try:
            summary = db.query(RunwayLightSummary).filter(RunwayLightSummary.job_id == job_id).first()
            if not summary:
                return None

            matrix = []
            if summary.matrix_json:
                try:
                    matrix = json.loads(summary.matrix_json)
                except Exception:
                    pass

            faults = []
            if summary.faults_json:
                try:
                    faults = json.loads(summary.faults_json)
                except Exception:
                    pass

            return {
                "job_id": summary.job_id,
                "total_lights": summary.total_lights,
                "lights_on": summary.lights_on,
                "lights_off": summary.lights_off,
                "lights_unknown": summary.lights_unknown,
                "confirmed_faults": summary.confirmed_faults,
                "total_rows": summary.total_rows,
                "total_columns": summary.total_columns,
                "average_confidence": summary.average_confidence,
                "processed_frames": summary.processed_frames,
                "analysis_duration": summary.analysis_duration,
                "matrix": matrix,
                "faults": faults
            }
        except Exception as e:
            logger.error(f"[DB] Error getting runway light summary: {e}")
            return None
        finally:
            db.close()

    def get_runway_light_results(self, job_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        db: DBSession = SessionLocal()
        try:
            results = (
                db.query(RunwayLightResult)
                .filter(RunwayLightResult.job_id == job_id)
                .order_by(RunwayLightResult.frame_id.asc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "job_id": r.job_id,
                    "light_id": r.light_id,
                    "row_id": r.row_id,
                    "column_id": r.column_id,
                    "frame_id": r.frame_id,
                    "timestamp": r.timestamp,
                    "class_name": r.class_name,
                    "status": r.status,
                    "confidence": r.confidence,
                    "bbox": [r.x1, r.y1, r.x2, r.y2],
                    "track_id": r.track_id,
                    "is_confirmed": r.is_confirmed,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"[DB] Error getting runway light results: {e}")
            return []
        finally:
            db.close()

database_service = DatabaseService()
