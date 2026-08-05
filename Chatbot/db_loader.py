from datetime import date, datetime
from tools.db_connect import get_mysql_connection
from tools.drug_db_tools import get_drug_detail

def calc_age(birth_date) -> int:
    """'1942-08-15' 형태의 문자열 또는 date 객체를 받아 만 나이를 계산."""
    if isinstance(birth_date, str):
        birth = datetime.strptime(birth_date, "%Y-%m-%d").date()
    else:
        birth = birth_date
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def load_patient_info(conn, patient_id: str) -> dict:
    """patient + prescription + prescription_detail + drug를 조회해 PatientInfo 형태로 매핑.
    (PyMySQL DictCursor 기준 - %s 플레이스홀더, row['col'] 접근)"""
    cur = conn.cursor()
 
    # 1. 환자 기본 정보 조회
    cur.execute(
        """
        SELECT name, birth_date, gender, is_pregnant
        FROM patient
        WHERE patient_id = %s
        """,
        (patient_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"patient_id={patient_id} 를 찾을 수 없습니다.")
 
    name = row["name"]
    birth_date = row["birth_date"]
    gender = row["gender"]
    is_pregnant = row["is_pregnant"]
 
    # 2. 가장 최근 처방 ID 조회
    cur.execute(
        """
        SELECT prescription_id
        FROM prescription
        WHERE patient_id = %s
        ORDER BY prescribed_at DESC
        LIMIT 1
        """,
        (patient_id,),
    )
    presc_row = cur.fetchone()
 
    ingredient_codes = []
    drug_names = []
    if presc_row:
        prescription_id = presc_row["prescription_id"]
        # MySQL에는 ingredient_code가 없으므로 제품코드/약품명만 가져온다
        cur.execute(
            """
            SELECT d.drug_product_code, d.drug_name
            FROM prescription_detail pd
            JOIN drug d ON pd.drug_product_code = d.drug_product_code
            WHERE pd.prescription_id = %s
            ORDER BY pd.seq ASC
            """,
            (prescription_id,),
        )
        drug_rows = cur.fetchall()
    
        # 제품코드별로 Neo4j에서 성분 목록을 조회해 매핑한다.
        # 약 하나에 성분이 여러 개(복합제)일 수 있어서, 성분마다 같은 약품명을 짝지어 기록한다.
        drug_infos = []

        for r in drug_rows:
            
            drug_name = r["drug_name"]
        
            product_code = r["drug_product_code"]
            detail = get_drug_detail(product_code)
            ingredient_code = detail.get("ingredient_code")
            
            if ingredient_code:
                ingredient_codes.append(ingredient_code)
                drug_names.append(drug_name)

                drug_infos.append({
                    "drug_name": drug_name,
                    "ingredient_code": ingredient_code,
                })
        
            for ing in detail.get("ingredients") or []:
                if ing.get("ingredient_code"):
                    drug_infos.append({
                        "drug_name": drug_name,
                        "ingredient_code": ing["ingredient_code"],
                    })
 
    return {
        "patient_id": patient_id,
        "name": name,
        "age": calc_age(birth_date),
        "gender": gender,
        "is_pregnant": bool(is_pregnant),
        "ingredient_code": ingredient_codes[0] if ingredient_codes else None,
        "drug": drug_names[0] if drug_names else None,
        "ingredient_codes": ingredient_codes,  
        "drugs": drug_names,
    }


def load_latest_medication_log(conn, patient_id: str) -> dict | None:
    """최근 복용 기록(dosing_log)을 조회."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, taken_at
        FROM dosing_log
        WHERE patient_id = %s AND status = 'done'
        ORDER BY taken_at DESC
        LIMIT 1
        """,
        (patient_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {
    "medication_log_id": row["id"],
    "taken_at": row["taken_at"],
}


def load_past_side_effect_summaries(conn, patient_id: str, limit: int = 5) -> list[dict]:
    """해당 환자의 과거 symptom_log 기록을 최근 순으로 조회."""
    cur = conn.cursor()
    # MySQL 안전성을 위해 limit 값을 int로 캐스팅 후 f-string 대입
    safe_limit = int(limit)
    
    cur.execute(
        f"""
        SELECT summary, keyword, reported_at, severity
        FROM symptom_log
        WHERE patient_id = %s
        ORDER BY reported_at DESC
        LIMIT {safe_limit}
        """,
        (patient_id,),
    )
    rows = cur.fetchall()
    return [
    {
        "summary": r["summary"],
        "symptom_keyword": r["symptom_keyword"],
        "reported_at": r["reported_at"],
        "severity": r["severity"],
    }
    for r in rows
]


def load_initial_state_data(conn,patient_id: str) -> dict:
    """세션 시작 시 한 번 호출해서 State에 그대로 얹을 수 있는 dict를 반환."""
    conn = get_mysql_connection()

    return {
        "patient_info": load_patient_info(conn, patient_id),
        "medication_log": load_latest_medication_log(conn, patient_id),
        "past_side_effect_summaries": load_past_side_effect_summaries(conn, patient_id),
    }

