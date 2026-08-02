# GraphRAG Research Notebook — Implementation Plan

> Last updated: 2026-08-02

---

## Project Overview

A full-stack **GraphRAG (Graph Retrieval-Augmented Generation)** research notebook that combines local vector search (ChromaDB + SentenceTransformers) with a Neo4j knowledge graph to enable multi-hop, grounded-citation question answering over uploaded documents. Deployed entirely on free tiers.

---

## Stack (Fixed — Do Not Substitute)

| Component | Technology | Status |
|-----------|-----------|--------|
| LLM / Extraction | Gemini 2.5 Flash (free tier) | Configured |
| Embeddings | `all-MiniLM-L6-v2` (local) | Working ✓ |
| Vector Store | ChromaDB (local embedded) | Working ✓ |
| Graph Store | Neo4j AuraDB Free | Pending credentials |
| Backend | FastAPI + Python | Scaffolded |
| Frontend | Next.js + Tailwind | Pending |
| Auth / Storage | Supabase Free Tier | Pending credentials |
| Audio TTS | `edge-tts` | Phase 9 |

---

## Open Questions

> [!IMPORTANT]
> **Credentials still needed for full pipeline testing:**
> - `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/)
> - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` — from [Neo4j AuraDB Free](https://neo4j.com/cloud/aura-free/)
> - `SUPABASE_URL`, `SUPABASE_KEY` — from [Supabase Free Project](https://supabase.com/)
>
> Configure all in `.env` (see `.env.example`). Run `scripts/check_services.py` to verify.

> [!NOTE]
> **HotpotQA dataset download (`loader.py`)** — the `hotpot_qa` → `hotpotqa/hotpot_qa` namespace fix was applied. Dataset download is running; `data/sample_hotpotqa.json` will be created when complete. Stats & `test_data_loader.py` will be run immediately after.

---

## Phase Progress

### ✅ Phase 0 — Repo Scaffold & Dataset Loader
**Commit:** `Phase 0: Initial repository structure and prompt setup` (`563f2b8`)

- [x] Repository structure, `requirements.txt`, `.env.example`, `.gitignore`
- [x] `data_loading/loader.py` — HotpotQA downloaded, 200-record sample saved to `data/sample_hotpotqa.json`
- [x] `data_loading/stats.py` — **Train: 90,447 | Validation: 7,405 | Local sample: 200 (150 train + 50 dev)**
- [x] `tests/test_data_loader.py` — **4/4 passed** ✓
- [x] Pushed to [Sudhanshu1894/notebooklm](https://github.com/Sudhanshu1894/notebooklm)

**Dataset Stats Output:**
```
Dataset Name    : HotpotQA (distractor subset)
Total Sample    : 200 (150 train + 50 dev)
Question Types  : {'comparison': 45, 'bridge': 155}
Difficulty      : {'medium': 86, 'hard': 78, 'easy': 36}
Context Paragraphs per entry: 10
```
**Warning (non-blocking):** HuggingFace Hub symlink warning on Windows (no Developer Mode). Resolved by `hotpotqa/hotpot_qa` namespace fix.

---

### ✅ Phase 1 — Service Connectivity Checks
**Commit:** `Phase 1 & 2: service connectivity setup and document ingestion pipeline` (`95ae179`)

- [x] [`config/settings.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/config/settings.py) — `pydantic-settings` env loader with `validate_required_keys()`
- [x] [`scripts/check_services.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/scripts/check_services.py) — Gemini, Neo4j, ChromaDB, Supabase connectivity checks
- [x] ChromaDB test: **PASS** (local embedded, no credentials needed)
- [x] Gemini / Neo4j / Supabase: SKIP (credentials not yet in `.env`)

---

### ✅ Phase 2 — Document Ingestion & Chunking
**Commit:** included in `95ae179`

- [x] [`ingestion/parsers.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/ingestion/parsers.py) — PDF (PyMuPDF), DOCX (python-docx), TXT parsers via `ParserRegistry`
- [x] [`ingestion/chunker.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/ingestion/chunker.py) — 500-token sentence-aware chunks, 50-token overlap, character offsets
- [x] [`ingestion/registry.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/ingestion/registry.py) — SQLite document status tracker (uploaded / parsed / chunked / failed)
- [x] [`ingestion/README.md`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/ingestion/README.md) — chunking strategy & rationale
- [x] [`tests/test_ingestion.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/tests/test_ingestion.py) — **5/5 passed** ✓

---

### ✅ Phase 3 — Embeddings & Vector Store
**Commit:** `Phase 3: embedding pipeline and Chroma vector store` (`61ff831`)

- [x] [`embedding/model.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/embedding/model.py) — singleton `EmbeddingModel` wrapping `all-MiniLM-L6-v2` (384d)
- [x] [`vector_store/chroma.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/vector_store/chroma.py) — per-notebook collection isolation, cosine similarity, metadata roundtrip
- [x] [`scripts/index_document.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/scripts/index_document.py) — end-to-end ingestion → embed → ChromaDB pipeline
- [x] [`scripts/test_vector_search.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/scripts/test_vector_search.py) — top-k similarity query runner
- [x] [`embedding/README.md`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/embedding/README.md), [`vector_store/README.md`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/vector_store/README.md)
- [x] [`tests/test_vector_store.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/tests/test_vector_store.py) — **3/3 passed** ✓ (determinism, collection isolation, metadata survival)
- [x] Deprecated `get_sentence_embedding_dimension` → `get_embedding_dimension` fixed

---

### 🔄 Phase 4 — Knowledge Graph Construction (In Progress)
**Planned Commit:** `Phase 4: LLM-based entity/relationship extraction into Neo4j`

- [x] [`graph_store/SCHEMA.md`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/graph_store/SCHEMA.md) — Entity node & RELATION edge spec with Cypher MERGE contracts
- [x] [`graph_store/extractor.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/graph_store/extractor.py) — Gemini Flash JSON extraction with retry logic + markdown code fence stripping
- [x] [`graph_store/neo4j_client.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/graph_store/neo4j_client.py) — MERGE upserts, 1-2 hop neighbor traversal, full graph export for frontend
- [x] [`graph_store/README.md`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/graph_store/README.md) — rate-limit guidance (1 Gemini call/chunk, 10 RPM limit)
- [x] [`scripts/build_graph.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/scripts/build_graph.py) — parse → chunk → extract → Neo4j upsert pipeline
- [x] [`scripts/query_graph.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/scripts/query_graph.py) — entity neighbor sanity check
- [ ] `tests/test_graph_extractor.py` — unit test with fixed sample chunks
- [ ] Commit Phase 4

---

### 🔄 Phase 5 — Hybrid Retrieval (In Progress)
**Planned Commit:** `Phase 5: hybrid vector + graph retrieval with query routing`

- [x] [`retrieval/vector_retriever.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/retrieval/vector_retriever.py) — vector-only path
- [x] [`retrieval/graph_retriever.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/retrieval/graph_retriever.py) — 1-2 hop graph expansion from vector seed chunks
- [x] [`retrieval/hybrid_reranker.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/retrieval/hybrid_reranker.py) — weighted fusion scoring, dedup, 4000-token budget trim
- [x] [`retrieval/router.py`](file:///c:/Users/Sudhanshu%20Singh/.gemini/antigravity-ide/scratch/graphrag-research-notebook/retrieval/router.py) — heuristic keyword router with JSONL analytics logging
- [ ] `scripts/test_retrieval.py` — side-by-side vector vs hybrid comparison
- [ ] `retrieval/README.md` — routing heuristic documentation
- [ ] Commit Phase 5

---

### ⚪ Phase 6 — Cited Answer Generation
- [ ] `generation/prompts.py` — Gemini grounded prompt with `[1]`, `[2]` citation markers
- [ ] `generation/generator.py` — citation-to-source mapping, "insufficient context" fallback
- [ ] `scripts/test_generation.py` — end-to-end query → citations test
- [ ] `generation/README.md`

---

### ⚪ Phase 7 — FastAPI Backend
- [ ] `api/main.py` — POST `/notebooks`, `/documents`, GET `/status`, POST `/chat`, GET `/graph`, GET `/sources`
- [ ] BackgroundTasks for document processing (ingestion + embedding + graph build)
- [ ] Pydantic request/response schemas, CORS, error handling
- [ ] `tests/test_api.py` — integration tests with `TestClient`
- [ ] `api/README.md` with curl examples

---

### ⚪ Phase 8 — Next.js Frontend
- [ ] `frontend/` — Next.js app scaffold
- [ ] 3-panel UI: Source List, Chat (clickable citations), Graph Explorer (`react-force-graph`)
- [ ] Real-time document processing polling
- [ ] `frontend/README.md`

---

### ⚪ Phase 9 — Novelty Features
- [ ] **9A** — User graph correction loop (flag entity → Supabase → negative prompt re-extraction)
- [ ] **9B** — Routing analytics summary script (`routing_log.jsonl` already being populated)
- [ ] **9C** — `edge-tts` two-speaker audio overview generation
- [ ] `NOVELTY.md`

---

### ⚪ Phase 10 — Evaluation Harness
- [ ] `evaluation/harness.py` — Vector vs Graph vs Hybrid on HotpotQA sample
- [ ] EM + F1 + gold supporting fact recall metrics
- [ ] `evaluation/README.md`

---

### ⚪ Phase 11 — Free-Tier Deployment
- [ ] Render/Railway FastAPI backend + Vercel Next.js frontend
- [ ] `DEPLOYMENT.md` — cold-start caveats, free-tier limits

---

## Current File Structure

```
graphrag-research-notebook/
├── config/
│   └── settings.py            ✓ Phase 1
├── data_loading/
│   ├── loader.py              ✓ Phase 0 (HF namespace fix applied)
│   └── stats.py               ✓ Phase 0
├── embedding/
│   ├── model.py               ✓ Phase 3
│   └── README.md              ✓ Phase 3
├── graph_store/
│   ├── SCHEMA.md              ✓ Phase 4
│   ├── extractor.py           ✓ Phase 4
│   ├── neo4j_client.py        ✓ Phase 4
│   └── README.md              ✓ Phase 4
├── ingestion/
│   ├── parsers.py             ✓ Phase 2
│   ├── chunker.py             ✓ Phase 2
│   ├── registry.py            ✓ Phase 2
│   └── README.md              ✓ Phase 2
├── retrieval/
│   ├── vector_retriever.py    ✓ Phase 5
│   ├── graph_retriever.py     ✓ Phase 5
│   ├── hybrid_reranker.py     ✓ Phase 5
│   └── router.py              ✓ Phase 5
├── generation/                ◻ Phase 6
├── vector_store/
│   ├── chroma.py              ✓ Phase 3
│   └── README.md              ✓ Phase 3
├── scripts/
│   ├── check_services.py      ✓ Phase 1
│   ├── index_document.py      ✓ Phase 3
│   ├── test_vector_search.py  ✓ Phase 3
│   ├── build_graph.py         ✓ Phase 4
│   └── query_graph.py         ✓ Phase 4
├── tests/
│   ├── test_data_loader.py    ✓ Phase 0
│   ├── test_ingestion.py      ✓ Phase 2 (5/5 passed)
│   └── test_vector_store.py   ✓ Phase 3 (3/3 passed)
├── api/                       ◻ Phase 7
├── frontend/                  ◻ Phase 8
├── .env.example               ✓
├── requirements.txt           ✓ (pymupdf, python-docx added)
└── prompt.md                  ✓
```

---

## Verification Plan

```powershell
# Phase 0 — Data Loader & Tests
.\venv\Scripts\python.exe -m data_loading.loader
.\venv\Scripts\python.exe data_loading/stats.py
.\venv\Scripts\python.exe -m pytest tests/test_data_loader.py -v

# Phase 1 — Service Connectivity
.\venv\Scripts\python.exe scripts/check_services.py

# Phase 2 — Ingestion Tests (5/5 PASSED)
.\venv\Scripts\python.exe -m pytest tests/test_ingestion.py -v

# Phase 3 — Vector Store Tests (3/3 PASSED)
.\venv\Scripts\python.exe -m pytest tests/test_vector_store.py -v

# Phase 4 — Graph Build (requires NEO4J + GEMINI creds)
.\venv\Scripts\python.exe scripts/build_graph.py --file <path> --notebook demo

# Phase 5 — Side-by-side retrieval comparison
.\venv\Scripts\python.exe scripts/test_retrieval.py --query "..." --notebook demo
```
