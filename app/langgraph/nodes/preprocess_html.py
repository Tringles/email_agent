"""Preprocess HTML Node."""

import re
import html

from loguru import logger
from typing import Optional

from app.langgraph.state import EmailProcessingState
from app.langgraph.utils.error_handler import handle_node_error
from app.langgraph.utils.state_validator import validate_state_for_node
from app.langgraph.utils.email_text_processing import remove_quoted_text


def preprocess_html_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    HTML 본문을 요약에 용이한 순수 텍스트로 전처리
    
    Args:
        state: EmailProcessingState
        
    Returns:
        업데이트된 EmailProcessingState
    """
    try:
        logger.info(f"Preprocessing HTML for email {state['email_id']}")
        
        # 상태 검증
        validation = validate_state_for_node(state, "preprocess_html")
        if not validation["valid"]:
            logger.warning(f"State validation failed for preprocess_html node: {validation['errors']}")
            # 필수 필드가 없으면 에러 발생
            if validation["errors"]:
                raise ValueError(f"State validation failed: {', '.join(validation['errors'])}")
        
        body_html = state["email_data"].get("body_html")
        body_text = state["email_data"].get("body_text", "")
        
        if body_html:
            # HTML 전처리
            processed = _preprocess_html(body_html)
            processed = remove_quoted_text(processed)
            # 중복 개행 압축 (최종 정리)
            processed = re.sub(r'\n{2,}', '\n', processed)
            state["processed_body_html"] = processed
        elif body_text:
            # HTML이 없으면 body_text 사용
            processed = remove_quoted_text(body_text)
            # 중복 개행 압축
            processed = re.sub(r'\n{2,}', '\n', processed)
            state["processed_body_html"] = processed
        else:
            state["processed_body_html"] = ""
        
        state["current_node"] = "preprocess_html"
        state["completed_nodes"].append("preprocess_html")
        
        logger.info(f"HTML preprocessing completed for email {state['email_id']}")
        
    except Exception as e:
        # 공통 에러 처리 (에러 발생 시 원본 body_text 사용)
        fallback_text = state["email_data"].get("body_text", "") if state.get("email_data") else ""
        handle_node_error(
            state=state,
            node_name="preprocess_html",
            error=e,
            default_values={"processed_body_html": fallback_text},
            continue_on_error=True
        )
    
    return state


def _preprocess_html(html_content: str) -> str:
    """
    HTML을 순수 텍스트로 변환
    
    Args:
        html_content: HTML 문자열
        
    Returns:
        전처리된 텍스트
    """
    if not html_content:
        return ""
    
    # 1. <script> 태그 제거
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. <style> 태그 제거
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 3. HTML 주석 제거
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    
    # 4. 이미지 alt 텍스트 추출
    def replace_img(match):
        alt_text = match.group(1) or ""
        return f"[이미지: {alt_text}]" if alt_text else "[이미지]"
    
    html_content = re.sub(r'<img[^>]*alt=["\']([^"\']*)["\'][^>]*>', replace_img, html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<img[^>]*>', '[이미지]', html_content, flags=re.IGNORECASE)
    
    # 5. 링크 URL 추출
    def replace_link(match):
        url = match.group(1) or ""
        text = match.group(2) or url
        return f"{text} ({url})" if url != text else text
    
    html_content = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', replace_link, html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 6. 블록 요소를 줄바꿈으로 변환
    html_content = re.sub(r'</(p|div|h[1-6]|li|br|tr)[^>]*>', '\n', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<(p|div|h[1-6]|li|br|tr)[^>]*>', '\n', html_content, flags=re.IGNORECASE)
    
    # 7. 모든 HTML 태그 제거
    html_content = re.sub(r'<[^>]+>', '', html_content)
    
    # 8. HTML 엔티티 디코딩
    html_content = html.unescape(html_content)
    
    # 9. 불필요한 공백/줄바꿈 정리
    # 연속된 공백을 하나로
    html_content = re.sub(r' +', ' ', html_content)
    # 연속된 줄바꿈을 하나로 압축 (2개 이상의 개행을 1개로)
    html_content = re.sub(r'\n{2,}', '\n', html_content)
    # 줄 앞뒤 공백 제거
    lines = [line.strip() for line in html_content.split('\n')]
    html_content = '\n'.join(lines)
    
    # 10. 최종 정리 (빈 줄 제거 후 다시 개행 정리)
    html_content = html_content.strip()
    # 빈 줄 제거 후 다시 중복 개행 압축
    html_content = re.sub(r'\n{2,}', '\n', html_content)
    
    return html_content
