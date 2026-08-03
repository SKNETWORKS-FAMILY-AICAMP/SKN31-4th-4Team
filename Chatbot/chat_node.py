from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, RemoveMessage
from state import State
from qdrant_loader import retriever
from datetime import datetime

llm = ChatOpenAI(model="gpt-5.4-mini")


load_dotenv()


class RouteResult(BaseModel):
    need_medicine: bool = Field(
        description="약에 대한 정보 조회가 필요한지 알려줘"
    )

class FollowupRouteResult(BaseModel):
    need_followup: bool = Field(
        description="사용자의 방금 답변이 여전히 부작용 문진(증상/복용 관련)과 관련이 있는지 알려줘"
    )
    sufficient_info: bool = Field(
        description="지금까지의 대화 내역으로 부작용 문진에 필요한 정보가 충분히 모였다고 판단되면 True"
    )

# boolean값 반환
router_llm = llm.with_structured_output(RouteResult)
followup_router_llm = llm.with_structured_output(FollowupRouteResult, method="function_calling")

# state 확인 후 약정보 조회 노드 및 일반 채팅 노드 분기
def router(state: State):
    if state["need_medicine"]:
        return "medicine_node"
    return "general_chat_node"


# 외부 시스템(타임아웃 스캐너, 앱 종료 감지 등)이 심어주는 신호. 사용자 메시지 없이도 트리거.
def is_system_end_signal(state: State) -> bool:
    return state.get("system_signal") in ("timeout", "disconnect")


# 서버에서 보낸 종료 신호가 있는지 우선 확인 후 분기
def entry_router(state: State):
    if is_system_end_signal(state):
        return "session_end_node"
    if state.get("symptom_followup"):
        return "followup_gate_node"
    return "chat_node"

# 일반 대화로 빠질지, 문진을 이어갈지, 증상 구간 요약으로 넘어갈지 판단.
def followup_router(state: State):
    if state.get("sufficient_info"):
        return "symptom_summary_node"
    if state["symptom_followup"]:
        return "side_effect_followup_node"
    return "general_chat_node"

# 약 정보가 필요한지 판단하는 노드
def chat_node(state: State):
    
    ROUTER_SYSTEM_PROMPT = """
    사용자가 방금 한 말이 다음에 해당하면 need_medicine=True로 판단한다:
    - 복용 중인 약의 부작용, 주의사항, 용법·용량에 대한 새로운 질문
    - 새로운 증상을 보고하거나 기존 증상에 대해 더 설명하는 경우
    - 단순 잡담 으로 보이나 현재 증상에 대해 포함되는 단어가 있을경우.

    다음은 need_medicine=False로 판단한다:
    - 이전 답변 내용을 표/목록 등 다른 형식으로 정리해달라는 요청
    - 단순 인사, 감사 표현, 잡담
    - 약과 무관한 일반 질문
    """

    result = router_llm.invoke(
        [SystemMessage(content=ROUTER_SYSTEM_PROMPT)] + state["messages"]
    )
    return {
        "need_medicine": result.need_medicine,
    }


# 세션 종료 확인 시 안내 메시지를 보내고 마무리하는 노드
def session_end_node(state: State):
    response = llm.invoke(
        "지금까지의 상담을 마무리한다는 짧고 정중한 인사말을 한다. "
        "필요할 경우 증상이 심해지면 병원에 방문하라는 안내를 짧게 덧붙인다."
    )
    return {
        "messages": [response],
        "symptom_followup": False,
        "end_signal": "session_end",
    }


# 문진 구간 종료 
def symptom_summary_node(state: State):
    checked = state["checked_symptoms"]
    closing_prompt = f"""
    지금까지 확인된 내용
    - 문진 응답 내역: {checked}
    복용 중인 약: {state['patient_info'].get('drugs')}
    조회된 부작용 정보: {state['medicine_side_effect']}
    과거 부작용 기록: {state.get("past_side_effect_summaries")}
    
    약물 부작용 분석 어시스턴트로서, 지금까지 확인한 내용을 종합해서 요약 안내한다.
    복용 중인 약이 2개 이상이면, 확인된 증상/부작용을 가능한 한 관련된 약별로 구분해서 요약한다. 특정 약과 명확히 연결 짓기 어려운 내용은 구분 없이 안내한다.
    과거 부작용 기록 중 이번과 관련된 이력(특히 과거 severity)이 있으면 위험성 판단에 참고한다.
    이어서 위 내용을 근거로 병원에 당장 방문해야 하는 수준인지 위험성을 판단해서 안내하고 대화를 마무리한다.
    """
    response = llm.invoke(closing_prompt)
    
    remove_old = [RemoveMessage(id=m.id) for m in state["messages"]]
    
    return {
        "messages": remove_old + [response],
        "checked_symptoms": checked,
        "symptom_followup": False,
        "end_signal": "symptom_segment",
    }


