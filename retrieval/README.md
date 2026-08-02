# Hybrid Retrieval Module (`retrieval/`)

## Intended Role
Coordinates hybrid retrieval combining vector similarity search (ChromaDB) with graph traversal / multi-hop reasoning (Neo4j).

## Key Responsibilities (DA2 Pipeline)
- Fusing vector search results with sub-graph context.
- Reranking or selecting context passages for multi-hop QA reasoning.
- Orchestrating retrieval pipelines with LangChain.
