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
                    "y2": "REAL"
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
                conn.commit()
        except Exception as e:
            pass

# Auto-ensure tables exist
try:
    init_db()
except Exception:
    pass

