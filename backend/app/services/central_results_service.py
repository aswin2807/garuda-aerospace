import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, desc, or_, and_

from backend.app.core.logging import logger
from backend.app.db.database import SessionLocal
from backend.app.db.models import (
    AnalysisResult,
    DetectionEvent,
    MediaAsset,
    SurveillanceSessionRecord,
    AuditLog,
    AnalysisJob,
    Detection,
    get_utc_now,
    generate_result_id,
    generate_event_id,
    generate_media_id,
    generate_surveillance_session_id
)
from backend.app.schemas.results import (
    AnalysisResultCreate,
    AnalysisResultUpdate,
    DetectionEventCreate,
    MediaAssetCreate,
    SurveillanceSessionCreate
)


class CentralResultsService:
    """
    Unified Centralized Database Service for Garuda Aerospace
    Stores, organizes, and retrieves detection and surveillance results
    from all five modules:
      1. Navigation
      2. Rod Debris Detection (FOD)
      3. Runway Lights Detection
      4. Live Surveillance
      5. Offline Surveillance
    """

    def normalize_module_type(self, raw_type: str) -> str:
        t = (raw_type or "").lower().strip()
        if t in ("nav", "navigation"):
            return "navigation"
        if t in ("fod", "rod", "fod_debris", "rod_debris", "debris"):
            return "rod_debris"
        if t in ("runway", "runway_light", "runway_lights", "lights"):
            return "runway_lights"
        if t in ("live", "live_surveillance", "live_camera", "camera"):
            return "live_surveillance"
        if t in ("offline", "offline_surveillance", "video", "batch"):
            return "offline_surveillance"
        return t or "navigation"

    def create_result(self, data: AnalysisResultCreate, db: Optional[DBSession] = None) -> Dict[str, Any]:
        """
        Creates a new centralized analysis result (FR-01).
        Supports idempotency by checking existing result ID.
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            res_id = data.id or generate_result_id()
            existing = db.query(AnalysisResult).filter(AnalysisResult.id == res_id).first()
            if existing:
                # Update existing rather than failing (idempotency)
                existing.status = data.status or existing.status
                existing.summary = data.summary or existing.summary
                if data.result_data:
                    existing.result_data = data.result_data
                existing.updated_at = get_utc_now()
                db.commit()
                return self._result_to_dict(existing)

            mod_type = self.normalize_module_type(data.module_type)
            result = AnalysisResult(
                id=res_id,
                module_type=mod_type,
                session_id=data.session_id,
                title=data.title,
                status=(data.status or "queued").lower(),
                summary=data.summary,
                result_data=data.result_data or {},
                started_at=data.started_at or get_utc_now(),
                completed_at=data.completed_at,
                media_reference=data.media_reference,
                error_message=data.error_message,
                created_at=get_utc_now(),
                updated_at=get_utc_now()
            )
            db.add(result)

            # Add nested events if provided
            if data.events:
                for ev in data.events:
                    event = DetectionEvent(
                        id=generate_event_id(),
                        analysis_result_id=res_id,
                        event_type=ev.event_type,
                        class_name=ev.class_name,
                        confidence=ev.confidence,
                        timestamp=ev.timestamp or get_utc_now(),
                        video_timestamp=ev.video_timestamp,
                        location_data=ev.location_data,
                        event_data=ev.event_data
                    )
                    db.add(event)

            # Add nested media assets if provided
            if data.media_assets:
                for ma in data.media_assets:
                    asset = MediaAsset(
                        id=generate_media_id(),
                        analysis_result_id=res_id,
                        media_type=ma.media_type,
                        storage_key=ma.storage_key,
                        file_name=ma.file_name,
                        file_size=ma.file_size or 0,
                        created_at=get_utc_now()
                    )
                    db.add(asset)

            # Audit log
            audit = AuditLog(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                action="CREATE_RESULT",
                resource_type="analysis_results",
                resource_id=res_id,
                details={"module_type": mod_type, "title": data.title},
                timestamp=get_utc_now()
            )
            db.add(audit)
            db.commit()
            db.refresh(result)
            logger.info(f"[CENTRAL_DB] Created result {res_id} [{mod_type}] - {data.title}")
            return self._result_to_dict(result)
        except Exception as e:
            db.rollback()
            logger.error(f"[CENTRAL_DB] Error creating result: {e}")
            raise
        finally:
            if own_session:
                db.close()

    def update_result(self, result_id: str, data: AnalysisResultUpdate, db: Optional[DBSession] = None) -> Optional[Dict[str, Any]]:
        """
        Updates processing status, summary, and module data for a result record (FR-10).
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            result = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
            if not result:
                return None

            if data.status is not None:
                result.status = data.status.lower()
                if result.status in ("completed", "failed") and not result.completed_at:
                    result.completed_at = data.completed_at or get_utc_now()
            if data.summary is not None:
                result.summary = data.summary
            if data.result_data is not None:
                current_data = result.result_data or {}
                if isinstance(current_data, dict) and isinstance(data.result_data, dict):
                    current_data.update(data.result_data)
                    result.result_data = current_data
                else:
                    result.result_data = data.result_data
            if data.media_reference is not None:
                result.media_reference = data.media_reference
            if data.error_message is not None:
                result.error_message = data.error_message
            if data.completed_at is not None:
                result.completed_at = data.completed_at

            result.updated_at = get_utc_now()

            audit = AuditLog(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                action="UPDATE_RESULT",
                resource_type="analysis_results",
                resource_id=result_id,
                details={"status": result.status},
                timestamp=get_utc_now()
            )
            db.add(audit)
            db.commit()
            db.refresh(result)
            return self._result_to_dict(result)
        except Exception as e:
            db.rollback()
            logger.error(f"[CENTRAL_DB] Error updating result {result_id}: {e}")
            raise
        finally:
            if own_session:
                db.close()

    def get_result(self, result_id: str, db: Optional[DBSession] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves one result with its complete details, events, and media (FR-09).
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            result = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
            if not result:
                return None

            out = self._result_to_dict(result)
            out["events"] = [self._event_to_dict(e) for e in result.events]
            out["media_assets"] = [self._media_to_dict(m) for m in result.media_assets]
            return out
        finally:
            if own_session:
                db.close()

    def list_results(
        self,
        module_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        detection_class: Optional[str] = None,
        camera_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        db: Optional[DBSession] = None
    ) -> Dict[str, Any]:
        """
        Retrieves paginated, filtered results across all modules (FR-07, FR-08).
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            query = db.query(AnalysisResult)

            if module_type and module_type.lower() != "all":
                norm_m = self.normalize_module_type(module_type)
                query = query.filter(AnalysisResult.module_type == norm_m)

            if status and status.lower() != "all":
                query = query.filter(AnalysisResult.status == status.lower())

            if start_date:
                query = query.filter(AnalysisResult.created_at >= start_date)

            if end_date:
                query = query.filter(AnalysisResult.created_at <= end_date)

            if search:
                term = f"%{search.strip()}%"
                query = query.filter(
                    or_(
                        AnalysisResult.id.ilike(term),
                        AnalysisResult.session_id.ilike(term),
                        AnalysisResult.title.ilike(term),
                        AnalysisResult.summary.ilike(term)
                    )
                )

            if camera_id:
                query = query.join(SurveillanceSessionRecord, AnalysisResult.session_id == SurveillanceSessionRecord.id, isouter=True)
                query = query.filter(SurveillanceSessionRecord.camera_id == camera_id)

            if detection_class:
                query = query.join(DetectionEvent, AnalysisResult.id == DetectionEvent.analysis_result_id)
                query = query.filter(DetectionEvent.class_name.ilike(f"%{detection_class.strip()}%"))

            total = query.distinct().count()
            query = query.order_by(desc(AnalysisResult.created_at))

            offset = max(0, (page - 1) * page_size)
            items = query.offset(offset).limit(page_size).all()

            total_pages = max(1, (total + page_size - 1) // page_size)

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "items": [self._result_to_dict(r) for r in items]
            }
        finally:
            if own_session:
                db.close()

    def get_summary(self, db: Optional[DBSession] = None) -> Dict[str, Any]:
        """
        Retrieves dashboard summary statistics across all modules (FR-07).
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            total_results = db.query(AnalysisResult).count()

            # By module
            by_mod_raw = db.query(AnalysisResult.module_type, func.count(AnalysisResult.id)).group_by(AnalysisResult.module_type).all()
            by_module = {
                "navigation": 0,
                "rod_debris": 0,
                "runway_lights": 0,
                "live_surveillance": 0,
                "offline_surveillance": 0
            }
            for m, count in by_mod_raw:
                if m in by_module:
                    by_module[m] = count
                else:
                    by_module[m] = count

            # By status
            by_stat_raw = db.query(AnalysisResult.status, func.count(AnalysisResult.id)).group_by(AnalysisResult.status).all()
            by_status = {
                "queued": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            }
            for s, count in by_stat_raw:
                by_status[s.lower()] = count

            total_events = db.query(DetectionEvent).count()
            total_media = db.query(MediaAsset).count()

            recent = db.query(AnalysisResult).order_by(desc(AnalysisResult.created_at)).limit(5).all()

            return {
                "total_results": total_results,
                "by_module": by_module,
                "by_status": by_status,
                "total_events": total_events,
                "total_media": total_media,
                "recent_results": [self._result_to_dict(r) for r in recent]
            }
        finally:
            if own_session:
                db.close()

    def add_detection_events(self, result_id: str, events: List[DetectionEventCreate], db: Optional[DBSession] = None) -> int:
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            res = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
            if not res:
                raise ValueError(f"Result {result_id} not found")

            count = 0
            for ev in events:
                event = DetectionEvent(
                    id=generate_event_id(),
                    analysis_result_id=result_id,
                    event_type=ev.event_type,
                    class_name=ev.class_name,
                    confidence=ev.confidence,
                    timestamp=ev.timestamp or get_utc_now(),
                    video_timestamp=ev.video_timestamp,
                    location_data=ev.location_data,
                    event_data=ev.event_data
                )
                db.add(event)
                count += 1

            db.commit()
            return count
        except Exception as e:
            db.rollback()
            logger.error(f"[CENTRAL_DB] Error adding events: {e}")
            raise
        finally:
            if own_session:
                db.close()

    def add_media_asset(self, result_id: str, asset: MediaAssetCreate, db: Optional[DBSession] = None) -> Dict[str, Any]:
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            res = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
            if not res:
                raise ValueError(f"Result {result_id} not found")

            m = MediaAsset(
                id=generate_media_id(),
                analysis_result_id=result_id,
                media_type=asset.media_type,
                storage_key=asset.storage_key,
                file_name=asset.file_name,
                file_size=asset.file_size or 0,
                created_at=get_utc_now()
            )
            db.add(m)
            db.commit()
            db.refresh(m)
            return self._media_to_dict(m)
        finally:
            if own_session:
                db.close()

    def create_surveillance_session(self, data: SurveillanceSessionCreate, db: Optional[DBSession] = None) -> Dict[str, Any]:
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            sid = data.id or generate_surveillance_session_id()
            sess = SurveillanceSessionRecord(
                id=sid,
                mode=data.mode,
                camera_id=data.camera_id,
                source_reference=data.source_reference,
                started_at=get_utc_now(),
                status=data.status or "active",
                metadata_json=data.metadata_json or {}
            )
            db.add(sess)
            db.commit()
            db.refresh(sess)
            return {
                "id": sess.id,
                "mode": sess.mode,
                "camera_id": sess.camera_id,
                "source_reference": sess.source_reference,
                "started_at": sess.started_at,
                "ended_at": sess.ended_at,
                "status": sess.status,
                "metadata_json": sess.metadata_json
            }
        finally:
            if own_session:
                db.close()

    def get_surveillance_session(self, session_id: str, db: Optional[DBSession] = None) -> Optional[Dict[str, Any]]:
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            sess = db.query(SurveillanceSessionRecord).filter(SurveillanceSessionRecord.id == session_id).first()
            if not sess:
                return None
            return {
                "id": sess.id,
                "mode": sess.mode,
                "camera_id": sess.camera_id,
                "source_reference": sess.source_reference,
                "started_at": sess.started_at,
                "ended_at": sess.ended_at,
                "status": sess.status,
                "metadata_json": sess.metadata_json
            }
        finally:
            if own_session:
                db.close()

    def sync_analysis_job_to_central_result(self, job_id: str, db: Optional[DBSession] = None) -> Optional[Dict[str, Any]]:
        """
        Synchronizes an AnalysisJob record into the centralized analysis_results table.
        Creates DetectionEvents and MediaAssets automatically.
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                return None

            # Determine module type
            atype = (job.analysis_type or "NAVIGATION").upper()
            if job.media_type == "VIDEO":
                mod_type = "offline_surveillance"
                sub_module = self.normalize_module_type(atype)
            else:
                mod_type = self.normalize_module_type(atype)
                sub_module = mod_type

            # Map status
            j_status = (job.status or "QUEUED").lower()
            if j_status in ("completed", "done", "finished"):
                res_status = "completed"
            elif j_status in ("failed", "error", "cancelled"):
                res_status = "failed"
            elif j_status in ("analyzing", "processing", "in_progress"):
                res_status = "processing"
            else:
                res_status = "queued"

            # Build result_data
            result_data = {
                "job_id": job.id,
                "source_file": job.filename,
                "media_type": job.media_type,
                "sub_module": sub_module,
                "total_frames": job.total_frames,
                "processed_frames": job.processed_frames,
                "duration_seconds": job.duration_seconds,
                "video_fps": job.video_fps,
                "speed_ratio": job.speed_ratio,
                "total_detections": job.total_detections,
                "avg_confidence": job.avg_confidence,
                "avg_inference_ms": job.avg_inference_ms,
                "model_version": job.model_version
            }

            # Module-specific metrics
            if atype == "RUNWAY_LIGHT":
                result_data.update({
                    "light_on_count": job.light_on_count,
                    "light_off_count": job.light_off_count,
                    "unknown_light_count": job.unknown_light_count,
                    "total_lights": job.light_on_count + job.light_off_count + job.unknown_light_count,
                    "confirmed_faults": job.confirmed_faults,
                    "rows_detected": job.rows_detected
                })
                if job.row_results:
                    try:
                        result_data["row_results"] = json.loads(job.row_results)
                    except Exception:
                        pass
                summary = f"Detected {result_data.get('total_lights', 0)} lights: {job.light_on_count} ON, {job.light_off_count} OFF, {job.unknown_light_count} UNKNOWN. Confirmed faults: {job.confirmed_faults}."
                title = f"Runway Light Inspection: {job.filename}"

            elif atype in ("FOD", "ROD_DEBRIS"):
                result_data.update({
                    "unique_fod_count": job.unique_fod_count or job.fod_count,
                    "cumulative_fod_detections": job.fod_count
                })
                summary = f"Identified {result_data.get('unique_fod_count', 0)} unique debris object(s) across {job.processed_frames} analyzed frames."
                title = f"Rod Debris (FOD) Scan: {job.filename}"

            else:  # NAVIGATION
                result_data.update({
                    "unique_nav_count": job.unique_nav_count or job.nav_count,
                    "total_obstacle_detections": job.nav_count
                })
                summary = f"Perceived operational flight path across {job.processed_frames} frames. Obstacle tracks: {result_data.get('unique_nav_count', 0)}."
                title = f"Navigation Analysis: {job.filename}"

            # Check existing central result
            c_res = db.query(AnalysisResult).filter(AnalysisResult.id == job.id).first()
            if not c_res:
                c_res = AnalysisResult(
                    id=job.id,
                    module_type=mod_type,
                    session_id=job.id,
                    title=title,
                    status=res_status,
                    summary=summary,
                    result_data=result_data,
                    started_at=job.started_at or job.created_at,
                    completed_at=job.completed_at,
                    media_reference=job.annotated_media_path,
                    error_message=job.error_message,
                    created_at=job.created_at or get_utc_now(),
                    updated_at=job.updated_at or get_utc_now()
                )
                db.add(c_res)
            else:
                c_res.status = res_status
                c_res.summary = summary
                c_res.result_data = result_data
                c_res.media_reference = job.annotated_media_path or c_res.media_reference
                c_res.completed_at = job.completed_at or c_res.completed_at
                c_res.error_message = job.error_message
                c_res.updated_at = get_utc_now()

            db.commit()
            db.refresh(c_res)

            # Sync media assets
            existing_media_keys = {m.storage_key for m in c_res.media_assets}
            if job.annotated_media_path and job.annotated_media_path not in existing_media_keys:
                med = MediaAsset(
                    id=generate_media_id(),
                    analysis_result_id=c_res.id,
                    media_type="video" if job.media_type == "VIDEO" else "image",
                    storage_key=job.annotated_media_path,
                    file_name=Path(job.annotated_media_path).name,
                    file_size=os.path.getsize(job.annotated_media_path) if os.path.exists(job.annotated_media_path) else 0,
                    created_at=get_utc_now()
                )
                db.add(med)

            if job.report_csv_path and job.report_csv_path not in existing_media_keys:
                med_csv = MediaAsset(
                    id=generate_media_id(),
                    analysis_result_id=c_res.id,
                    media_type="report",
                    storage_key=job.report_csv_path,
                    file_name=Path(job.report_csv_path).name,
                    file_size=os.path.getsize(job.report_csv_path) if os.path.exists(job.report_csv_path) else 0,
                    created_at=get_utc_now()
                )
                db.add(med_csv)

            if job.report_json_path and job.report_json_path not in existing_media_keys:
                med_json = MediaAsset(
                    id=generate_media_id(),
                    analysis_result_id=c_res.id,
                    media_type="report",
                    storage_key=job.report_json_path,
                    file_name=Path(job.report_json_path).name,
                    file_size=os.path.getsize(job.report_json_path) if os.path.exists(job.report_json_path) else 0,
                    created_at=get_utc_now()
                )
                db.add(med_json)

            # Sync detection events from detections table if not populated
            if len(c_res.events) == 0:
                raw_dets = db.query(Detection).filter(Detection.job_id == job.id).limit(100).all()
                for d in raw_dets:
                    is_fod = (d.analysis_type or atype) in ("FOD", "FOD_DEBRIS")
                    coords_dict = None
                    if is_fod:
                        coords_dict = {
                            "latitude": d.latitude,
                            "longitude": d.longitude,
                            "crs": d.coordinate_crs or "WGS84",
                            "uncertainty_m": d.coordinate_uncertainty_m,
                            "status": d.coordinate_status or "unavailable",
                            "method": d.coordinate_method or "none",
                            "formatted": d.coordinate_formatted or (
                                "Coordinates unavailable"
                                if d.latitude is None
                                else f"{abs(d.latitude):.6f}° {'N' if d.latitude >= 0 else 'S'}, {abs(d.longitude):.6f}° {'E' if d.longitude >= 0 else 'W'}"
                            )
                        }

                    ev = DetectionEvent(
                        id=generate_event_id(),
                        analysis_result_id=c_res.id,
                        event_type=d.analysis_type or atype,
                        class_name=d.class_name,
                        confidence=d.confidence,
                        timestamp=d.timestamp,
                        video_timestamp=float(d.frame_number) / max(1.0, job.video_fps or 30.0),
                        location_data={
                            "x1": d.x1 or d.x,
                            "y1": d.y1 or d.y,
                            "x2": d.x2,
                            "y2": d.y2,
                            "latitude": d.latitude,
                            "longitude": d.longitude,
                            "uncertainty_m": d.coordinate_uncertainty_m,
                            "status": d.coordinate_status,
                            "method": d.coordinate_method,
                            "formatted": d.coordinate_formatted or (coords_dict["formatted"] if coords_dict else None)
                        },
                        event_data={
                            "track_id": d.track_id,
                            "frame": d.frame_number,
                            "debris_coordinates": coords_dict
                        }
                    )
                    db.add(ev)

            db.commit()
            db.refresh(c_res)
            return self._result_to_dict(c_res)
        except Exception as e:
            db.rollback()
            logger.error(f"[CENTRAL_DB] Error syncing job {job_id}: {e}")
            return None
        finally:
            if own_session:
                db.close()

    def backfill_all_historical_jobs(self) -> int:
        """
        Backfills un-synced historical AnalysisJob records into the centralized analysis_results table.
        """
        with SessionLocal() as db:
            existing_ids = set(r[0] for r in db.query(AnalysisResult.id).all())
            missing_job_ids = [j[0] for j in db.query(AnalysisJob.id).all() if j[0] not in existing_ids]

        synced = 0
        for jid in missing_job_ids:
            try:
                res = self.sync_analysis_job_to_central_result(jid)
                if res:
                    synced += 1
            except Exception as e:
                logger.error(f"[CENTRAL_DB] Backfill error for job {jid}: {e}")
        if synced > 0:
            logger.info(f"[CENTRAL_DB] Backfilled {synced} historical analysis jobs into centralized results.")
        return synced

    def _result_to_dict(self, r: AnalysisResult) -> Dict[str, Any]:
        return {
            "id": r.id,
            "module_type": r.module_type,
            "session_id": r.session_id,
            "title": r.title,
            "status": r.status,
            "summary": r.summary,
            "result_data": r.result_data or {},
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "media_reference": r.media_reference,
            "error_message": r.error_message,
            "events_count": len(r.events) if r.events else 0,
            "media_count": len(r.media_assets) if r.media_assets else 0
        }

    def _event_to_dict(self, e: DetectionEvent) -> Dict[str, Any]:
        return {
            "id": e.id,
            "analysis_result_id": e.analysis_result_id,
            "event_type": e.event_type,
            "class_name": e.class_name,
            "confidence": e.confidence,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "video_timestamp": e.video_timestamp,
            "location_data": e.location_data,
            "event_data": e.event_data
        }

    def _media_to_dict(self, m: MediaAsset) -> Dict[str, Any]:
        key = m.storage_key or ""
        access_url = key
        if key.startswith("/") or key.startswith("data/") or key.startswith("static/"):
            # Provide static / api download link
            access_url = f"/api/v1/analysis/{m.analysis_result_id}/media"
        return {
            "id": m.id,
            "analysis_result_id": m.analysis_result_id,
            "media_type": m.media_type,
            "storage_key": m.storage_key,
            "file_name": m.file_name,
            "file_size": m.file_size,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "access_url": access_url
        }


central_results_service = CentralResultsService()
