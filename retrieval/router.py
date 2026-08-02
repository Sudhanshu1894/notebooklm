"""
Query Router for GraphRAG Research Notebook.
Classifies queries as single-hop/factual (vector-only) or multi-hop/relational (hybrid)
and logs routing decisions with latency for Phase 9B analytics.
"""

import re
import time
import json
import os
from typing import Tuple, Optional
from datetime import datetime


# Multi-hop keywords that signal relational queries needing graph traversal
MULTI_HOP_PATTERNS = [
    r"\b(both|same|common|shared)\b",
    r"\b(connect|link|relate|relationship|between)\b",
    r"\b(compared? to|vs\.?|versus|differ)\b",
    r"\b(who|what|which).{0,40}(and|also|both|or)\b",
    r"\b(first|earlier|before|after|older|newer|prior|later)\b",
    r"\b(cause[sd]?|result[s]? in|lead[s]? to|because of)\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in MULTI_HOP_PATTERNS]

ROUTING_LOG_PATH = "./data/routing_log.jsonl"


class QueryRouter:
    """
    Lightweight heuristic-based query router with optional Gemini classification fallback.
    Logs routing decisions for Phase 9B analytics evaluation.
    """

    def __init__(self, log_routing: bool = True):
        self.log_routing = log_routing

    def classify(self, query: str) -> Tuple[str, str]:
        """
        Classifies a query as 'vector_only' or 'hybrid'.

        Returns:
            Tuple of (route: str, reason: str)
        """
        for pattern in COMPILED_PATTERNS:
            if pattern.search(query):
                return "hybrid", f"Matched multi-hop pattern: '{pattern.pattern}'"

        return "vector_only", "No multi-hop keywords detected; routing to vector-only."

    def route(
        self,
        query: str,
        notebook_id: str = "default",
    ) -> Tuple[str, str, float]:
        """
        Routes the query, logs the decision, and returns route+reason+latency.

        Returns:
            Tuple of (route, reason, routing_latency_ms)
        """
        t0 = time.perf_counter()
        route, reason = self.classify(query)
        latency_ms = round((time.perf_counter() - t0) * 1000, 3)

        if self.log_routing:
            self._log(query, notebook_id, route, reason, latency_ms)

        return route, reason, latency_ms

    def _log(
        self,
        query: str,
        notebook_id: str,
        route: str,
        reason: str,
        latency_ms: float,
    ):
        """Appends routing decision to JSONL log file for analytics."""
        os.makedirs(os.path.dirname(os.path.abspath(ROUTING_LOG_PATH)), exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "notebook_id": notebook_id,
            "query": query,
            "route": route,
            "reason": reason,
            "routing_latency_ms": latency_ms,
        }
        with open(ROUTING_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
