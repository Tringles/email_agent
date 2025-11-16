"""Load Email Node - Entry Node."""

from loguru import logger

from app.db.session import SessionLocal
from app.langgraph.state import EmailProcessingState
from app.db.repositories.email_repo import EmailRepository


def load_email_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    Entry Node: 이메일 데이터 로드 및 검증
    
    이 노드는 파이프라인의 진입점으로, DB에서 이메일 데이터를 로드하고
    사용자 권한을 검증합니다.
    
    Args:
        state: EmailProcessingState (기본 구조만 초기화됨)
        
    Returns:
        업데이트된 EmailProcessingState (email_data 포함)
    """
    email_id = state["email_id"]
    user_id = state["user_id"]
    db = None
    
    try:
        logger.info(f"Loading email {email_id} for user {user_id}")
        
        # DB 세션 생성
        db = SessionLocal()
        email_repo = EmailRepository(db)
        
        # 이메일 조회
        email = email_repo.get_email_by_id(email_id)
        
        if not email:
            error_msg = f"Email {email_id} not found"
            logger.error(error_msg)
            state["errors"].append({
                "node": "load_email",
                "error": error_msg,
                "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
            })
            raise ValueError(error_msg)
        
        # 사용자 권한 확인 (이메일 계정이 해당 사용자의 것인지 확인)
        if email.email_account.user_id != user_id:
            error_msg = f"Email {email_id} does not belong to user {user_id}"
            logger.error(error_msg)
            state["errors"].append({
                "node": "load_email",
                "error": error_msg,
                "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
            })
            raise PermissionError(error_msg)
        
        # 이메일 데이터 로드
        state["email_data"] = {
            # 기본 정보
            "subject": email.subject,
            "sender": email.sender,
            "sender_name": email.sender_name,
            "recipient": email.recipient,
            "recipient_name": email.recipient_name,
            # 본문
            "body_text": email.body_text,
            "body_html": email.body_html,
            # 날짜
            "email_date": email.email_date.isoformat() if email.email_date else None,
            "received_date": email.received_date.isoformat() if email.received_date else None,
            # 폴더/라벨
            "folder": email.folder,
            "labels": email.labels,
            # 참조
            "cc": email.cc,
            "bcc": email.bcc,
            "reply_to": email.reply_to,
            # 첨부파일
            "attachments": email.attachments,  # 전체 첨부파일 메타데이터 리스트
            "attachment_count": email.attachment_count,
            "has_attachments": email.has_attachments,
            "attachment_names": [
                att.get("filename", "") for att in (email.attachments or [])
                if att.get("filename")
            ],  # 첨부파일 이름 리스트 (중요도 판별 및 VectorDB 저장용)
            # 기타
            "preview": email.preview,
            "headers": email.headers,
            "provider_metadata": email.provider_metadata,
            "provider_message_id": email.provider_message_id,
            "provider_thread_id": email.provider_thread_id,
        }
        
        state["current_node"] = "load_email"
        state["completed_nodes"].append("load_email")
        
        logger.info(f"Email {email_id} loaded successfully")
        
    except (ValueError, PermissionError):
        # 이미 에러가 state에 추가되었으므로 재발생
        raise
    except Exception as e:
        logger.error(f"Error loading email {email_id}: {e}", exc_info=True)
        state["errors"].append({
            "node": "load_email",
            "error": str(e),
            "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
        })
        raise
    finally:
        # DB 세션 정리
        if db:
            db.close()
    
    return state

