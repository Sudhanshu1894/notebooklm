# Embedding Module (`embedding/`)

## Intended Role
This module handles local text embedding generation using open-source Hugging Face models via `sentence-transformers` (e.g., `all-MiniLM-L6-v2`).

## Key Responsibilities (DA2 Pipeline)
- Initializing local sentence-transformer models.
- Embedding text chunks for vector indexing in ChromaDB.
- Embedding user queries for similarity search.
