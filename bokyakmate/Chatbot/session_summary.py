"""
세션 종료 시(명시적 종료 API 또는 타임아웃 스캐너에서) 호출되는 별도 그래프/모듈.
체크포인터에 쌓인 State를 읽어 LLM으로 요약한 뒤 장기메모리(side_effect_log 테이블)에 저장.
"""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from bokyakmate.Chatbot.builder import graph  # 메인 문진 그래프의 checkpointer를 그대로 재사용

llm = ChatOpenAI(model="gpt-5.4-mini")

class SessionSummaryResult(BaseModel):
    summary: str = Field(
        description="이번 대화 세션에서 확인된 부작용/증상 내용과 위험성 판단을 종합한 요약문"
    )
    symptom_keyword: str = Field(
        description="확인된 증상을 쉼표로 구분한 키워드 목록 (예: '불면증, 심계항진, 발한')"
    )
    severity: Literal["낮음", "중간", "높음"] = Field(
        description="지금까지 확인된 내용을 근거로 판단한 위험도"
    )



# 체크포인터에서 thread_id의 최종 State를 읽어 LLM으로 요약.
def summarize_session(thread_id: str) -> SessionSummaryResult | None:

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
    당신은 약물 부작용 상담 세션 내용을 정리해 장기 기록(side_effect_log)으로 남기는 어시스턴트다.

    # Task
    위 세션 내용을 근거로 summary, symptom_keyword, severity를 산출한다.
    summary에는 환자가 어떤 증상을 언제부터 겪었는지, 관련 약은 무엇인지가 드러나도록 작성한다.
    """
    return summary_llm.invoke(prompt)


def save_session_summary(
    patient_db_conn,
    patient_id: str,
    chat_session_id: int,
    medication_log_id: int | None,
    result: SessionSummaryResult,
) -> None:
    cur = patient_db_conn.cursor()
    cur.execute(
        """
        INSERT INTO side_effect_log
            (patient_id, chat_session_id, medication_log_id, summary, symptom_keyword, reported_at, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_id,
            chat_session_id,
            medication_log_id,
            result.summary,
            result.symptom_keyword,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            result.severity,
        ),
    )

def close_chat_session(patient_db_conn, chat_session_id: int) -> None:
    cur = patient_db_conn.cursor()
    cur.execute(
        "UPDATE chat_session SET ended_at = ? WHERE chat_session_id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), chat_session_id),
    )
    

def end_session_and_summarize(
    thread_id: str,
    patient_db_conn,
    patient_id: str,
    chat_session_id: int,
    medication_log_id: int | None = None,
    close_session: bool = True,
):
    """close_session=True(기본값, session_end 트리거): 저장 + chat_session 닫기(ended_at 기록).
    close_session=False(symptom_segment 트리거): 저장만 하고 chat_session은 유지 - 대화가 계속됨."""
    result = summarize_session(thread_id)
    if result is None:
        return None

    try:
        save_session_summary(patient_db_conn, patient_id, chat_session_id, medication_log_id, result)
        if close_session:
            close_chat_session(patient_db_conn, chat_session_id)
        patient_db_conn.commit()
    except Exception:
        patient_db_conn.rollback()
        raise

    return result


def handle_end_signal(
    thread_id: str,
    result_state: dict,
    patient_db_conn,
    patient_id: str,
    chat_session_id: int,
) -> SessionSummaryResult | None:
    """graph.invoke() 결과를 그대로 넘기면 end_signal 여부를 보고 저장까지 처리한다.
    end_signal이 없으면 아무것도 안 하고 None을 반환한다.

    처리 후에는 end_signal/checked_symptoms/medicine_side_effect를 체크포인터에서
    직접 초기화한다(graph.update_state - 노드 실행 없이 State만 패치) - 다음 턴부터
    end_signal이 계속 "symptom_segment"로 남아 매 턴 재저장되는 걸 차단.
    """
    signal = result_state.get("end_signal")
    if not signal:
        return None

    medication_log = result_state.get("medication_log") or {}
    medication_log_id = medication_log.get("medication_log_id")

    result = end_session_and_summarize(
        thread_id=thread_id,
        patient_db_conn=patient_db_conn,
        patient_id=patient_id,
        chat_session_id=chat_session_id,
        medication_log_id=medication_log_id,
        close_session=(signal == "session_end"),
    )

    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, {
        "end_signal": None,
        "checked_symptoms": [],
        "medicine_side_effect": None,
    })

    return result