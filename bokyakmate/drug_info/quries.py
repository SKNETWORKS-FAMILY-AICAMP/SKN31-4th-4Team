from .db_connector import get_neo4j_graph

def get_drug_details_batch(product_codes: list[str]) -> list[dict]:
    """여러 제품코드를 한 번에 조회해서 각각의 상세정보 + 성분 목록을 반환합니다.
    환자 처방 목록(여러 개 약)을 대시보드에 뿌릴 때, 약마다 get_drug_detail을
    반복 호출하지 않고 이 함수 하나로 배치 처리합니다 (N+1 쿼리 방지)."""
    graph = get_neo4j_graph()
    query = """
    UNWIND $product_codes AS code
    MATCH (d:Drug {product_code: code})
    OPTIONAL MATCH (d)-[:HAS_INGREDIENT]->(i:Ingredient)
    WITH d, collect({
        ingredient_code: i.ingredient_code,
        name_kr: i.name_kr,
        name_en: i.name_en
    }) AS ingredients
    RETURN
        d.product_code AS product_code,
        d.name AS drug_name,
        d.company AS company,
        d.content_code AS content_code,
        d.is_combination AS is_combination,
        ingredients
    """
    return graph.query(query, params={"product_codes": product_codes})


def check_interactions_in_medication_list(product_codes: list[str]) -> list[dict]:
    """환자가 현재 복용 중인 여러 약(제품코드 리스트) 사이에 병용금기 조합이
    있는지 전부 한 번에 조회합니다. check_drug_interaction을 약 쌍마다
    반복 호출하는 대신, 처방 전체를 한 번의 쿼리로 훑을 때 사용합니다.
    d1.product_code < d2.product_code 조건으로 같은 쌍이 중복 반환되는 것을 방지합니다."""
    graph = get_neo4j_graph()
    query = """
    MATCH (d1:Drug)-[:HAS_INGREDIENT]->(i1:Ingredient)
    MATCH (i1)-[c:CONTRAINDICATED_WITH]-(i2:Ingredient)
    MATCH (d2:Drug)-[:HAS_INGREDIENT]->(i2)
    WHERE d1.product_code IN $product_codes
      AND d2.product_code IN $product_codes
      AND d1.product_code < d2.product_code
    RETURN DISTINCT
        d1.product_code AS drug_a_code, d1.name AS drug_a_name,
        i1.ingredient_code AS ingredient_a_code, i1.name_kr AS ingredient_a_name,
        d2.product_code AS drug_b_code, d2.name AS drug_b_name,
        i2.ingredient_code AS ingredient_b_code, i2.name_kr AS ingredient_b_name,
        c.reason AS interaction_reason
    """
    return graph.query(query, params={"product_codes": product_codes})


def get_medication_graph_for_visualization(product_codes: list[str]) -> dict:
    """환자가 현재 복용 중인 약들을 '나의 약물 표출' 노드-링크 그래프용
    {nodes: [...], edges: [...]} 형태로 반환합니다.
    - 노드: Drug 노드 + 그 안에 포함된 Ingredient 노드
    - 엣지: HAS_INGREDIENT(약→성분), CONTRAINDICATED_WITH(성분↔성분, 복용 중인
      약들 사이에서만) 두 종류를 합쳐서 반환
    프론트엔드(d3.js/vis.js)에서 그대로 렌더링할 수 있는 형태로 Python에서 조립합니다."""
    graph = get_neo4j_graph()

    node_query = """
    UNWIND $product_codes AS code
    MATCH (d:Drug {product_code: code})
    OPTIONAL MATCH (d)-[:HAS_INGREDIENT]->(i:Ingredient)
    RETURN
        d.product_code AS product_code,
        d.name AS drug_name,
        collect(DISTINCT {
            ingredient_code: i.ingredient_code,
            name_kr: i.name_kr
        }) AS ingredients
    """
    edge_query = """
    MATCH (d1:Drug)-[:HAS_INGREDIENT]->(i1:Ingredient)
    MATCH (i1)-[c:CONTRAINDICATED_WITH]-(i2:Ingredient)
    MATCH (d2:Drug)-[:HAS_INGREDIENT]->(i2)
    WHERE d1.product_code IN $product_codes
      AND d2.product_code IN $product_codes
      AND i1.ingredient_code < i2.ingredient_code
    RETURN DISTINCT
        i1.ingredient_code AS source,
        i2.ingredient_code AS target,
        c.reason AS reason
    """

    drug_rows = graph.query(node_query, params={"product_codes": product_codes})
    interaction_rows = graph.query(edge_query, params={"product_codes": product_codes})

    nodes = []
    edges = []
    seen_ingredient_codes = set()

    for row in drug_rows:
        nodes.append({
            "id": f"drug:{row['product_code']}",
            "type": "drug",
            "label": row["drug_name"],
        })
        for ing in row["ingredients"]:
            if not ing.get("ingredient_code"):
                continue
            ing_node_id = f"ingredient:{ing['ingredient_code']}"
            if ing["ingredient_code"] not in seen_ingredient_codes:
                nodes.append({
                    "id": ing_node_id,
                    "type": "ingredient",
                    "label": ing["name_kr"],
                })
                seen_ingredient_codes.add(ing["ingredient_code"])
            edges.append({
                "source": f"drug:{row['product_code']}",
                "target": ing_node_id,
                "type": "HAS_INGREDIENT",
            })

    for row in interaction_rows:
        edges.append({
            "source": f"ingredient:{row['source']}",
            "target": f"ingredient:{row['target']}",
            "type": "CONTRAINDICATED_WITH",
            "reason": row["reason"],
        })

    return {"nodes": nodes, "edges": edges}