from typing import TypedDict, Annotated, Literal, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class PatientInfo(TypedDict):
    name: str
    age: int
    gender: str
    is_pregnant: bool
    ingredient_codes: list[str]
    drugs: list[str | None]


class MedicationLog(TypedDict):
    medication_log_id: int
    taken_at: str


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    need_medicine: bool
    medicine_side_effect: list[dict] | None
    patient_info: PatientInfo
    medication_log: MedicationLog | None
    hours_since_dose: float | None
    past_side_effect_summaries: list[dict]
    symptom_followup: bool
    checklist_index: int
    checked_symptoms: list[dict]
    sufficient_info: bool
    system_signal: Literal["timeout", "disconnect"] | None
    end_signal: Literal["session_end", "symptom_segment"] | None



class ChatRequest(BaseModel):
    query: str
    thread_id: str
    model: str
    patient_info: PatientInfo
