"""Celery tasks for email fetching and processing."""

from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task
from app.tasks.providers.factory import get_email_provider
from app.tasks.providers.base import EmailMessage
from app.db.repositories.email_repo import EmailRepository
from app.models.email import EmailStatus


@shared_task(name="fetch_emails_task")
def fetch_emails_task(account_id: int, provider_type: str, credentials: dict):
    """
    Celery task to fetch emails for a specific account and save to DB.
    
    Args:
        account_id: User account ID
        provider_type: Email provider type ('gmail', 'naver', etc.)
        credentials: Provider-specific credentials
    """
    # TODO: Get last fetch time from DB
    # For now, fetch emails from last 24 hours
    since = datetime.now() - timedelta(days=1)
    
    try:
        # Get email provider
        provider = get_email_provider(provider_type, credentials)
        
        # Fetch emails (async function needs to be run in async context)
        import asyncio
        emails = asyncio.run(provider.fetch_emails(limit=50, since=since))
        
        # Save to database
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            email_repo = EmailRepository(db)
            
            saved_count = 0
            for email_msg in emails:
                # Convert EmailMessage to DB model and save
                email_data = {
                    "email_account_id": account_id,
                    "provider_message_id": email_msg.message_id,
                    "subject": email_msg.subject,
                    "sender": email_msg.sender,
                    "recipient": email_msg.recipient,
                    "body_text": email_msg.body,
                    "body_html": email_msg.html_body,
                    "email_date": email_msg.date,
                    "raw_mime_storage_path": None,  # TODO: Save to S3/MinIO
                    "status": EmailStatus.PENDING,
                    "is_processed": False,
                }
                email_repo.create_email(email_data)
                saved_count += 1
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
        
        # Disconnect provider
        asyncio.run(provider.disconnect())
        
        return {
            "account_id": account_id,
            "fetched_count": len(emails),
            "saved_count": saved_count,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "account_id": account_id,
            "status": "error",
            "error": str(e)
        }


@shared_task(name="fetch_emails_for_account")
def fetch_emails_for_account(account_id: int):
    """
    Celery task to fetch emails for a specific account.
    Fetches account credentials from DB and calls fetch_emails_task.
    
    Args:
        account_id: User account ID
    """
    # TODO: Get account credentials from DB
    # For now, this is a placeholder
    # account = get_account_from_db(account_id)
    # return fetch_emails_task.delay(
    #     account_id=account_id,
    #     provider_type=account.provider_type,
    #     credentials=account.credentials
    # )
    pass


@shared_task(name="fetch_all_accounts_emails")
def fetch_all_accounts_emails():
    """
    Scheduled Celery task to fetch emails for all active accounts.
    This should be called periodically (e.g., every 5 minutes).
    """
    # TODO: Get all active accounts from DB
    # For each account, call fetch_emails_for_account.delay(account.id)
    pass

