from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.database import get_db
from backend.app.services.inference_service import inference_service

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "degraded"

    model_status = "loaded" if inference_service.loaded else "unavailable"

    return {
        "api": "healthy",
        "database": db_status,
        "model": model_status
    }
