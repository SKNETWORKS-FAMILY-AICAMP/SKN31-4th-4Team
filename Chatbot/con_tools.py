from langchain_mcp_adapters.client import MultiServerMCPClient

async def load_all_tools():
    mcp_client = MultiServerMCPClient({
        "drug_agent": {
            "command": "python",
            "args": ["mcp_server/server.py"],
            "transport": "stdio",
        }
    })
    mcp_tools = await mcp_client.get_tools()
    return mcp_tools