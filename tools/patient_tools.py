from .db_connect import get_mysql_connection
from datetime import date, datetime
from langchain_core.tools import tool

#-----------------------------------------
def calc_age(birth_date) -> int:
    birth = birth_date if isinstance(birth_date, date) else datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

# ----------------------------------------

def get_patient_profile(patient_id: str) -> dict:
    """환자의 기본 정보(이름/나이/성별/임신여부/키/몸무게)를 조회한다."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, birth_date, gender, is_pregnant, height, weight FROM patient WHERE patient_id = %s",
                (patient_id,),
            )
            row = cur.fetchone()
            if row is None:
                return {"error": f"patient_id={patient_id}를 찾을 수 없습니다."}
            return {
                "name": row["name"],
                "age": calc_age(row["birth_date"]),
                "gender": row["gender"],
                "is_pregnant": bool(row["is_pregnant"]),
                "height": row["height"],
                "weight": row["weight"]
            }
    finally:
        conn.close()
        

def get_patient_side_effect_history(patient_id: str, symptom_keyword: str = None) -> list:
    """
    환자의 과거 부작용(이상반응) 기록을 조회한다. 
    과거에도 비슷한 부작용을 호소한 적이 있는지 확인할 때 사용한다.
    """
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            # 기본 쿼리: 부작용 로그를 중심으로 복약 기록과 처방 약품 정보를 조인
            query = """
                SELECT 
                    sel.reported_at,
                    sel.symptom_keyword,
                    sel.severity,
                    sel.summary,
                    pd.drug_product_code,
                    ml.intake_date
                FROM side_effect_log sel
                LEFT JOIN medication_log ml ON sel.medication_log_id = ml.medication_log_id
                LEFT JOIN prescription p ON ml.prescription_id = p.prescription_id
                LEFT JOIN prescription_drug pd ON p.prescription_id = pd.prescription_id
                WHERE sel.patient_id = %s
            """
            params = [patient_id]
            
            # 특정 증상 키워드가 입력된 경우 필터 조건 추가
            if symptom_keyword:
                query += " AND sel.symptom_keyword LIKE %s"
                params.append(f"%{symptom_keyword}%")
                
            query += " ORDER BY sel.reported_at DESC"
            
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            
            # 검색 결과가 없는 경우 빈 리스트 반환
            if not rows:
                return []
                
            # 결과를 딕셔너리 리스트 형태로 가공하여 반환
            history = []
            for row in rows:
                history.append({
                    "reported_at": str(row["reported_at"]) if row["reported_at"] else None,
                    "symptom_keyword": row["symptom_keyword"],
                    "severity": row["severity"],
                    "summary": row["summary"],
                    "drug_product_code": row["drug_product_code"],
                    "intake_date": str(row["intake_date"]) if row["intake_date"] else None
                })
                
            return history
    finally:
        conn.close()


def get_current_medication_context(patient_id: str) -> dict:
    """
    환자의 가장 최근 처방, 처방된 약물(Product Code),
    그리고 각 약물의 가장 최근 복약 기록을 조회한다.

    Returns:
    {
        "prescription_id": ...,
        "prescription_date": ...,
        "diagnosis": ...,
        "drugs": [
            {
                "drug_product_code": "...",
                "start_date": "...",
                "end_date": "...",
                "intake_time": "...",
                "last_taken": {
                    "took_medicine": 1,
                    "taken_at": "...",
                    "intake_date": "...",
                    "intake_time_type": "..."
                }
            }
        ]
    }
    """
    conn = get_mysql_connection()
    try:
            with conn.cursor() as cur:

                # 1. 가장 최근 처방
                cur.execute(
                    """
                    SELECT
                        prescription_id,
                        prescription_date,
                        diagnosis
                    FROM prescription
                    WHERE patient_id = %s
                    ORDER BY prescription_date DESC
                    LIMIT 1
                    """,
                    (patient_id,),
                )

                prescription = cur.fetchone()

                if prescription is None:
                    return {}

                prescription_id = prescription["prescription_id"]

                # 2. 처방 약 목록
                cur.execute(
                    """
                    SELECT
                        drug_product_code,
                        start_date,
                        end_date,
                        intake_time
                    FROM prescription_drug
                    WHERE prescription_id = %s
                    ORDER BY drug_product_code
                    """,
                    (prescription_id,),
                )

                drugs = cur.fetchall()

                # 3. 최근 복약기록
                cur.execute(
                    """
                    SELECT
                        took_medicine,
                        taken_at,
                        intake_date,
                        intake_time_type
                    FROM medication_log
                    WHERE
                        patient_id = %s
                        AND prescription_id = %s
                    ORDER BY medication_log_id DESC
                    LIMIT 1
                    """,
                    (patient_id, prescription_id),
                )

                last_log = cur.fetchone()

                result = {
                    "prescription_id": prescription_id,
                    "prescription_date": prescription["prescription_date"],
                    "diagnosis": prescription["diagnosis"],
                    "drugs": [],
                }

                for drug in drugs:
                    result["drugs"].append(
                        {
                            "drug_product_code": drug["drug_product_code"],
                            "start_date": drug["start_date"],
                            "end_date": drug["end_date"],
                            "intake_time": drug["intake_time"],
                            "last_taken": last_log,
                        }
                    )

                return result

    finally:
        conn.close()