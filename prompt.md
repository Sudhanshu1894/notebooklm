# Agent Build Instructions — GraphRAG Research Notebook

This file contains instructions for the remaining final phases of the project.
**Phases 0 through 9 are fully implemented, verified, and merged.**

---

## Global Constraints (Apply to Every Phase)

- **Free tier only.** No paid APIs, no credit-card-required services, no services that silently start billing past a quota.
- **Stack is fixed**:
  - LLM + entity extraction: Gemini API (`gemini-flash-latest` / `gemini-3.6-flash`)
  - Local SLM: Hugging Face Transformers (`Qwen2.5-0.5B`) & Ollama
  - Embeddings: `sentence-transformers` (local, `all-MiniLM-L6-v2`)
  - Vector store: ChromaDB (local, embedded)
  - Graph store: Neo4j AuraDB Free
  - Backend: FastAPI (Python)
  - Frontend: Next.js 16 + Tailwind CSS
  - Auth / Relational DB: Supabase Free Tier
  - Audio TTS: `edge-tts`
- **Secrets never hardcoded.** All credentials load through `.env`.
- **Quality & Testing**: Automated tests must remain passing.

---

## 🏁 Phase Implementation Status Summary

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 0** | Repo scaffold, HotpotQA data loader & stats | ✅ Completed |
| **Phase 1** | Free-tier service setup & connectivity checks | ✅ Completed |
| **Phase 2** | Document ingestion (PDF, DOCX, TXT), chunking & SQLite registry | ✅ Completed |
| **Phase 3** | Local sentence embeddings & ChromaDB vector store | ✅ Completed |
| **Phase 4** | Knowledge graph schema, Gemini entity extraction & Neo4j | ✅ Completed |
| **Phase 5** | Hybrid vector + graph retrieval with heuristic routing | ✅ Completed |
| **Phase 6** | Answer generation with bracketed inline citations `[1]`, `[2]` | ✅ Completed |
| **Phase 7** | FastAPI backend with async background tasks & Swagger docs | ✅ Completed |
| **Phase 8** | Next.js 16 + React 19 3-panel UI & Graph Explorer | ✅ Completed |
| **Phase 9** | Novelty: Audio overview (`edge-tts`), Routing analytics, PPTX, Local SLM | ✅ Completed |
| **Phase 10** | Baseline evaluation on HotpotQA sample (EM, F1, Recall) | 🔄 In Progress |
| **Phase 11** | Free-tier deployment (Render/Railway backend + Vercel frontend) | ⚪ Next Up |

---

## Phase 10 — Evaluation Against Baselines

**Goal:** Benchmark the system against baseline retrieval configurations on the HotpotQA sample dataset (`data/sample_hotpotqa.json`).

```
Build an evaluation harness in evaluation/ using the HotpotQA sample dataset:

1. Implement three retrieval configurations to compare:
   - Vector-only (dense semantic similarity via ChromaDB)
   - Graph-only (entity-based subgraph traversal via Neo4j)
   - Hybrid (weighted fusion reranker: 0.7 vector + 0.3 graph boost)

2. For each configuration, run the evaluation subset through the retrieval -> generation pipeline:
   - Score answers against ground-truth gold answers using standard QA metrics:
     * Exact Match (EM)
     * Token-level F1 score
   - Also evaluate retrieval-only metrics:
     * Gold supporting fact recall (% of supporting facts found in retrieved context)

3. Output a comparative results table (Markdown and CSV) comparing all three configurations.

4. Write evaluation/README.md explaining the metrics, dataset subset size, and how to reproduce a run.
```

**Verify:** Run `python -m evaluation.harness --sample-size 10` and confirm metrics compute cleanly.

---

## Phase 11 — Free-Tier Deployment

**Goal:** A live, production-grade deployment running entirely on free tiers.

```
Deploy the full stack:

1. Deploy the FastAPI backend to Render free tier (or Railway free credits):
   - Configure start command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
   - Configure environment variables in dashboard (GEMINI_API_KEY, NEO4J_URI, etc.).

2. Deploy the Next.js frontend to Vercel free tier:
   - Set NEXT_PUBLIC_API_URL to the deployed backend URL.
   - Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.

3. Confirm Neo4j AuraDB Free and Supabase are reachable from the deployed cloud instances.

4. Create DEPLOYMENT.md documenting live URLs, redeployment steps, and free-tier caveats (e.g. cold starts).
```

**Verify:** Complete a live browser smoke test: create a notebook, upload a document, ask a question, verify citations and graph visualization.
