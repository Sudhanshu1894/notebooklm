"""
ChromaDB Vector Store Wrapper for GraphRAG Research Notebook.
Handles persistent collection management per notebook, chunk indexing, and similarity search.
"""

import os
from typing import List, Dict, Any, Optional
import chromadb
from config.settings import get_settings
from ingestion.chunker import DocumentChunk


class VectorStore:
    """
    ChromaDB wrapper maintaining persistent vector search indices isolated by notebook_id.
    """
    def __init__(self, persist_dir: Optional[str] = None):
        settings = get_settings()
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        os.makedirs(os.path.abspath(self.persist_dir), exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)

    def _get_collection_name(self, notebook_id: str) -> str:
        """Sanitizes notebook_id into valid ChromaDB collection name."""
        clean_id = "".join(c if c.isalnum() else "_" for c in notebook_id)
        return f"notebook_{clean_id}"

    def get_or_create_collection(self, notebook_id: str):
        """Retrieves or creates isolated ChromaDB collection for a notebook."""
        name = self._get_collection_name(notebook_id)
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(
        self,
        notebook_id: str,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> int:
        """
        Upserts document chunks and their precomputed embeddings into the notebook collection.

        Returns:
            Number of chunks indexed.
        """
        if not chunks:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks provided but {len(embeddings)} embeddings."
            )

        collection = self.get_or_create_collection(notebook_id)

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "section_header": chunk.section_header or "",
                "start_char_offset": chunk.start_char_offset,
                "end_char_offset": chunk.end_char_offset,
            }
            for chunk in chunks
        ]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(chunks)

    def query_similar_chunks(
        self,
        notebook_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        doc_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries top-k similar chunks from a notebook collection.

        Args:
            notebook_id: Notebook ID target.
            query_embedding: Precomputed query embedding vector.
            top_k: Number of results to return.
            doc_id: Optional doc_id metadata filter.

        Returns:
            List of matching records with similarity score, text, and metadata.
        """
        collection = self.get_or_create_collection(notebook_id)

        where_filter = {"doc_id": doc_id} if doc_id else None

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        matches = []
        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]

            for i in range(len(ids)):
                # Convert cosine distance to similarity score (1 - distance)
                distance = distances[i] if distances else 0.0
                similarity_score = max(0.0, 1.0 - distance)

                matches.append(
                    {
                        "chunk_id": ids[i],
                        "text": docs[i],
                        "metadata": metas[i],
                        "distance": distance,
                        "similarity_score": round(similarity_score, 4),
                    }
                )

        return matches

    def delete_notebook_collection(self, notebook_id: str) -> bool:
        """Deletes collection associated with a notebook ID."""
        name = self._get_collection_name(notebook_id)
        try:
            self.client.delete_collection(name)
            return True
        except Exception:
            return False
