# Vector Store Module — ChromaDB Persistent Storage

## Overview
The `vector_store/` module provides a persistent, embedded ChromaDB vector database wrapper with strict multi-tenant collection isolation per notebook.

---

## Features & Key Functions

### 1. Notebook Collection Isolation
- Collections are named `notebook_<notebook_id>` so document chunks indexed in Notebook A are never returned in queries for Notebook B.

### 2. Distance Metric
- Uses Cosine Similarity (`hnsw:space: cosine`).
- Converts raw cosine distance to similarity score `1.0 - distance` for intuition.

### 3. Metadata Roundtrip
Every indexed vector retains the original source chunk metadata:
- `doc_id`
- `chunk_index`
- `page_number`
- `section_header`
- `start_char_offset` / `end_char_offset`

---

## Core API

```python
from vector_store.chroma import VectorStore

vs = VectorStore()

# Index chunks
vs.upsert_chunks(notebook_id="nb_123", chunks=chunks, embeddings=embeddings)

# Query similar chunks
matches = vs.query_similar_chunks(
    notebook_id="nb_123",
    query_embedding=query_vec,
    top_k=5
)
```

---

## Verification Scripts

### Index a document end-to-end:
```powershell
.\venv\Scripts\python.exe scripts/index_document.py --file data/sample.pdf --notebook demo_nb
```

### Search vector index:
```powershell
.\venv\Scripts\python.exe scripts/test_vector_search.py --query "What is GraphRAG?" --notebook demo_nb
```
