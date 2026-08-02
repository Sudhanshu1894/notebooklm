# Vector Store Module (`vector_store/`)

## Intended Role
Manages local, embedded vector database operations using ChromaDB.

## Key Responsibilities (DA2 Pipeline)
- Initializing local ChromaDB client (`PersistentClient`).
- Managing vector collections, indexing passage chunks, and similarity search.
- Persisting vector store locally under `data/chroma_db/`.
