# GraphRAG Research Notebook

> A production-grade hybrid Retrieval-Augmented Generation (RAG) and Knowledge Graph system built using strict free-tier and open-source tools for research document exploration, multi-hop reasoning, and interactive learning.

---

## 📌 Project Overview
The **GraphRAG Research Notebook** integrates semantic vector similarity search with structured knowledge graph traversal to answer complex, multi-hop research questions across academic and technical documents. By combining dense passage embeddings with entity-relationship subgraphs extracted into Neo4j, the system grounds every generated answer with verifiable inline citations.

Beyond standard Q&A, the platform offers an interactive **3-panel workspace** featuring automated Quiz Generation, Socratic Teaching Mode, Interactive Graph Exploration, Two-Speaker Audio Overviews via `edge-tts`, and local Small Language Model (SLM) fallback support.

---

## 🛠️ Tech Stack & Tool Architecture

| Layer | Selected Tool / Library | Tier | Role & Why Chosen |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | **Next.js 16 (App Router) + Tailwind CSS + Lucide** | Open Source | Modern, responsive 3-panel notebook interface with real-time status polling and clickable citations. |
| **Interactive Graph Visualizer** | **react-force-graph-2d** | Open Source | 2D physics-directed canvas graph explorer for navigating entities and multi-hop relationships. |
| **Backend Framework** | **FastAPI + Uvicorn** | Open Source | Asynchronous high-throughput Python REST API with auto-generated Swagger documentation. |
| **Primary LLM** | **Gemini Flash (`gemini-flash-latest` / `gemini-3.6-flash`)** | Free Tier | Ultra-fast inference with long-context windows for synthesis, citation extraction, and KG building. |
| **Local SLM & Fine-Tuning** | **Hugging Face Transformers (`Qwen2.5-0.5B`) & Ollama** | Open Source (Local) | Offline SLM fallback inference and local LoRA adapter training capabilities. |
| **Dense Embeddings** | **sentence-transformers (`all-MiniLM-L6-v2`)** | Open Source (Local) | Fast 384-dimensional dense semantic embeddings executed locally on CPU/GPU without API quotas. |
| **Vector Database** | **ChromaDB** | Open Source (Local) | Serverless, disk-persisted vector store featuring notebook-level collection isolation and cosine similarity. |
| **Knowledge Graph Store** | **Neo4j AuraDB Free** | Free Tier | Cloud-hosted graph database with Cypher query execution for entity-relationship traversal and subgraphs. |
| **Multi-Format Ingestion** | **PyMuPDF, python-docx, python-pptx, youtube-transcript-api** | Open Source | Ingestion pipeline supporting PDF, Word DOCX, PowerPoint PPTX, plain text, and YouTube video transcripts. |
| **Web Fallback** | **duckduckgo-search (`DDGS`)** | Open Source | Real-time web retrieval fallback when local notebook context is insufficient. |
| **Audio Overview** | **edge-tts** | Open Source | Generates natural two-speaker conversational podcast summaries from document context. |
| **Auth & Database** | **Supabase Free Tier** | Free Tier | User authentication, PostgreSQL document storage, and user profile management. |
| **Testing & Evaluation** | **pytest & HotpotQA Benchmark** | Open Source | Comprehensive test suite (21 unit tests) and multi-hop evaluation harness (EM, F1, Recall). |

---

## 📂 Repository Structure

```
graphrag-research-notebook/
├── .env.example            # Template for free-tier API credentials
├── README.md               # Main project documentation
├── requirements.txt        # Pinned Python dependencies
├── api/
│   ├── main.py             # FastAPI backend with REST endpoints & BackgroundTasks
│   └── README.md           # API documentation with curl examples
├── config/
│   └── settings.py         # Pydantic environment configuration & validation
├── data/
│   ├── sample_hotpotqa.json# 200-example HotpotQA multi-hop benchmark sample
│   └── uploads/            # Local document storage directory
├── data_loading/
│   ├── loader.py           # Hugging Face HotpotQA dataset loader & schema validator
│   ├── stats.py            # Dataset split statistics script
│   └── youtube.py          # YouTube transcript extractor
├── embedding/
│   ├── model.py            # Singleton all-MiniLM-L6-v2 embedding model
│   └── README.md
├── frontend/               # Next.js 16 + React 19 Frontend Application
│   ├── app/                # Next.js App Router (pages & layout)
│   ├── components/         # Workspace, Chat, GraphExplorer, KnowledgeExplorer, Quiz
│   └── lib/                # API client & Supabase auth helpers
├── generation/
│   ├── generator.py        # Gemini Flash generation with citations, chat & teach modes
│   ├── local_slm.py        # Hugging Face local SLM fallback (CPU/CUDA)
│   ├── ollama_slm.py       # Ollama local inference integration
│   ├── ollama_trainer.py   # Ollama LoRA fine-tuning trainer
│   ├── audio_overview.py   # edge-tts two-speaker podcast generator
│   └── prompts.py          # Grounded citation prompt templates
├── graph_store/
│   ├── extractor.py        # Gemini structured entity & relationship extractor
│   ├── neo4j_client.py     # Neo4j AuraDB driver, MERGE contracts & multi-hop traversal
│   └── SCHEMA.md           # Entity node & RELATION edge schema specification
├── ingestion/
│   ├── parsers.py          # Extensible ParserRegistry (PDF, DOCX, TXT)
│   ├── pptx_parser.py      # PowerPoint PPTX parser
│   ├── chunker.py          # 500-token sentence-aware chunker with metadata
│   └── registry.py         # SQLite document status tracker
├── retrieval/
│   ├── vector_retriever.py # ChromaDB dense vector similarity retriever
│   ├── graph_retriever.py  # 1-2 hop Neo4j graph entity expansion
│   ├── hybrid_reranker.py  # Weighted fusion score reranker (0.7 vector + 0.3 graph)
│   ├── router.py           # Multi-hop vs. single-hop heuristic query router
│   └── web_search.py       # DuckDuckGo fallback searcher
├── evaluation/
│   ├── harness.py          # Evaluation harness: Vector vs. Graph vs. Hybrid on HotpotQA
│   └── README.md           # Benchmark evaluation documentation
├── scripts/
│   ├── check_services.py   # Connectivity verification for Gemini, Neo4j, Chroma, Supabase
│   ├── build_graph.py      # End-to-end document chunk → Neo4j KG build script
│   ├── query_graph.py      # Entity neighborhood sanity checker
│   └── routing_analytics.py# Query routing summary analytics script
└── tests/
    ├── test_api.py         # FastAPI TestClient endpoint integration tests
    ├── test_data_loader.py # HotpotQA schema & sampling unit tests
    ├── test_generation.py  # Prompt building & citation mapping tests
    ├── test_graph_extractor.py # Entity & relationship extraction tests
    ├── test_ingestion.py   # Multi-format parser & chunker unit tests
    ├── test_retrieval.py   # Query router & ranking unit tests
    └── test_vector_store.py# ChromaDB isolation & metadata survival tests
```

