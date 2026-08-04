from mcp.server.fastmcp import FastMCP

from tools.patient_tools import (
    get_patient_profile,
    get_patient_side_effect_history,
    get_current_medication_context,
)
from tools.drug_db_tools import (
    search_drug,
    get_drug_detail,
    check_drug_interaction,
    check_ingredient_interaction,
    list_drug_contraindications,
)
from tools.web_search_tools import search_drug_info_web

mcp = FastMCP("drug-agent-mcp-server")

# Neo4j 약물 그래프 tool
mcp.add_tool(search_drug)
mcp.add_tool(get_drug_detail)
mcp.add_tool(check_drug_interaction)
mcp.add_tool(check_ingredient_interaction)
mcp.add_tool(list_drug_contraindications)

# 환자 정보 (RDB) tool
mcp.add_tool(get_patient_profile)
mcp.add_tool(get_patient_side_effect_history)
mcp.add_tool(get_current_medication_context)

# 웹 검색 tool
mcp.add_tool(search_drug_info_web)

if __name__ == "__main__":
    mcp.run(transport="stdio")