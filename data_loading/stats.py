"""
Dataset Statistics Script for GraphRAG Research Notebook.

Prints row counts, split breakdown, question types, difficulty levels, context
lengths, and a sample record for the loaded HotpotQA benchmark.
"""

import sys
import os
from typing import Dict, Any
from collections import Counter

# Add parent directory to path for clean imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_loading.loader import load_hotpotqa_dataset, load_local_sample


def print_dataset_statistics(ds_dict: Dict[str, Any] = None, is_local_sample: bool = False):
    """
    Computes and displays comprehensive statistics for the HotpotQA dataset.
    """
    print("=" * 65)
    print("        GRAPHRAG RESEARCH NOTEBOOK - DATASET STATISTICS        ")
    print("=" * 65)

    if is_local_sample:
        metadata = ds_dict.get("metadata", {})
        records = ds_dict.get("records", [])

        print(f"Dataset Name       : {metadata.get('dataset_name')}")
        print(f"Source             : {metadata.get('source')}")
        print(f"Total Sample Count : {metadata.get('total_samples')}")
        print(f"  - Train Split    : {metadata.get('train_sample_count')}")
        print(f"  - Dev Split      : {metadata.get('dev_sample_count')}")
        print("-" * 65)

        type_counter = Counter([r.get("type") for r in records])
        level_counter = Counter([r.get("level") for r in records])

        print(f"Question Types     : {dict(type_counter)}")
        print(f"Difficulty Levels  : {dict(level_counter)}")

        if records:
            sample = records[0]
            context_paragraphs = len(sample.get("context", {}).get("title", []))
            print(f"Sample Question ID : {sample.get('id')}")
            print(f"Sample Question    : {sample.get('question')}")
            print(f"Sample Answer      : {sample.get('answer')}")
            print(f"Context Paragraphs : {context_paragraphs}")

    else:
        # Full Hugging Face dataset statistics
        print("Dataset Source     : Hugging Face (hotpot_qa / distractor)")
        print(f"Available Splits   : {list(ds_dict.keys())}")
        for split_name, split_data in ds_dict.items():
            print(f"  - {split_name:<16}: {len(split_data):,} rows")
        print("-" * 65)

        sample = ds_dict["train"][0]
        context_paragraphs = len(sample["context"]["title"])
        type_counter = Counter(ds_dict["train"]["type"])
        level_counter = Counter(ds_dict["train"]["level"])

        print(f"Train Question Types : {dict(type_counter)}")
        print(f"Train Difficulty     : {dict(level_counter)}")
        print("-" * 65)
        print("SAMPLE ENTRY (Train Record #0):")
        print(f"  ID        : {sample['id']}")
        print(f"  Type      : {sample['type']}")
        print(f"  Level     : {sample['level']}")
        print(f"  Question  : {sample['question']}")
        print(f"  Answer    : {sample['answer']}")
        print(f"  Contexts  : {context_paragraphs} paragraphs ({', '.join(sample['context']['title'][:3])}...)")

    print("=" * 65)


if __name__ == "__main__":
    sample_file = "data/sample_hotpotqa.json"
    if os.path.exists(sample_file):
        print(f"[stats] Reading from local sample file: {sample_file}")
        data = load_local_sample(sample_file)
        print_dataset_statistics(data, is_local_sample=True)
    else:
        print("[stats] Local sample file not found. Fetching full dataset from Hugging Face...")
        ds = load_hotpotqa_dataset()
        print_dataset_statistics(ds, is_local_sample=False)
