# Embedding Module — Local SentenceTransformers Wrapper

## Overview
The `embedding/` module generates dense vector representations of text passages and user search queries using local sentence-transformers model `all-MiniLM-L6-v2`.

---

## Technical Specifications
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (Local execution, no external API calls, zero cost)
- **Vector Dimension**: 384 dimensions
- **Singleton Architecture**: The `EmbeddingModel` class implements a singleton pattern so weights are loaded into memory exactly once per application lifespan.

---

## Interface Usage

```python
from embedding.model import EmbeddingModel, embed_query, embed_texts

# Embed a batch of document chunks
texts = ["First passage...", "Second passage..."]
embeddings = embed_texts(texts)  # returns List[List[float]]

# Embed a search query
query_vector = embed_query("What is GraphRAG?")  # returns List[float] (len 384)
```

---

## Testing
Run embedding and vector store unit tests:
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_vector_store.py -v
```
