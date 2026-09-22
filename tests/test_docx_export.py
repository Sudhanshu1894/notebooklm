"""
Unit and Integration Tests for Microsoft Word (.docx) Export.
"""

import io
import pytest
import docx
from fastapi.testclient import TestClient
from unittest.mock import patch
from types import SimpleNamespace

from generation.docx_exporter import (
    DocxExporter,
    build_answer_docx,
    build_study_guide_docx,
    build_chat_transcript_docx,
    extract_key_takeaways_from_text,
    HEX_SHADING_CALLOUT,
    HEX_TABLE_HEADER,
)
from api.main import app

@pytest.fixture(autouse=True)
def mock_env_settings():
    mock_settings = SimpleNamespace(neo4j_uri="", gemini_api_key="")
    with patch("api.main.get_settings", return_value=mock_settings):
        yield

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit Tests: DocxExporter Engine
# ---------------------------------------------------------------------------

def test_docx_exporter_initialization():
    exporter = DocxExporter()
    assert exporter.doc is not None
    # Verify 1-inch margins
    for s in exporter.doc.sections:
        assert s.top_margin.inches == 1.0
        assert s.left_margin.inches == 1.0


def test_docx_exporter_title_and_headings():
    exporter = DocxExporter()
    exporter.add_title_block(
        title="Research Evaluation",
        subtitle="Evaluating Hybrid Graph Retrieval",
        notebook_name="AI Papers",
        total_sources=3
    )
    exporter.add_heading("Section 1: Overview", level=1)
    exporter.add_heading("1.1 Architecture", level=2)
    exporter.add_heading("1.1.1 Embeddings", level=3)

    buf = exporter.to_bytes()
    assert buf.getvalue().startswith(b"PK\x03\x04")  # Standard zip header for docx

    # Read back with python-docx
    loaded = docx.Document(buf)
    texts = [p.text for p in loaded.paragraphs]
    assert any("Research Evaluation" in t for t in texts)
    assert any("Evaluating Hybrid Graph Retrieval" in t for t in texts)
    assert any("Section 1: Overview" in t for t in texts)
    assert any("1.1 Architecture" in t for t in texts)
    assert any("1.1.1 Embeddings" in t for t in texts)


def test_docx_callout_box():
    exporter = DocxExporter()
    points = [
        "First major discovery regarding graph traversal.",
        "Second insight about vector similarity bounds."
    ]
    exporter.add_callout_box("Core Takeaways", points, badge_text="KEY TAKEAWAYS")

    buf = exporter.to_bytes()
    loaded = docx.Document(buf)
    
    # Verify table creation (callout box is a 1x1 table)
    assert len(loaded.tables) >= 1
    cell_text = loaded.tables[0].cell(0, 0).text
    assert "KEY TAKEAWAYS" in cell_text
    assert "First major discovery" in cell_text
    assert "Second insight" in cell_text


def test_docx_markdown_conversion():
    exporter = DocxExporter()
    md_content = """# Main Header
This is a paragraph with **bold text**, *italic text*, and `code snippet`.
It also cites [1] and [2].

- First bullet with **bold label**
- Second bullet point

1. Numbered item one
2. Numbered item two

> [!NOTE]
> Important callout blockquote translated to callout box.
"""
    exporter.add_markdown_content(md_content)
    buf = exporter.to_bytes()
    loaded = docx.Document(buf)

    p_texts = [p.text for p in loaded.paragraphs]
    assert any("Main Header" in t for t in p_texts)
    assert any("bold text" in t for t in p_texts)
    assert any("First bullet with" in t for t in p_texts)
    assert any("Numbered item one" in t for t in p_texts)


