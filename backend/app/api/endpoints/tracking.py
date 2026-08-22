import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.tracking_service import TrackingService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{tracking_id}")
def get_application_status(tracking_id: str, db: Session = Depends(get_db)):
    """
    Public tracking endpoint — no authentication required.
    Citizen can check application status using only their Tracking ID.

    Example: GET /api/v1/track/MH-2026-NCL-A83K92P1

    Returns full application timeline, current status, document status, payment status.
    """
    if not tracking_id.startswith("MH-"):
        raise HTTPException(status_code=400, detail="Invalid tracking ID format. Must start with 'MH-'.")

    result = TrackingService.get_tracking_status(tracking_id, db)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No application found for Tracking ID: {tracking_id}. Please check the ID and try again."
        )

    return result
