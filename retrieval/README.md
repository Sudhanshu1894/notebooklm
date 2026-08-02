# Retrieval Module — Hybrid Vector + Graph Retrieval

## Overview
The `retrieval/` module implements a two-path retrieval system: **vector-only** (fast, single-hop) and **hybrid** (graph-augmented, multi-hop). A query router decides the path automatically based on query characteristics.

---

## Architecture

```
User Query
    │
    ▼
[router.py] ─── heuristic keyword classification
    │
    ├─── "vector_only" ──► [vector_retriever.py] ──► ChromaDB top-k
    │
    └─── "hybrid" ──────► [vector_retriever.py] ──► ChromaDB top-k
                               │
                               ▼
                          [graph_retriever.py] ──► Neo4j 1-2 hop expansion
                               │
                               ▼
                          [hybrid_reranker.py] ──► Weighted fusion + dedup + token trim
```

---

## Routing Heuristic (`router.py`)
Queries containing relational keywords trigger the hybrid path:
- `"both"`, `"same"`, `"common"`, `"shared"`
- `"connect"`, `"link"`, `"relationship between"`
- `"compared to"`, `"vs."`, `"versus"`
- `"caused by"`, `"results in"`, `"leads to"`

All routing decisions are logged to `data/routing_log.jsonl` for Phase 9B analytics.

---

## Merge/Rerank Scoring (`hybrid_reranker.py`)
- **Vector chunks**: `score = similarity_score × 0.7`
- **Graph-expanded chunks**: `score += 0.3` boost
- **Chunks in both**: receive combined score
- Context trimmed to ~**4,000 token budget** (~16,000 chars) for generation

---

## Scripts

### Side-by-side vector vs hybrid comparison:
```powershell
.\venv\Scripts\python.exe scripts/test_retrieval.py --query "Were Scott Derrickson and Ed Wood of the same nationality?" --notebook demo
```

### Vector-only search:
```powershell
.\venv\Scripts\python.exe scripts/test_vector_search.py --query "What is GraphRAG?" --notebook demo
```
