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
from retrieval.web_search import WebSearcher
from data_loading.youtube import YouTubeExtractor
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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    mode: Optional[str] = "auto"  # "auto" | "chat" | "teach"
    model_preference: Optional[str] = "auto"

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
    citations: List[Dict[str, Any]]
    route: str
    is_insufficient: bool = False
    new_title: Optional[str] = None
    mode_used: Optional[str] = None

class QuizRequest(BaseModel):
    topic: Optional[str] = ""
    top_k: Optional[int] = 20

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: str
    source_hint: Optional[str] = ""
    difficulty: Optional[str] = "medium"

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str


# ─── Utility ──────────────────────────────────────────────────────────────────

def _process_document_background(file_path: str, doc_id: str, notebook_id: str):
    """Background task: parse → chunk → embed → ChromaDB → extract knowledge → train Ollama."""
    try:
        doc_registry.update_status(doc_id, "parsing")
        parsed = global_parser_registry.parse_file(file_path, doc_id=doc_id)
        doc_registry.update_status(doc_id, "chunking")
        chunks = chunk_parsed_document(parsed)
        if not chunks:
            doc_registry.update_status(
                doc_id,
                "failed",
                chunk_count=0,
                error_message="No readable text found in document. If this is a PDF, it may be scanned/image-only without OCR text.",
            )
            return

        doc_registry.update_status(doc_id, "embedding")
        embedder = EmbeddingModel()
        embeddings = embedder.embed_texts([c.text for c in chunks])
        vs = VectorStore()
        vs.upsert_chunks(notebook_id, chunks, embeddings)

        # Build knowledge graph: extract entities/relationships and upsert into Neo4j
        settings = get_settings()
        if settings.neo4j_uri and settings.neo4j_password:
            doc_registry.update_status(doc_id, "building_graph")
            try:
                from graph_store.extractor import GraphExtractor
                from graph_store.neo4j_client import Neo4jGraphStore
                extractor = GraphExtractor()
                neo4j_store = Neo4jGraphStore()
                total_nodes = 0
                total_edges = 0
                for idx, chunk in enumerate(chunks):
                    chunk_id = chunk.chunk_id if hasattr(chunk, 'chunk_id') else f"{doc_id}_chunk_{idx}"
                    extracted = extractor.extract_from_text(chunk.text, chunk_id=chunk_id)
                    entities = extracted.get("entities", [])
                    relationships = extracted.get("relationships", [])
                    if entities or relationships:
                        stats = neo4j_store.upsert_graph_data(
                            notebook_id=notebook_id,
                            entities=entities,
                            relationships=relationships,
                        )
                        total_nodes += stats["nodes"]
                        total_edges += stats["edges"]
                neo4j_store.close()
                print(f"[background] Graph built for doc '{doc_id}': {total_nodes} nodes, {total_edges} edges")
            except Exception as graph_err:
                print(f"[background] Graph extraction warning (non-fatal): {graph_err}")

        # Extract knowledge and train Ollama model
        doc_registry.update_status(doc_id, "training")
        try:
            from generation.ollama_trainer import OllamaTrainer
            trainer = OllamaTrainer()
            # Convert chunk objects to dicts for the trainer
            chunk_dicts = [{"text": c.text, "chunk_id": c.chunk_id if hasattr(c, 'chunk_id') else f"{doc_id}_chunk_{i}",
                           "metadata": {"doc_id": doc_id, "page_number": getattr(c, 'page_number', '?')}}
                          for i, c in enumerate(chunks)]
            trainer.train_on_chunks(notebook_id, doc_id, chunk_dicts)
        except Exception as train_err:
            print(f"[background] Knowledge extraction/training warning (non-fatal): {train_err}")

        doc_registry.update_status(doc_id, "ready", chunk_count=len(chunks))
    except Exception as e:
        doc_registry.update_status(doc_id, "failed", error_message=str(e))


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/notebooks", response_model=NotebookResponse)
def create_notebook(body: NotebookCreate):
    """Creates a new notebook in SQLite database and returns its ID."""
    notebook_id = str(uuid.uuid4())[:8]
    nb = doc_registry.create_notebook(notebook_id, body.name, body.description or "")
    return NotebookResponse(notebook_id=nb["notebook_id"], name=nb["name"], description=nb["description"])


