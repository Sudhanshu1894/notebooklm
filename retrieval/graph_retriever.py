"""
Graph-Augmented Retriever for GraphRAG Research Notebook.
Expands initial vector search hits via 1-2 hop Neo4j graph traversals to find
related entity chunks not surfaced by vector search alone.
"""

from typing import List, Dict, Any, Set
from graph_store.neo4j_client import Neo4jGraphStore
from embedding.model import EmbeddingModel
from vector_store.chroma import VectorStore


class GraphRetriever:
    """
    Graph-augmented retriever:
    1. Receives top-k vector-retrieved chunks.
    2. Extracts entities referenced in those chunks.
    3. Traverses Neo4j graph 1-2 hops to find related entity chunk IDs.
    4. Fetches additional chunks by ID from ChromaDB.
    """

    def __init__(self):
        self.embedder = EmbeddingModel()
        self.vector_store = VectorStore()

    def expand_via_graph(
        self,
        notebook_id: str,
        seed_chunks: List[Dict[str, Any]],
        max_hops: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Given seed chunks from vector search, traverses Neo4j graph to find
        additional chunks via entity neighbors.

        Returns:
            List of additional chunk dicts from graph expansion.
        """
        graph_store = Neo4jGraphStore()
        expanded_chunk_ids: Set[str] = set()
        seed_chunk_ids: Set[str] = {c["chunk_id"] for c in seed_chunks}

        try:
            for chunk in seed_chunks:
                # Use doc_id as a proxy to find entities from that chunk's document
                doc_id = chunk["metadata"].get("doc_id", "")
                if not doc_id:
                    continue

                # Query graph for entities sourced from this chunk
                chunk_id = chunk["chunk_id"]
                neighbors = self._get_entity_chunk_ids_for_chunk(
                    graph_store, notebook_id, chunk_id, max_hops
                )
                expanded_chunk_ids.update(neighbors)
        finally:
            graph_store.close()

        # Remove chunk IDs already in the seed set
        new_chunk_ids = expanded_chunk_ids - seed_chunk_ids

        if not new_chunk_ids:
            return []

        # Fetch expanded chunks from ChromaDB by IDs
        expanded_chunks = self._fetch_chunks_by_ids(notebook_id, list(new_chunk_ids))
        for c in expanded_chunks:
            c["retrieval_path"] = "graph_expansion"

        return expanded_chunks

    def _get_entity_chunk_ids_for_chunk(
        self,
        graph_store: Neo4jGraphStore,
        notebook_id: str,
        chunk_id: str,
        max_hops: int,
    ) -> Set[str]:
        """
        Queries Neo4j for entities sourced from a chunk_id, then traverses 
        their neighbors to collect associated chunk IDs.
        """
        chunk_ids: Set[str] = set()
        query = """
        MATCH (e:Entity {notebook_id: $notebook_id})
        WHERE $chunk_id IN e.source_chunk_ids
        MATCH (e)-[:RELATION*1..2]-(neighbor:Entity {notebook_id: $notebook_id})
        UNWIND neighbor.source_chunk_ids AS cid
        RETURN DISTINCT cid
        """
        with graph_store.driver.session() as session:
            result = session.run(query, notebook_id=notebook_id, chunk_id=chunk_id)
            for record in result:
                if record["cid"]:
                    chunk_ids.add(record["cid"])
        return chunk_ids

    def _fetch_chunks_by_ids(
        self, notebook_id: str, chunk_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Fetches chunk texts and metadata from ChromaDB by exact chunk IDs."""
        if not chunk_ids:
            return []
        collection = self.vector_store.get_or_create_collection(notebook_id)
        try:
            result = collection.get(
                ids=chunk_ids,
                include=["documents", "metadatas"],
            )
            chunks = []
            for i, cid in enumerate(result.get("ids", [])):
                chunks.append(
                    {
                        "chunk_id": cid,
                        "text": result["documents"][i],
                        "metadata": result["metadatas"][i],
                        "similarity_score": 0.0,
                        "distance": 1.0,
                        "retrieval_path": "graph_expansion",
                    }
                )
            return chunks
        except Exception:
            return []
