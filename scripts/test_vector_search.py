"""
Vector Search Test Script for GraphRAG Research Notebook.
Embeds a query string and searches ChromaDB for top-k matching chunks.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embedding.model import EmbeddingModel
from vector_store.chroma import VectorStore


def search_vectors(query: str, notebook_id: str = "default_notebook", top_k: int = 5):
    """
    Embeds search query and retrieves top-k matching chunks from ChromaDB.
    """
    print("=" * 65)
    print("           GRAPHRAG VECTOR SEARCH QUERY TEST           ")
    print("=" * 65)
    print(f"Query       : '{query}'")
    print(f"Notebook ID : '{notebook_id}'")
    print(f"Top K       : {top_k}")
    print("-" * 65)

    embedder = EmbeddingModel()
    query_vector = embedder.embed_query(query)

    vector_store = VectorStore()
    matches = vector_store.query_similar_chunks(
        notebook_id=notebook_id,
        query_embedding=query_vector,
        top_k=top_k,
    )

    if not matches:
        print("No matching chunks found in vector store.")
        return []

    print(f"Retrieved {len(matches)} matching chunks:\n")
    for idx, m in enumerate(matches, start=1):
        meta = m["metadata"]
        doc_id = meta.get("doc_id", "N/A")
        page_num = meta.get("page_number", "N/A")
        sec_header = meta.get("section_header", "")
        header_str = f" | Section: {sec_header}" if sec_header else ""

        print(f"[{idx}] Score: {m['similarity_score']} (Distance: {m['distance']:.4f})")
        print(f"    Chunk ID : {m['chunk_id']} (Doc: {doc_id} | Page: {page_num}{header_str})")
        print(f"    Text     : \"{m['text'].strip()[:200]}...\"")
        print("-" * 65)

    return matches


def main():
    parser = argparse.ArgumentParser(description="Test ChromaDB vector similarity search.")
    parser.add_argument("--query", required=True, help="Text query to search for")
    parser.add_argument("--notebook", default="default_notebook", help="Notebook ID")
    parser.add_argument("--top_k", type=int, default=5, help="Number of results")

    args = parser.parse_args()
    search_vectors(args.query, notebook_id=args.notebook, top_k=args.top_k)


if __name__ == "__main__":
    main()
