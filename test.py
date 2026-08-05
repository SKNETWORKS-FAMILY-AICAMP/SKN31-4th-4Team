from Chatbot.builder import build_graph, build_initial_state
from tools.db_connect import get_mysql_connection
from langchain_core.messages import HumanMessage

graph = build_graph()

conn = get_mysql_connection()

# try:
#     state = build_initial_state(conn, "P-2001")

#     state["messages"].append(
#         HumanMessage(content="머리가 아파")
#     )

#     result = graph.invoke(
#         state,
#         config={
#             "configurable": {
#                 "thread_id": "P-2001"
#             }
#         }
#     )

#     print(result)

# finally:
#     conn.close()

from tools.db_connect import get_mysql_connection
from Chatbot.db_loader import get_drug_detail

conn = get_mysql_connection()

try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT drug_product_code
            FROM prescription_detail
            WHERE prescription_id = %s
            LIMIT 1
        """, ("1",))

        row = cur.fetchone()

        print(row)

        product_code = row["drug_product_code"]
        print(product_code)

        result = get_drug_detail(product_code)
        print(result)

finally:
    conn.close()