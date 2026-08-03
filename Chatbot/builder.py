import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from chat_node import (
    State,
    chat_node,
    medicine_node,
    side_effect_node,
    router,
    general_chat_node,
    side_effect_followup_node,
    entry_router,
    followup_gate_node,
    followup_router,
    session_end_node,
    symptom_summary_node,
)
from db_loader import load_initial_state_data

# 그래프 조립
def build_graph():
    graph = StateGraph(State)

    graph.add_node("chat_node", chat_node)
    graph.add_node("medicine_node", medicine_node)
    graph.add_node("side_effect_node",side_effect_node)
    graph.add_node("general_chat_node", general_chat_node) 
    graph.add_node("side_effect_followup_node", side_effect_followup_node)
    graph.add_node("followup_gate_node", followup_gate_node)
    graph.add_node("session_end_node", session_end_node)
    graph.add_node("symptom_summary_node", symptom_summary_node)

    graph.add_conditional_edges(
        START,
        entry_router,
        {
            "followup_gate_node": "followup_gate_node",
            "chat_node": "chat_node",
            "session_end_node": "session_end_node",
        },
    )
    graph.add_conditional_edges(
        "chat_node",
        router,
        {
            "medicine_node": "medicine_node",
            "general_chat_node": "general_chat_node",  
        }
    )
    graph.add_conditional_edges(
        "followup_gate_node",
        followup_router,
        {
            "side_effect_followup_node": "side_effect_followup_node",
            "general_chat_node": "general_chat_node",
            "symptom_summary_node": "symptom_summary_node",
        }
    )
    graph.add_edge("medicine_node", "side_effect_node")
    graph.add_edge("side_effect_node", END)
    graph.add_edge("side_effect_followup_node", END)
    graph.add_edge("general_chat_node", END)
    graph.add_edge("session_end_node", END)
    graph.add_edge("symptom_summary_node", END)

    conn = sqlite3.connect("langgraph_checkpoint.db", check_same_thread=False)
    memory = SqliteSaver(conn)

    return graph.compile(checkpointer=memory)


def build_initial_state(patient_db_conn, patient_id: str) -> State:
    """새 세션(thread_id) 시작 시 한 번만 호출. 환자DB를 조회해 State 초기값을 제공"""
    loaded = load_initial_state_data(patient_db_conn, patient_id)

    return {
        "messages": [],
        "need_medicine": False,
        "medicine_side_effect": None,
        "patient_info": loaded["patient_info"],
        "medication_log": loaded["medication_log"],
        "hours_since_dose": None,
        "past_side_effect_summaries": loaded["past_side_effect_summaries"],
        "symptom_followup": False,
        "checklist_index": -1,
        "checked_symptoms": [],
        "sufficient_info": False,
        "system_signal": None,
        "end_signal": None,
    }


