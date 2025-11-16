"""Agent Service - LangGraph 실행 래퍼."""

from loguru import logger
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.models.email import EmailStatus
from app.db.repositories.email_repo import EmailRepository
from app.langgraph.graph import create_email_processing_graph
from app.langgraph.state import EmailProcessingState, initialize_state


class AgentService:
    """AI Agent 서비스 - LangGraph 파이프라인 실행"""
    
    def __init__(self):
        """Agent Service 초기화"""
        self.graph = None
        self._initialize_graph()
    
    def _initialize_graph(self):
        """그래프 초기화 (싱글톤 패턴)"""
        if self.graph is None:
            logger.info("Initializing email processing graph")
            self.graph = create_email_processing_graph()
            logger.info("Email processing graph initialized")
    
    async def process_email(
        self,
        email_id: int,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        이메일을 AI Agent로 처리
        
        Args:
            email_id: 처리할 이메일 ID
            user_id: 사용자 ID
            db: SQLAlchemy 세션
            
        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"Starting email processing: email_id={email_id}, user_id={user_id}")
            
            # 처리 시작 시 status를 'processing'으로 업데이트
            email_repo = EmailRepository(db)
            email = email_repo.get_email_by_id(email_id, user_id)
            if email:
                email_repo.update_email(email, status=EmailStatus.PROCESSING)
                db.commit()
                logger.info(f"Updated email {email_id} status to PROCESSING")
            
            # State 초기화 (기본 구조만 생성, 이메일 데이터는 load_email_node에서 로드)
            initial_state = initialize_state(email_id, user_id)
            
            # 그래프 실행
            config = {"configurable": {"thread_id": f"email_{email_id}"}}
            final_state = await self.graph.ainvoke(initial_state, config)
            
            logger.info(
                f"Email processing completed: email_id={email_id}, "
                f"completed_nodes={final_state.get('completed_nodes', [])}"
            )
            
            # 결과 반환
            return {
                "success": True,
                "email_id": email_id,
                "completed_nodes": final_state.get("completed_nodes", []),
                "errors": final_state.get("errors", []),
                "summary": final_state.get("summary"),
                "importance_level": final_state.get("importance_level"),
                "classification": final_state.get("classification"),
            }
            
        except Exception as e:
            logger.error(f"Error processing email {email_id}: {e}", exc_info=True)
            
            # 에러 발생 시 status를 'failed'로 업데이트
            try:
                email_repo = EmailRepository(db)
                email = email_repo.get_email_by_id(email_id, user_id)
                if email:
                    email_repo.update_email(email, status=EmailStatus.FAILED)
                    db.commit()
                    logger.info(f"Updated email {email_id} status to FAILED due to error")
            except Exception as update_error:
                logger.error(f"Failed to update email status to FAILED: {update_error}")
            
            return {
                "success": False,
                "email_id": email_id,
                "error": str(e),
            }
    
    def process_email_sync(
        self,
        email_id: int,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        이메일을 AI Agent로 처리 (동기 버전 - Celery task용)
        
        주의: 이 메서드는 Celery task에서만 사용해야 합니다.
        FastAPI async 엔드포인트에서는 process_email()을 직접 await하세요.
        
        Args:
            email_id: 처리할 이메일 ID
            user_id: 사용자 ID
            db: SQLAlchemy 세션
            
        Returns:
            처리 결과 딕셔너리
        """
        import asyncio
        
        try:
            # Celery task는 별도의 프로세스에서 실행되므로 새로운 이벤트 루프 생성 가능
            # uvloop는 FastAPI에서만 사용되므로, Celery worker에서는 일반 asyncio 사용
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 실행 중인 루프가 있는 경우 (드물지만 가능)
                    # 새로운 스레드에서 실행
                    import concurrent.futures
                    def run_in_new_loop():
                        return asyncio.run(self.process_email(email_id, user_id, db))
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_new_loop)
                        return future.result()
                else:
                    return loop.run_until_complete(
                        self.process_email(email_id, user_id, db)
                    )
            except RuntimeError:
                # 이벤트 루프가 없는 경우 새로 생성
                return asyncio.run(self.process_email(email_id, user_id, db))
        except Exception as e:
            logger.error(f"Error in process_email_sync: {e}", exc_info=True)
            raise
