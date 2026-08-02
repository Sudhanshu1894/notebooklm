# Ingestion Module — Document Parsing & Chunking Pipeline

## Overview
The `ingestion/` module converts heterogeneous raw document uploads (PDF, DOCX, TXT) into structured text chunks carrying rich metadata for downstream embedding, vector search, knowledge graph entity extraction, and citation grounding.

---

## Strategy & Design Rationale

### 1. Extensible Parser Architecture (`parsers.py`)
- **PDF Parsing**: Powered by `PyMuPDF` (`fitz`), preserving page numbers and text layouts per page.
- **DOCX Parsing**: Powered by `python-docx`, maintaining section headers and hierarchical document structures.
- **TXT Parsing**: Reads plain text with encoding auto-fallback (`utf-8`).
- **Registry Pattern**: `ParserRegistry` decouples document format detection from downstream chunking, making adding new file extensions (e.g. Markdown, HTML) straightforward.

### 2. Sentence-Aware Text Chunking (`chunker.py`)
- **Default Chunk Size**: ~500 tokens (~2,000 characters).
- **Default Overlap**: ~50 tokens (~200 characters).
- **Rationale**: 
  - 500 tokens provides sufficient semantic context for sentence-transformer embedding vectors (`all-MiniLM-L6-v2`) and Gemini entity/relationship extraction without exceeding LLM context windows or diluting vector similarity scores.
  - Sentence-aware splitting (`RecursiveCharacterTextSplitter`) ensures breaks occur at natural paragraph or sentence boundaries rather than splitting mid-sentence or mid-word.
  - Overlap prevents loss of contextual information across chunk boundaries.

### 3. Source Citation Metadata
Each generated `DocumentChunk` carries:
- `chunk_id`: Unique identifier (e.g., `doc_123_c0`)
- `doc_id`: Source document ID
- `chunk_index`: Zero-based chunk order within the document
- `page_number`: Source page or section number
- `section_header`: Section title or heading (if available in DOCX/Markdown)
- `start_char_offset` / `end_char_offset`: Character offsets into source text

### 4. Document Registry (`registry.py`)
- SQLite-backed store (`./data/doc_registry.db`) tracking document status (`uploaded`, `parsed`, `chunked`, `failed`) and metadata.

---

## Testing
Run unit tests for parsers, chunker, and registry:
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_ingestion.py -v
```
