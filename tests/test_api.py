"""
Integration tests for FastAPI Backend endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from types import SimpleNamespace
from api.main import app

@pytest.fixture(autouse=True)
def mock_env_settings():
    mock_settings = SimpleNamespace(neo4j_uri="", gemini_api_key="")
    with patch("api.main.get_settings", return_value=mock_settings):
        yield

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_notebook_crud():
    # Create notebook
    create_res = client.post("/notebooks", json={"name": "Test Notebook", "description": "Unit test"})
    assert create_res.status_code == 200
    nb_data = create_res.json()
    assert "notebook_id" in nb_data
    assert nb_data["name"] == "Test Notebook"

    notebook_id = nb_data["notebook_id"]

    # List notebooks
    list_res = client.get("/notebooks")
    assert list_res.status_code == 200
    notebooks = list_res.json()
    assert any(n["notebook_id"] == notebook_id for n in notebooks)

    # Get sources (empty initially)
    sources_res = client.get(f"/notebooks/{notebook_id}/sources")
    assert sources_res.status_code == 200

    # Get graph (empty demo mode)
    graph_res = client.get(f"/notebooks/{notebook_id}/graph")
    assert graph_res.status_code == 200
    assert "nodes" in graph_res.json()


def test_chat_demo_mode():
    # Create notebook first
    nb_res = client.post("/notebooks", json={"name": "Chat Demo"})
    nb_id = nb_res.json()["notebook_id"]

    chat_res = client.post(
        f"/notebooks/{nb_id}/chat",
        json={"query": "What is the capital of France?", "top_k": 3},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["query"] == "What is the capital of France?"
    assert "answer" in chat_data
    assert "route" in chat_data
    assert "citations" in chat_data
