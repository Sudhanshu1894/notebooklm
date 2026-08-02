"""
Document Indexing Script for GraphRAG Research Notebook.
Runs document ingestion -> sentence chunking -> embedding -> ChromaDB indexing.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.parsers import global_parser_registry
from ingestion.chunker import chunk_parsed_document
from ingestion.registry import DocumentRegistry
from embedding.model import EmbeddingModel
from vector_store.chroma import VectorStore


def index_file(file_path: str, notebook_id: str = "default_notebook", doc_id: str = None) -> int:
    """
    Ingests, chunks, embeds, and indexes a file into ChromaDB for a given notebook ID.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1].lower()
    doc_id = doc_id or f"doc_{abs(hash(file_path)) % 100000}"

    print(f"[index] Starting processing for '{filename}' (Doc ID: {doc_id}, Notebook: {notebook_id})...")

    # 1. Register document in SQLite status tracker
    registry = DocumentRegistry()
    registry.register_document(
        doc_id=doc_id,
        filename=filename,
        file_path=os.path.abspath(file_path),
        file_type=file_ext.lstrip("."),
    )

    # 2. Parse file
    print("[index] Parsing document...")
    parsed_doc = global_parser_registry.parse_file(file_path, doc_id=doc_id)
    registry.update_status(doc_id, status="parsed")

    # 3. Chunk text into sentence-aware segments
    print("[index] Chunking document text...")
    chunks = chunk_parsed_document(parsed_doc)
    print(f"[index] Extracted {len(chunks)} chunks.")

    # 4. Generate embeddings
    print("[index] Computing embeddings using SentenceTransformer (all-MiniLM-L6-v2)...")
    embedder = EmbeddingModel()
    texts = [c.text for c in chunks]
    embeddings = embedder.embed_texts(texts)

    # 5. Upsert into ChromaDB
    print("[index] Indexing vectors into ChromaDB...")
    vector_store = VectorStore()
    count = vector_store.upsert_chunks(notebook_id, chunks, embeddings)

    # 6. Update registry
    registry.update_status(doc_id, status="chunked", chunk_count=count)
    print(f"[index] SUCCESS: Indexed {count} chunks for document '{filename}' in notebook '{notebook_id}'.")
    return count


def main():
    parser = argparse.ArgumentParser(description="Index a document into GraphRAG vector store.")
    parser.add_argument("--file", required=True, help="Path to document file (PDF, DOCX, TXT)")
    parser.add_argument("--notebook", default="default_notebook", help="Notebook ID target")
    parser.add_argument("--doc_id", default=None, help="Optional custom Document ID")

    args = parser.parse_args()
    index_file(args.file, notebook_id=args.notebook, doc_id=args.doc_id)


if __name__ == "__main__":
    main()
