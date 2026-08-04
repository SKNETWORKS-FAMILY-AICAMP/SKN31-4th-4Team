import os
from dotenv import load_dotenv
from .db_connect import get_neo4j_graph

load_dotenv(override=True)

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
