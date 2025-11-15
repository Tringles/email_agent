"""Email API endpoints."""

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.models.user import User
from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/email", tags=["email"])


@router.get("/{email_id}")
async def get_email(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get email by ID."""
    # TODO: Implement email retrieval
    return {"email_id": email_id}


@router.post("/ingest")
async def trigger_email_ingest(
    current_user: User = Depends(get_current_user)
):
    """Trigger email ingestion manually."""
    # TODO: Implement manual ingestion trigger
    return {"message": "Email ingestion triggered"}


@router.get("/{email_id}/summary")
async def get_email_summary(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get email summary."""
    # TODO: Implement summary retrieval
    return {"email_id": email_id, "summary": None}
