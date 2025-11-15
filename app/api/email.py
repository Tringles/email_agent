"""Email API endpoints."""

from loguru import logger
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.user import User
from app.db.session import get_db
from app.core.security import get_current_user
from app.db.repositories.email_repo import EmailRepository

router = APIRouter(prefix="/api/v1/email", tags=["email"])


@router.get("")
async def get_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    is_important: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    account_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get emails with pagination and filtering.

    Query Parameters:
        page: Page number (default: 1)
        page_size: Items per page (default: 20, max: 100)
        status: Filter by status (pending, processing, processed, failed)
        is_read: Filter by read status
        is_important: Filter by important status
        search: Search in subject, sender, recipient, body
        account_id: Filter by email account ID
    """
    try:
        email_repo = EmailRepository(db)
        emails, total = email_repo.get_emails(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            status=status,
            is_read=is_read,
            is_important=is_important,
            search=search,
            account_id=account_id,
        )

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        # Convert Email models to dict
        items = []
        for email in emails:
            items.append({
                "id": email.id,
                "email_account_id": email.email_account_id,
                "subject": email.subject,
                "sender": email.sender,
                "sender_name": email.sender_name,
                "recipient": email.recipient,
                "recipient_name": email.recipient_name,
                "body_text": email.body_text,
                "body_html": email.body_html,
                "preview": email.preview,
                "email_date": email.email_date.isoformat() if email.email_date else None,
                "received_date": email.received_date.isoformat() if email.received_date else None,
                "status": email.status.value if email.status else None,
                "is_read": email.is_read,
                "is_important": email.is_important,
                "is_archived": email.is_archived,
                "is_deleted": email.is_deleted,
                "is_processed": email.is_processed,
                "has_attachments": email.has_attachments,
                "attachment_count": email.attachment_count,
                "attachments": email.attachments or [],
                "summary": email.summary,
                "importance_level": email.importance_level.value if email.importance_level else None,
                "importance_score": email.importance_score,
                "classification": email.classification,
                "sentiment": email.sentiment,
                "created_at": email.created_at.isoformat() if email.created_at else None,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{email_id}")
async def get_email(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get email by ID."""
    try:
        email_repo = EmailRepository(db)
        email = email_repo.get_email_by_id(email_id, current_user.id)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        # Convert Email model to dict
        return {
            "id": email.id,
            "email_account_id": email.email_account_id,
            "provider_message_id": email.provider_message_id,
            "provider_thread_id": email.provider_thread_id,
            "subject": email.subject,
            "sender": email.sender,
            "sender_name": email.sender_name,
            "recipient": email.recipient,
            "recipient_name": email.recipient_name,
            "cc": email.cc,
            "bcc": email.bcc,
            "reply_to": email.reply_to,
            "body_text": email.body_text,
            "body_html": email.body_html,
            "preview": email.preview,
            "email_date": email.email_date.isoformat() if email.email_date else None,
            "received_date": email.received_date.isoformat() if email.received_date else None,
            "folder": email.folder,
            "labels": email.labels,
            "attachments": email.attachments or [],
            "attachment_count": email.attachment_count,
            "has_attachments": email.has_attachments,
            "status": email.status.value if email.status else None,
            "is_read": email.is_read,
            "is_important": email.is_important,
            "is_archived": email.is_archived,
            "is_deleted": email.is_deleted,
            "is_starred": email.is_starred,
            "is_processed": email.is_processed,
            "processed_at": email.processed_at.isoformat() if email.processed_at else None,
            "summary": email.summary,
            "importance_score": email.importance_score,
            "importance_level": email.importance_level.value if email.importance_level else None,
            "classification": email.classification,
            "sentiment": email.sentiment,
            "rule_applied": email.rule_applied,
            "auto_action": email.auto_action,
            "headers": email.headers,
            "provider_metadata": email.provider_metadata,
            "created_at": email.created_at.isoformat() if email.created_at else None,
            "updated_at": email.updated_at.isoformat() if email.updated_at else None,
            "fetched_at": email.fetched_at.isoformat() if email.fetched_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{email_id}/read")
async def mark_email_as_read(
    email_id: int,
    read: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark email as read/unread."""
    try:
        email_repo = EmailRepository(db)
        email = email_repo.mark_as_read(email_id, current_user.id, read)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        return {"message": f"Email marked as {'read' if read else 'unread'}", "is_read": email.is_read}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking email {email_id} as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{email_id}/important")
async def mark_email_as_important(
    email_id: int,
    important: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark email as important/unimportant."""
    try:
        email_repo = EmailRepository(db)
        email = email_repo.mark_as_important(email_id, current_user.id, important)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        return {"message": f"Email marked as {'important' if important else 'unimportant'}", "is_important": email.is_important}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking email {email_id} as important: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{email_id}/archive")
async def archive_email(
    email_id: int,
    archived: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive/unarchive email."""
    try:
        email_repo = EmailRepository(db)
        email = email_repo.archive_email(email_id, current_user.id, archived)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        return {"message": f"Email {'archived' if archived else 'unarchived'}", "is_archived": email.is_archived}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{email_id}")
async def delete_email(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete email (soft delete)."""
    try:
        email_repo = EmailRepository(db)
        deleted = email_repo.delete_email(email_id, current_user.id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Email not found")

        return {"message": "Email deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        email_repo = EmailRepository(db)
        email = email_repo.get_email_by_id(email_id, current_user.id)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        return {
            "email_id": email_id,
            "summary": email.summary or None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching email summary {email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
