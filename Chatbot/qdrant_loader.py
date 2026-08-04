
import os
import time
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client.models import Filter, FieldCondition, MatchValue

# .env 파일이 있다면 로드
load_dotenv()

QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "medical_docs")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
QDRANT_URL = os.getenv("QDRANT_URL", "http://192.168.0.32:6333")


def load_vectorstore():
    """
    기존에 생성된 Qdrant Vector DB를 불러옵니다.
    """
    embedding = OpenAIEmbeddings(
        model=EMBEDDING_MODEL
    )

    # 기존 컬렉션과 경로를 바라보도록 설정하여 로드
    vectorstore = QdrantVectorStore.from_existing_collection(
        embedding=embedding,
        # path=QDRANT_PATH,
        url=QDRANT_URL,
        collection_name=QDRANT_COLLECTION
    )
    
    return vectorstore


def retriever(query, ingredient_code, section=None, k=3):
    """
    FieldCondition + MatchValue로 구성

    {"page_content": ..., "metadata": {...}} 구조로 저장하기 때문에,
    ingredient_code/section은 metadata 안에 중첩되어 있다.
    """
    must_conditions = [
        FieldCondition(
            key="metadata.ingredient_code",
            match=MatchValue(value=ingredient_code),
        )
    ]

    if section:
        must_conditions.append(
            FieldCondition(
                key="metadata.section",
                match=MatchValue(value=section),
            )
        )

    qdrant_filter = Filter(must=must_conditions)
    vectorstore = load_vectorstore()
    result = vectorstore.similarity_search(
        query=query,
        k=k,
        filter=qdrant_filter,
    )

    return result