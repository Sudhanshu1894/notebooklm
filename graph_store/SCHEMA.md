# Graph Store Schema Specification — GraphRAG Research Notebook

## Node & Edge Definitions

### 1. Entity Node (`:Entity`)
Represents an extracted entity (person, organization, concept, location, event, product).

- **Primary Identifier / Key**: `(name, type, notebook_id)`
- **Properties**:
  - `name`: string (e.g., `"GraphRAG"`, `"Scott Derrickson"`)
  - `type`: string (e.g., `"CONCEPT"`, `"PERSON"`, `"ORGANIZATION"`, `"LOCATION"`, `"EVENT"`)
  - `notebook_id`: string (scoping property for multi-tenant isolation)
  - `source_chunk_ids`: list of strings (e.g., `["doc_123_c0", "doc_123_c1"]`)

### 2. Relationship Edge (`:RELATION`)
Represents a directed link between a source Entity and a target Entity.

- **Primary Identifier / Key**: `(source_entity, target_entity, relation_type, notebook_id)`
- **Properties**:
  - `relation_type`: string (e.g., `"USES"`, `"DIRECTED"`, `"IS_LOCATED_IN"`, `"PART_OF"`)
  - `description`: string (e.g., `"Combines vector search and Neo4j knowledge graphs"`)
  - `notebook_id`: string (scoping property)
  - `source_chunk_ids`: list of strings (citation grounding references)

---

## Cypher Upsert Contracts

### Entity Merging:
```cypher
MERGE (e:Entity {name: $name, type: $type, notebook_id: $notebook_id})
ON CREATE SET e.source_chunk_ids = [$chunk_id], e.created_at = timestamp()
ON MATCH SET e.source_chunk_ids = apoc.coll.toSet(e.source_chunk_ids + [$chunk_id])
```

### Relationship Merging:
```cypher
MATCH (source:Entity {name: $source_name, type: $source_type, notebook_id: $notebook_id})
MATCH (target:Entity {name: $target_name, type: $target_type, notebook_id: $notebook_id})
MERGE (source)-[r:RELATION {relation_type: $relation_type, notebook_id: $notebook_id}]->(target)
ON CREATE SET r.description = $description, r.source_chunk_ids = [$chunk_id]
ON MATCH SET r.source_chunk_ids = apoc.coll.toSet(r.source_chunk_ids + [$chunk_id])
```
