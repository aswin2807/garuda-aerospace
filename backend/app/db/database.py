from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend.app.db import models  # noqa
    Base.metadata.create_all(bind=engine)

    # Automatic column additions for SQLite if schema evolved
    if settings.DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                # Check detections columns
                res = conn.execute(text("PRAGMA table_info(detections)"))
                cols = [r[1] for r in res.fetchall()]
                needed_cols = {
                    "session_id": "TEXT",
                    "camera_id": "TEXT",
                    "job_id": "TEXT",
                    "model_name": "TEXT",
                    "analysis_type": "TEXT",
                    "track_id": "INTEGER",
                    "x1": "REAL",
                    "y1": "REAL",
                    "x2": "REAL",
                    "y2": "REAL",
                    "latitude": "REAL",
                    "longitude": "REAL",
                    "coordinate_uncertainty_m": "REAL",
                    "coordinate_status": "TEXT",
                    "coordinate_method": "TEXT",
                    "coordinate_crs": "TEXT",
                    "coordinate_formatted": "TEXT"
                }
                for col, col_type in needed_cols.items():
                    if col not in cols:
                        conn.execute(text(f"ALTER TABLE detections ADD COLUMN {col} {col_type}"))

                # Check analysis_jobs columns
                res_jobs = conn.execute(text("PRAGMA table_info(analysis_jobs)"))
                job_cols = [r[1] for r in res_jobs.fetchall()]
                needed_job_cols = {
                    "analysis_type": "TEXT",
                    "unknown_light_count": "INTEGER",
                    "rows_detected": "INTEGER",
                    "row_results": "TEXT",
                    "total_detections": "INTEGER",
                    "speed_ratio": "REAL",
                    "class_counts": "TEXT"
                }
                for col, col_type in needed_job_cols.items():
                    if col not in job_cols:
                        conn.execute(text(f"ALTER TABLE analysis_jobs ADD COLUMN {col} {col_type}"))

                # Check alerts columns
                res = conn.execute(text("PRAGMA table_info(alerts)"))
                alert_cols = [r[1] for r in res.fetchall()]
                for col in ["session_id", "camera_id"]:
                    if col not in alert_cols:
                        conn.execute(text(f"ALTER TABLE alerts ADD COLUMN {col} TEXT"))

                # Check runway_faults columns
                res = conn.execute(text("PRAGMA table_info(runway_faults)"))
                fault_cols = [r[1] for r in res.fetchall()]
                for col in ["job_id", "first_detected_frame", "last_detected_frame"]:
                    if col not in fault_cols:
                        conn.execute(text(f"ALTER TABLE runway_faults ADD COLUMN {col} {'INTEGER' if 'frame' in col else 'TEXT'}"))

                # Check users columns
                res_users = conn.execute(text("PRAGMA table_info(users)"))
                user_cols = [r[1] for r in res_users.fetchall()]
                if "last_login_at" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP"))
                if "is_email_verified" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 1"))
                if "account_status" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN account_status TEXT DEFAULT 'ACTIVE'"))
                if "session_invalidated_at" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN session_invalidated_at TIMESTAMP"))
                if "updated_at" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP"))

                # Check navigation_routes table columns
                res_routes = conn.execute(text("PRAGMA table_info(navigation_routes)"))
                route_cols = [r[1] for r in res_routes.fetchall()]
                needed_route_cols = {
                    "target_name": "TEXT",
                    "total_distance_m": "REAL",
                    "estimated_time_s": "REAL",
                    "waypoints_json": "TEXT",
                    "status": "TEXT",
                    "created_by": "TEXT"
                }
                for col, col_type in needed_route_cols.items():
                    if col not in route_cols:
                        conn.execute(text(f"ALTER TABLE navigation_routes ADD COLUMN {col} {col_type}"))

                conn.commit()
        except Exception as e:
            pass

    # Ensure default operator account exists and all non-disabled accounts are active without email verification
    try:
        import os
        from backend.app.core.security import get_password_hash
        db = SessionLocal()
        try:
            db.query(models.User).filter(
                models.User.account_status == "PENDING_VERIFICATION"
            ).update({"account_status": "ACTIVE", "is_email_verified": True})
            db.commit()

            default_email = os.getenv("DEFAULT_OPERATOR_EMAIL", "operator@garuda.aero")
            default_password = os.getenv("DEFAULT_OPERATOR_PASSWORD", "password123")
            operator = db.query(models.User).filter(models.User.email == default_email).first()
            if not operator:
                operator = models.User(
                    email=default_email,
                    name="Aswin S P",
                    password_hash=get_password_hash(default_password),
                    role="ADMIN",
                    is_active=True,
                    is_email_verified=True,
                    account_status="ACTIVE",
                )
                db.add(operator)
                db.commit()
            else:
                if not operator.is_email_verified or operator.account_status != "ACTIVE":
                    operator.is_email_verified = True
                    operator.account_status = "ACTIVE"
                    db.commit()
        finally:
            db.close()
    except Exception:
        pass


# Auto-ensure tables exist
try:
    init_db()
except Exception:
    pass
