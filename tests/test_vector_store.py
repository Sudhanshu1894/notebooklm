"""
Unit Test Suite for Embedding Model and ChromaDB Vector Store.
"""

import os
import pytest
from embedding.model import EmbeddingModel, embed_query, embed_texts
from vector_store.chroma import VectorStore
from ingestion.chunker import DocumentChunk


def test_embedding_determinism():
    text = "GraphRAG integrates knowledge graphs and vector databases."
    vec1 = embed_query(text)
    vec2 = embed_query(text)
    assert len(vec1) == 384  # default all-MiniLM-L6-v2 dimension
    assert vec1 == vec2


def test_collection_isolation(tmp_path):
    chroma_dir = os.path.join(tmp_path, "chroma_isolation_test")
    vs = VectorStore(persist_dir=chroma_dir)

    chunk_a = DocumentChunk(
        chunk_id="chunk_a_1",
        doc_id="doc_a",
        chunk_index=0,
        text="Alpha document about artificial intelligence and neural networks.",
        page_number=1,
        section_header="AI Section",
        start_char_offset=0,
        end_char_offset=65,
        char_length=65,
    )
    emb_a = embed_query(chunk_a.text)

    chunk_b = DocumentChunk(
        chunk_id="chunk_b_1",
        doc_id="doc_b",
        chunk_index=0,
        text="Beta document discussing astrophysics and planetary motion.",
        page_number=1,
        section_header="Physics Section",
        start_char_offset=0,
        end_char_offset=58,
        char_length=58,
    )
    emb_b = embed_query(chunk_b.text)

    vs.upsert_chunks("notebook_A", [chunk_a], [emb_a])
    vs.upsert_chunks("notebook_B", [chunk_b], [emb_b])

    # Search query in notebook_A
    query_vec = embed_query("artificial intelligence")
    matches_a = vs.query_similar_chunks("notebook_A", query_vec, top_k=5)

    # Search same query in notebook_B
    matches_b = vs.query_similar_chunks("notebook_B", query_vec, top_k=5)

    # notebook_A must only return chunk_a
    assert len(matches_a) == 1
    assert matches_a[0]["chunk_id"] == "chunk_a_1"

    # notebook_B must only return chunk_b (no cross-leakage)
    assert len(matches_b) == 1
    assert matches_b[0]["chunk_id"] == "chunk_b_1"

    # Cleanup collections
    vs.delete_notebook_collection("notebook_A")
    vs.delete_notebook_collection("notebook_B")


def test_metadata_survival(tmp_path):
    chroma_dir = os.path.join(tmp_path, "chroma_meta_test")
    vs = VectorStore(persist_dir=chroma_dir)

    chunk = DocumentChunk(
        chunk_id="chunk_meta_1",
        doc_id="doc_meta_99",
        chunk_index=3,
        text="Sample text for metadata preservation verification.",
        page_number=12,
        section_header="Chapter 3 Overview",
        start_char_offset=450,
        end_char_offset=501,
        char_length=51,
    )
    emb = embed_query(chunk.text)
    vs.upsert_chunks("notebook_meta", [chunk], [emb])

    matches = vs.query_similar_chunks("notebook_meta", emb, top_k=1)
    assert len(matches) == 1
    match = matches[0]

    assert match["chunk_id"] == "chunk_meta_1"
    assert match["text"] == chunk.text
    meta = match["metadata"]
    assert meta["doc_id"] == "doc_meta_99"
    assert meta["chunk_index"] == 3
    assert meta["page_number"] == 12
    assert meta["section_header"] == "Chapter 3 Overview"
    assert meta["start_char_offset"] == 450

    vs.delete_notebook_collection("notebook_meta")
