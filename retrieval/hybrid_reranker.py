"""
Hybrid Reranker for GraphRAG Research Notebook.
Merges and deduplicates vector-retrieved and graph-expanded chunks,
scores them with weighted fusion, and trims to a token budget.
"""

from typing import List, Dict, Any


# Target token budget for generation context (~4000 tokens ≈ 16000 chars)
DEFAULT_TOKEN_BUDGET = 4000
CHARS_PER_TOKEN = 4


class HybridReranker:
    """
    Merges vector search hits and graph expansion chunks into a
    single ranked, deduplicated context list within a token budget.
    """

    def __init__(
        self,
        vector_weight: float = 0.7,
        graph_boost: float = 0.3,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ):
        """
        Args:
            vector_weight: Weight applied to vector similarity scores.
            graph_boost: Additive boost given to graph-expanded chunks.
            token_budget: Max output tokens for the merged context.
        """
        self.vector_weight = vector_weight
        self.graph_boost = graph_boost
        self.char_budget = token_budget * CHARS_PER_TOKEN

    def merge_and_rerank(
        self,
        vector_chunks: List[Dict[str, Any]],
        graph_chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Combines and reranks vector and graph-expanded chunks.

        Scoring logic:
        - Vector-retrieved chunks: score = similarity_score * vector_weight
        - Graph-expanded chunks: score = graph_boost (flat, since no cosine score)
        - Chunks appearing in BOTH: score = (similarity_score * vector_weight) + graph_boost

        Returns:
            Deduplicated, ranked list trimmed to the character budget.
        """
        seen_ids: Dict[str, Dict[str, Any]] = {}

        # Process vector chunks first
        for chunk in vector_chunks:
            cid = chunk["chunk_id"]
            base_score = chunk.get("similarity_score", 0.0) * self.vector_weight
            chunk["fusion_score"] = round(base_score, 4)
            chunk["in_vector"] = True
            chunk["in_graph"] = False
            seen_ids[cid] = chunk

        # Merge graph chunks — boost if also in vector results
        for chunk in graph_chunks:
            cid = chunk["chunk_id"]
            if cid in seen_ids:
                # Boost existing entry
                existing = seen_ids[cid]
                existing["fusion_score"] = round(
                    existing["fusion_score"] + self.graph_boost, 4
                )
                existing["in_graph"] = True
            else:
                chunk["fusion_score"] = round(self.graph_boost, 4)
                chunk["in_vector"] = False
                chunk["in_graph"] = True
                seen_ids[cid] = chunk

        # Sort by fusion score descending
        ranked = sorted(seen_ids.values(), key=lambda x: x["fusion_score"], reverse=True)

        # Trim to token/character budget
        trimmed = []
        total_chars = 0
        for chunk in ranked:
            chunk_len = len(chunk.get("text", ""))
            if total_chars + chunk_len > self.char_budget:
                break
            trimmed.append(chunk)
            total_chars += chunk_len

        return trimmed
