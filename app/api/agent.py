"""Agent API endpoints."""

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.models.user import User
from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/run")
async def run_agent(
    email_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run LangGraph agent pipeline."""
    # TODO: Implement agent execution
    return {"message": "Agent execution triggered", "email_id": email_id}
