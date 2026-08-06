from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
import logging
from Chatbot.builder import build_graph, build_initial_state

logger = logging.getLogger(__name__)

class SessionSummary(BaseModel):
    summary_title: str = Field(description="20자 이내의 상담 제목")
    summary_detail: str = Field(description="상담 내용을 4~8줄 정도로 요약")

summary_llm = ChatOpenAI(
    model="gpt-5.5",
    temperature=0
).with_structured_output(SessionSummary)


def generate_chat_summary(messages: list) -> SessionSummary:
    """
    LangGraph messages를 받아
    ChatSession에 저장할 title/detail을 생성한다.
    """

    conversation = []

    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("type", "")
            content = msg.get("content", "")
        else:
            role = msg.type
            content = msg.content

        speaker = "환자" if role == "human" else "AI"
        conversation.append(f"{speaker}: {content}")

    conversation_text = "\n".join(conversation)

    prompt = f"""
    당신은 정신건강의학과 복약 상담 기록을 정리하는 AI입니다.

    다음 상담 내용을 보고
    반드시 JSON 형태로만 출력하세요.

    규칙
    - 새로운 정보를 만들지 않는다.
    - 제목은 20자 이내
    - 제목은 상담의 핵심만 표현
    - 요약은 4~8줄
    - 객관적인 상담기록처럼 작성
    - AI의 권고사항도 포함

    상담 내용

    {conversation_text}
    """

    return summary_llm.invoke(prompt)


# --- 3. 장고 뷰(View)에서 호출할 안전망 함수 ---
def process_chat_summary(session_id: str) -> tuple[str, str]:
    """
    LangGraph 상태를 가져와 요약을 실행하고, 실패 시 안전한 기본값을 반환합니다.
    """
    try:
        graph = build_graph()
        config = {"configurable": {"thread_id": str(session_id)}}
        state = graph.get_state(config)
        messages = state.values.get("messages", [])
        
        if not messages:
            return "상담 내용 없음", "요약할 대화 기록이 존재하지 않습니다."

        # 질문자님의 핵심 함수 호출!
        summary_result = generate_chat_summary(messages)
        
        return summary_result.summary_title, summary_result.summary_detail

    except Exception as e:
        logger.error(f"Failed to generate summary for session {session_id}: {e}")
        return "요약 생성 실패", "서버 오류로 요약을 생성하지 못했습니다."