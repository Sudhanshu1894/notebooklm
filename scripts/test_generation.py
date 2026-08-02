"""
End-to-end Generation Test Script for GraphRAG Research Notebook.
Runs retrieval → generation and prints the cited answer.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retrieval.router import QueryRouter
from retrieval.vector_retriever import VectorRetriever
from retrieval.graph_retriever import GraphRetriever
from retrieval.hybrid_reranker import HybridReranker
from generation.generator import AnswerGenerator
from config.settings import get_settings


def run_generation(query: str, notebook_id: str = "default_notebook", top_k: int = 5):
    print("=" * 70)
    print("          GRAPHRAG FULL PIPELINE — RETRIEVAL + GENERATION          ")
    print("=" * 70)
    print(f"Query    : {query}")
    print(f"Notebook : {notebook_id}")
    print("-" * 70)

    settings = get_settings()

    # Route
    router = QueryRouter(log_routing=True)
    route, reason, latency = router.route(query, notebook_id=notebook_id)
    print(f"[router] {route.upper()} ({latency}ms) — {reason}")

    # Retrieve
    vector_retriever = VectorRetriever()
    vector_chunks = vector_retriever.retrieve(query, notebook_id=notebook_id, top_k=top_k)
    print(f"[vector] Retrieved {len(vector_chunks)} chunks")

    context_chunks = vector_chunks
    if route == "hybrid" and settings.neo4j_uri:
        graph_retriever = GraphRetriever()
        graph_chunks = graph_retriever.expand_via_graph(notebook_id, vector_chunks)
        reranker = HybridReranker()
        context_chunks = reranker.merge_and_rerank(vector_chunks, graph_chunks)
        print(f"[hybrid] Merged to {len(context_chunks)} chunks after graph expansion")

    if not context_chunks:
        print("\n[!] No context found. Index a document first using scripts/index_document.py")
        return

    # Generate
    print("[generation] Calling Gemini Flash...")
    generator = AnswerGenerator()
    result = generator.generate(query, context_chunks)

    print("\n" + "=" * 70)
    print("ANSWER:")
    print(result["answer_text"])
    print("\nCITATIONS:")
    for c in result["citations"]:
        print(f"  [{c['citation_number']}] {c['doc_id']} | Page {c['page_number']} | {c['text_preview'][:100]}...")
    print("=" * 70)
    return result


def main():
    parser = argparse.ArgumentParser(description="Test full generation pipeline.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--notebook", default="default_notebook")
    parser.add_argument("--top_k", type=int, default=5)
    args = parser.parse_args()
    run_generation(args.query, notebook_id=args.notebook, top_k=args.top_k)


if __name__ == "__main__":
    main()
