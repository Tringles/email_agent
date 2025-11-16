"""Agent API endpoints."""

from loguru import logger
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel

from app.models.user import User
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.id_encryption import decrypt_email_id, encrypt_email_id
from app.services.agent_service import AgentService
from app.tasks.email_tasks import process_email_agent_task

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class ProcessEmailsRequest(BaseModel):
    """여러 이메일 일괄 처리 요청"""
    email_ids: List[str]  # Encrypted email IDs
    async_mode: bool = False  # True면 Celery task로 백그라운드 처리


@router.post("/process")
async def process_email(
    email_id: str = Query(..., description="Encrypted email ID"),
    async_mode: bool = Query(False, description="Process in background (Celery task)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    단일 이메일을 LangGraph AI Agent로 처리
    
    Args:
        email_id: 암호화된 이메일 ID
        async_mode: True면 Celery task로 백그라운드 처리, False면 동기 처리
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        처리 결과
    """
    try:
        # 이메일 ID 복호화
        try:
            decrypted_email_id = decrypt_email_id(email_id)
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")
        
        if async_mode:
            # Celery task로 백그라운드 처리
            task = process_email_agent_task.delay(decrypted_email_id, current_user.id)
            logger.info(f"Triggered background AI processing for email {decrypted_email_id}, task_id={task.id}")
            
            return {
                "success": True,
                "message": "AI processing started in background",
                "email_id": email_id,
                "task_id": task.id,
                "status": "processing"
            }
        else:
            # 동기 처리 (즉시 실행)
            agent_service = AgentService()
            result = agent_service.process_email_sync(decrypted_email_id, current_user.id, db)
            
            return {
                "success": result.get("success", False),
                "email_id": email_id,
                "completed_nodes": result.get("completed_nodes", []),
                "errors": result.get("errors", []),
                "summary": result.get("summary"),
                "importance_level": result.get("importance_level"),
                "classification": result.get("classification"),
                "status": "completed" if result.get("success") else "failed"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing email {email_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process email: {str(e)}")


@router.post("/process/batch")
async def process_emails_batch(
    request: ProcessEmailsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    여러 이메일을 일괄 처리 (LangGraph AI Agent)
    
    Args:
        request: 이메일 ID 리스트 및 처리 모드
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        처리 결과 (task IDs 또는 처리 결과)
    """
    try:
        if not request.email_ids:
            raise HTTPException(status_code=400, detail="email_ids cannot be empty")
        
        # 이메일 ID 복호화
        decrypted_ids = []
        for encrypted_id in request.email_ids:
            try:
                decrypted_id = decrypt_email_id(encrypted_id)
                decrypted_ids.append((encrypted_id, decrypted_id))
            except ValueError as e:
                logger.warning(f"Invalid encrypted email_id {encrypted_id}: {e}")
                continue
        
        if not decrypted_ids:
            raise HTTPException(status_code=400, detail="No valid email IDs provided")
        
        if request.async_mode:
            # Celery task로 백그라운드 처리
            task_ids = []
            for encrypted_id, decrypted_id in decrypted_ids:
                task = process_email_agent_task.delay(decrypted_id, current_user.id)
                task_ids.append({
                    "email_id": encrypted_id,
                    "task_id": task.id
                })
            
            logger.info(f"Triggered background AI processing for {len(decrypted_ids)} emails")
            
            return {
                "success": True,
                "message": f"AI processing started for {len(decrypted_ids)} emails",
                "tasks": task_ids,
                "total": len(decrypted_ids),
                "status": "processing"
            }
        else:
            # 동기 처리 (순차 실행)
            agent_service = AgentService()
            results = []
            
            for encrypted_id, decrypted_id in decrypted_ids:
                try:
                    result = agent_service.process_email_sync(decrypted_id, current_user.id, db)
                    results.append({
                        "email_id": encrypted_id,
                        "success": result.get("success", False),
                        "completed_nodes": result.get("completed_nodes", []),
                        "errors": result.get("errors", []),
                        "summary": result.get("summary"),
                        "importance_level": result.get("importance_level"),
                    })
                except Exception as e:
                    logger.error(f"Error processing email {decrypted_id}: {e}")
                    results.append({
                        "email_id": encrypted_id,
                        "success": False,
                        "error": str(e)
                    })
            
            success_count = sum(1 for r in results if r.get("success", False))
            
            return {
                "success": True,
                "message": f"Processed {len(results)} emails",
                "results": results,
                "total": len(results),
                "success_count": success_count,
                "failed_count": len(results) - success_count,
                "status": "completed"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process emails: {str(e)}")


@router.post("/run")
async def run_agent(
    email_id: Optional[str] = Query(None, description="Encrypted email ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run LangGraph agent pipeline (deprecated, use /process instead).
    
    This endpoint is kept for backward compatibility.
    """
    if not email_id:
        raise HTTPException(status_code=400, detail="email_id is required")
    
    # Redirect to new endpoint
    return await process_email(email_id=email_id, async_mode=False, db=db, current_user=current_user)
