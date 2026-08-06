from django.apps import apps

def get_neo4j_drug_details(product_codes: list[str]) -> dict:
    """
    약물 제품 코드 리스트를 받아 Neo4j에서 단일 노드의 상세 정보를 조회합니다.
    """
    if not product_codes:
        return {}

    # 1. Fallback 처리: 찾고자 하는 필드들을 명시적으로 빈값 설정
    result = {
        code: {
            "name": None,           # 제품명
            "company": None,        # 회사명
            "spec": None,           # 규격 (예: 95ml 병)
            "ingredient_code": None # 주성분코드 (예: 130830ASY)
        } 
        for code in product_codes
    }

    patients_config = apps.get_app_config('patients')
    graph = patients_config.neo4j_graph

    if not graph:
        return result

    # 2. 쿼리 실행
    query = """
    MATCH (d:Drug) WHERE d.product_code IN $product_codes
    RETURN d
    """
    records = graph.query(query, params={"product_codes": product_codes})

    # 3. 결과 파싱 및 매핑
    for record in records:
        drug_node = record.get("d")
        if not drug_node:
            continue
            
        code = drug_node.get("product_code")
        
        result[code] = {
            "name": drug_node.get("name"),
            "company": drug_node.get("company"),
            "spec": drug_node.get("spec"),
            "ingredient_code": drug_node.get("content_code") # Neo4j에 저장된 속성명 매핑
        }  
        
    return result