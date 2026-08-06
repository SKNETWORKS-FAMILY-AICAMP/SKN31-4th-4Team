from datetime import date, datetime
from .db_connect import get_neo4j_graph, get_mysql_connection

def calc_age(birth_date) -> int:
    """'1942-08-15' 형태의 문자열 또는 date 객체를 받아 만 나이를 계산."""
    if isinstance(birth_date, str):
        birth = datetime.strptime(birth_date, "%Y-%m-%d").date()
    else:
        birth = birth_date
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

def get_drug_detail(product_code: str) -> dict:
    try:
        graph = get_neo4j_graph()

        # 하드코딩된 특정 코드 대신 $product_code 파라미터를 사용하도록 수정
        query = """
            MATCH (d:Drug {product_code: $product_code}) 
            OPTIONAL MATCH (d)-[:HAS_INGREDIENT]->(i:Ingredient)
            RETURN 
                d.product_code AS product_code, 
                d.name AS drug_name, 
                d.company AS company,
                d.content_code AS content_code,
                collect({
                    ingredient_code: i.ingredient_code,
                    name_kr: i.name_kr,
                    name_en: i.name_en
                }) AS ingredients
        """

        # params 딕셔너리로 넘긴 product_code가 쿼리의 $product_code에 쏙 들어갑니다.
        result = graph.query(query, params={"product_code": product_code})

        if not result:
            print(f"[Neo4j] Drug not found. product_code={product_code}")
            return {}

        return result[0]
        
    except Exception as e:
        print(f"[Neo4j Error] Failed to get drug detail: {e}")
        return {}
    
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
        # MySQL drug 테이블에 처방된 약이 누락되었을 수 있으므로, prescription_detail에서 제품코드만 가져온 뒤
        # Neo4j(get_drug_detail)를 통해 상세 약명과 성분코드를 매핑합니다.
        cur.execute(
            """
            SELECT drug_product_code
            FROM prescription_detail
            WHERE prescription_id = %s
            ORDER BY seq ASC
            """,
            (prescription_id,),
        )
        drug_rows = cur.fetchall()

        for r in drug_rows:
            product_code = r["drug_product_code"]
            detail = get_drug_detail(product_code)
            
            drug_name = detail.get("drug_name") if detail else None
            ingredient_code = detail.get("content_code") if detail else None
            
            ingredient_codes.append(ingredient_code)
            drug_names.append(drug_name)
 
    return {
        "patient_id": patient_id,
        "name": name,
        "age": calc_age(birth_date),
        "gender": gender,
        "is_pregnant": bool(is_pregnant),
        "ingredient_code": ingredient_codes[0] if ingredient_codes else None,
        "drug": drug_names[0] if drug_names else None,
        "ingredient_codes": ingredient_codes,  # 다중 약 대응을 위해 참고용으로 같이 실어둠
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
            "summary": r[0],
            "symptom_keyword": r[1],
            "reported_at": r[2],
            "severity": r[3],
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

