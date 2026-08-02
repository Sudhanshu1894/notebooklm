"""
Vector-only Retriever for GraphRAG Research Notebook.
Retrieves top-k chunks from ChromaDB based on vector similarity.
"""

from typing import List, Dict, Any, Optional
from embedding.model import EmbeddingModel
from vector_store.chroma import VectorStore


class VectorRetriever:
    """Pure vector similarity retriever using ChromaDB."""

    def __init__(self):
        self.embedder = EmbeddingModel()
        self.vector_store = VectorStore()

    def retrieve(
        self,
        query: str,
        notebook_id: str,
        top_k: int = 5,
        doc_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Embeds the query and retrieves top-k chunks by cosine similarity.

        Returns:
            List of chunk dicts with text, metadata, and similarity_score.
        """
        query_embedding = self.embedder.embed_query(query)
        matches = self.vector_store.query_similar_chunks(
            notebook_id=notebook_id,
            query_embedding=query_embedding,
            top_k=top_k,
            doc_id=doc_id,
        )
        # Tag retrieval path
        for m in matches:
            m["retrieval_path"] = "vector"
        return matches
