"""Agent Service - LangGraph 실행 래퍼."""

from loguru import logger
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

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
            
            # 사용자 권한 확인 (이메일이 해당 사용자의 것인지 확인)
            from app.db.repositories.email_repo import EmailRepository
            email_repo = EmailRepository(db)
            email = email_repo.get_email_by_id(email_id)
            
            if not email:
                raise ValueError(f"Email {email_id} not found")
            
            # 이메일 계정이 해당 사용자의 것인지 확인
            if email.email_account.user_id != user_id:
                raise PermissionError(f"Email {email_id} does not belong to user {user_id}")
            
            # State 초기화
            initial_state = initialize_state(email_id, user_id, db)
            
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
        이메일을 AI Agent로 처리 (동기 버전)
        
        Args:
            email_id: 처리할 이메일 ID
            user_id: 사용자 ID
            db: SQLAlchemy 세션
            
        Returns:
            처리 결과 딕셔너리
        """
        import asyncio
        
        try:
            # 이미 이벤트 루프가 실행 중인 경우
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 새로운 태스크로 실행
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(
                    self.process_email(email_id, user_id, db)
                )
            else:
                return loop.run_until_complete(
                    self.process_email(email_id, user_id, db)
                )
        except RuntimeError:
            # 이벤트 루프가 없는 경우 새로 생성
            return asyncio.run(self.process_email(email_id, user_id, db))
