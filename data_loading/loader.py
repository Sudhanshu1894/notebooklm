"""
HotpotQA Dataset Loader Module for GraphRAG Research Notebook.

Downloads and loads the HotpotQA distractor benchmark subset from Hugging Face
`datasets`, enforces split structures (train/validation), validates schema
integrity, and extracts a 200-example sample for fast local iteration.
"""

import json
import os
from typing import Dict, Any, Tuple, List
from datetime import datetime
from datasets import load_dataset, DatasetDict


REQUIRED_SCHEMA_KEYS = {
    "id",
    "question",
    "answer",
    "type",
    "level",
    "supporting_facts",
    "context",
}


def load_hotpotqa_dataset() -> DatasetDict:
    """
    Downloads and loads the official HotpotQA distractor dataset from Hugging Face.

    Returns:
        DatasetDict containing original benchmark splits ('train', 'validation').
    """
    print("[loader] Downloading/Loading HotpotQA distractor dataset from Hugging Face...")
    dataset = load_dataset("hotpot_qa", "distractor")
    print(f"[loader] Successfully loaded splits: {list(dataset.keys())}")
    return dataset


def validate_schema(example: Dict[str, Any]) -> bool:
    """
    Sanity check to validate schema structure for a HotpotQA record.

    Args:
        example: Dictionary representing a single dataset row.

    Returns:
        True if all required keys are present and non-empty.
    """
    missing_keys = REQUIRED_SCHEMA_KEYS - set(example.keys())
    if missing_keys:
        raise ValueError(f"Schema validation failed. Missing keys: {missing_keys}")

    if not isinstance(example["id"], str) or not example["id"]:
        raise ValueError("Invalid 'id' field: must be a non-empty string.")

    if not isinstance(example["question"], str) or not example["question"]:
        raise ValueError("Invalid 'question' field: must be a non-empty string.")

    if not isinstance(example["answer"], str) or not example["answer"]:
        raise ValueError("Invalid 'answer' field: must be a non-empty string.")

    if "context" not in example or "title" not in example["context"]:
        raise ValueError("Invalid 'context' field: missing title list.")

    return True


def create_sample_subset(
    dataset: DatasetDict,
    train_count: int = 150,
    val_count: int = 50,
    output_path: str = "data/sample_hotpotqa.json",
) -> Dict[str, Any]:
    """
    Extracts a small representative sample (e.g. 200 items) for fast local development,
    retaining original benchmark split information.

    Args:
        dataset: DatasetDict containing 'train' and 'validation' splits.
        train_count: Number of training examples to extract.
        val_count: Number of validation examples to extract.
        output_path: Target JSON file path.

    Returns:
        Dictionary containing summary metadata and sample records.
    """
    train_split = dataset["train"]
    val_split = dataset["validation"]

    train_samples = [train_split[i] for i in range(min(train_count, len(train_split)))]
    val_samples = [val_split[i] for i in range(min(val_count, len(val_split)))]

    # Validate first example of each split
    if train_samples:
        validate_schema(train_samples[0])
    if val_samples:
        validate_schema(val_samples[0])

    # Add split tag to each record
    tagged_records = []
    for item in train_samples:
        item_copy = dict(item)
        item_copy["split"] = "train"
        tagged_records.append(item_copy)

    for item in val_samples:
        item_copy = dict(item)
        item_copy["split"] = "dev"
        tagged_records.append(item_copy)

    payload = {
        "metadata": {
            "dataset_name": "HotpotQA (distractor subset)",
            "source": "Hugging Face datasets (hotpot_qa/distractor)",
            "total_samples": len(tagged_records),
            "train_sample_count": len(train_samples),
            "dev_sample_count": len(val_samples),
            "created_at": datetime.now().isoformat(),
        },
        "records": tagged_records,
    }

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(
        f"[loader] Saved sample dataset ({len(tagged_records)} records: "
        f"{len(train_samples)} train, {len(val_samples)} dev) to '{output_path}'"
    )
    return payload


def load_local_sample(file_path: str = "data/sample_hotpotqa.json") -> Dict[str, Any]:
    """
    Reads the locally cached sample JSON dataset.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Sample dataset file not found at '{file_path}'. "
            "Please run 'python -m data_loading.loader' to generate it."
        )

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    ds = load_hotpotqa_dataset()
    create_sample_subset(ds)
