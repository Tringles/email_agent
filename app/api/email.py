"""Email API endpoints."""

from loguru import logger
from typing import Optional
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.user import User
from app.db.session import get_db
from app.core.security import get_current_user
from app.tasks.providers.factory import get_email_provider
from app.db.repositories.email_repo import EmailRepository
from app.tasks.email_tasks import fetch_emails_for_account
from app.services.storage_service import get_storage_service
from app.db.repositories.email_account_repo import EmailAccountRepository
from app.core.id_encryption import encrypt_email_id, decrypt_email_id, encrypt_account_id, decrypt_account_id

router = APIRouter(prefix="/api/v1/email", tags=["email"])


@router.get("")
async def get_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    is_important: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None, description="Encrypted account ID"),
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
        # Decrypt account_id if provided
        decrypted_account_id = None
        if account_id:
            try:
                decrypted_account_id = decrypt_account_id(account_id)
            except ValueError as e:
                logger.warning(f"Invalid encrypted account_id: {e}")
                raise HTTPException(status_code=400, detail="Invalid account ID")

        email_repo = EmailRepository(db)
        emails, total = email_repo.get_emails(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            status=status,
            is_read=is_read,
            is_important=is_important,
            search=search,
            account_id=decrypted_account_id,
        )

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        # Convert Email models to dict
        items = []
        for email in emails:
            # Get provider_type from email_account relationship
            provider_type = email.email_account.provider_type.value if email.email_account else None
            items.append({
                "id": encrypt_email_id(email.id),  # 암호화된 ID
                "email_account_id": encrypt_account_id(email.email_account_id),  # 암호화된 ID
                "provider_type": provider_type,
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


@router.get("/{encrypted_email_id}")
async def get_email(
    encrypted_email_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get email by encrypted ID."""
    try:
        # Decrypt email ID
        try:
            email_id = decrypt_email_id(encrypted_email_id)
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")

        email_repo = EmailRepository(db)
        email = email_repo.get_email_by_id(email_id, current_user.id)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        # Mark email as read when viewing
        if not email.is_read:
            email_repo.mark_as_read(email_id, current_user.id, read=True)

        # Convert Email model to dict
        # Get provider_type from email_account relationship
        provider_type = email.email_account.provider_type.value if email.email_account else None
        return {
            "id": encrypt_email_id(email.id),  # 암호화된 ID
            "email_account_id": encrypt_account_id(email.email_account_id),  # 암호화된 ID
            "provider_type": provider_type,
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
        logger.error(f"Error fetching email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{encrypted_email_id}/read")
async def mark_email_as_read(
    encrypted_email_id: str,
    read: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark email as read/unread."""
    try:
        # Decrypt email ID
        try:
            email_id = decrypt_email_id(encrypted_email_id)
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")

        email_repo = EmailRepository(db)
        email = email_repo.mark_as_read(email_id, current_user.id, read)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        return {"message": f"Email marked as {'read' if read else 'unread'}", "is_read": email.is_read}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking email as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{encrypted_email_id}/important")
async def mark_email_as_important(
    encrypted_email_id: str,
    important: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark email as important/unimportant."""
    try:
        # Decrypt email ID
        try:
            email_id = decrypt_email_id(encrypted_email_id)
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")

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


@router.patch("/{encrypted_email_id}/archive")
async def archive_email(
    encrypted_email_id: str,
    archived: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive/unarchive email."""
    try:
        # Decrypt email ID
        try:
            email_id = decrypt_email_id(encrypted_email_id)
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")

        email_repo = EmailRepository(db)
        email = email_repo.archive_email(email_id, current_user.id, archived)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        return {"message": f"Email {'archived' if archived else 'unarchived'}", "is_archived": email.is_archived}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{encrypted_email_id}")
async def delete_email(
    encrypted_email_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete email from provider and soft delete in database.
    Raw MIME files in storage are preserved.
    """
    try:        
        # Decrypt email ID
        try:
            email_id = decrypt_email_id(encrypted_email_id)
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")

        email_repo = EmailRepository(db)
        email = email_repo.get_email_by_id(email_id, current_user.id)
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Delete email from provider (Gmail/Naver)
        try:
            account_repo = EmailAccountRepository(db)
            account = account_repo.get_account_by_id(email.email_account_id)
            
            if account and account.is_active:
                provider = get_email_provider(
                    account.provider_type.value,
                    account.credentials
                )
                
                # Connect and delete from provider
                connected = await provider.connect()
                if connected:
                    deleted = await provider.delete_email(email.provider_message_id)
                    await provider.disconnect()
                    
                    if deleted:
                        logger.info(f"Deleted email {email_id} from {account.provider_type.value}")
                    else:
                        logger.warning(f"Failed to delete email {email_id} from {account.provider_type.value}")
                else:
                    logger.warning(f"Failed to connect to {account.provider_type.value} for deletion")
        except Exception as provider_error:
            # Log error but continue with soft delete
            logger.warning(f"Error deleting email from provider: {provider_error}")

        # Soft delete email in database
        deleted = email_repo.delete_email(email_id, current_user.id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Email not found")

        return {"message": "Email deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def trigger_email_ingest(
    account_id: Optional[str] = Query(None, description="Encrypted account ID to sync (optional, syncs all if not provided)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger email ingestion manually.
    Syncs emails for all active accounts of the current user, or a specific account if account_id is provided.
    """
    try:
        account_repo = EmailAccountRepository(db)
        
        if account_id:
            # Decrypt account ID
            try:
                decrypted_account_id = decrypt_account_id(account_id)
            except ValueError as e:
                logger.warning(f"Invalid encrypted account_id: {e}")
                raise HTTPException(status_code=400, detail="Invalid account ID")
            
            # Sync specific account
            account = account_repo.get_account_by_id(decrypted_account_id)
            if not account:
                raise HTTPException(status_code=404, detail="Email account not found")
            
            # Verify account belongs to current user
            if account.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied to this account")
            
            if not account.is_active:
                raise HTTPException(status_code=400, detail="Email account is not active")
            
            # Trigger Celery task (use decrypted account_id for internal task)
            task_result = fetch_emails_for_account.delay(decrypted_account_id)
            
            return {
                "message": "Email sync triggered",
                "account_id": account_id,  # Return encrypted ID
                "account_email": account.email_address,
                "task_id": task_result.id,
            }
        else:
            # Sync all active accounts for current user
            accounts = account_repo.get_active_accounts(user_id=current_user.id)
            
            if not accounts:
                return {
                    "message": "No active email accounts found",
                    "triggered_count": 0,
                    "accounts": []
                }
            
            triggered_accounts = []
            for account in accounts:
                # Trigger Celery task for each account (use decrypted account_id for internal task)
                task_result = fetch_emails_for_account.delay(account.id)
                triggered_accounts.append({
                    "account_id": encrypt_account_id(account.id),  # Return encrypted ID
                    "account_email": account.email_address,
                    "task_id": task_result.id,
                })
            
            return {
                "message": "Email sync triggered for all accounts",
                "triggered_count": len(triggered_accounts),
                "accounts": triggered_accounts,
            }
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        error_module = type(e).__module__
        
        # Check if it's a Redis/Celery broker connection error
        is_redis_error = (
            'kombu' in error_module or
            'kombu' in error_str or
            'redis' in error_str or
            'celery' in error_str or
            'amqp' in error_module
        )
        
        if 'connection refused' in error_str and is_redis_error:
            logger.error(f"Redis/Celery broker connection failed: {e}")
            raise HTTPException(
                status_code=503,
                detail="Redis/Celery broker is not available. Please ensure Redis is running."
            )
        elif 'connection refused' in error_str:
            logger.error(f"Connection refused error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable: {str(e)}"
            )
        else:
            logger.error(f"Error triggering email ingest: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/{encrypted_email_id}/summary")
async def get_email_summary(
    encrypted_email_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get email summary."""
    try:
        # Decrypt email ID
        try:
            email_id = decrypt_email_id(encrypted_email_id)
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")

        email_repo = EmailRepository(db)
        email = email_repo.get_email_by_id(email_id, current_user.id)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        return {
            "email_id": encrypted_email_id,  # Return encrypted ID
            "summary": email.summary or None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching email summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{encrypted_email_id}/attachments/{attachment_index}")
async def download_attachment(
    encrypted_email_id: str,
    attachment_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download an attachment file for an email.
    
    Args:
        encrypted_email_id: Encrypted email ID
        attachment_index: Index of the attachment (0-based)
    """
    try:
        # Decrypt email ID
        try:
            email_id = decrypt_email_id(encrypted_email_id)
        except ValueError as e:
            logger.warning(f"Invalid encrypted email_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid email ID")

        email_repo = EmailRepository(db)
        email = email_repo.get_email_by_id(email_id, current_user.id)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        if not email.has_attachments or not email.attachments:
            raise HTTPException(status_code=404, detail="Email has no attachments")

        # Validate attachment index
        if attachment_index < 0 or attachment_index >= len(email.attachments):
            raise HTTPException(status_code=404, detail="Attachment not found")

        attachment = email.attachments[attachment_index]
        filename = attachment.get("filename", f"attachment_{attachment_index}")
        storage_path = attachment.get("storage_path")

        # If storage_path is not available, try to construct it
        if not storage_path:
            # Fallback: construct path from email metadata
            logger.warning(f"Attachment {attachment_index} for email {email_id} has no storage_path, attempting to construct path")
            # This should not happen if email was fetched correctly, but handle gracefully
            raise HTTPException(
                status_code=404,
                detail="Attachment file not found in storage"
            )

        # Get storage service and download attachment
        storage = get_storage_service()
        
        # Extract index from storage_path or use attachment_index
        # Storage path format: users/{user_id}/emails/{email_id}/attachments/{index}_{filename}
        attachment_data = storage.get_attachment(
            user_id=current_user.id,
            email_id=email_id,
            index=attachment_index,
            filename=filename
        )

        if not attachment_data:
            raise HTTPException(status_code=404, detail="Attachment file not found in storage")

        # Get content type from attachment metadata
        content_type = attachment.get("mime_type", "application/octet-stream")

        # Return file as streaming response
        return StreamingResponse(
            iter([attachment_data]),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(attachment_data))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading attachment {attachment_index} for email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
