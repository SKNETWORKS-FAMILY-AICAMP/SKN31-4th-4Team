import os
import pymysql
from langchain_neo4j import Neo4jGraph
from dotenv import load_dotenv

load_dotenv()

def get_mysql_connection():
    """MySQL 데이터베이스 커넥션을 반환합니다 (환자 정보용)"""
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT')),
        user=os.getenv('MYSQL_USER'),
        passwd=os.getenv('MYSQL_PASSWORD'),
        db=os.getenv('MYSQL_DB'),
        charset='utf8',
        cursorclass=pymysql.cursors.DictCursor
    )
    
def get_neo4j_graph():
    """Neo4j 그래프 데이터베이스 객체를 반환합니다 (약물 정보용)"""
    return Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE"),
    )