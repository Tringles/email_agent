"""Agent API endpoints."""

from loguru import logger
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query, HTTPException

from app.models.user import User
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.id_encryption import decrypt_email_id, encrypt_email_id

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/run")
async def run_agent(
    email_id: Optional[str] = Query(None, description="Encrypted email ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run LangGraph agent pipeline."""
    # TODO: Implement agent execution
    encrypted_email_id = None
    if email_id:
        # Decrypt email ID
        try:
            decrypted_email_id = decrypt_email_id(email_id)
            encrypted_email_id = email_id  # Return encrypted ID
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")
    
    return {
        "message": "Agent execution triggered",
        "email_id": encrypted_email_id  # Return encrypted ID
    }
