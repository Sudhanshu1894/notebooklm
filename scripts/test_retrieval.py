"""
Side-by-side Retrieval Comparison Script for GraphRAG Research Notebook.
Runs vector-only and hybrid retrieval for the same query and prints both result sets.
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retrieval.router import QueryRouter
from retrieval.vector_retriever import VectorRetriever
from retrieval.graph_retriever import GraphRetriever
from retrieval.hybrid_reranker import HybridReranker


def compare_retrieval(query: str, notebook_id: str = "default_notebook", top_k: int = 5):
    print("=" * 70)
    print("         GRAPHRAG HYBRID vs VECTOR RETRIEVAL COMPARISON         ")
    print("=" * 70)
    print(f"Query      : '{query}'")
    print(f"Notebook   : '{notebook_id}'")
    print("-" * 70)

    # 1. Route query
    router = QueryRouter(log_routing=True)
    route, reason, latency_ms = router.route(query, notebook_id=notebook_id)
    print(f"[router] Route: {route.upper()} ({latency_ms}ms) — {reason}")
    print("-" * 70)

    # 2. Vector-only retrieval
    t0 = time.perf_counter()
    vector_retriever = VectorRetriever()
    vector_results = vector_retriever.retrieve(query, notebook_id=notebook_id, top_k=top_k)
    vector_latency = round((time.perf_counter() - t0) * 1000, 1)

    print(f"\n[VECTOR-ONLY] {len(vector_results)} results ({vector_latency}ms):")
    for i, r in enumerate(vector_results, 1):
        meta = r["metadata"]
        print(f"  [{i}] Score={r['similarity_score']} | Doc={meta.get('doc_id')} | Page={meta.get('page_number')}")
        print(f"       \"{r['text'].strip()[:150]}...\"")

    # 3. Graph-augmented hybrid retrieval
    t1 = time.perf_counter()
    graph_retriever = GraphRetriever()
    graph_expanded = graph_retriever.expand_via_graph(notebook_id, vector_results)
    reranker = HybridReranker()
    hybrid_results = reranker.merge_and_rerank(vector_results, graph_expanded)
    hybrid_latency = round((time.perf_counter() - t1) * 1000, 1)

    print(f"\n[HYBRID] {len(hybrid_results)} results after graph expansion ({hybrid_latency}ms):")
    for i, r in enumerate(hybrid_results, 1):
        meta = r["metadata"]
        path = r.get("retrieval_path", "?")
        print(f"  [{i}] FusionScore={r.get('fusion_score')} | Path={path} | Doc={meta.get('doc_id')} | Page={meta.get('page_number')}")
        print(f"       \"{r['text'].strip()[:150]}...\"")

    # 4. Summary
    graph_only_ids = {r["chunk_id"] for r in graph_expanded}
    vector_only_ids = {r["chunk_id"] for r in vector_results}
    new_via_graph = graph_only_ids - vector_only_ids

    print(f"\n[summary] Graph expansion added {len(new_via_graph)} new chunk(s) not in vector results.")
    print("=" * 70)
    return {"vector": vector_results, "hybrid": hybrid_results}


def main():
    parser = argparse.ArgumentParser(description="Compare vector-only vs hybrid retrieval.")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--notebook", default="default_notebook", help="Notebook ID")
    parser.add_argument("--top_k", type=int, default=5, help="Top-k results")
    args = parser.parse_args()
    compare_retrieval(args.query, notebook_id=args.notebook, top_k=args.top_k)


if __name__ == "__main__":
    main()