---

## 🚀 Getting Started

### 1. Clone & Set Up Python Virtual Environment
```bash
git clone https://github.com/Sudhanshu1894/notebooklm.git
cd notebooklm

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```
Fill in your free-tier credentials:
- `GEMINI_API_KEY`: From [Google AI Studio](https://aistudio.google.com/)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: From [Neo4j AuraDB Free](https://neo4j.com/cloud/platform/aura-graph-database/)
- `SUPABASE_URL`, `SUPABASE_KEY`: From [Supabase Free Project](https://supabase.com/)

### 3. Verify Service Connectivity
Run the automated verification script to confirm all external services are reachable:
```bash
python scripts/check_services.py
```

### 4. Run Test Suite
Execute the unit and integration tests across the entire pipeline:
```bash
python -m pytest tests/
```

### 5. Launch the Application

#### Terminal 1 — Backend (FastAPI)
```bash
python -m uvicorn api.main:app --reload --port 8000
```
API Documentation available at: `http://localhost:8000/docs`

#### Terminal 2 — Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 💡 Key Features & Workflow

1. **Multi-Format Source Ingestion**:
   - Upload PDF, Word (`.docx`), PowerPoint (`.pptx`), plain text files, or paste YouTube links directly in the chat query.
   - Text is parsed with section headers and page offsets, segmented into 500-token sentence-aware chunks, and indexed in ChromaDB.

2. **Hybrid GraphRAG Retrieval**:
   - **Vector Search**: Finds top-$k$ semantic neighbors using local 384-dimensional dense vectors.
   - **Graph Traversal**: Identifies seed entities and traverses 1–2 hops in Neo4j to pull relational context missed by standard dense embeddings.
   - **Weighted Fusion**: Combines and deduplicates contexts with budget-capped token limits.

3. **Verifiable Citations & Interactive Learning**:
   - **Clickable Citations**: Every claim in the LLM response maps to a bracketed citation `[1]`, `[2]` that highlights the source document and page.
   - **Teaching Mode**: Automatically triggers on explanatory questions (*"Teach me about..."* or *"Explain..."*) to return analogies, structured explanations, and key takeaways.
   - **Interactive Quiz Generation**: Creates 5-question multiple-choice quizzes with explanations and source hints.
   - **Interactive Graph Explorer**: Explore knowledge graph nodes and relational connections dynamically.
   - **Audio Overview**: Generate two-speaker audio conversations summarizing your notebook's key documents using `edge-tts`.

---

## 📊 System Status

- [x] **Core Pipeline**: Multi-format ingestion (PDF, DOCX, PPTX, TXT, YouTube), 500-token sentence chunking, local MiniLM embeddings, and ChromaDB vector store.
- [x] **Knowledge Graph**: Neo4j AuraDB schema, Gemini structured extraction, Cypher MERGE contracts, and 1-2 hop neighborhood expansion.
- [x] **Hybrid Retrieval & Generation**: Heuristic query routing, weighted reranking, and Gemini Flash grounded answer generation with inline citations.
- [x] **Full-Stack Application**: FastAPI backend with background processing tasks + Next.js 16 React 19 responsive UI.
- [x] **Novelty Features**: User-in-the-loop graph explorer, routing analytics logger, two-speaker audio podcast synthesis (`edge-tts`), and local SLM inference/training.
- [x] **Quality Assurance**: 21/21 automated tests passing cleanly.
