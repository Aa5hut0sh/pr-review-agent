import logging
from typing import List, Dict, Any, Set
import networkx as nx
from app.core.config import settings
from app.indexing.parser import CodeEntity

logger = logging.getLogger(__name__)


class CodeGraph:
    """
    Structural code graph representing Files, Classes, and Functions
    with CALLS, IMPORTS, and DEFINES edges to determine the blast radius of changes.
    Uses Neo4j if reachable, with an automatic NetworkX in-memory fallback.
    """

    def __init__(self):
        self.use_neo4j = False
        self.driver = None
        self.nx_graph = nx.DiGraph()

        if settings.neo4j_uri:
            try:
                from neo4j import GraphDatabase
                self.driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                self.driver.verify_connectivity()
                self.use_neo4j = True
                logger.info("Connected to Neo4j successfully.")
            except Exception as e:
                logger.info(f"Neo4j not reachable ({e}). Using NetworkX in-memory graph fallback.")
                self.use_neo4j = False

    def close(self):
        if self.driver:
            self.driver.close()

    def build_from_entities(self, entities: List[CodeEntity]):
        """
        Populate the code graph with nodes and relationships from parsed entities.
        """
        for entity in entities:
            # Add to NetworkX
            self.nx_graph.add_node(
                entity.name,
                type=entity.entity_type,
                file=entity.file_path,
                start=entity.start_line,
                end=entity.end_line,
            )
            self.nx_graph.add_node(entity.file_path, type="file")
            self.nx_graph.add_edge(entity.file_path, entity.name, relation="DEFINES")

            for called_fn in entity.calls:
                self.nx_graph.add_edge(entity.name, called_fn, relation="CALLS")

            for imp in entity.imports:
                self.nx_graph.add_edge(entity.file_path, imp, relation="IMPORTS")

        # Sync to Neo4j if available
        if self.use_neo4j:
            try:
                with self.driver.session() as session:
                    for entity in entities:
                        session.run(
                            """
                            MERGE (f:File {path: $file})
                            MERGE (e:Entity {name: $name, type: $type, file: $file})
                            MERGE (f)-[:DEFINES]->(e)
                            """,
                            file=entity.file_path,
                            name=entity.name,
                            type=entity.entity_type,
                        )
                        for called in entity.calls:
                            session.run(
                                """
                                MERGE (caller:Entity {name: $caller})
                                MERGE (callee:Entity {name: $callee})
                                MERGE (caller)-[:CALLS]->(callee)
                                """,
                                caller=entity.name,
                                callee=called,
                            )
            except Exception as e:
                logger.warning(f"Failed to sync to Neo4j: {e}")

    def get_blast_radius(self, modified_entities: List[str]) -> Dict[str, Any]:
        """
        Finds all direct callers, callees, and affected files for the modified entities.
        """
        callers: Set[str] = set()
        callees: Set[str] = set()
        affected_files: Set[str] = set()

        for entity_name in modified_entities:
            # NetworkX query
            if entity_name in self.nx_graph:
                # Predecessors are callers (who calls this entity?)
                for pred in self.nx_graph.predecessors(entity_name):
                    edge_data = self.nx_graph.get_edge_data(pred, entity_name)
                    if edge_data and edge_data.get("relation") == "CALLS":
                        callers.add(pred)
                        file_attr = self.nx_graph.nodes[pred].get("file")
                        if file_attr:
                            affected_files.add(file_attr)

                # Successors are callees (what does this entity call?)
                for succ in self.nx_graph.successors(entity_name):
                    edge_data = self.nx_graph.get_edge_data(entity_name, succ)
                    if edge_data and edge_data.get("relation") == "CALLS":
                        callees.add(succ)

        return {
            "modified": modified_entities,
            "callers": list(callers),
            "callees": list(callees),
            "affected_files": list(affected_files),
        }
