"""
Unit tests for Generation module (Prompt Builder & Citations).
"""

from generation.generator import build_generation_prompt


def test_build_generation_prompt():
    query = "Who founded Apple?"
    chunks = [
        {
            "chunk_id": "c1",
            "text": "Steve Jobs and Steve Wozniak founded Apple Computer in 1976.",
            "metadata": {"doc_id": "tech_history.pdf", "page_number": 4, "section_header": "Founding"},
        },
        {
            "chunk_id": "c2",
            "text": "Apple is an American multinational technology company headquartered in Cupertino.",
            "metadata": {"doc_id": "tech_history.pdf", "page_number": 5},
        },
    ]

    prompt, sources = build_generation_prompt(query, chunks)

    assert "[1] (Source: tech_history.pdf, Page 4 — Founding)" in prompt
    assert "[2] (Source: tech_history.pdf, Page 5)" in prompt
    assert "Steve Jobs and Steve Wozniak" in prompt
    assert f"QUESTION: {query}" in prompt

    assert len(sources) == 2
    assert sources[0]["citation_number"] == 1
    assert sources[0]["doc_id"] == "tech_history.pdf"
    assert sources[0]["page_number"] == 4
    assert sources[0]["section_header"] == "Founding"

    assert sources[1]["citation_number"] == 2
    assert sources[1]["doc_id"] == "tech_history.pdf"
    assert sources[1]["page_number"] == 5
