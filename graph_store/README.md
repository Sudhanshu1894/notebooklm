# Graph Store Module — Knowledge Graph Construction

## Overview
The `graph_store/` module extracts structured entities and relationships from document text chunks via **Gemini 2.5 Flash** (free tier) and persists them in **Neo4j AuraDB Free** as a queryable knowledge graph.

---

## Graph Schema
See [SCHEMA.md](./SCHEMA.md) for the full node/edge specification.

- **Nodes** — `:Entity` (name, type, notebook_id, source_chunk_ids)
- **Edges** — `:RELATION` (relation_type, description, notebook_id, source_chunk_ids)

---

## Key Files

| File | Purpose |
|------|---------|
| `SCHEMA.md` | Graph schema specification and Cypher contracts |
| `extractor.py` | Gemini-powered JSON entity/relationship extractor with retry logic |
| `neo4j_client.py` | Neo4j MERGE upserts, 1-2 hop traversals, graph export for frontend |

---

## Rate-Limit & Cost Notice

> [!IMPORTANT]
> **This phase makes one Gemini API call per document chunk.** The free tier (`gemini-2.5-flash`) allows approximately 500 requests/day and 10 requests/minute. For a 200-chunk document:
> - At 10 RPM: ~20 minutes total ingestion time.
> - To stay safe, add a `time.sleep(6)` between Gemini calls in `build_graph.py` or batch chunk extraction to avoid rate-limit errors.

---

## Scripts

### Build a knowledge graph from a document:
```powershell
.\venv\Scripts\python.exe scripts/build_graph.py --file data/sample.pdf --notebook my_notebook
```

### Query entity neighbors (sanity check):
```powershell
.\venv\Scripts\python.exe scripts/query_graph.py --entity "GraphRAG" --notebook my_notebook
```
