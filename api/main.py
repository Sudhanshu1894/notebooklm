"""
FastAPI Backend for GraphRAG Research Notebook.
Exposes the full pipeline: document upload, processing, chat with citations, graph export.
"""

import os
import uuid
import sys
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil

# Pipeline imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
from data_loading.loader import load_local_sample
from ingestion.parsers import global_parser_registry
from ingestion.chunker import chunk_parsed_document
from ingestion.registry import DocumentRegistry
from embedding.model import EmbeddingModel
from vector_store.chroma import VectorStore
from retrieval.router import QueryRouter
from retrieval.vector_retriever import VectorRetriever
from retrieval.graph_retriever import GraphRetriever
from retrieval.hybrid_reranker import HybridReranker
from config.settings import get_settings

UPLOAD_DIR = "./data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="GraphRAG Research Notebook API",
    description="Hybrid RAG + Knowledge Graph Research System (Free-Tier Stack)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory notebook registry (use Supabase in production)
_notebooks: Dict[str, Dict] = {}
doc_registry = DocumentRegistry()


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class NotebookCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class NotebookResponse(BaseModel):
    notebook_id: str
    name: str
    description: str

class ChatRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class CitationItem(BaseModel):
    citation_number: int
    chunk_id: str
    doc_id: str
    page_number: Any
    section_header: str
    text_preview: str

class ChatResponse(BaseModel):
    query: str
    answer: str
    citations: List[dict]
    route: str
    is_insufficient: bool

class HealthResponse(BaseModel):
    status: str
    version: str


# ─── Utility ──────────────────────────────────────────────────────────────────

def _process_document_background(file_path: str, doc_id: str, notebook_id: str):
    """Background task: parse → chunk → embed → ChromaDB."""
    try:
        doc_registry.update_status(doc_id, "parsing")
        parsed = global_parser_registry.parse_file(file_path, doc_id=doc_id)
        doc_registry.update_status(doc_id, "chunking")
        chunks = chunk_parsed_document(parsed)
        doc_registry.update_status(doc_id, "embedding")
        embedder = EmbeddingModel()
        embeddings = embedder.embed_texts([c.text for c in chunks])
        vs = VectorStore()
        vs.upsert_chunks(notebook_id, chunks, embeddings)
        doc_registry.update_status(doc_id, "ready", chunk_count=len(chunks))
    except Exception as e:
        doc_registry.update_status(doc_id, "failed", error_message=str(e))


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/notebooks", response_model=NotebookResponse)
def create_notebook(body: NotebookCreate):
    """Creates a new notebook and returns its ID."""
    notebook_id = str(uuid.uuid4())[:8]
    _notebooks[notebook_id] = {"name": body.name, "description": body.description}
    return NotebookResponse(notebook_id=notebook_id, name=body.name, description=body.description or "")


@app.get("/notebooks")
def list_notebooks():
    return [{"notebook_id": nid, **meta} for nid, meta in _notebooks.items()]


@app.post("/notebooks/{notebook_id}/documents")
async def upload_document(
    notebook_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Uploads a document and starts async ingestion pipeline."""
    if notebook_id not in _notebooks:
        raise HTTPException(status_code=404, detail=f"Notebook '{notebook_id}' not found.")

    doc_id = str(uuid.uuid4())[:8]
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc_registry.register_document(
        doc_id=doc_id,
        filename=file.filename,
        file_path=save_path,
        file_type=os.path.splitext(file.filename)[1].lstrip("."),
    )
    background_tasks.add_task(_process_document_background, save_path, doc_id, notebook_id)
    return {"doc_id": doc_id, "filename": file.filename, "status": "processing"}


@app.get("/notebooks/{notebook_id}/documents/{doc_id}/status")
def get_document_status(notebook_id: str, doc_id: str):
    """Returns current processing status of a document."""
    doc = doc_registry.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@app.get("/notebooks/{notebook_id}/sources")
def list_sources(notebook_id: str):
    """Lists all documents in the registry (scoped to notebook by convention)."""
    return doc_registry.list_documents()


@app.post("/notebooks/{notebook_id}/chat", response_model=ChatResponse)
def chat(notebook_id: str, body: ChatRequest):
    """Runs hybrid retrieval + Gemini generation and returns cited answer."""
    if notebook_id not in _notebooks:
        raise HTTPException(status_code=404, detail=f"Notebook '{notebook_id}' not found.")

    settings = get_settings()
    router = QueryRouter(log_routing=True)
    route, reason, _ = router.route(body.query, notebook_id=notebook_id)

    vector_retriever = VectorRetriever()
    vector_chunks = vector_retriever.retrieve(body.query, notebook_id=notebook_id, top_k=body.top_k)

    if route == "hybrid" and settings.neo4j_uri:
        graph_retriever = GraphRetriever()
        graph_chunks = graph_retriever.expand_via_graph(notebook_id, vector_chunks)
        reranker = HybridReranker()
        context_chunks = reranker.merge_and_rerank(vector_chunks, graph_chunks)
    else:
        context_chunks = vector_chunks

    # Generation
    if not settings.gemini_api_key:
        # Demo mode — no Gemini key
        answer = f"[DEMO MODE — No GEMINI_API_KEY set]\n\nTop retrieved chunk:\n\"{context_chunks[0]['text'][:300]}...\"" if context_chunks else "No context found."
        return ChatResponse(query=body.query, answer=answer, citations=[], route=route, is_insufficient=True)

    from generation.generator import AnswerGenerator
    generator = AnswerGenerator()
    result = generator.generate(body.query, context_chunks)
    return ChatResponse(
        query=body.query,
        answer=result["answer_text"],
        citations=result["citations"],
        route=route,
        is_insufficient=result["is_insufficient"],
    )


@app.get("/notebooks/{notebook_id}/graph")
def get_graph(notebook_id: str):
    """Returns the knowledge graph as nodes/edges JSON for react-force-graph."""
    settings = get_settings()
    if not settings.neo4j_uri:
        # Return empty graph in demo mode
        return {"nodes": [], "edges": [], "demo_mode": True}
    from graph_store.neo4j_client import Neo4jGraphStore
    store = Neo4jGraphStore()
    graph = store.get_notebook_graph(notebook_id)
    store.close()
    return graph


@app.get("/api/dataset/sample-stats")
def get_sample_stats():
    sample_path = os.path.join("data", "sample_hotpotqa.json")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Run 'python -m data_loading.loader' first.")
    data = load_local_sample(sample_path)
    return data.get("metadata", {})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
