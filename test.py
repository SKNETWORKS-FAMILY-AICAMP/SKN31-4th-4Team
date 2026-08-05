from Chatbot.builder import build_graph, build_initial_state
from tools.db_connect import get_mysql_connection
from langchain_core.messages import HumanMessage
graph = build_graph()

conn = get_mysql_connection()


try:
    # 1. 초기 상태는 최초 1회만 생성
    state = build_initial_state(conn, "P-2001")
    config = {"configurable": {"thread_id": "P-2001"}}

    print(" 대화를 시작합니다. (종료하려면 '종료' 또는 'q'를 입력하세요)\n" + "-"*40)

    while True:
        # 2. 사용자 입력 받기
        user_input = input(" 유저: ")
        
        # 종료 조건 체크
        if user_input.strip() in ["종료", "q", "quit", "exit"]:
            print("대화를 종료합니다.")
            break
            
        if not user_input.strip():
            continue

        # 3. 기존 state의 메시지 리스트에 새 입력 추가
        state["messages"].append(HumanMessage(content=user_input))
        
        # 4. 그래프 실행 후 업데이트된 최신 상태를 다시 state에 저장
        state = graph.invoke(state, config=config)
        
        # 5. 마지막 AI 대답만 추출하여 출력
        if "messages" in state and state["messages"]:
            last_message = state["messages"][-1]
            print(f" AI: {last_message.content}")
            print("-" * 40)
        else:
            print(" AI: 답변을 가져오지 못했습니다.")
            
finally:
    conn.close()