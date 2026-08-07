from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from Chatbot.builder import graph  

llm = ChatOpenAI(model="gpt-5.4-mini")

class SessionSummaryResult(BaseModel):
    summary: str = Field(
        description="이번 대화 세션에서 확인된 부작용/증상 내용과 위험성 판단을 종합한 요약문"
    )
    keyword: str = Field(
        description="확인된 증상을 쉼표로 구분한 키워드 목록 (예: '불면증, 심계항진, 발한')"
    )
    severity: Literal["낮음", "중간", "높음"] = Field(
        description="지금까지 확인된 내용을 근거로 판단한 위험도"
    )



# 체크포인터에서 thread_id의 최종 State를 읽어 LLM으로 요약 및 저장
def summarize_and_save_session(
    patient_db_conn,
    thread_id: str,
    patient_id: str,
    chat_session_id: int,
    prescription_id: int | None,
) -> SessionSummaryResult | None:
    summary_llm = llm.with_structured_output(SessionSummaryResult)

    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    state_values = snapshot.values

    if not state_values or not state_values.get("messages"):
        return None

    prompt = f"""
    # Context
    - 환자 기본정보: {state_values.get("patient_info")}
    - 전체 대화 이력: {state_values.get("messages")}
    - 문진 응답 내역: {state_values.get("checked_symptoms")}
    - 조회된 부작용 정보: {state_values.get("medicine_side_effect")}
    - 복용 후 경과 시간: {state_values.get("hours_since_dose")}시간

    # Role
    당신은 약물 부작용 상담 세션 내용을 정리해 symptom_log에 저장하는 어시스턴트다.

    # Task
    위 세션 내용을 근거로 summary, keyword, severity를 산출한다.
    summary에는 환자가 어떤 증상을 언제부터 겪었는지, 관련 약은 무엇인지가 드러나도록 작성한다.
    """

    result = summary_llm.invoke(prompt)

    cur = patient_db_conn.cursor()
    cur.execute(
        """
        INSERT INTO symptom_log (
            patient_id,
            chat_session_id,
            prescription_id,
            summary,
            keyword,
            severity,
            reported_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            patient_id,
            chat_session_id,
            prescription_id,
            result.summary,
            result.keyword,
            result.severity,
            datetime.now(),
        ),
    )
    patient_db_conn.commit()

    return result

###############################



# summarize_and_save_session(
#     patient_db_conn=patient_db_conn,
#     thread_id=thread_id,
#     patient_id=patient_id,
#     chat_session_id=chat_session_id,
#     prescription_id=prescription_id,
# )
