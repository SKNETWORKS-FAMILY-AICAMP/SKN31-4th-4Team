"""
DB(patient / prescription / prescription_drug / medication_log)에서
챗봇 State(PatientInfo, medication_log)에 맞는 형태로 데이터를 조회·변환하는 모듈.
get_connection()  sqlite3 문법 기준.
"""

from datetime import date, datetime


def calc_age(birth_date: str) -> int:
    """'1942-08-15' 같은 문자열을 받아 만 나이를 계산."""
    birth = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def load_patient_info(conn, patient_id: str) -> dict:
    """patient + prescription + prescription_drug를 조회해 PatientInfo 형태로 매핑."""
    cur = conn.cursor()

    cur.execute(
        """
        SELECT name, birth_date, gender, is_pregnant
        FROM patient
        WHERE patient_id = ?
        """,
        (patient_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"patient_id={patient_id} 를 찾을 수 없습니다.")
    name, birth_date, gender, is_pregnant = row

    # 가장 최근 처방 하나를 기준으로, 처방된 약(복수 가능)을 가져온다.
    cur.execute(
        """
        SELECT pd.ingredient_code, pd.drug_product_code
        FROM prescription p
        JOIN prescription_drug pd ON pd.prescription_id = p.prescription_id
        WHERE p.patient_id = ?
        ORDER BY p.prescription_date DESC
        """,
        (patient_id,),
    )
    drug_rows = cur.fetchall()

    ingredient_codes = [r[0] for r in drug_rows]
    drug_names = [r[1] for r in drug_rows]

    return {
        "name": name,
        "age": calc_age(birth_date),
        "gender": gender,
        "is_pregnant": bool(is_pregnant),
        "ingredient_code": ingredient_codes[0] if ingredient_codes else None,
        "drug": drug_names[0] if drug_names else None,
        "ingredient_codes": ingredient_codes,
        "drugs": drug_names,
    }

#  최근 복용 기록을 조회. calc_hours_since_dose()에 맞게 dict로 반환.
def load_latest_medication_log(conn, patient_id: str) -> dict | None:

    cur = conn.cursor()
    cur.execute(
        """
        SELECT medication_log_id, taken_at
        FROM medication_log
        WHERE patient_id = ? AND took_medicine = 1
        ORDER BY taken_at DESC
        LIMIT 1
        """,
        (patient_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {"medication_log_id": row[0], "taken_at": row[1]}


def load_past_side_effect_summaries(conn, patient_id: str, limit: int = 5) -> list[dict]:
    """해당 환자의 과거 side_effect_log(장기메모리) 기록을 최근 순으로 조회."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT summary, symptom_keyword, reported_at, severity
        FROM side_effect_log
        WHERE patient_id = ?
        ORDER BY reported_at DESC
        LIMIT ?
        """,
        (patient_id, limit),
    )
    rows = cur.fetchall()
    return [
        {
            "summary": r[0],
            "symptom_keyword": r[1],
            "reported_at": r[2],
            "severity": r[3],
        }
        for r in rows
    ]


def load_initial_state_data(conn, patient_id: str) -> dict:
    """세션 시작 시 한 번 호출해서 State에 그대로 얹을 수 있는 dict를 반환."""
    return {
        "patient_info": load_patient_info(conn, patient_id),
        "medication_log": load_latest_medication_log(conn, patient_id),
        "past_side_effect_summaries": load_past_side_effect_summaries(conn, patient_id),
    }
