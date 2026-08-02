"""
Neo4j Graph Store Client for GraphRAG Research Notebook.
Handles Cypher MERGE queries for nodes and relationships, multi-tenant notebook isolation,
and multi-hop graph retrieval queries.
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from config.settings import get_settings


class Neo4jGraphStore:
    """
    Neo4j client wrapper for knowledge graph storage and multi-hop graph queries.
    """
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        settings = get_settings()
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password

        if not self.uri or not self.password:
            raise ValueError(
                "NEO4J_URI or NEO4J_PASSWORD not configured. Please set them in .env"
            )

        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        if self.driver:
            self.driver.close()

    def upsert_graph_data(
        self,
        notebook_id: str,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        Upserts entities and relationships into Neo4j scoped by notebook_id.
        """
        nodes_upserted = 0
        edges_upserted = 0

        with self.driver.session() as session:
            # 1. Upsert Entity Nodes
            for entity in entities:
                query = """
                MERGE (e:Entity {name: $name, type: $type, notebook_id: $notebook_id})
                ON CREATE SET e.source_chunk_ids = [$chunk_id], e.created_at = timestamp()
                ON MATCH SET e.source_chunk_ids = 
                    CASE 
                        WHEN $chunk_id IN e.source_chunk_ids THEN e.source_chunk_ids 
                        ELSE e.source_chunk_ids + $chunk_id 
                    END
                """
                session.run(
                    query,
                    name=entity["name"].strip(),
                    type=entity["type"].strip().upper(),
                    notebook_id=notebook_id,
                    chunk_id=entity.get("chunk_id", ""),
                )
                nodes_upserted += 1

            # 2. Upsert Relationship Edges
            for rel in relationships:
                query = """
                MATCH (source:Entity {name: $source_name, type: $source_type, notebook_id: $notebook_id})
                MATCH (target:Entity {name: $target_name, type: $target_type, notebook_id: $notebook_id})
                MERGE (source)-[r:RELATION {relation_type: $relation_type, notebook_id: $notebook_id}]->(target)
                ON CREATE SET r.description = $description, r.source_chunk_ids = [$chunk_id]
                ON MATCH SET r.source_chunk_ids = 
                    CASE 
                        WHEN $chunk_id IN r.source_chunk_ids THEN r.source_chunk_ids 
                        ELSE r.source_chunk_ids + $chunk_id 
                    END
                """
                session.run(
                    query,
                    source_name=rel["source_name"].strip(),
                    source_type=rel["source_type"].strip().upper(),
                    target_name=rel["target_name"].strip(),
                    target_type=rel["target_type"].strip().upper(),
                    relation_type=rel["relation_type"].strip().upper(),
                    notebook_id=notebook_id,
                    description=rel.get("description", ""),
                    chunk_id=rel.get("chunk_id", ""),
                )
                edges_upserted += 1

        return {"nodes": nodes_upserted, "edges": edges_upserted}

    def get_entity_neighbors(
        self, notebook_id: str, entity_name: str, max_hops: int = 2
    ) -> Dict[str, Any]:
        """
        Traverses graph 1-2 hops out from a given entity name for graph-augmented retrieval.

        Returns:
            Dict containing connected entities, relationship descriptions, and source_chunk_ids.
        """
        query = """
        MATCH (start:Entity {notebook_id: $notebook_id})
        WHERE toLower(start.name) = toLower($entity_name)
        MATCH path = (start)-[r:RELATION*1..2]-(neighbor:Entity {notebook_id: $notebook_id})
        RETURN start, relationships(path) AS rels, neighbor
        LIMIT 25
        """
        connected_chunks = set()
        entities = []
        relationships = []

        with self.driver.session() as session:
            result = session.run(query, notebook_id=notebook_id, entity_name=entity_name)
            for record in result:
                neighbor = record["neighbor"]
                rels = record["rels"]

                entities.append({"name": neighbor["name"], "type": neighbor["type"]})

                for chunk_id in neighbor.get("source_chunk_ids", []):
                    if chunk_id:
                        connected_chunks.add(chunk_id)

                for rel in rels:
                    relationships.append(
                        {
                            "relation_type": rel.get("relation_type"),
                            "description": rel.get("description"),
                        }
                    )
                    for chunk_id in rel.get("source_chunk_ids", []):
                        if chunk_id:
                            connected_chunks.add(chunk_id)

        return {
            "entity_name": entity_name,
            "connected_entities": entities,
            "relationships": relationships,
            "source_chunk_ids": list(connected_chunks),
        }

    def get_notebook_graph(self, notebook_id: str) -> Dict[str, Any]:
        """
        Retrieves entire graph for a notebook formatted for frontend react-force-graph rendering.
        """
        query = """
        MATCH (n:Entity {notebook_id: $notebook_id})
        OPTIONAL MATCH (n)-[r:RELATION {notebook_id: $notebook_id}]->(m:Entity {notebook_id: $notebook_id})
        RETURN n, r, m
        """
        nodes = {}
        edges = []

        with self.driver.session() as session:
            result = session.run(query, notebook_id=notebook_id)
            for record in result:
                n = record["n"]
                r = record["r"]
                m = record["m"]

                n_id = f"{n['name']}_{n['type']}"
                if n_id not in nodes:
                    nodes[n_id] = {
                        "id": n_id,
                        "name": n["name"],
                        "type": n["type"],
                        "source_chunk_ids": n.get("source_chunk_ids", []),
                    }

                if m and r:
                    m_id = f"{m['name']}_{m['type']}"
                    if m_id not in nodes:
                        nodes[m_id] = {
                            "id": m_id,
                            "name": m["name"],
                            "type": m["type"],
                            "source_chunk_ids": m.get("source_chunk_ids", []),
                        }

                    edges.append(
                        {
                            "source": n_id,
                            "target": m_id,
                            "label": r.get("relation_type", "RELATION"),
                            "description": r.get("description", ""),
                            "source_chunk_ids": r.get("source_chunk_ids", []),
                        }
                    )

        return {"nodes": list(nodes.values()), "edges": edges}
