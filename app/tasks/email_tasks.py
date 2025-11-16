"""Celery tasks for email fetching and processing."""

import asyncio
from loguru import logger
from typing import Optional
from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError

from app.db.session import SessionLocal
from app.core.celery_app import celery_app
from app.models.email import Email, EmailStatus
from app.services.agent_service import AgentService
from app.tasks.providers.factory import get_email_provider
from app.db.repositories.email_repo import EmailRepository
from app.services.storage_service import get_storage_service
from app.db.repositories.email_account_repo import EmailAccountRepository


@shared_task(name="fetch_emails_task", app=celery_app)
def fetch_emails_task(account_id: int, provider_type: str, credentials: dict, since: Optional[datetime] = None):
    """
    Celery task to fetch emails for a specific account and save to DB.

    Args:
        account_id: Email account ID
        provider_type: Email provider type ('gmail', 'naver', etc.)
        credentials: Provider-specific credentials
        since: Fetch emails since this datetime (optional)
    """
    # If since not provided, default to last 24 hours
    if since is None:
        since = datetime.now() - timedelta(days=1)

    try:
        # Get email provider
        provider = get_email_provider(provider_type, credentials)

        # Fetch emails (async function needs to be run in async context)
        emails = asyncio.run(provider.fetch_emails(limit=50, since=since))

        # Save to database
        db = None
        try:
            db = SessionLocal()
            email_repo = EmailRepository(db)
            account_repo = EmailAccountRepository(db)
            storage = get_storage_service()

            # Get account to retrieve user_id
            account = account_repo.get_account_by_id(account_id)
            if not account:
                raise ValueError(f"Email account {account_id} not found")
            
            user_id = account.user_id

            saved_count = 0
            skipped_count = 0

            for email_msg in emails:
                # Check if email already exists (by provider_message_id)
                existing = db.query(Email).filter(
                    Email.email_account_id == account_id,
                    Email.provider_message_id == email_msg.message_id
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Save raw MIME to MinIO if available
                raw_mime_storage_path = None
                if email_msg.raw_mime:
                    try:
                        # Encode raw_mime to bytes if it's a string
                        if isinstance(email_msg.raw_mime, str):
                            raw_mime_bytes = email_msg.raw_mime.encode('utf-8')
                        else:
                            raw_mime_bytes = email_msg.raw_mime
                        
                        # We'll get email_id after creating the email record
                        # For now, use a temporary path and update later
                        pass
                    except Exception as e:
                        logger.warning(f"Failed to prepare raw MIME for storage: {e}")

                # Convert EmailMessage to DB model and save
                attachments = email_msg.attachments or []
                
                # Create email record first to get email_id
                email_data = {
                    "email_account_id": account_id,
                    "provider_message_id": email_msg.message_id,
                    "subject": email_msg.subject or "",
                    "sender": email_msg.sender or "",
                    "recipient": email_msg.recipient or "",
                    "body_text": email_msg.body or "",
                    "body_html": email_msg.html_body,
                    "email_date": email_msg.date or datetime.now(),
                    "attachments": attachments,
                    "attachment_count": len(attachments),
                    "has_attachments": len(attachments) > 0,
                    "raw_mime_storage_path": None,  # Will be updated after saving
                    "status": EmailStatus.PENDING,
                    "is_processed": False,
                }
                email = email_repo.create_email(email_data)
                email_id = email.id
                
                # Save raw MIME to MinIO
                if email_msg.raw_mime:
                    try:
                        if isinstance(email_msg.raw_mime, str):
                            raw_mime_bytes = email_msg.raw_mime.encode('utf-8')
                        else:
                            raw_mime_bytes = email_msg.raw_mime
                        
                        raw_mime_path = storage.save_raw_mime(
                            user_id=user_id,
                            email_id=email_id,
                            mime_data=raw_mime_bytes
                        )
                        if raw_mime_path:
                            email.raw_mime_storage_path = raw_mime_path
                            email.raw_mime_size = len(raw_mime_bytes)
                            logger.debug(f"Saved raw MIME to {raw_mime_path}")
                    except Exception as e:
                        logger.error(f"Failed to save raw MIME to storage: {e}")

                # Save attachments to MinIO
                updated_attachments = []
                for idx, attachment in enumerate(attachments):
                    try:
                        attachment_data = None
                        
                        # Download attachment data based on provider
                        if provider_type == "gmail":
                            # Gmail: download using attachment_id
                            attachment_id = attachment.get("attachment_id")
                            if attachment_id:
                                attachment_data = asyncio.run(
                                    provider.download_attachment(
                                        email_msg.message_id,
                                        attachment_id
                                    )
                                )
                        elif provider_type == "naver":
                            # Naver: attachment data is already in the attachment dict
                            attachment_data = attachment.get("data")
                            if attachment_data:
                                filename = attachment.get("filename", f"attachment_{idx}")
                                mime_type = attachment.get("mime_type")
                                
                                storage_path = storage.save_attachment(
                                    user_id=user_id,
                                    email_id=email_id,
                                    index=idx,
                                    filename=filename,
                                    attachment_data=attachment_data,
                                    content_type=mime_type
                                )
                                
                                if storage_path:
                                    # Update attachment metadata with storage path
                                    updated_attachment = attachment.copy()
                                    updated_attachment["storage_path"] = storage_path
                                    updated_attachment["index"] = idx
                                    # Remove data from metadata (already stored in MinIO)
                                    updated_attachment.pop("data", None)
                                    updated_attachments.append(updated_attachment)
                                    logger.debug(f"Saved Naver attachment {filename} to {storage_path}")
                                else:
                                    updated_attachments.append(attachment)
                            else:
                                updated_attachments.append(attachment)
                            continue
                        
                        if attachment_data:
                            filename = attachment.get("filename", f"attachment_{idx}")
                            mime_type = attachment.get("mime_type")
                            
                            storage_path = storage.save_attachment(
                                user_id=user_id,
                                email_id=email_id,
                                index=idx,
                                filename=filename,
                                attachment_data=attachment_data,
                                content_type=mime_type
                            )
                            
                            if storage_path:
                                # Update attachment metadata with storage path
                                updated_attachment = attachment.copy()
                                updated_attachment["storage_path"] = storage_path
                                updated_attachment["index"] = idx
                                updated_attachments.append(updated_attachment)
                                logger.debug(f"Saved attachment {filename} to {storage_path}")
                            else:
                                updated_attachments.append(attachment)
                        else:
                            # Keep original attachment metadata even if download failed
                            updated_attachments.append(attachment)
                    except Exception as e:
                        logger.error(f"Failed to save attachment {idx} to storage: {e}")
                        # Keep original attachment metadata
                        updated_attachments.append(attachment)
                
                # Update email with attachment storage paths
                if updated_attachments != attachments:
                    email.attachments = updated_attachments
                
                db.commit()
                saved_count += 1

            logger.info(
                f"Saved {saved_count} new emails, skipped {skipped_count} duplicates "
                f"for account {account_id}"
            )
        except OperationalError as e:
            error_str = str(e).lower()
            if 'connection refused' in error_str or 'can\'t connect' in error_str:
                logger.error(
                    f"Database connection failed for account {account_id}: {e}. "
                    f"Please ensure MySQL is running."
                )
            if db:
                db.rollback()
            raise e
        except Exception as e:
            if db:
                db.rollback()
            logger.error(
                f"Error saving emails to DB for account {account_id}: {e}")
            raise e
        finally:
            if db:
                db.close()

        # Disconnect provider
        asyncio.run(provider.disconnect())

        return {
            "account_id": account_id,
            "fetched_count": len(emails),
            "saved_count": saved_count,
            "skipped_count": skipped_count,
            "status": "success"
        }

    except Exception as e:
        return {
            "account_id": account_id,
            "status": "error",
            "error": str(e)
        }


@shared_task(name="fetch_emails_for_account", app=celery_app)
def fetch_emails_for_account(account_id: int):
    """
    Celery task to fetch emails for a specific account.
    Fetches account credentials from DB and calls fetch_emails_task.

    Args:
        account_id: Email account ID

    Returns:
        Result dictionary with fetch status
    """
    db = None
    try:
        db = SessionLocal()
        # Get email account from DB
        account_repo = EmailAccountRepository(db)
        account = account_repo.get_account_by_id(account_id)

        if not account:
            error_msg = f"Email account {account_id} not found"
            logger.error(error_msg)
            return {
                "account_id": account_id,
                "status": "error",
                "error": error_msg
            }

        if not account.is_active:
            error_msg = f"Email account {account_id} is not active"
            logger.warning(error_msg)
            return {
                "account_id": account_id,
                "status": "skipped",
                "error": error_msg
            }

        # Convert credentials format for Gmail provider
        # Gmail provider expects credentials in format compatible with Credentials.from_authorized_user_info
        credentials = account.credentials.copy()

        # Don't convert expiry - Gmail provider will handle it
        # Keep expiry as string (ISO format) or datetime as stored in DB

        # Determine since date (last fetch or default)
        since = None
        if account.last_fetch_at:
            since = account.last_fetch_at
        else:
            # First fetch: get last 7 days
            since = datetime.now() - timedelta(days=7)

        # Call fetch_emails_task with account info
        result = fetch_emails_task(
            account_id=account_id,
            provider_type=account.provider_type.value,
            credentials=credentials,
            since=since
        )

        # Update last_fetch_at based on result
        if result.get("status") == "success":
            account_repo.update_last_fetch(account_id, success=True)
            logger.info(
                f"Successfully fetched {result.get('saved_count', 0)} emails "
                f"for account {account_id} ({account.email_address})"
            )
        else:
            error_msg = result.get("error", "Unknown error")
            account_repo.update_last_fetch(
                account_id, success=False, error_message=error_msg)
            logger.error(
                f"Failed to fetch emails for account {account_id} ({account.email_address}): {error_msg}"
            )

        return result

    except OperationalError as e:
        error_str = str(e).lower()
        if 'connection refused' in error_str or 'can\'t connect' in error_str:
            logger.error(
                f"Database connection failed for account {account_id}: {e}. "
                f"Please ensure MySQL is running."
            )
        logger.exception(
            f"Error in fetch_emails_for_account for account {account_id}: {e}")
        try:
            if db:
                account_repo = EmailAccountRepository(db)
                account_repo.update_last_fetch(
                    account_id, success=False, error_message=str(e))
        except:
            pass

        return {
            "account_id": account_id,
            "status": "error",
            "error": f"Database connection failed: {str(e)}"
        }
    except Exception as e:
        logger.exception(
            f"Error in fetch_emails_for_account for account {account_id}: {e}")
        try:
            if db:
                account_repo = EmailAccountRepository(db)
                account_repo.update_last_fetch(
                    account_id, success=False, error_message=str(e))
        except:
            pass

        return {
            "account_id": account_id,
            "status": "error",
            "error": str(e)
        }
    finally:
        if db:
            db.close()


@shared_task(name="fetch_all_accounts_emails", app=celery_app)
def fetch_all_accounts_emails():
    """
    Scheduled Celery task to fetch emails for all active accounts.
    This should be called periodically (e.g., every 5 minutes).
    """
    db = None
    try:
        db = SessionLocal()
        account_repo = EmailAccountRepository(db)
        active_accounts = account_repo.get_active_accounts()

        results = []
        for account in active_accounts:
            # Check if it's time to fetch (based on fetch_interval)
            if account.last_fetch_at:
                time_since_last_fetch = (
                    datetime.now() - account.last_fetch_at).total_seconds()
                if time_since_last_fetch < account.fetch_interval:
                    logger.debug(
                        f"Skipping account {account.id} - "
                        f"last fetch was {time_since_last_fetch:.0f}s ago "
                        f"(interval: {account.fetch_interval}s)"
                    )
                    continue

            # Trigger async task for each account
            result = fetch_emails_for_account.delay(account.id)
            results.append({
                "account_id": account.id,
                "email": account.email_address,
                "task_id": result.id
            })
            logger.info(
                f"Triggered email fetch for account {account.id} ({account.email_address})")

        return {
            "status": "success",
            "triggered_count": len(results),
            "accounts": results
        }

    except OperationalError as e:
        error_str = str(e).lower()
        if 'connection refused' in error_str or 'can\'t connect' in error_str:
            logger.error(
                f"Database connection failed: {e}. "
                f"Please ensure MySQL is running."
            )
        logger.exception(f"Error in fetch_all_accounts_emails: {e}")
        return {
            "status": "error",
            "error": f"Database connection failed: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Error in fetch_all_accounts_emails: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        if db:
            db.close()


@shared_task(name="process_email_agent_task", app=celery_app)
def process_email_agent_task(email_id: int, user_id: int):
    """
    Celery task to process a single email with LangGraph AI Agent.
    
    Args:
        email_id: Email ID to process
        user_id: User ID (owner of the email)
        
    Returns:
        Result dictionary with processing status
    """
    db = None
    try:
        db = SessionLocal()
        agent_service = AgentService()
        
        # LangGraph 실행 (동기 버전 사용)
        result = agent_service.process_email_sync(email_id, user_id, db)
        
        logger.info(
            f"Email {email_id} processed: success={result.get('success')}, "
            f"nodes={result.get('completed_nodes', [])}"
        )
        
        return result
        
    except OperationalError as e:
        error_str = str(e).lower()
        if 'connection refused' in error_str or 'can\'t connect' in error_str:
            logger.error(
                f"Database connection failed for email {email_id}: {e}. "
                f"Please ensure MySQL is running."
            )
        logger.exception(f"Error processing email {email_id} with agent: {e}")
        return {
            "success": False,
            "email_id": email_id,
            "error": f"Database connection failed: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Error processing email {email_id} with agent: {e}")
        return {
            "success": False,
            "email_id": email_id,
            "error": str(e)
        }
    finally:
        if db:
            db.close()


@shared_task(name="process_pending_emails_task", app=celery_app)
def process_pending_emails_task(limit: int = 50):
    """
    Celery task to process pending emails with LangGraph AI Agent.
    Processes emails with status PENDING that haven't been processed yet.
    
    Args:
        limit: Maximum number of emails to process in one run
        
    Returns:
        Result dictionary with processing status
    """
    db = None
    try:
        db = SessionLocal()
        email_repo = EmailRepository(db)
        
        # PENDING 상태이고 아직 처리되지 않은 이메일 조회
        pending_emails = db.query(Email).filter(
            Email.status == EmailStatus.PENDING,
            Email.is_processed == False
        ).limit(limit).all()
        
        if not pending_emails:
            logger.debug("No pending emails to process")
            return {
                "status": "success",
                "processed_count": 0,
                "emails": []
            }
        
        logger.info(f"Processing {len(pending_emails)} pending emails")
        
        agent_service = AgentService()
        results = []
        
        for email in pending_emails:
            try:
                user_id = email.email_account.user_id
                
                # LangGraph 실행
                result = agent_service.process_email_sync(email.id, user_id, db)
                
                results.append({
                    "email_id": email.id,
                    "success": result.get("success", False),
                    "completed_nodes": result.get("completed_nodes", []),
                    "errors": result.get("errors", []),
                })
                
                logger.info(
                    f"Email {email.id} processed: success={result.get('success')}"
                )
                
            except Exception as e:
                logger.error(f"Error processing email {email.id}: {e}", exc_info=True)
                results.append({
                    "email_id": email.id,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r.get("success", False))
        
        logger.info(
            f"Processed {len(results)} emails: {success_count} successful, "
            f"{len(results) - success_count} failed"
        )
        
        return {
            "status": "success",
            "processed_count": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "emails": results
        }
        
    except OperationalError as e:
        error_str = str(e).lower()
        if 'connection refused' in error_str or 'can\'t connect' in error_str:
            logger.error(
                f"Database connection failed: {e}. "
                f"Please ensure MySQL is running."
            )
        logger.exception(f"Error in process_pending_emails_task: {e}")
        return {
            "status": "error",
            "error": f"Database connection failed: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Error in process_pending_emails_task: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        if db:
            db.close()
