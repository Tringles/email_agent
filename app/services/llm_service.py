"""LLM Service - OpenAI LLM 관리."""

from loguru import logger
from pathlib import Path
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings


class LLMService:
    """OpenAI LLM 서비스 클래스"""
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ):
        """
        LLM 서비스 초기화
        
        Args:
            model: 사용할 모델명 (기본값: gpt-4o-mini)
            temperature: 모델 temperature (기본값: 0.3)
            max_tokens: 최대 토큰 수
        """
        self.model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set, LLM service may not work")
    
    def get_llm(self, **kwargs) -> ChatOpenAI:
        """
        ChatOpenAI 인스턴스 생성
        
        Args:
            **kwargs: 추가 ChatOpenAI 파라미터
                - temperature: 모델 temperature
                - max_tokens: 최대 토큰 수
                - model_kwargs: 모델별 추가 파라미터 (예: response_format)
            
        Returns:
            ChatOpenAI 인스턴스
        """
        llm_params = {
            "model": self.model,
            "temperature": kwargs.get("temperature", self.temperature),
        }
        
        if self.max_tokens:
            llm_params["max_tokens"] = self.max_tokens
        elif "max_tokens" in kwargs:
            llm_params["max_tokens"] = kwargs["max_tokens"]
        
        # model_kwargs 처리 (LangChain 1.0에서 response_format 등은 model_kwargs로 전달)
        if "model_kwargs" in kwargs:
            llm_params["model_kwargs"] = kwargs["model_kwargs"]
        elif "response_format" in kwargs:
            # response_format이 직접 전달된 경우 model_kwargs로 변환
            llm_params["model_kwargs"] = {"response_format": kwargs["response_format"]}
        
        # 나머지 파라미터는 제외 (temperature, max_tokens, model_kwargs, response_format)
        excluded_keys = {"temperature", "max_tokens", "model_kwargs", "response_format"}
        for k, v in kwargs.items():
            if k not in excluded_keys:
                llm_params[k] = v
        
        return ChatOpenAI(**llm_params)
    
    def load_system_prompt(self, prompt_name: str) -> str:
        """
        시스템 프롬프트 파일 로드
        
        Args:
            prompt_name: 프롬프트 파일명 (예: "summarize_system", "classify_system")
            
        Returns:
            프롬프트 내용
        """
        # 프로젝트 루트 경로 찾기
        project_root = Path(__file__).parent.parent.parent
        prompts_dir = project_root / "app" / "prompts"
        prompt_file = prompts_dir / f"{prompt_name}.txt"
        
        if not prompt_file.exists():
            logger.warning(f"Prompt file not found: {prompt_file}, using default")
            return ""
        
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            logger.debug(f"Loaded system prompt from: {prompt_file}")
            return content
        except Exception as e:
            logger.error(f"Error loading prompt file {prompt_file}: {e}")
            return ""
    
    def create_prompt_template(
        self,
        system_prompt_name: str,
        human_template: str,
        system_prompt_override: Optional[str] = None
    ) -> ChatPromptTemplate:
        """
        프롬프트 템플릿 생성
        
        Args:
            system_prompt_name: 시스템 프롬프트 파일명
            human_template: Human 메시지 템플릿
            system_prompt_override: 시스템 프롬프트 오버라이드 (파일 대신 직접 제공)
            
        Returns:
            ChatPromptTemplate 인스턴스
        """
        if system_prompt_override:
            system_prompt = system_prompt_override
        else:
            system_prompt = self.load_system_prompt(system_prompt_name)
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_template)
        ])
    
    def invoke(
        self,
        prompt_template: ChatPromptTemplate,
        input_variables: Dict[str, Any],
        **llm_kwargs
    ) -> str:
        """
        프롬프트 실행 및 응답 반환
        
        Args:
            prompt_template: ChatPromptTemplate 인스턴스
            input_variables: 프롬프트 변수 딕셔너리
            **llm_kwargs: LLM 추가 파라미터
            
        Returns:
            LLM 응답 텍스트
        """
        llm = self.get_llm(**llm_kwargs)
        chain = prompt_template | llm
        response = chain.invoke(input_variables)
        
        # 토큰 사용량 로깅
        self._log_token_usage(response, llm_kwargs.get("operation_name", "LLM invoke"))
        
        return response.content.strip()
    
    def _log_token_usage(self, response, operation_name: str = "LLM invoke"):
        """
        토큰 사용량 정보를 logger.debug로 로깅
        
        Args:
            response: LLM 응답 객체
            operation_name: 작업 이름 (로깅용)
        """
        try:
            # LangChain 1.0: response_metadata에서 토큰 정보 가져오기
            response_metadata = getattr(response, "response_metadata", {})
            token_usage = response_metadata.get("token_usage", {})
            
            if token_usage:
                prompt_tokens = token_usage.get("prompt_tokens", 0)
                completion_tokens = token_usage.get("completion_tokens", 0)
                total_tokens = token_usage.get("total_tokens", 0)
                
                logger.debug(
                    f"[{operation_name}] Token usage - "
                    f"Prompt: {prompt_tokens}, "
                    f"Completion: {completion_tokens}, "
                    f"Total: {total_tokens}"
                )
            else:
                logger.debug(f"[{operation_name}] Token usage information not available")
        except Exception as e:
            logger.debug(f"[{operation_name}] Error logging token usage: {e}")


# 싱글톤 인스턴스
_default_llm_service: Optional[LLMService] = None


def get_llm_service(
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None
) -> LLMService:
    """
    LLM 서비스 싱글톤 인스턴스 가져오기
    
    Args:
        model: 모델명 (기본값 사용 시 None)
        temperature: temperature (기본값 사용 시 None)
        max_tokens: max_tokens (기본값 사용 시 None)
        
    Returns:
        LLMService 인스턴스
    """
    global _default_llm_service
    
    if _default_llm_service is None:
        _default_llm_service = LLMService(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    return _default_llm_service

