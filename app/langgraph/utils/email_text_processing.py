"""이메일 본문 텍스트 처리 유틸리티."""

import re
import tiktoken

from loguru import logger
from typing import Optional


def remove_quoted_text(text: str) -> str:
    """
    이메일 인용문 및 이전 대화 제거
    
    Args:
        text: 원본 텍스트
        
    Returns:
        인용문이 제거된 텍스트
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    result = []
    in_quote = False
    quote_started = False
    
    # 인용문 시작 패턴
    quote_indicators = [
        '-----Original Message-----',
        '-----원본 메시지-----',
        'From:',
        'Sent:',
        'To:',
        'Subject:',
        '제목:',
        '보낸 사람:',
        '받는 사람:',
        'On ',  # "On 2024-01-01, ... wrote:"
        '작성일:',
    ]
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # 인용문 시작 감지
        if not in_quote:
            # 인용문 표시로 시작하는 줄
            if line_stripped.startswith('>'):
                in_quote = True
                quote_started = True
                continue
            
            # 인용문 시작 패턴 감지
            for indicator in quote_indicators:
                if indicator in line_stripped:
                    # 다음 줄이 인용문 표시('>')로 시작하면 인용문 시작
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('>'):
                        in_quote = True
                        quote_started = True
                        break
                    # 또는 "On ... wrote:" 같은 패턴
                    if 'wrote:' in line_stripped.lower() or '작성:' in line_stripped:
                        in_quote = True
                        quote_started = True
                        break
            
            if in_quote:
                continue
        
        # 인용문 내부 처리
        if in_quote:
            # 인용문 표시가 있으면 계속 인용문
            if line_stripped.startswith('>'):
                continue
            
            # 빈 줄이 2개 연속이면 인용문 종료로 간주
            if not line_stripped:
                if result and not result[-1].strip():
                    in_quote = False
                    quote_started = False
                    continue
            
            # 인용문이 시작되었는데 일반 텍스트가 나오면 종료
            if quote_started and not line_stripped.startswith('>'):
                # 다음 줄도 인용문 표시가 없으면 인용문 종료
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('>'):
                    in_quote = False
                    quote_started = False
        
        # 인용문이 아닌 경우만 추가
        if not in_quote:
            result.append(line)
    
    return '\n'.join(result)


def truncate_by_tokens(
    text: str,
    max_tokens: int,
    model: str = "gpt-4o-mini"
) -> str:
    """
    토큰 수 기준으로 텍스트 잘라내기 (앞뒤 보존)
    
    Args:
        text: 원본 텍스트
        max_tokens: 최대 토큰 수
        model: 사용할 모델명 (tiktoken 인코딩 결정용)
        
    Returns:
        잘라낸 텍스트
    """
    if not text:
        return ""
    
    try:
        # 모델별 인코딩 가져오기 (gpt-5-nano는 아직 없을 수 있으므로 fallback)
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # gpt-5-nano가 없으면 gpt-4o-mini 사용
            logger.warning(f"Model {model} not found in tiktoken, using gpt-4o-mini encoding")
            encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        
        tokens = encoding.encode(text)
        
        # 토큰 수가 제한 이하면 그대로 반환
        if len(tokens) <= max_tokens:
            return text
        
        # 앞부분 60%, 뒷부분 40% 보존
        front_tokens = int(max_tokens * 0.6)
        back_tokens = max_tokens - front_tokens
        
        front_text = encoding.decode(tokens[:front_tokens])
        back_text = encoding.decode(tokens[-back_tokens:])
        
        return f"{front_text}\n\n[... 중간 생략 ...]\n\n{back_text}"
        
    except Exception as e:
        logger.error(f"Error truncating text by tokens: {e}")
        # 에러 발생 시 문자 수 기준으로 fallback
        max_chars = max_tokens * 2  # 대략적인 변환 (토큰당 2자)
        if len(text) <= max_chars:
            return text
        front_chars = int(max_chars * 0.6)
        back_chars = max_chars - front_chars
        return f"{text[:front_chars]}\n\n[... 중간 생략 ...]\n\n{text[-back_chars:]}"


def prepare_email_content_for_llm(
    body_text: str,
    subject: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 8000
) -> str:
    """
    LLM에 전달할 이메일 내용 준비 (개선 버전)
    
    Args:
        body_text: 이메일 본문
        subject: 이메일 제목
        model: 사용할 모델명
        max_tokens: 최대 토큰 수
        
    Returns:
        전처리된 이메일 내용
    """
    # 1. 인용문 제거
    body_text = remove_quoted_text(body_text)
    
    # 2. 제목과 본문 결합
    email_content = f"제목: {subject}\n\n본문:\n{body_text}"
    
    # 3. 토큰 기반 잘라내기 (앞뒤 보존)
    email_content = truncate_by_tokens(email_content, max_tokens, model)
    
    return email_content

