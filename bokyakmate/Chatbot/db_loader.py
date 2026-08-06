import os 
from datetime import date, datetime
from .db_connect import get_mysql_connection, get_neo4j_graph
from tavily import TavilyClient
from Chatbot.state import State
from langchain_core.tools import tool

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
        SELECT name, birth_date, gender, is_pregnant, is_smoker, average_sleep_time, average_wake_time, meal_pattern
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
    is_smoker= row['is_smoker']
    meal_pattern=row['meal_pattern']
    average_wake_time=row['average_wake_time']
    average_sleep_time=row['average_sleep_time']


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
    product_codes= []
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
            product_codes.append(product_code)
            ingredient_codes.append(ingredient_code)
            drug_names.append(drug_name)
 
    return {
        "patient_id": patient_id,
        "name": name,
        "age": calc_age(birth_date),
        "gender": gender,
        "is_pregnant": bool(is_pregnant),
        "ingredient_codes": ingredient_codes,  # 다중 약 대응을 위해 참고용으로 같이 실어둠
        "drugs": drug_names,
        "product_codes":product_codes,
        "is_smoker":is_smoker,
        "average_sleep_time": average_sleep_time,
        "average_wake_time": average_wake_time,
        "meal_pattern": meal_pattern
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


def search_drug(name: str, limit: int = 10) -> list[dict]:
    """제품명(일부)으로 약품을 검색합니다. 제품코드, 회사, 규격 여부를 반환합니다."""
    graph = get_neo4j_graph()
    query = """
    MATCH (d:Drug)
    WHERE d.name CONTAINS $name
    RETURN d.product_code AS product_code, d.name AS name, d.company AS company,
           d.is_combination AS is_combination
    LIMIT $limit
    """
    return graph.query(query, params={"name": name, "limit": limit})

def get_drug_detail(product_code: str) -> dict:
    """제품코드로 약품 상세정보와 포함된 모든 성분 목록(성분코드, 이름, 함량)을 조회합니다."""
    graph = get_neo4j_graph()
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
    result = graph.query(query, params={"product_code": product_code})
    return result[0] if result else {}

def check_drug_interaction(product_code_a: str, product_code_b: str) -> list[dict]:
    """두 제품(제품코드)을 함께 복용할 때 병용금기인 성분 조합이 있는지 확인합니다.
    각 제품에 포함된 성분들 사이의 CONTRAINDICATED_WITH 관계를 전부 찾아 반환합니다."""
    graph = get_neo4j_graph()
    query = """
    MATCH (d1:Drug {product_code: $product_code_a})-[:HAS_INGREDIENT]->(i1:Ingredient)
    MATCH (d2:Drug {product_code: $product_code_b})-[:HAS_INGREDIENT]->(i2:Ingredient)
    MATCH (i1)-[c:CONTRAINDICATED_WITH]-(i2)
    RETURN 
        d1.name AS drug_a_name, i1.name_kr AS ingredient_a_name,
        d2.name AS drug_b_name, i2.name_kr AS ingredient_b_name,
        c.reason AS interaction_reason
    """
    return graph.query(query, params={"a": product_code_a, "b": product_code_b})

def check_ingredient_interaction(ingredient_code_a: str, ingredient_code_b: str) -> dict:
    """성분코드(4자리) 두 개 사이에 병용금기 관계가 있는지 직접 확인합니다."""
    graph = get_neo4j_graph()
    query = """
    MATCH (i1:Ingredient {ingredient_code: $a})-[c:CONTRAINDICATED_WITH]-(i2:Ingredient {ingredient_code: $b})
    RETURN c.reason AS reason
    """
    result = graph.query(query, params={"a": ingredient_code_a, "b": ingredient_code_b})
    return {
        "is_contraindicated": bool(result),
        "reason": result[0]["reason"] if result else None,
    }

def list_drug_contraindications(product_code: str) -> list[dict]:
    """이 약(제품코드)에 포함된 성분들과 병용금기인 다른 모든 성분 목록을 조회합니다.
    "이 약이랑 같이 먹으면 안 되거나 피해야 할 성분이 뭐야?" 같은 질문에 사용합니다."""
    graph = get_neo4j_graph()
    query = """
    MATCH (d:Drug {product_code: $product_code})-[:HAS_INGREDIENT]->(i1:Ingredient)
    MATCH (i1)-[c:CONTRAINDICATED_WITH]-(i2:Ingredient)
    RETURN i1.ingredient_code AS my_ingredient, i1.name_kr AS my_ingredient_name,
           i2.ingredient_code AS conflicting_ingredient,
           i2.name_kr AS conflicting_ingredient_name,
           c.reason AS reason
    """
    return graph.query(query, params={"product_code": product_code})




def make_check_interaction_tool(state: State):
    @tool
    def check_interaction_with_my_drugs(asked_drug_name: str) -> dict:
        """사용자가 특정 약을 복용해도 되는지, 현재 복용 중인 약과 함께 복용 가능한지 묻는 경우 사용합니다.
    질문한 약물과 환자의 현재 복용 약물 간 병용금기를 조회합니다.
    """
        my_product_codes = state["patient_info"].get("product_codes") or []
        ...
        return ...
    return check_interaction_with_my_drugs



# 인터넷 검색 tool
@tool
def search_info_web(query: str) -> str:
    """최신 정보가 필요하거나 추가적인 정보가 필요하다 판단 될 경우 실행. 인터넷 검색 도구 """

    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    try:
        # tavily AI 검색 실행 (한국어 및 신뢰성 높은 결과 위주)
        response = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=3,
            include_answer=True,
        )

        # Tavily가 자체 요약한 AI 답변이 있으면 우선 활용
        answer = response.get("answer", "")
        results = response.get("results", [])

        snippets = "\n".join(f"- [{r['title']}] {r['content']}" for r in results)

        return f"검색 요약: {answer}\n\n상세 출처 내용:\n{snippets}"

    except Exception as e:
        return f"웹 검색 중 오류가 발생했습니다: {str(e)}"
