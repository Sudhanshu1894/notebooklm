"""
Knowledge Graph Construction Script for GraphRAG Research Notebook.
Extracts entities and relationships from document chunks via Gemini Flash and indexes into Neo4j.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.parsers import global_parser_registry
from ingestion.chunker import chunk_parsed_document
from graph_store.extractor import GraphExtractor
from graph_store.neo4j_client import Neo4jGraphStore


def build_graph_for_file(file_path: str, notebook_id: str = "default_notebook") -> Dict[str, int]:
    """
    Parses file, chunks text, extracts graph via Gemini Flash, and upserts into Neo4j.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    doc_id = f"doc_{abs(hash(file_path)) % 100000}"

    print(f"[build_graph] Parsing '{filename}'...")
    parsed_doc = global_parser_registry.parse_file(file_path, doc_id=doc_id)
    chunks = chunk_parsed_document(parsed_doc)
    print(f"[build_graph] Created {len(chunks)} chunks.")

    extractor = GraphExtractor()
    neo4j_store = Neo4jGraphStore()

    total_nodes = 0
    total_edges = 0

    for idx, chunk in enumerate(chunks, start=1):
        print(f"[build_graph] Extracting graph for chunk {idx}/{len(chunks)} ({chunk.chunk_id})...")
        extracted = extractor.extract_from_text(chunk.text, chunk_id=chunk.chunk_id)

        entities = extracted.get("entities", [])
        relationships = extracted.get("relationships", [])

        if entities or relationships:
            stats = neo4j_store.upsert_graph_data(
                notebook_id=notebook_id,
                entities=entities,
                relationships=relationships,
            )
            total_nodes += stats["nodes"]
            total_edges += stats["edges"]

    neo4j_store.close()
    print(f"[build_graph] SUCCESS: Processed {len(chunks)} chunks into Neo4j (Nodes: {total_nodes}, Edges: {total_edges}).")
    return {"nodes": total_nodes, "edges": total_edges}


def main():
    parser = argparse.ArgumentParser(description="Extract entities and build Neo4j knowledge graph.")
    parser.add_argument("--file", required=True, help="Path to document file")
    parser.add_argument("--notebook", default="default_notebook", help="Notebook ID target")

    args = parser.parse_args()
    build_graph_for_file(args.file, notebook_id=args.notebook)


if __name__ == "__main__":
    main()