# 여러 턴의 추가 문진 진행 중 사용자의 해당 답변 이탈 여부 및 상태를 파악할 충분한 정보가 필요한지 판단.
def followup_gate_node(state: State):

    FOLLOWUP_ROUTER_SYSTEM_PROMPT = """
    당신은 진행 중인 약물 부작용 문진 대화에서, 사용자의 방금 답변이
    계속 문진을 이어가야 하는 내용인지, 그리고 문진에 필요한 정보가 이미 충분히 모였는지 판단하는 라우터 입니다.

    사용자가 방금 한 말이 다음에 해당하면 need_followup=True로 판단한다:
    - 증상/부작용에 대한 답변을 계속하는 경우
    - 이전 답변 내용을 표/목록 등 다른 형식으로 정리해달라는 요청 (형식 변경 요청은 문진 이탈이 아니다)
    
    다음은 need_followup=False로 판단한다:
    - 문진과 무관한 화제로 전환하는 경우

    sufficient_info는 need_followup 여부와 별개로, 지금까지 오간 대화만으로 증상 양상/경과를 판단하기에
    충분한 정보가 모였다고 볼 수 있으면 True로 판단한다.
    """

    result = followup_router_llm.invoke(
        [SystemMessage(content=FOLLOWUP_ROUTER_SYSTEM_PROMPT)] + state["messages"]
    )
    return {
        "symptom_followup": result.need_followup,
        "sufficient_info": result.sufficient_info,
    }



# 약 복용기록 시간, 증상 입력 시간 차이 비교 후 증상 발생 시간 state추가 함수(medicine_node에서 사용)
def calc_hours_since_dose(medication_log: dict | None) -> float | None:
    if not medication_log or not medication_log.get("taken_at"):
        return None
    taken_at = medication_log["taken_at"]
    taken_dt = datetime.fromisoformat(taken_at)
    now = datetime.now(taken_dt.tzinfo) if taken_dt.tzinfo else datetime.now()
    return round((now - taken_dt).total_seconds() / 3600, 1)


# 약에 대한 처방 갯수 만큼 약 부작용 retriever 호출 노드
def medicine_node(state: State):

    patient_info = state.get("patient_info", {})
    ingredient_codes = patient_info.get("ingredient_codes") or []
    drugs = patient_info.get("drugs") or []

    if not ingredient_codes:
        return {"medicine_side_effect": None}

    last_message = state["messages"][-1].content if state["messages"] else ""
    query = f"부작용 및 주의사항: {last_message}"

    medicine_side_effect = []
    for i, code in enumerate(ingredient_codes):
        side_effect_info = retriever(query=query, ingredient_code=code)
        medicine_side_effect.append({
            "ingredient_code": code,
            "drug": drugs[i] if i < len(drugs) else None,
            "side_effect_info": side_effect_info,
        })

    hours_since_dose = calc_hours_since_dose(state.get("medication_log"))

    return {
        "medicine_side_effect": medicine_side_effect,
        "hours_since_dose": hours_since_dose,
    }


# 약에 대한 정보 조회 후 답변 하는 노드, side_effect_followup_node에서의 첫 질문인지 판단 여부를 위해 checklist_index -1을 설정
def side_effect_node(state: State):
    medicine_side_effect = state.get("medicine_side_effect")
    if not medicine_side_effect:
        return {}

    prompt = f"""
    # Context
    - 전체 대화 이력: {state["messages"]}
    - 복용 중인 약: {state['patient_info'].get('drugs')}
    - 이전에 조회된 부작용 정보: {state["medicine_side_effect"]}
    - 복용 후 경과 시간: {state.get("hours_since_dose")}시간
    - 과거 부작용 기록: {state.get("past_side_effect_summaries")}
    - 환자 정보
        - 이름: {state['patient_info']['name']}
        - 나이: {state['patient_info']['age']}
        - 성별: {state['patient_info']['gender']}
        - 임신 여부: {state['patient_info']['is_pregnant']}

    Role
    당신은 약물 부작용 분석 전문 어시스턴트다.

    Constraints
    "조회된 부작용 정보"에 있는 내용을 근거로 요약과정을 진행한후 판단을 시작한다.
    정보가 없거나 비어있으면 "죄송하지만 다른 증상을 알려 주실 수 있으신가요?"라고만 답한다.
    사용자와 대화를 이어갈 수 있는 느낌으로 부작용을 설명하거나 물어보면서 대답한다.
    약때문인지 다른원인인지에 대한 판단은 하지 않는다. 또 이와 관련된 대답도 하지 않는다.
    복용 중인 약이 2개 이상이면, "이전에 조회된 부작용 정보"의 각 항목이 어떤 약(drug)에 대한 정보인지 명시하며 약별로 구분해서 설명한다.
    "과거 부작용 기록"에 이번 증상과 관련된 내용이 있으면, 과거에도 유사한 증상이 있었다는 점을 자연스럽게 언급한다. 관련 없으면 굳이 언급하지 않는다.
    Output Format
    복용 중인 약: {state['patient_info'].get('drugs')}
    """
    response = llm.invoke(prompt)

    return {
        "messages": [response],
        "checklist_index": -1,      
        "checked_symptoms": [],
        "symptom_followup": True,
    }