def test_docx_references_table():
    exporter = DocxExporter()
    citations = [
        {
            "citation_number": 1,
            "doc_id": "Research_Paper.pdf",
            "page_number": 5,
            "section_header": "Methodology",
            "text_preview": "The hybrid retrieval model utilizes reciprocal rank fusion."
        },
        {
            "citation_number": 2,
            "doc_id": "Architecture.docx",
            "page_number": 12,
            "section_header": "Graph Store",
            "text_preview": "Knowledge graph edges store predicate labels and source chunk ids."
        }
    ]
    exporter.add_references_table(citations)

    buf = exporter.to_bytes()
    loaded = docx.Document(buf)

    # Verify table has 3 rows (1 header + 2 citations)
    assert len(loaded.tables) >= 1
    tbl = loaded.tables[0]
    assert len(tbl.rows) == 3
    # Check headers
    hdr_texts = [c.text for c in tbl.rows[0].cells]
    assert hdr_texts == ["Ref #", "Source Document", "Page / Section", "Context Excerpt"]
    # Check citation 1
    r1_texts = [c.text for c in tbl.rows[1].cells]
    assert r1_texts[0] == "[1]"
    assert r1_texts[1] == "Research_Paper.pdf"
    assert "Page 5" in r1_texts[2]
    assert "hybrid retrieval model" in r1_texts[3]


def test_high_level_builders():
    citations = [
        {"citation_number": 1, "doc_id": "DocA.pdf", "page_number": 1, "section_header": "Intro", "text_preview": "Text excerpt"}
    ]

    # 1. Answer docx
    ans_buf = build_answer_docx(
        query="What is GraphRAG?",
        answer="GraphRAG combines vector search with Neo4j [1].\n\nKey takeaways:\n- Improves multi-hop reasoning.\n- Grounded in source documents.",
        citations=citations,
        notebook_name="Graph Science"
    )
    assert len(ans_buf.getvalue()) > 5000

    # 2. Study guide docx
    sg_buf = build_study_guide_docx(
        notebook_name="Graph Science",
        overview_text="Detailed overview of graph methods.",
        topics=[{"title": "Neo4j", "content": "Neo4j is a graph database."}],
        citations=citations
    )
    assert len(sg_buf.getvalue()) > 5000

    # 3. Chat transcript docx
    chat_buf = build_chat_transcript_docx(
        notebook_name="Graph Science",
        messages=[
            {"role": "user", "content": "Explain Neo4j"},
            {"role": "assistant", "content": "Neo4j stores nodes and edges [1].", "citations": citations}
        ]
    )
    assert len(chat_buf.getvalue()) > 5000


# ---------------------------------------------------------------------------
# Integration Tests: FastAPI Endpoints
# ---------------------------------------------------------------------------

def test_api_export_answer_docx():
    # Create notebook
    nb_res = client.post("/notebooks", json={"name": "Export Test Notebook"})
    assert nb_res.status_code == 200
    nb_id = nb_res.json()["notebook_id"]

    # Export answer docx
    payload = {
        "export_type": "answer",
        "title": "Query on Multi-Hop Reasoning",
        "content": "Multi-hop reasoning traverses connected entities in the graph [1].",
        "citations": [
            {
                "citation_number": 1,
                "doc_id": "HotpotQA_Paper.pdf",
                "page_number": 4,
                "section_header": "Results",
                "text_preview": "Supporting facts require 2 or more hops to answer."
            }
        ]
    }
    res = client.post(f"/notebooks/{nb_id}/export/docx", json=payload)
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in res.headers["content-type"]
    assert res.content.startswith(b"PK\x03\x04")

    # Verify docx parses cleanly
    doc = docx.Document(io.BytesIO(res.content))
    all_text = " ".join(p.text for p in doc.paragraphs)
    assert "Query on Multi-Hop Reasoning" in all_text


def test_api_export_chat_docx():
    # Create notebook and post a chat
    nb_res = client.post("/notebooks", json={"name": "Chat Export Test"})
    nb_id = nb_res.json()["notebook_id"]

    # Export chat transcript
    res = client.post(f"/notebooks/{nb_id}/export/docx", json={"export_type": "chat"})
    assert res.status_code == 200
    assert res.content.startswith(b"PK\x03\x04")


def test_api_export_auto_study_guide():
    nb_res = client.post("/notebooks", json={"name": "Study Guide Test"})
    nb_id = nb_res.json()["notebook_id"]

    res = client.post(f"/notebooks/{nb_id}/export/study-guide")
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in res.headers["content-type"]
    assert res.content.startswith(b"PK\x03\x04")
