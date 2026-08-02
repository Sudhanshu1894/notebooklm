# GraphRAG Research Notebook — Task List

Track progress of each phase as defined in [prompt.md](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/prompt.md).

---

## ✅ Phase 0: Repo Scaffold & Dataset Loader (Complete)
- [x] Create project structure, dependencies (`requirements.txt`), and `.env.example`.
- [x] Commit and push to GitHub (`Sudhanshu1894/notebooklm`).
- [x] `data_loading/loader.py` — HotpotQA downloaded successfully (`hotpotqa/hotpot_qa` namespace fix applied).
- [x] `data_loading/stats.py` — **Train: 90,447 | Validation: 7,405 | Local sample: 200 (150 train + 50 dev)**.
- [x] `tests/test_data_loader.py` — **4/4 passed** ✓

---

## ✅ Phase 1: Service Setup & Connectivity Checks (Complete)
- [x] `config/settings.py` — pydantic-settings env validation.
- [x] `scripts/check_services.py` — Gemini, Neo4j, ChromaDB, Supabase checks.
- [x] ChromaDB local: **PASS**. Gemini/Neo4j/Supabase: SKIP (credentials needed in `.env`).

---

## ✅ Phase 2: Document Ingestion & Chunking Pipeline (Complete)
- [x] `ingestion/parsers.py` — PDF, DOCX, TXT via `ParserRegistry`.
- [x] `ingestion/chunker.py` — 500-token sentence-aware chunks with page/header/offset metadata.
- [x] `ingestion/registry.py` — SQLite document status tracker.
- [x] `tests/test_ingestion.py` — **5/5 passed** ✓
- [x] `ingestion/README.md`

---

## ✅ Phase 3: Embeddings & Vector Store (Complete)
- [x] `embedding/model.py` — singleton `all-MiniLM-L6-v2` (384d) wrapper.
- [x] `vector_store/chroma.py` — notebook-isolated collections, cosine similarity, metadata roundtrip.
- [x] `scripts/index_document.py` — end-to-end ingestion → embedding → ChromaDB script.
- [x] `scripts/test_vector_search.py` — top-k query runner.
- [x] `tests/test_vector_store.py` — **3/3 passed** ✓ (determinism, isolation, metadata).
- [x] `embedding/README.md`, `vector_store/README.md`

---

## ✅ Phase 4: Knowledge Graph Construction (Complete)
- [x] `graph_store/SCHEMA.md` — Entity + RELATION schema with Cypher MERGE contracts.
- [x] `graph_store/extractor.py` — Gemini Flash JSON extractor with retry + code-fence stripping.
- [x] `graph_store/neo4j_client.py` — MERGE upserts, 1-2 hop traversal, full graph export.
- [x] `graph_store/README.md` — rate-limit guidance (10 RPM Gemini free tier).
- [x] `scripts/build_graph.py` — file → chunk → extract → Neo4j pipeline.
- [x] `scripts/query_graph.py` — entity neighbor sanity checker.
- [ ] `tests/test_graph_extractor.py` — *(deferred; requires Gemini key)*

---

## ✅ Phase 5: Hybrid Retrieval (Complete)
- [x] `retrieval/vector_retriever.py` — vector-only ChromaDB path.
- [x] `retrieval/graph_retriever.py` — 1-2 hop Neo4j entity expansion from seed chunks.
- [x] `retrieval/hybrid_reranker.py` — weighted fusion scoring (0.7 vector + 0.3 graph boost), 4000-token budget trim.
- [x] `retrieval/router.py` — heuristic keyword router logging to `data/routing_log.jsonl`.
- [x] `scripts/test_retrieval.py` — side-by-side vector vs hybrid comparison.
- [x] `retrieval/README.md`
- [x] **Committed and pushed** (`a0c1ce8`)

---

## ⚪ Phase 6: Answer Generation with Citations (Next Up)
- [ ] `generation/prompts.py` — Gemini prompt with bracketed `[1]`, `[2]` citation markers.
- [ ] `generation/generator.py` — citation-to-source mapping + "insufficient context" fallback.
- [ ] `scripts/test_generation.py` — end-to-end query → answer with citations.
- [ ] `generation/README.md`

---

## ⚪ Phase 7: FastAPI Backend
- [ ] `api/main.py` — 6 REST endpoints with BackgroundTasks, Pydantic schemas, CORS.
- [ ] `tests/test_api.py` — TestClient integration tests.
- [ ] `api/README.md` with curl examples.

---

## ⚪ Phase 8: Next.js Frontend UI
- [ ] `frontend/` — Next.js scaffold.
- [ ] 3-panel UI: Source List, Chat (clickable citations), Graph Explorer (`react-force-graph`).
- [ ] Real-time processing status polling.

---

## ⚪ Phase 9: Novelty Features
- [ ] 9A: User graph correction loop (Supabase store + negative prompt re-extraction).
- [ ] 9B: Routing analytics summary (log already being written in `data/routing_log.jsonl`).
- [ ] 9C: `edge-tts` two-speaker audio overview synthesis.
- [ ] `NOVELTY.md`

---

## ⚪ Phase 10: Baseline Evaluation
- [ ] `evaluation/harness.py` — Vector vs Graph vs Hybrid on HotpotQA sample.
- [ ] EM + F1 + gold supporting fact recall metrics.
- [ ] `evaluation/README.md`

---

## ⚪ Phase 11: Deployment
- [ ] Render/Railway backend + Vercel frontend.
- [ ] `DEPLOYMENT.md` with cold-start caveats.
