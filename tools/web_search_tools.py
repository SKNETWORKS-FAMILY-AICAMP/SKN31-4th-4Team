import os
from dotenv import load_dotenv
from tavily import TavilyClient


load_dotenv(override=True)

api_key = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=api_key)

def search_drug_info_web(drug_name: str, query_type: str = "효능 부작용") -> str:
    """
    약물에 대해 더 풍부하고 상세한 텍스트 정보가 필요하다고 판단될 때 인터넷에서 검색합니다.
    DB 조회만으로 정보가 부족하거나, 환자에게 구체적인 효능/효과, 실제 부작용 발생 증상, 
    올바른 복용법 및 주의사항 등을 자세히 설명해야 할 때 적극적으로 호출하세요.
    
    Args:
        drug_name: 검색할 약품명 또는 성분명 (예: "타이레놀", "아세트아미노펜")
        query_type: 검색 목적 (예: "부작용", "효능/효과", "용법용량", "주의사항")
    """
    search_query = f"약품 {drug_name} {query_type} 의학정보"
    
    try:
        # tavily AI 검색 실행 (한국어 및 신뢰성 높은 결과 위주)
        response = tavily.search(
            query=search_query,
            search_depth="advanced",
            max_results=3,
            include_answer=True
        )
        
        # Tavily가 자체 요약한 AI 답변이 있으면 우선 활용
        answer = response.get("answer", "")
        results = response.get("results", [])
        
        snippets = "\n".join([f"- [{r['title']}] {r['content']}" for r in results])
        
        output = f"🔍 **검색 요약**: {answer}\n\n**상세 출처 내용**:\n{snippets}"
        return output
        
    except Exception as e:
        return f"웹 검색 중 오류가 발생했습니다: {str(e)}"