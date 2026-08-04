from Chatbot.builder import build_graph, build_initial_state
from tools.db_connect import get_mysql_connection
from langchain_core.messages import HumanMessage

graph = build_graph()

conn = get_mysql_connection()

try:
    state = build_initial_state(conn, "P-2001")

    state["messages"].append(
        HumanMessage(content="머리가 아파")
    )

    result = graph.invoke(
        state,
        config={
            "configurable": {
                "thread_id": "P-2001"
            }
        }
    )

    print(result)

finally:
    conn.close()