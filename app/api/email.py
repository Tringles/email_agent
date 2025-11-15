"""Email API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(prefix="/api/v1/email", tags=["email"])


@router.get("/{email_id}")
async def get_email(email_id: int, db: Session = Depends(get_db)):
    """Get email by ID."""
    # TODO: Implement email retrieval
    return {"email_id": email_id}


@router.post("/ingest")
async def trigger_email_ingest():
    """Trigger email ingestion manually."""
    # TODO: Implement manual ingestion trigger
    return {"message": "Email ingestion triggered"}


@router.get("/{email_id}/summary")
async def get_email_summary(email_id: int, db: Session = Depends(get_db)):
    """Get email summary."""
    # TODO: Implement summary retrieval
    return {"email_id": email_id, "summary": None}