@app.get("/notebooks")
def list_notebooks():
    """Lists all notebooks."""
    return doc_registry.list_notebooks()

@app.delete("/notebooks/{notebook_id}")
def delete_notebook(notebook_id: str):
    """Deletes a notebook."""
    doc_registry.delete_notebook(notebook_id)
    return {"status": "success"}


@app.post("/notebooks/{notebook_id}/documents")
async def upload_document(
    notebook_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Uploads a document and starts async ingestion pipeline."""
    nb = doc_registry.get_notebook(notebook_id)
    if not nb:
        doc_registry.create_notebook(notebook_id, f"Notebook {notebook_id}")

    doc_id = str(uuid.uuid4())[:8]
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc_registry.register_document(
        doc_id=doc_id,
        filename=file.filename,
        file_path=save_path,
        file_type=os.path.splitext(file.filename)[1].lstrip("."),
        notebook_id=notebook_id,
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
    """Lists documents uploaded to this specific notebook."""
    return doc_registry.list_documents(notebook_id=notebook_id)


@app.get("/notebooks/{notebook_id}/messages")
def get_messages(notebook_id: str):
    """Returns chat history for a notebook."""
    return doc_registry.list_messages(notebook_id)


@app.post("/notebooks/{notebook_id}/chat", response_model=ChatResponse)
def chat(notebook_id: str, body: ChatRequest):
    """Runs hybrid retrieval + Gemini generation and returns cited answer."""
    nb = doc_registry.get_notebook(notebook_id)
    if not nb:
        doc_registry.create_notebook(notebook_id, f"Notebook {notebook_id}")

    try:
        settings = get_settings()
        
        # Save user message
        user_msg_id = str(uuid.uuid4())
        doc_registry.save_message(
            message_id=user_msg_id,
            notebook_id=notebook_id,
            role="user",
            content=body.query,
        )

        # 1. YouTube Link Extraction
        yt_extractor = YouTubeExtractor()
        yt_urls = yt_extractor.extract_urls(body.query)
        yt_chunks = []
        for vid in yt_urls:
            yt_chunks.extend(yt_extractor.get_transcript_chunks(vid))

        router = QueryRouter(log_routing=True)
        route, reason, _ = router.route(body.query, notebook_id=notebook_id)

        vector_retriever = VectorRetriever()
        vector_chunks = vector_retriever.retrieve(body.query, notebook_id=notebook_id, top_k=body.top_k)

        if route == "hybrid" and settings.neo4j_uri:
            try:
                graph_retriever = GraphRetriever()
                graph_chunks = graph_retriever.expand_via_graph(notebook_id, vector_chunks)
                reranker = HybridReranker()
                context_chunks = reranker.merge_and_rerank(vector_chunks, graph_chunks)
            except Exception as ge:
                print(f"[chat] Graph expansion failed, falling back to vector: {ge}")
                context_chunks = vector_chunks
        else:
            context_chunks = vector_chunks

        # Add YT chunks to context
        if yt_chunks:
            context_chunks = yt_chunks + context_chunks
            route = "youtube_explain"
            # If query is mostly just the URL, tell Gemini to summarize it
            if len(body.query.split()) <= 2:
                body.query = f"Please summarize the main points of this video transcript."

        # Generation — cascades through Gemini -> Groq -> LocalMiniModel automatically
        # Pass the mode from the request body ("auto" | "chat" | "teach")
        from generation.generator import generate_with_fallback
        result = generate_with_fallback(
            body.query, 
            context_chunks, 
            mode=body.mode or "auto",
            model_preference=body.model_preference or "auto",
            notebook_id=notebook_id
        )
        generator_name = result.pop("_generator", "gemini")
        result.pop("_fallback_reason", None)
        
        # 2. Web Search Fallback (only for Gemini answers, never when user forced local model)
        _is_local = generator_name in ("ollama_slm", "local_mini_model", "none")
        _user_forced_local = (body.model_preference or "auto") == "local"
        if result["is_insufficient"] and not _is_local and not _user_forced_local:
            print("[chat] Local context insufficient. Falling back to web search...")
            web_searcher = WebSearcher()
            web_chunks = web_searcher.search(body.query)
            if web_chunks:
                context_chunks = web_chunks + context_chunks
                result = generate_with_fallback(body.query, context_chunks)
                generator_name = result.pop("_generator", generator_name)
                result.pop("_fallback_reason", None)
                if not result["is_insufficient"]:
                    route = "web_fallback"

        # Save assistant message
        assistant_msg_id = str(uuid.uuid4())
        doc_registry.save_message(
            message_id=assistant_msg_id,
            notebook_id=notebook_id,
            role="assistant",
            content=result["answer_text"],
            citations=result["citations"],
            route=route,
            is_insufficient=result["is_insufficient"],
        )

        # 3. Auto-rename notebook if it has default name (only when Gemini is active, not local)
        nb = doc_registry.get_notebook(notebook_id)
        new_title = None
        _is_local_gen = generator_name in ("ollama_slm", "local_mini_model", "none")
        if nb and nb.get("name", "").startswith("Research Chat") and not _is_local_gen:
            try:
                from generation.generator import AnswerGenerator
                _gen = AnswerGenerator()
                title_prompt = f"Given the user's query, generate a very short, concise title (max 5 words) for this chat. Do not use quotes or punctuation. Query: {body.query}"
                title_res = _gen.llm.generate_content(title_prompt)
                new_title = title_res.text.strip().replace('"', '')
                if new_title:
                    doc_registry.update_notebook_name(notebook_id, new_title)
            except Exception as e:
                print(f"[chat] Failed to auto-rename notebook: {e}")

        # Append generator name to route so frontend can indicate which model answered
        effective_route = f"{route}:{generator_name}" if generator_name not in ("gemini",) else route

        return ChatResponse(
            query=body.query,
            answer=result["answer_text"],
            citations=result["citations"],
            route=effective_route,
            is_insufficient=result["is_insufficient"],
            new_title=new_title,
            mode_used=result.get("mode_used"),
        )
    except Exception as e:
        print(f"[chat error]: {e}")
        return ChatResponse(
            query=body.query,
            answer=f"Error processing query: {str(e)}",
            citations=[],
            route="error",
            is_insufficient=True,
        )


@app.post("/notebooks/{notebook_id}/quiz", response_model=QuizResponse)
def generate_quiz(notebook_id: str, body: QuizRequest):
    """Generate a 5-question MCQ quiz from the notebook's documents."""
    try:
        vector_retriever = VectorRetriever()
        context_chunks = vector_retriever.retrieve(
            body.topic or "key concepts definitions important",
            notebook_id=notebook_id,
            top_k=body.top_k or 20,
        )
        if not context_chunks:
            return QuizResponse(questions=[], error="No documents found in this notebook. Please upload a document first.")

        settings = get_settings()
        if settings.gemini_api_key:
            try:
                from generation.generator import AnswerGenerator
                gen = AnswerGenerator(api_key=settings.gemini_api_key)
                raw = gen.generate_quiz(context_chunks, topic=body.topic or "")
                if "error" not in raw:
                    questions = [
                        QuizQuestion(
                            question=q["question"],
                            options=q["options"],
                            correct_index=q["correct_index"],
                            explanation=q["explanation"],
                            source_hint=q.get("source_hint", ""),
                            difficulty=q.get("difficulty", "medium"),
                        )
                        for q in raw.get("questions", [])
                    ]
                    return QuizResponse(questions=questions)
            except Exception as e:
                print(f"[quiz] Gemini failed ({e}), falling back to LocalMiniModel...")

        # LocalMiniModel fallback
        from generation.local_mini_model import LocalMiniModel
        local = LocalMiniModel()
        raw = local.generate_quiz(context_chunks, topic=body.topic or "")
        if "error" in raw:
            return QuizResponse(questions=[], error=raw["error"])
        questions = [
            QuizQuestion(
                question=q["question"],
                options=q["options"],
                correct_index=q["correct_index"],
                explanation=q["explanation"],
                source_hint=q.get("source_hint", ""),
                difficulty=q.get("difficulty", "medium"),
            )
            for q in raw.get("questions", [])
        ]
        return QuizResponse(questions=questions)
    except Exception as e:
        print(f"[quiz error]: {e}")
        return QuizResponse(questions=[], error=f"Quiz generation failed: {str(e)}")


@app.get("/notebooks/{notebook_id}/graph")
def get_graph(notebook_id: str):
    """Returns the knowledge graph as nodes/edges JSON for react-force-graph."""
    settings = get_settings()
    if not settings.neo4j_uri:
        # Return empty graph in demo mode
        return {"nodes": [], "edges": [], "demo_mode": True}
    try:
        from graph_store.neo4j_client import Neo4jGraphStore
        store = Neo4jGraphStore()
        graph = store.get_notebook_graph(notebook_id)
        store.close()
        return graph
    except Exception as e:
        error_msg = str(e)
        print(f"[graph] Neo4j connection error: {error_msg}")
        return {"nodes": [], "edges": [], "error": error_msg}


@app.post("/notebooks/{notebook_id}/build-graph")
def build_graph(notebook_id: str, background_tasks: BackgroundTasks):
    """Manually triggers graph building for all ready documents in a notebook."""
    settings = get_settings()
    if not settings.neo4j_uri or not settings.neo4j_password:
        raise HTTPException(status_code=400, detail="Neo4j credentials not configured. Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env")

    docs = doc_registry.list_documents(notebook_id=notebook_id)
    ready_docs = [d for d in docs if d["status"] == "ready"]
    if not ready_docs:
        raise HTTPException(status_code=400, detail="No ready documents found in this notebook.")

    def _build_graph_task():
        try:
            from graph_store.extractor import GraphExtractor
            from graph_store.neo4j_client import Neo4jGraphStore
            extractor = GraphExtractor()
            neo4j_store = Neo4jGraphStore()
            total_nodes = 0
            total_edges = 0

            for doc in ready_docs:
                doc_id = doc["doc_id"]
                file_path = doc["file_path"]
                if not os.path.exists(file_path):
                    print(f"[build_graph] Skipping missing file: {file_path}")
                    continue

                parsed = global_parser_registry.parse_file(file_path, doc_id=doc_id)
                chunks = chunk_parsed_document(parsed)

                for idx, chunk in enumerate(chunks):
                    chunk_id = chunk.chunk_id if hasattr(chunk, 'chunk_id') else f"{doc_id}_chunk_{idx}"
                    extracted = extractor.extract_from_text(chunk.text, chunk_id=chunk_id)
                    entities = extracted.get("entities", [])
                    relationships = extracted.get("relationships", [])
                    if entities or relationships:
                        stats = neo4j_store.upsert_graph_data(
                            notebook_id=notebook_id,
                            entities=entities,
                            relationships=relationships,
                        )
                        total_nodes += stats["nodes"]
                        total_edges += stats["edges"]

            neo4j_store.close()
            print(f"[build_graph] Complete for notebook '{notebook_id}': {total_nodes} nodes, {total_edges} edges")
        except Exception as e:
            print(f"[build_graph] Error: {e}")

    background_tasks.add_task(_build_graph_task)
    return {"status": "building", "documents": len(ready_docs)}


@app.get("/notebooks/{notebook_id}/knowledge")
def get_knowledge(notebook_id: str, knowledge_type: Optional[str] = None):
    """Returns extracted knowledge items for a notebook (summaries, entities, concepts, facts)."""
    items = doc_registry.get_knowledge(notebook_id, knowledge_type)
    return {"notebook_id": notebook_id, "items": items, "count": len(items)}


@app.get("/notebooks/{notebook_id}/knowledge/stats")
def get_knowledge_stats(notebook_id: str):
    """Returns knowledge statistics for a notebook."""
    stats = doc_registry.get_knowledge_stats(notebook_id)
    # Check if Ollama custom model exists
    try:
        from generation.ollama_trainer import OllamaTrainer
        trainer = OllamaTrainer()
        model_name = trainer.get_model_name(notebook_id)
        stats["ollama_model"] = model_name
        stats["ollama_available"] = model_name is not None
    except Exception:
        stats["ollama_model"] = None
        stats["ollama_available"] = False
    return stats


@app.get("/notebooks/{notebook_id}/knowledge/system-prompt")
def get_knowledge_system_prompt(notebook_id: str):
    """Returns the SYSTEM prompt that is injected into the Ollama model for transparency."""
    try:
        from generation.ollama_trainer import OllamaTrainer
        trainer = OllamaTrainer()
        prompt = trainer.get_system_prompt(notebook_id)
        return {"notebook_id": notebook_id, "system_prompt": prompt}
    except Exception as e:
        return {"notebook_id": notebook_id, "system_prompt": f"Error: {e}"}


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
