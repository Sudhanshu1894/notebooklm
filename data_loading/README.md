# Data Loading Module (`data_loading/`)

## Intended Role
This directory is responsible for downloading, preprocessing, and loading benchmark datasets (e.g., HotpotQA distractor dataset) for the GraphRAG research notebook system.

## Components
- `loader.py`: Downloads HotpotQA via Hugging Face `datasets`, enforces train/dev/test splits, extracts a 200-example sample for fast local iteration, and validates schema integrity.
- `stats.py`: Utility script to inspect row counts, split ratios, document lengths, and sample entries.

## Data Storage
Raw downloaded data and local sample subsets are stored in `../data/`.
