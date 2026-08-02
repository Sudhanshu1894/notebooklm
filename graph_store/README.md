# Graph Store Module (`graph_store/`)

## Intended Role
Manages knowledge graph connection and Cypher queries against Neo4j AuraDB (Free Tier).

## Key Responsibilities (DA2 Pipeline)
- Connecting to Neo4j AuraDB instance using credentials from `.env`.
- Defining graph schemas (Entity nodes, Relationship edges, Community structures).
- Executing Cypher graph queries for multi-hop neighborhood retrieval.
