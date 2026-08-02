# API & Web Application Module (`api/`)

## Intended Role
Exposes FastAPI REST endpoints to serve the GraphRAG research notebook backend.

## Key Responsibilities
- Endpoint for dataset summary/stats (`/api/dataset/stats`).
- Healthcheck endpoint (`/health`).
- (DA2 Pipeline) Endpoints for ingestion (`/api/ingest`), query execution (`/api/query`), and graph visual inspection (`/api/graph`).
