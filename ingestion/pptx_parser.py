"""
PowerPoint PPTX Parser for GraphRAG Research Notebook.
Extracts text from slides including text boxes, tables, and speaker notes.
"""

import os
from typing import List
from pptx import Presentation
from pptx.util import Inches
from ingestion.parsers import ExtractedPage, ParsedDocument


class PPTXParser:
    """Extracts text from PowerPoint PPTX files using python-pptx."""

    def parse(self, file_path: str, doc_id: str) -> ParsedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PPTX file not found: {file_path}")

        prs = Presentation(file_path)
        pages: List[ExtractedPage] = []
        full_text_chunks: List[str] = []

        for slide_num, slide in enumerate(prs.slides, start=1):
            slide_texts: List[str] = []
            slide_title = ""

            for shape in slide.shapes:
                # Extract title
                if shape.has_text_frame:
                    if shape.shape_id == slide.shapes.title and slide.shapes.title:
                        slide_title = shape.text_frame.text.strip()

                    # Extract all text from text frames
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_texts.append(text)

                # Extract text from tables
                if shape.has_table:
                    table = shape.table
                    for row in table.rows:
                        row_texts = []
                        for cell in row.cells:
                            cell_text = cell.text.strip()
                            if cell_text:
                                row_texts.append(cell_text)
                        if row_texts:
                            slide_texts.append(" | ".join(row_texts))

            # Extract speaker notes
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes_text = slide.notes_slide.notes_text_frame.text.strip()
                if notes_text:
                    slide_texts.append(f"[Speaker Notes] {notes_text}")

            if slide_texts:
                combined = "\n".join(slide_texts)
                pages.append(ExtractedPage(
                    page_number=slide_num,
                    text=combined,
                    section_header=slide_title or f"Slide {slide_num}",
                ))
                full_text_chunks.append(combined)

        filename = os.path.basename(file_path)
        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type="pptx",
            pages=pages,
            full_text="\n\n".join(full_text_chunks),
        )
