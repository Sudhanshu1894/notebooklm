"""
Graph Neighbor Query Script for GraphRAG Research Notebook.
Retrieves an entity's direct neighbors from Neo4j for sanity-checking graph construction.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph_store.neo4j_client import Neo4jGraphStore


def query_entity_neighbors(entity_name: str, notebook_id: str = "default_notebook", max_hops: int = 2):
    """
    Fetches and prints entity neighbors and relationships from Neo4j.
    """
    print("=" * 65)
    print("         GRAPHRAG NEO4J ENTITY NEIGHBOR QUERY         ")
    print("=" * 65)
    print(f"Entity      : '{entity_name}'")
    print(f"Notebook ID : '{notebook_id}'")
    print(f"Max Hops    : {max_hops}")
    print("-" * 65)

    store = Neo4jGraphStore()
    result = store.get_entity_neighbors(
        notebook_id=notebook_id,
        entity_name=entity_name,
        max_hops=max_hops,
    )
    store.close()

    entities = result.get("connected_entities", [])
    rels = result.get("relationships", [])
    chunks = result.get("source_chunk_ids", [])

    if not entities:
        print(f"No neighbors found for entity '{entity_name}'.")
        return result

    print(f"Found {len(entities)} connected entities:\n")
    for e in entities:
        print(f"  - [{e['type']}] {e['name']}")

    print(f"\nRelationships ({len(rels)}):")
    for r in rels:
        print(f"  - {r['relation_type']}: {r['description']}")

    print(f"\nSource Chunk IDs ({len(chunks)}):")
    for c in chunks:
        print(f"  - {c}")

    print("=" * 65)
    return result


def main():
    parser = argparse.ArgumentParser(description="Query entity neighbors in Neo4j knowledge graph.")
    parser.add_argument("--entity", required=True, help="Entity name to query")
    parser.add_argument("--notebook", default="default_notebook", help="Notebook ID")
    parser.add_argument("--hops", type=int, default=2, help="Max graph hops (default: 2)")
    args = parser.parse_args()
    query_entity_neighbors(args.entity, notebook_id=args.notebook, max_hops=args.hops)


if __name__ == "__main__":
    main()
