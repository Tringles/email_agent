"""Agent API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/run")
async def run_agent(email_id: int = None, db: Session = Depends(get_db)):
    """Run LangGraph agent pipeline."""
    # TODO: Implement agent execution
    return {"message": "Agent execution triggered", "email_id": email_id}
