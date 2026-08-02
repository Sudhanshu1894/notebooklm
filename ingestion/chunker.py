"""
Sentence-aware Text Chunking Module for GraphRAG Research Notebook.
Splits parsed documents into clean text chunks carrying citation metadata.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ingestion.parsers import ParsedDocument


@dataclass
class DocumentChunk:
    """Represents a text chunk extracted from a document with citation metadata."""
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    page_number: int
    section_header: str
    start_char_offset: int
    end_char_offset: int
    char_length: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentChunker:
    """
    Sentence-aware chunker that divides documents into token/character-bounded segments
    while preserving page/section location metadata for citation grounding.
    """
    def __init__(
        self,
        chunk_size: int = 500,  # Target tokens (~2000 characters)
        chunk_overlap: int = 50,  # Overlap tokens (~200 characters)
        char_per_token: float = 4.0,
    ):
        self.chunk_size_chars = int(chunk_size * char_per_token)
        self.chunk_overlap_chars = int(chunk_overlap * char_per_token)

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size_chars,
            chunk_overlap=self.chunk_overlap_chars,
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
            keep_separator=True,
        )

    def chunk_document(self, doc: ParsedDocument) -> List[DocumentChunk]:
        """
        Processes a ParsedDocument into a list of DocumentChunks with rich metadata.
        """
        chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page in doc.pages:
            page_text = page.text
            if not page_text:
                continue

            # Split page text into chunks
            raw_splits = self.splitter.split_text(page_text)

            current_search_pos = 0
            for split_text in raw_splits:
                # Find start and end character offsets within page text
                start_offset = page_text.find(split_text, current_search_pos)
                if start_offset == -1:
                    start_offset = current_search_pos
                end_offset = start_offset + len(split_text)
                current_search_pos = max(0, start_offset + len(split_text) - self.chunk_overlap_chars)

                chunk_id = f"{doc.doc_id}_c{global_chunk_idx}"
                chunk_obj = DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    chunk_index=global_chunk_idx,
                    text=split_text,
                    page_number=page.page_number,
                    section_header=page.section_header,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    char_length=len(split_text),
                )
                chunks.append(chunk_obj)
                global_chunk_idx += 1

        return chunks


def chunk_parsed_document(
    doc: ParsedDocument,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[DocumentChunk]:
    """Helper function to chunk a parsed document with default or custom parameters."""
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_document(doc)
