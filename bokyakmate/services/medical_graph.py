from django.apps import apps

def get_neo4j_drug_details(product_codes: list) -> dict:
    """
    약물 제품 코드 리스트를 받아 Neo4j에서 상세 정보를 조회합니다.
    (반환되는 name 필드는 괄호 '(' 앞부분만 잘린 짧은 이름입니다.)
    """
    if not product_codes:
        return {}

    # 1. 중복 제거 및 무조건 문자열(str)로 통일 (에러 방지)
    str_codes = list(set(str(code) for code in product_codes if code))
    
    if not str_codes:
        return {}

    # 2. Fallback 처리: 찾고자 하는 필드들을 명시적으로 빈값 설정
    result = {
        code: {
            "name": "약 이름 정보 없음",   # 기본값도 통일
            "company": None,
            "spec": None,
            "ingredient_code": None
        } 
        for code in str_codes
    }

    patients_config = apps.get_app_config('patients')
    graph = patients_config.neo4j_graph

    if not graph:
        return result

    # 3. 쿼리 실행
    query = """
    MATCH (d:Drug) WHERE d.product_code IN $product_codes
    RETURN d
    """
    records = graph.query(query, params={"product_codes": str_codes})

    # 4. 결과 파싱 및 매핑
    for record in records:
        drug_node = record.get("d")
        if not drug_node:
            continue
            
        code = str(drug_node.get("product_code"))
        
        # 원본 이름 가져오기
        full_name = drug_node.get("name")
        
        # 💡 핵심: 여기서 괄호 앞부분만 잘라서 저장!
        short_name = full_name.split("(")[0].strip() if full_name else "약 이름 정보 없음"
        
        result[code] = {
            "name": short_name, # 잘라낸 이름 적용
            "company": drug_node.get("company"),
            "spec": drug_node.get("spec"),
            "ingredient_code": drug_node.get("content_code")
        }  
        
    return result