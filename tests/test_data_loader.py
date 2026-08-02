"""
Sanity Test Suite for GraphRAG Research Notebook Data Loader & API.
"""

import os
import json
import pytest
from unittest.mock import MagicMock
from data_loading.loader import validate_schema, create_sample_subset, load_local_sample


@pytest.fixture
def mock_hotpotqa_example():
    return {
        "id": "5a8b73255542995e1d6113b1",
        "question": "Were Scott Derrickson and Ed Wood of the same nationality?",
        "answer": "yes",
        "type": "comparison",
        "level": "easy",
        "supporting_facts": {
            "title": ["Scott Derrickson", "Ed Wood"],
            "sent_id": [0, 0],
        },
        "context": {
            "title": ["Scott Derrickson", "Ed Wood"],
            "sentences": [
                ["Scott Derrickson (born July 16, 1966) is an American director."],
                ["Edward Davis Wood Jr. (July 9, 1924) was an American filmmaker."],
            ],
        },
    }


def test_schema_validation_success(mock_hotpotqa_example):
    """Verifies schema validation succeeds for valid HotpotQA record."""
    assert validate_schema(mock_hotpotqa_example) is True


def test_schema_validation_missing_key(mock_hotpotqa_example):
    """Verifies schema validation fails when required keys are missing."""
    invalid_item = dict(mock_hotpotqa_example)
    del invalid_item["question"]
    with pytest.raises(ValueError, match="Schema validation failed"):
        validate_schema(invalid_item)


def test_create_sample_subset(tmp_path, mock_hotpotqa_example):
    """Verifies create_sample_subset creates valid sample JSON with benchmark splits."""
    mock_train = [mock_hotpotqa_example] * 10
    mock_val = [mock_hotpotqa_example] * 5

    mock_dataset = {
        "train": mock_train,
        "validation": mock_val,
    }

    target_file = os.path.join(tmp_path, "sample_test.json")
    result = create_sample_subset(
        dataset=mock_dataset,
        train_count=5,
        val_count=3,
        output_path=target_file,
    )

    assert os.path.exists(target_file)
    assert result["metadata"]["total_samples"] == 8
    assert result["metadata"]["train_sample_count"] == 5
    assert result["metadata"]["dev_sample_count"] == 3
    assert len(result["records"]) == 8


def test_load_local_sample_nonexistent():
    """Verifies FileNotFoundError is raised if sample file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_local_sample("data/nonexistent_file.json")
