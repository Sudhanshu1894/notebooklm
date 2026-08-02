"""
Unit tests for Retrieval module (Router & Hybrid Reranker).
"""

import pytest
from retrieval.router import QueryRouter
from retrieval.hybrid_reranker import HybridReranker


def test_query_router_classification():
    router = QueryRouter(log_routing=False)

    # Multi-hop queries
    route1, reason1 = router.classify("Which magazine was started first Arthur's Magazine or First for Women?")
    assert route1 == "hybrid"

    route2, reason2 = router.classify("What is the relationship between Scott Derrickson and Marvel?")
    assert route2 == "hybrid"

    route3, reason3 = router.classify("Are both directors from the same country?")
    assert route3 == "hybrid"

    # Single-hop queries
    route4, reason4 = router.classify("What is GraphRAG?")
    assert route4 == "vector_only"

    route5, reason5 = router.classify("Summarize chapter 3.")
    assert route5 == "vector_only"


def test_hybrid_reranker_merge_and_dedup():
    reranker = HybridReranker(vector_weight=0.7, graph_boost=0.3, token_budget=1000)

    vector_chunks = [
        {
            "chunk_id": "chunk_1",
            "text": "Vector chunk 1 content.",
            "similarity_score": 0.8,
            "metadata": {"doc_id": "doc1", "page_number": 1},
        },
        {
            "chunk_id": "chunk_2",
            "text": "Vector chunk 2 content.",
            "similarity_score": 0.5,
            "metadata": {"doc_id": "doc1", "page_number": 2},
        },
    ]

    graph_chunks = [
        {
            "chunk_id": "chunk_2",  # Overlaps with vector chunk
            "text": "Vector chunk 2 content.",
            "metadata": {"doc_id": "doc1", "page_number": 2},
        },
        {
            "chunk_id": "chunk_3",  # Graph-only chunk
            "text": "Graph chunk 3 content.",
            "metadata": {"doc_id": "doc2", "page_number": 1},
        },
    ]

    results = reranker.merge_and_rerank(vector_chunks, graph_chunks)

    assert len(results) == 3
    # Check chunk_2 got boosted (0.5 * 0.7 + 0.3 = 0.65) vs chunk_1 (0.8 * 0.7 = 0.56)
    # chunk_2 should be ranked top
    assert results[0]["chunk_id"] == "chunk_2"
    assert results[0]["in_vector"] is True
    assert results[0]["in_graph"] is True

    # Check chunk_3 is included as graph-only
    chunk_3_item = next(r for r in results if r["chunk_id"] == "chunk_3")
    assert chunk_3_item["in_vector"] is False
    assert chunk_3_item["in_graph"] is True
    assert chunk_3_item["fusion_score"] == 0.3
