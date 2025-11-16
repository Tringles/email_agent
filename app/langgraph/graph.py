"""LangGraph 그래프 정의."""

from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.langgraph.state import EmailProcessingState
from app.langgraph.nodes.classify import classify_node
from app.langgraph.nodes.summarize import summarize_node
from app.langgraph.nodes.load_email import load_email_node
from app.langgraph.nodes.rule_engine import rule_engine_node
from app.langgraph.nodes.save_results import save_results_node
from app.langgraph.nodes.vector_search import vector_search_node
from app.langgraph.nodes.preprocess_html import preprocess_html_node


def create_email_processing_graph():
    """이메일 처리 그래프 생성 및 컴파일"""
    
    # 그래프 생성
    workflow = StateGraph(EmailProcessingState)
    
    # 노드 추가 (Phase 2에서 구현 예정)
    # 현재는 placeholder 함수 사용
    workflow.add_node("load_email", load_email_node)
    workflow.add_node("preprocess_html", preprocess_html_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("rule_engine", rule_engine_node)
    workflow.add_node("save_results", save_results_node)
    
    # 엣지 정의 (순차 실행)
    workflow.set_entry_point("load_email")
    workflow.add_edge("load_email", "preprocess_html")
    workflow.add_edge("preprocess_html", "summarize")
    workflow.add_edge("summarize", "classify")
    workflow.add_edge("classify", "vector_search")
    workflow.add_edge("vector_search", "rule_engine")
    workflow.add_edge("rule_engine", "save_results")
    workflow.add_edge("save_results", END)
    
    # 체크포인트 설정 (선택적, 재시도/복구용)
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    logger.info("Email processing graph compiled successfully")
    
    return app
