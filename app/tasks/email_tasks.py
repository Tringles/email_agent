"""Celery tasks for email fetching and processing."""

import asyncio
from loguru import logger
from typing import Optional
from celery import shared_task
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models.email import Email, EmailStatus
from app.tasks.providers.base import EmailMessage
from app.tasks.providers.factory import get_email_provider
from app.db.repositories.email_repo import EmailRepository
from app.db.repositories.email_account_repo import EmailAccountRepository


@shared_task(name="fetch_emails_task")
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
        db = SessionLocal()
        try:
            email_repo = EmailRepository(db)

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

                # Convert EmailMessage to DB model and save
                attachments = email_msg.attachments or []
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
                    "raw_mime_storage_path": None,  # TODO: Save to S3/MinIO
                    "status": EmailStatus.PENDING,
                    "is_processed": False,
                }
                email_repo.create_email(email_data)
                saved_count += 1

            db.commit()
            logger.info(
                f"Saved {saved_count} new emails, skipped {skipped_count} duplicates "
                f"for account {account_id}"
            )
        except Exception as e:
            db.rollback()
            logger.error(
                f"Error saving emails to DB for account {account_id}: {e}")
            raise e
        finally:
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


@shared_task(name="fetch_emails_for_account")
def fetch_emails_for_account(account_id: int):
    """
    Celery task to fetch emails for a specific account.
    Fetches account credentials from DB and calls fetch_emails_task.

    Args:
        account_id: Email account ID

    Returns:
        Result dictionary with fetch status
    """
    db = SessionLocal()
    try:
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

    except Exception as e:
        logger.exception(
            f"Error in fetch_emails_for_account for account {account_id}: {e}")
        try:
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
        db.close()


@shared_task(name="fetch_all_accounts_emails")
def fetch_all_accounts_emails():
    """
    Scheduled Celery task to fetch emails for all active accounts.
    This should be called periodically (e.g., every 5 minutes).
    """
    db = SessionLocal()
    try:
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

    except Exception as e:
        logger.exception(f"Error in fetch_all_accounts_emails: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()
