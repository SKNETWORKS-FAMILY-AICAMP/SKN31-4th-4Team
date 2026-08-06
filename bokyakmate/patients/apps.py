from django.apps import AppConfig
import logging
from services.db_connector import get_neo4j_graph


logger = logging.getLogger(__name__)


class PatientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'patients'
    # driver 대신 graph 객체를 저장
    neo4j_graph = None

    def ready(self):
        if self.neo4j_graph is None:
            try:
                self.neo4j_graph = get_neo4j_graph()
                logger.info("Neo4jGraph initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4jGraph: {e}")