# 추가 문진 노드 및 종료시 대화 섹션 삭제
def side_effect_followup_node(state: State):

    MAX_FOLLOWUP_TURNS = 6  # 자유 문진 턴 수 제한

    idx = state["checklist_index"]
    last_user_answer = state["messages"][-1].content

    if idx == -1:
        # side_effect_node의 자유 질문에 대한 첫 답변
        checked = state["checked_symptoms"] + [{"symptom": "일반 증상", "answer": last_user_answer}]
    else:
        checked = state["checked_symptoms"] + [{"symptom": f"추가 문진 {idx + 1}", "answer": last_user_answer}]

    idx += 1
    is_last = idx >= MAX_FOLLOWUP_TURNS

    if is_last:
        closing_prompt = f"""
        지금까지 확인된 내용
        - 문진 응답 내역: {checked}
        복용 중인 약: {state['patient_info'].get('drugs')}
        조회된 부작용 정보: {state['medicine_side_effect']}
        과거 부작용 기록: {state.get("past_side_effect_summaries")}

        약물 부작용 분석 어시스턴트로서, 지금까지 확인한 내용을 종합해서 요약 안내한다.
        복용 중인 약이 2개 이상이면, 확인된 증상/부작용을 가능한 한 관련된 약별로 구분해서 요약한다. 특정 약과 명확히 연결 짓기 어려운 내용은 구분 없이 안내한다.
        과거 부작용 기록 중 이번과 관련된 이력(특히 과거 severity)이 있으면 위험성 판단에 참고한다.
        이어서 위 내용을 근거로 병원에 당장 방문해야 하는 수준인지 위험성을 판단해서 안내하고 대화를 마무리한다.
        """
        response = llm.invoke(closing_prompt)

        remove_old = [RemoveMessage(id=m.id) for m in state["messages"]]

        return {
            "messages": remove_old + [response],
            "checked_symptoms": checked,
            "checklist_index": idx,
            "symptom_followup": False,
            "end_signal": "symptom_segment",
        }

    prompt = f"""
    # Context
    - 전체 대화 이력: {state["messages"]}
    - 복용 중인 약: {state['patient_info'].get('drugs')}
    - 조회된 부작용 정보: {state["medicine_side_effect"]}

    # Role
    당신은 약물 부작용 문진을 돕는 어시스턴트다.

    # Next Step
    사용자의 방금 답변에 자연스럽게 반응한 뒤, 조회된 부작용 정보와 지금까지의 대화 흐름을 참고해서
    부작용 원인 파악에 도움이 될 만한 추가 질문을 자연스럽게 이어서 물어봐줘.

    # Constraints
    1. 인과성에 대한 최종 판단(약 때문인지 아닌지)은 하지 않고 이와 관련된 답변도 하지 않는다.
    2. 이미 물어본 내용은 다시 묻지 않는다.
    3. 복용 중인 약이 2개 이상이면, 필요 시 어떤 약과 관련된 질문인지 명시하며 약별로 구분해서 질문한다.
    """
    response = llm.invoke(prompt)
    return {
        "messages": [response],
        "checked_symptoms": checked,
        "checklist_index": idx,
        "symptom_followup": True,
    }



# 일반 대화 채팅 노드
def general_chat_node(state: State):
    prompt = f"""
    # Context
    - 환자 정보
        - 이름: {state['patient_info']['name']}
        - 나이: {state['patient_info']['age']}
        - 성별: {state['patient_info']['gender']}
        - 임신 여부: {state['patient_info']['is_pregnant']}
        - 복용 중인 약: {state['patient_info'].get('drugs')}
    - 전체 대화 이력: {state["messages"]}
    - 과거 부작용 기록: {state.get("past_side_effect_summaries")}

    # Role
    당신은 환자의 복약/부작용 상담을 돕는 어시스턴트다.

    # Constraints
    1. 일반적인 잡담이라고 판단 될 경우 자연스럽게 대화를 이어 간다.
    2. 구체적인 약물/부작용 관련 질문이 다시 나오면, 답변하지 말고 그 부분을 다시 문의해달라고 자연스럽게 안내한다.
    3. 답변은 간결하게 한다.
    """
    response = llm.invoke(prompt)
    return {"messages": [response]}
