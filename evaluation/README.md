# GraphRAG Benchmark Evaluation Module

This module implements the **Phase 10 Evaluation Harness** for benchmarking the GraphRAG system against standard retrieval configurations on the **HotpotQA** multi-hop question answering benchmark.

---

## 🎯 Benchmark Objectives

To prove the effectiveness of Knowledge Graph integration, the evaluation harness compares three retrieval strategies under identical conditions:

1. **Vector-Only**: Dense semantic similarity search using ChromaDB (`all-MiniLM-L6-v2` embeddings).
2. **Graph-Only**: Entity-based subgraph traversal linking shared named entities across candidate paragraphs.
3. **Hybrid GraphRAG**: Weighted fusion reranking combining dense vector similarity ($0.7$) with graph relational expansion boost ($0.3$).

---

## 📊 Evaluated Metrics

| Metric | Type | Description |
| :--- | :--- | :--- |
| **Supporting Fact Recall (%)** | Retrieval | Percentage of ground-truth supporting facts retrieved in the context window. |
| **F1 Score (%)** | Generation | Token-level precision and recall harmonic mean between predicted answer and gold answer. |
| **Exact Match (EM) (%)** | Generation | Normalized string equality between predicted answer and gold ground-truth. |
| **Average Latency (s)** | Performance | Retrieval query execution time per question. |

---

## 🚀 How to Run the Evaluation

### 1. Fast Retrieval-Only Evaluation (No LLM Calls)
Runs retrieval comparison instantly across questions without calling Gemini API:
```bash
python -m evaluation.harness --sample-size 10 --no-llm
```

### 2. Full End-to-End Evaluation (Retrieval + LLM Generation)
Runs both retrieval comparison and Gemini Flash answer generation to measure EM, F1, and Fact Recall:
```bash
python -m evaluation.harness --sample-size 5
```

### 3. Custom Dataset / Split
```bash
python -m evaluation.harness --dataset data/sample_hotpotqa.json --split dev --sample-size 20
```

---

## 📁 Output Artifacts

Running the evaluation harness generates:
- **`evaluation/results/benchmark_report.md`**: Markdown formatted comparison table with key findings.
- **`evaluation/results/benchmark_summary.json`**: Raw numerical scores across all three configurations for reporting.
