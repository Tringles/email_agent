"""Vector Search Node."""

import uuid

from loguru import logger
from qdrant_client import QdrantClient
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client.models import Distance, VectorParams
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.langgraph.state import EmailProcessingState

# Qdrant 컬렉션 이름
COLLECTION_NAME = "emails"


def vector_search_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    임베딩 생성, VectorDB 저장 (메타데이터 포함), 유사 이메일 검색

    Args:
        state: EmailProcessingState

    Returns:
        업데이트된 EmailProcessingState
    """
    try:
        logger.info(f"Vector searching for email {state['email_id']}")

        # VectorDB 설정 확인
        if not settings.VECTOR_DB_URL:
            logger.warning("VECTOR_DB_URL not set, skipping vector search")
            state["vector_db_id"] = None
            state["embedding_model"] = None
            state["similar_emails"] = None
            state["vector_metadata"] = None
            state["current_node"] = "vector_search"
            state["completed_nodes"].append("vector_search")
            return state

        # OpenAI API 키 확인
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set, skipping vector search")
            state["vector_db_id"] = None
            state["embedding_model"] = None
            state["similar_emails"] = None
            state["vector_metadata"] = None
            state["current_node"] = "vector_search"
            state["completed_nodes"].append("vector_search")
            return state

        # 텍스트 준비 (임베딩용)
        text_for_embedding = _prepare_text_for_embedding(state)

        if not text_for_embedding:
            logger.warning(
                f"No text available for embedding email {state['email_id']}")
            state["vector_db_id"] = None
            state["embedding_model"] = None
            state["similar_emails"] = None
            state["vector_metadata"] = None
            state["current_node"] = "vector_search"
            state["completed_nodes"].append("vector_search")
            return state

        # 메타데이터 준비
        vector_metadata = _prepare_metadata(state)

        # 임베딩 모델 초기화
        embedding_model = "text-embedding-3-small"
        embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=settings.OPENAI_API_KEY
        )

        # Qdrant 클라이언트 및 벡터 스토어 초기화
        qdrant_client = _get_qdrant_client()
        vector_store = _get_or_create_vector_store(qdrant_client, embeddings)

        # 문서 ID 생성
        doc_id = str(uuid.uuid4())

        # 벡터 저장
        vector_store.add_texts(
            texts=[text_for_embedding],
            metadatas=[vector_metadata],
            ids=[doc_id]
        )

        logger.info(
            f"Vector stored for email {state['email_id']} with ID: {doc_id}")

        # 유사 이메일 검색 (같은 사용자의 다른 이메일만)
        similar_emails = _search_similar_emails(
            vector_store=vector_store,
            query_text=text_for_embedding,
            user_id=state["user_id"],
            current_email_id=state["email_id"],
            limit=5
        )

        state["vector_db_id"] = doc_id
        state["embedding_model"] = embedding_model
        state["similar_emails"] = similar_emails
        state["vector_metadata"] = vector_metadata

        state["current_node"] = "vector_search"
        state["completed_nodes"].append("vector_search")

        logger.info(
            f"Vector search completed for email {state['email_id']}: "
            f"found {len(similar_emails)} similar emails"
        )

    except Exception as e:
        logger.error(
            f"Error in vector search for email {state['email_id']}: {e}", exc_info=True)
        # VectorDB 실패해도 다음 노드로 진행 (선택적 기능)
        state["vector_db_id"] = None
        state["embedding_model"] = None
        state["similar_emails"] = None
        state["vector_metadata"] = None
        state["errors"].append({
            "node": "vector_search",
            "error": str(e),
            "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
        })
        state["current_node"] = "vector_search"
        state["completed_nodes"].append("vector_search")

    return state


def _prepare_text_for_embedding(state: EmailProcessingState) -> str:
    """
    임베딩용 텍스트 준비

    Args:
        state: EmailProcessingState

    Returns:
        임베딩용 텍스트
    """
    parts = []

    # 요약 추가
    summary = state.get("summary")
    if summary:
        parts.append(f"요약: {summary}")

    # 본문 추가 (processed_body_html 우선)
    body = state.get("processed_body_html") or state["email_data"].get(
        "body_text", "")
    if body:
        # 너무 긴 본문은 잘라서 처리
        max_body_length = 2000
        if len(body) > max_body_length:
            body = body[:max_body_length] + "..."
        parts.append(f"본문: {body}")

    # 첨부파일 이름 추가
    attachment_names = state["email_data"].get("attachment_names", [])
    if attachment_names:
        parts.append(f"첨부파일: {', '.join(attachment_names)}")

    return "\n\n".join(parts)


def _prepare_metadata(state: EmailProcessingState) -> Dict[str, Any]:
    """
    VectorDB에 저장할 메타데이터 준비

    Args:
        state: EmailProcessingState

    Returns:
        메타데이터 딕셔너리
    """
    email_data = state["email_data"]

    metadata = {
        # 기본 정보
        "email_id": state["email_id"],
        "user_id": state["user_id"],
        "subject": email_data.get("subject", ""),
        "sender": email_data.get("sender", ""),
        "recipient": email_data.get("recipient", ""),
        "email_date": email_data.get("email_date", ""),
        "folder": email_data.get("folder", ""),

        # 분류 정보
        "importance_level": state.get("importance_level", ""),
        "classification": str(state.get("classification", {})),
        "labels": str(email_data.get("labels", [])),

        # 첨부파일
        "attachment_count": email_data.get("attachment_count", 0),
        "has_attachments": email_data.get("has_attachments", False),
        "attachment_names": str(email_data.get("attachment_names", [])),

        # 기타
        "cc": str(email_data.get("cc", [])),
        "bcc": str(email_data.get("bcc", [])),
        "reply_to": email_data.get("reply_to", ""),
    }

    # Qdrant는 문자열 키와 값만 지원하므로 모든 값을 문자열로 변환
    return {k: str(v) if v is not None else "" for k, v in metadata.items()}


def _get_qdrant_client() -> QdrantClient:
    """
    Qdrant 클라이언트 생성

    Returns:
        QdrantClient 인스턴스
    """
    url = settings.VECTOR_DB_URL
    api_key = settings.VECTOR_DB_API_KEY

    if api_key:
        return QdrantClient(url=url, api_key=api_key)
    else:
        return QdrantClient(url=url)


def _get_or_create_vector_store(
    qdrant_client: QdrantClient,
    embeddings: OpenAIEmbeddings
) -> QdrantVectorStore:
    """
    Qdrant 벡터 스토어 가져오기 또는 생성

    Args:
        qdrant_client: QdrantClient 인스턴스
        embeddings: Embeddings 인스턴스

    Returns:
        Qdrant 벡터 스토어
    """
    # 컬렉션이 존재하는지 확인
    try:
        collections = qdrant_client.get_collections()
        collection_exists = any(
            c.name == COLLECTION_NAME for c in collections.collections)

        if not collection_exists:
            # 컬렉션 생성
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=1536,  # text-embedding-3-small의 차원
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
    except Exception as e:
        logger.warning(f"Error checking/creating collection: {e}")

    # 벡터 스토어 생성 (QdrantVectorStore 사용)
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings
    )

    return vector_store


def _search_similar_emails(
    vector_store: QdrantVectorStore,
    query_text: str,
    user_id: int,
    current_email_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    유사 이메일 검색

    Args:
        vector_store: Qdrant 벡터 스토어
        query_text: 검색 쿼리 텍스트
        user_id: 사용자 ID (같은 사용자의 이메일만 검색)
        current_email_id: 현재 이메일 ID (자기 자신 제외)
        limit: 최대 결과 수

    Returns:
        유사 이메일 목록
    """
    try:
        # 필터: 같은 사용자의 이메일만, 현재 이메일 제외

        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="user_id", match=MatchValue(value=str(user_id)))
            ],
            must_not=[
                FieldCondition(key="email_id", match=MatchValue(
                    value=str(current_email_id)))
            ]
        )

        # 유사도 검색 (QdrantVectorStore는 filter 파라미터 사용)
        results = vector_store.similarity_search_with_score(
            query=query_text,
            k=limit,
            filter=filter_condition  # QdrantVectorStore는 filter 파라미터 사용
        )

        # 결과 포맷팅
        similar_emails = []
        for doc, score in results:
            similar_emails.append({
                "email_id": doc.metadata.get("email_id", ""),
                "subject": doc.metadata.get("subject", ""),
                "sender": doc.metadata.get("sender", ""),
                "similarity_score": float(score),
                "importance_level": doc.metadata.get("importance_level", ""),
            })

        return similar_emails

    except Exception as e:
        logger.error(f"Error searching similar emails: {e}")
        return []
