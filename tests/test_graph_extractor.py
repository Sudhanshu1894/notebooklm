import pytest
from unittest.mock import MagicMock, patch
from graph_store.extractor import GraphExtractor

class MockResponse:
    def __init__(self, text):
        self.text = text

@pytest.fixture
def mock_genai_client():
    with patch("graph_store.extractor.genai.Client") as mock_client:
        client_instance = mock_client.return_value
        yield client_instance

def test_successful_extraction(mock_genai_client):
    # Mock the Gemini API response with valid JSON inside markdown
    mock_genai_client.models.generate_content.return_value = MockResponse(
        """```json
{
  "entities": [
    {"name": "Alice", "type": "PERSON"},
    {"name": "Bob", "type": "PERSON"}
  ],
  "relationships": [
    {
      "source_name": "Alice",
      "source_type": "PERSON",
      "target_name": "Bob",
      "target_type": "PERSON",
      "relation_type": "KNOWS",
      "description": "Alice knows Bob"
    }
  ]
}
```"""
    )

    extractor = GraphExtractor(api_key="fake_key")
    result = extractor.extract_from_text("Alice knows Bob.", chunk_id="chunk123")

    assert len(result["entities"]) == 2
    assert result["entities"][0]["name"] == "Alice"
    assert result["entities"][0]["chunk_id"] == "chunk123"

    assert len(result["relationships"]) == 1
    assert result["relationships"][0]["relation_type"] == "KNOWS"
    assert result["relationships"][0]["chunk_id"] == "chunk123"

def test_retry_on_invalid_json(mock_genai_client):
    # First response is invalid JSON, second is valid
    mock_genai_client.models.generate_content.side_effect = [
        MockResponse("This is not JSON"),
        MockResponse(
            """{
              "entities": [{"name": "Charlie", "type": "PERSON"}],
              "relationships": []
            }"""
        )
    ]

    extractor = GraphExtractor(api_key="fake_key")
    result = extractor.extract_from_text("Charlie is here.", chunk_id="chunk456")

    assert mock_genai_client.models.generate_content.call_count == 2
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Charlie"
    assert result["entities"][0]["chunk_id"] == "chunk456"

def test_empty_text():
    extractor = GraphExtractor(api_key="fake_key")
    result = extractor.extract_from_text("   ", chunk_id="chunk789")
    
    assert result == {"entities": [], "relationships": []}
