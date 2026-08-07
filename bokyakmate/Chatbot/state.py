from typing import TypedDict, Optional
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, TypedDict


class MedicationLog(TypedDict):
    medication_log_id: int
    taken_at: str


class State(TypedDict):
    messages: List[Dict[str, Any]]
    need_medicine: bool
    medicine_side_effect: Optional[str]
    patient_info: Dict[str, Any]
    medication_log: Optional[Dict[str, Any]]
    hours_since_dose: Optional[float]
    past_side_effect_summaries: List[Dict[str, Any]]
    symptom_followup: bool
    checklist_index: int
    checked_symptoms: List[str]
    sufficient_info: bool
    system_signal: Optional[str]
    end_signal: Optional[str]
