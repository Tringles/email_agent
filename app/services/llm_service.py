"""LLM Service - OpenAI LLM 관리."""

import time
from pathlib import Path
from loguru import logger
from langchain_openai import ChatOpenAI
from typing import Optional, Dict, Any, List
from langchain.messages import SystemMessage, HumanMessage, AIMessage

from app.core.config import settings
from app.langgraph.utils.error_handler import is_retryable_error


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
        # temperature 처리: kwargs에 있으면 사용, 없으면 self.temperature, 둘 다 없으면 기본값 0.3
        temperature = kwargs.get("temperature")
        if temperature is None:
            temperature = self.temperature if self.temperature is not None else 0.3
        
        llm_params = {
            "model": self.model,
            "temperature": temperature,
        }
        
        # OpenAI API 키 설정 (LangChain은 api_key 파라미터 사용)
        if settings.OPENAI_API_KEY:
            llm_params["api_key"] = settings.OPENAI_API_KEY
        elif "api_key" in kwargs:
            llm_params["api_key"] = kwargs["api_key"]
        
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
        
        # 나머지 파라미터는 제외 (temperature, max_tokens, model_kwargs, response_format, operation_name, api_key)
        # operation_name은 로깅용이므로 LLM에 전달하지 않음
        # api_key는 이미 위에서 처리했으므로 제외
        excluded_keys = {"temperature", "max_tokens", "model_kwargs", "response_format", "operation_name", "api_key"}
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
    
    def invoke_with_messages(
        self,
        system_prompt: str,
        human_content: str,
        **llm_kwargs
    ) -> str:
        """
        LangChain 1.0 메시지 시스템을 사용하여 LLM 호출
        
        Args:
            system_prompt: 시스템 프롬프트
            human_content: Human 메시지 내용
            **llm_kwargs: LLM 추가 파라미터
            
        Returns:
            LLM 응답 텍스트 (AIMessage.content)
        """
        operation_name = llm_kwargs.get("operation_name", "LLM invoke")
        
        # LangChain 1.0 메시지 객체 생성
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_content)
        ]
        
        # LLM 호출 (재시도 가능한 에러에 대해서만 재시도)
        try:
            llm = self.get_llm(**llm_kwargs)
            
            # 재시도 가능한 에러에 대해서만 재시도
            max_retries = 2
            retry_delay = 1.0
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    response = llm.invoke(messages)
                    break  # 성공 시 루프 종료
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries and is_retryable_error(e):
                        logger.warning(
                            f"[{operation_name}] Retryable error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {retry_delay:.2f}s..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                    else:
                        # 재시도 불가능하거나 최대 재시도 횟수 초과
                        logger.error(f"[{operation_name}] Error invoking LLM: {e}", exc_info=True)
                        raise
            
        except Exception as e:
            logger.error(f"[{operation_name}] Error invoking LLM after retries: {e}", exc_info=True)
            raise
        
        # Output 추출
        output_content = None
        if hasattr(response, 'content'):
            output_content = response.content
            if output_content is None:
                output_content = ""
            elif isinstance(output_content, str):
                output_content = output_content.strip()
            elif isinstance(output_content, list):
                # 멀티모달 콘텐츠인 경우 텍스트만 추출
                text_parts = []
                for item in output_content:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif hasattr(item, 'text'):
                        text_parts.append(str(item.text))
                    elif hasattr(item, 'content'):
                        text_parts.append(str(item.content))
                    else:
                        text_parts.append(str(item))
                output_content = " ".join(text_parts).strip()
            else:
                output_content = str(output_content).strip()
        elif hasattr(response, 'text'):
            output_content = str(response.text).strip()
        else:
            logger.error(f"[{operation_name}] Cannot extract content from response")
            output_content = ""
        
        # 토큰 사용량 로깅
        self._log_token_usage(response, operation_name)
        
        return output_content
    
    def invoke(
        self,
        system_prompt_name: str,
        human_content: str,
        system_prompt_override: Optional[str] = None,
        system_prompt_vars: Optional[Dict[str, Any]] = None,
        **llm_kwargs
    ) -> str:
        """
        시스템 프롬프트 파일을 로드하여 LLM 호출 (편의 메서드)
        
        Args:
            system_prompt_name: 시스템 프롬프트 파일명
            human_content: Human 메시지 내용
            system_prompt_override: 시스템 프롬프트 오버라이드 (파일 대신 직접 제공)
            system_prompt_vars: 시스템 프롬프트 변수 (예: {"max_length": 500})
            **llm_kwargs: LLM 추가 파라미터
            
        Returns:
            LLM 응답 텍스트
        """
        if system_prompt_override:
            system_prompt = system_prompt_override
        else:
            system_prompt = self.load_system_prompt(system_prompt_name)
        
        # 프롬프트 변수 포맷팅
        # 프롬프트에 {변수명} 형식이 있으면 변수를 전달해야 함
        if "{max_length}" in system_prompt or (system_prompt_vars and any(f"{{{key}}}" in system_prompt for key in system_prompt_vars)):
            # 기본값 설정
            default_vars = {"max_length": 500}
            # 전달된 변수와 기본값 병합 (전달된 변수가 우선)
            vars_to_use = {**default_vars, **(system_prompt_vars or {})}
            try:
                system_prompt = system_prompt.format(**vars_to_use)
            except KeyError as e:
                logger.warning(f"Missing prompt variable: {e}, using original prompt")
        
        return self.invoke_with_messages(
            system_prompt=system_prompt,
            human_content=human_content,
            **llm_kwargs
        )
    
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

