"""
Microsoft Word (.docx) Export Module for GraphRAG Research Notebook.

Generates beautifully styled, publication-grade .docx documents using python-docx:
- Custom title styling and metadata banners
- Hierarchical headings (H1, H2, H3) with Slate & Indigo color palette
- Highlighted callout boxes for key takeaways (shaded box with accent left border)
- Markdown parsing to native Word runs (bold, italic, code, bullet lists, inline citations)
- Structured references table with zebra striping and document provenance
"""

import io
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn


# ---------------------------------------------------------------------------
# Color Palette Constants (Slate & Indigo Modern Design System)
# ---------------------------------------------------------------------------
COLOR_PRIMARY = RGBColor(0x1E, 0x29, 0x3B)       # Slate 900 (Main Headings / Title)
COLOR_SECONDARY = RGBColor(0x43, 0x38, 0xCA)     # Indigo 700 (H2)
COLOR_ACCENT = RGBColor(0x0F, 0x76, 0x6E)        # Teal 700 (H3)
COLOR_TEXT = RGBColor(0x33, 0x41, 0x55)          # Slate 700 (Body)
COLOR_MUTED = RGBColor(0x64, 0x74, 0x8B)         # Slate 500 (Captions / Meta)
COLOR_INDIGO_ACCENT = RGBColor(0x4F, 0x46, 0xE5) # Indigo 600 (Callout / Citations)

HEX_SHADING_CALLOUT = "EEF2FF"                   # Soft Indigo 50
HEX_BORDER_CALLOUT = "4F46E5"                    # Indigo 600 (3pt border)
HEX_TABLE_HEADER = "1E293B"                      # Slate 900
HEX_TABLE_ZEBRA = "F8FAFC"                       # Slate 50
HEX_BORDER_LIGHT = "CBD5E1"                      # Slate 300


# ---------------------------------------------------------------------------
# XML Helper Functions for Advanced docx Styling
# ---------------------------------------------------------------------------

def set_cell_background(cell, hex_color: str):
    """Sets the background fill color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shading)


def set_callout_borders(cell, border_color: str = HEX_BORDER_CALLOUT, border_size: str = "24"):
    """
    Applies a callout box border style: thick solid left border, none for top/right/bottom.
    border_size: in 1/8 pt (24 = 3pt).
    """
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:left w:val="single" w:sz="{border_size}" w:space="0" w:color="{border_color}"/>
            <w:bottom w:val="none"/>
            <w:right w:val="none"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)


def set_cell_margins(cell, top: int = 140, bottom: int = 140, left: int = 220, right: int = 160):
    """Sets internal padding (in dxa) for a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)


def set_table_light_borders(table, border_color: str = HEX_BORDER_LIGHT):
    """Applies clean horizontal borders to a structured table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="6" w:space="0" w:color="{border_color}"/>
            <w:left w:val="none"/>
            <w:bottom w:val="single" w:sz="8" w:space="0" w:color="{border_color}"/>
            <w:right w:val="none"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)


def set_row_header_properties(row):
    """Marks a table row as a repeating header row that will not split across pages."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))


# ---------------------------------------------------------------------------
# Main Document Exporter Class
# ---------------------------------------------------------------------------

class DocxExporter:
    """
    Builds styled Microsoft Word documents (.docx) from GraphRAG syntheses,
    notes, and research transcripts.
    """

    def __init__(self):
        self.doc = docx.Document()
        self._configure_document_styles()

    def _configure_document_styles(self):
        """Sets standard page margins, default fonts, and paragraph line spacing."""
        # 1-inch margins
        for section in self.doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Normal body style
        normal_style = self.doc.styles['Normal']
        normal_style.font.name = 'Calibri'
        normal_style.font.size = Pt(10.5)
        normal_style.font.color.rgb = COLOR_TEXT
        normal_style.paragraph_format.line_spacing = 1.15
        normal_style.paragraph_format.space_after = Pt(5)

    def add_title_block(
        self,
        title: str,
        subtitle: Optional[str] = None,
        notebook_name: Optional[str] = None,
        total_sources: Optional[int] = None,
    ):
        """
        Renders a header block with document title, subtitle, and metadata banner.
        """
        # Main Title
        title_p = self.doc.add_paragraph()
        title_p.paragraph_format.space_before = Pt(0)
        title_p.paragraph_format.space_after = Pt(2)
        title_run = title_p.add_run(title)
        title_run.font.name = 'Calibri'
        title_run.font.size = Pt(24)
        title_run.font.bold = True
        title_run.font.color.rgb = COLOR_PRIMARY

        # Subtitle
        if subtitle:
            sub_p = self.doc.add_paragraph()
            sub_p.paragraph_format.space_before = Pt(0)
            sub_p.paragraph_format.space_after = Pt(6)
            sub_run = sub_p.add_run(subtitle)
            sub_run.font.name = 'Calibri'
            sub_run.font.size = Pt(11)
            sub_run.font.italic = True
            sub_run.font.color.rgb = COLOR_MUTED

        # Metadata banner line
        meta_items = []
        if notebook_name:
            meta_items.append(f"Notebook: {notebook_name}")
        meta_items.append(f"Date: {datetime.now().strftime('%B %d, %Y')}")
        if total_sources is not None and total_sources > 0:
            meta_items.append(f"Sources Cited: {total_sources}")
        meta_items.append("Generated by GraphRAG Research Notebook")

        meta_p = self.doc.add_paragraph()
        meta_p.paragraph_format.space_before = Pt(2)
        meta_p.paragraph_format.space_after = Pt(16)
        meta_run = meta_p.add_run("  •  ".join(meta_items))
        meta_run.font.name = 'Calibri'
        meta_run.font.size = Pt(9)
        meta_run.font.color.rgb = COLOR_MUTED

        # Horizontal accent rule
        p_hr = self.doc.add_paragraph()
        p_hr.paragraph_format.space_before = Pt(0)
        p_hr.paragraph_format.space_after = Pt(14)
        p_hr_border = parse_xml(f'''
            <w:pBdr {nsdecls("w")}>
                <w:bottom w:val="single" w:sz="12" w:space="1" w:color="{HEX_BORDER_CALLOUT}"/>
            </w:pBdr>
        ''')
        p_hr._p.get_or_add_pPr().append(p_hr_border)

    def add_heading(self, text: str, level: int = 1):
        """Adds a styled heading (1, 2, or 3) with precise colors and spacing."""
        p = self.doc.add_paragraph()

        if level == 1:
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(text)
            run.font.name = 'Calibri'
            run.font.size = Pt(16)
            run.font.bold = True
            run.font.color.rgb = COLOR_PRIMARY
        elif level == 2:
            p.paragraph_format.space_before = Pt(11)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(text)
            run.font.name = 'Calibri'
            run.font.size = Pt(13)
            run.font.bold = True
            run.font.color.rgb = COLOR_SECONDARY
        else:
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(text)
            run.font.name = 'Calibri'
            run.font.size = Pt(11)
            run.font.bold = True
            run.font.color.rgb = COLOR_ACCENT

        return p

    def add_callout_box(self, title: str, points: List[str] | str, badge_text: str = "KEY TAKEAWAYS"):
        """
        Generates a highlighted callout box with light indigo shading and a thick
        solid left border for key takeaways or core concept summaries.
        """
        table = self.doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        cell = table.cell(0, 0)
        cell.width = Inches(6.5)

        set_cell_background(cell, HEX_SHADING_CALLOUT)
        set_callout_borders(cell, HEX_BORDER_CALLOUT, border_size="24")
        set_cell_margins(cell, top=140, bottom=140, left=200, right=140)

        # Callout Header Badge
        header_p = cell.paragraphs[0]
        header_p.paragraph_format.space_before = Pt(2)
        header_p.paragraph_format.space_after = Pt(4)
        
        badge_run = header_p.add_run(f"💡  {badge_text}")
        badge_run.font.name = 'Calibri'
        badge_run.font.size = Pt(10)
        badge_run.font.bold = True
        badge_run.font.color.rgb = COLOR_INDIGO_ACCENT

        if title and title != badge_text:
            sub_title_run = header_p.add_run(f" — {title}")
            sub_title_run.font.name = 'Calibri'
            sub_title_run.font.size = Pt(10)
            sub_title_run.font.bold = True
            sub_title_run.font.color.rgb = COLOR_PRIMARY

        # Points
        if isinstance(points, list):
            for pt_text in points:
                pt_p = cell.add_paragraph()
                pt_p.paragraph_format.space_before = Pt(2)
                pt_p.paragraph_format.space_after = Pt(3)
                pt_p.paragraph_format.left_indent = Inches(0.2)
                
                bullet_run = pt_p.add_run("•  ")
                bullet_run.font.bold = True
                bullet_run.font.color.rgb = COLOR_INDIGO_ACCENT
                
                self._render_markdown_in_paragraph(pt_p, pt_text)
        else:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            self._render_markdown_in_paragraph(p, points)

        # Add spacing after callout box
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(6)

    def _render_markdown_in_paragraph(self, paragraph, text: str):
        """
        Parses inline markdown tokens (**bold**, *italic*, `code`, and [1] citations)
        and appends them as formatted runs into the paragraph.
        """
        # Tokenizer regex for bold, italic, inline code, and citations like [1] or [1, 2]
        pattern = re.compile(r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\[\d+(?:,\s*\d+)*\])')
        parts = pattern.split(text)

        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                run = paragraph.add_run(part[2:-2])
                run.font.name = 'Calibri'
                run.font.bold = True
                run.font.color.rgb = COLOR_PRIMARY
            elif part.startswith("*") and part.endswith("*") and len(part) >= 2:
                run = paragraph.add_run(part[1:-1])
                run.font.name = 'Calibri'
                run.font.italic = True
                run.font.color.rgb = COLOR_TEXT
            elif part.startswith("`") and part.endswith("`") and len(part) >= 2:
                run = paragraph.add_run(f" {part[1:-1]} ")
                run.font.name = 'Consolas'
                run.font.size = Pt(9.5)
                run.font.color.rgb = COLOR_SECONDARY
            elif re.match(r'^\[\d+(?:,\s*\d+)*\]$', part):
                # Inline citation marker [1], [2]
                run = paragraph.add_run(part)
                run.font.name = 'Calibri'
                run.font.size = Pt(9)
                run.font.bold = True
                run.font.color.rgb = COLOR_INDIGO_ACCENT
            else:
                run = paragraph.add_run(part)
                run.font.name = 'Calibri'
                run.font.color.rgb = COLOR_TEXT

    def add_markdown_table(self, table_lines: List[str]):
        """Renders a Markdown pipe table into a beautifully styled Word table."""
        if not table_lines:
            return

        rows_data = []
        for line in table_lines:
            line_str = line.strip()
            # Skip separator lines like | :--- | :--- |
            if re.match(r'^\|(?:\s*:?-+:?\s*\|)+$', line_str):
                continue
            cells = [c.strip() for c in line_str.strip('|').split('|')]
            if cells:
                rows_data.append(cells)

        if not rows_data:
            return

        num_cols = max(len(r) for r in rows_data)
        num_rows = len(rows_data)

        table = self.doc.add_table(rows=num_rows, cols=num_cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_light_borders(table)

        # Style header row
        hdr_row = table.rows[0]
        set_row_header_properties(hdr_row)
        for c_idx, text in enumerate(rows_data[0]):
            cell = hdr_row.cells[c_idx]
            set_cell_background(cell, HEX_TABLE_HEADER)
            set_cell_margins(cell, top=100, bottom=100, left=120, right=100)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(text)
            run.font.name = 'Calibri'
            run.font.size = Pt(9.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        # Style data rows
        for r_idx in range(1, num_rows):
            row = table.rows[r_idx]
            is_zebra = (r_idx % 2 == 0)
            bg_color = HEX_TABLE_ZEBRA if is_zebra else "FFFFFF"
            for c_idx, text in enumerate(rows_data[r_idx]):
                if c_idx < num_cols:
                    cell = row.cells[c_idx]
                    set_cell_background(cell, bg_color)
                    set_cell_margins(cell, top=90, bottom=90, left=120, right=100)
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    self._render_markdown_in_paragraph(p, text)

        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(6)

    def add_markdown_content(self, markdown_text: str):
        """
        Translates multi-paragraph markdown text into native Word headings,
        bulleted lists, numbered lists, blockquotes, tables, and body paragraphs.
        """
        lines = markdown_text.split("\n")
        in_callout = False
        callout_lines = []
        in_table = False
        table_lines = []

        for line in lines:
            trimmed = line.strip()

            if not trimmed:
                if in_callout:
                    self.add_callout_box("Note", "\n".join(callout_lines), badge_text="NOTE")
                    in_callout = False
                    callout_lines = []
                if in_table:
                    self.add_markdown_table(table_lines)
                    in_table = False
                    table_lines = []
                continue

            # Check for table line
            if trimmed.startswith("|") and trimmed.endswith("|"):
                if in_callout:
                    self.add_callout_box("Note", "\n".join(callout_lines), badge_text="NOTE")
                    in_callout = False
                    callout_lines = []
                in_table = True
                table_lines.append(trimmed)
                continue
            elif in_table:
                self.add_markdown_table(table_lines)
                in_table = False
                table_lines = []

            # Check for blockquote / callout
            if trimmed.startswith(">"):
                in_callout = True
                callout_content = trimmed.lstrip(">").strip()
                callout_content = re.sub(r'^\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*', '', callout_content)
                callout_lines.append(callout_content)
                continue
            elif in_callout:
                self.add_callout_box("Note", "\n".join(callout_lines), badge_text="NOTE")
                in_callout = False
                callout_lines = []

            # Check for Headings
            if trimmed.startswith("### "):
                self.add_heading(trimmed[4:].strip(), level=3)
            elif trimmed.startswith("## "):
                self.add_heading(trimmed[3:].strip(), level=2)
            elif trimmed.startswith("# "):
                self.add_heading(trimmed[2:].strip(), level=1)
            # Check for Bullet List
            elif trimmed.startswith(("- ", "* ", "• ")):
                p = self.doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.25)
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(2)
                bullet_run = p.add_run("•  ")
                bullet_run.font.bold = True
                bullet_run.font.color.rgb = COLOR_SECONDARY
                self._render_markdown_in_paragraph(p, trimmed[2:].strip())
            # Check for Numbered List
            elif re.match(r'^\d+\.\s+', trimmed):
                match = re.match(r'^(\d+\.)\s+(.*)$', trimmed)
                p = self.doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.25)
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(2)
                num_run = p.add_run(f"{match.group(1)}  ")
                num_run.font.bold = True
                num_run.font.color.rgb = COLOR_SECONDARY
                self._render_markdown_in_paragraph(p, match.group(2))
            else:
                # Regular paragraph
                p = self.doc.add_paragraph()
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(5)
                self._render_markdown_in_paragraph(p, trimmed)

        if in_callout and callout_lines:
            self.add_callout_box("Note", "\n".join(callout_lines), badge_text="NOTE")
        if in_table and table_lines:
            self.add_markdown_table(table_lines)

    def add_references_table(self, citations: List[Dict[str, Any]]):
        """
        Appends a styled References & Source Citations table at the document's end,
        complete with zebra striping, dark slate header, and clean borders.
        """
        if not citations:
            return

        self.add_heading("References & Source Citations", level=1)

        intro_p = self.doc.add_paragraph()
        intro_p.paragraph_format.space_before = Pt(1)
        intro_p.paragraph_format.space_after = Pt(8)
        intro_run = intro_p.add_run("The following source materials were retrieved and cited in this research synthesis:")
        intro_run.font.size = Pt(9.5)
        intro_run.font.italic = True
        intro_run.font.color.rgb = COLOR_MUTED

        # Table dimensions
        col_widths = [Inches(0.7), Inches(1.8), Inches(1.2), Inches(2.8)]
        headers = ["Ref #", "Source Document", "Page / Section", "Context Excerpt"]

        table = self.doc.add_table(rows=len(citations) + 1, cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_light_borders(table)

        # Header Row
        hdr_row = table.rows[0]
        set_row_header_properties(hdr_row)
        for i, heading in enumerate(headers):
            cell = hdr_row.cells[i]
            cell.width = col_widths[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_background(cell, HEX_TABLE_HEADER)
            set_cell_margins(cell, top=100, bottom=100, left=120, right=100)

            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            if i == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER

            run = p.add_run(heading)
            run.font.name = 'Calibri'
            run.font.size = Pt(9.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        # Data Rows
        for r_idx, cite in enumerate(citations, start=1):
            row = table.rows[r_idx]
            is_zebra = (r_idx % 2 == 0)
            bg_color = HEX_TABLE_ZEBRA if is_zebra else "FFFFFF"

            cite_num = str(cite.get("citation_number", r_idx))
            doc_id = str(cite.get("doc_id", "Unknown Source"))
            page_num = str(cite.get("page_number", ""))
            section = str(cite.get("section_header", "")).strip()
            preview = str(cite.get("text_preview", "")).strip()

            # Location formatting
            loc_parts = []
            if page_num and page_num != "?":
                loc_parts.append(f"Page {page_num}")
            if section:
                loc_parts.append(section)
            location_text = " • ".join(loc_parts) if loc_parts else "—"

            row_data = [
                f"[{cite_num}]",
                doc_id,
                location_text,
                f'"{preview[:140]}…"' if len(preview) > 140 else f'"{preview}"'
            ]

            for c_idx, val in enumerate(row_data):
                cell = row.cells[c_idx]
                cell.width = col_widths[c_idx]
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                set_cell_background(cell, bg_color)
                set_cell_margins(cell, top=90, bottom=90, left=120, right=100)

                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)

                if c_idx == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run(val)
                    run.font.name = 'Calibri'
                    run.font.size = Pt(9.5)
                    run.font.bold = True
                    run.font.color.rgb = COLOR_INDIGO_ACCENT
                elif c_idx == 1:
                    run = p.add_run(val)
                    run.font.name = 'Calibri'
                    run.font.size = Pt(9)
                    run.font.bold = True
                    run.font.color.rgb = COLOR_PRIMARY
                elif c_idx == 2:
                    run = p.add_run(val)
                    run.font.name = 'Calibri'
                    run.font.size = Pt(8.5)
                    run.font.color.rgb = COLOR_MUTED
                else:
                    run = p.add_run(val)
                    run.font.name = 'Calibri'
                    run.font.size = Pt(8.5)
                    run.font.italic = True
                    run.font.color.rgb = COLOR_TEXT

    def to_bytes(self) -> io.BytesIO:
        """Saves the document into an in-memory BytesIO buffer ready for transmission."""
        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer


# ---------------------------------------------------------------------------
# High-Level Pre-configured Document Builders
# ---------------------------------------------------------------------------

def extract_key_takeaways_from_text(text: str) -> List[str]:
    """
    Heuristically extracts key takeaways or highlights from an answer text
    to populate the callout box if explicit takeaways are not provided.
    """
    takeaways = []
    # 1. Look for explicit takeaways or key points sections
    lines = text.split("\n")
    collecting = False
    for line in lines:
        l_clean = line.strip()
        if re.search(r'(?i)key takeaway|takeaways|summary|in summary|core findings', l_clean):
            collecting = True
            continue
        if collecting:
            if l_clean.startswith(("- ", "* ", "• ")) or re.match(r'^\d+\.\s+', l_clean):
                clean_pt = re.sub(r'^(?:[-*•]|\d+\.)\s+', '', l_clean)
                takeaways.append(clean_pt)
                if len(takeaways) >= 4:
                    break
            elif l_clean.startswith("#"):
                break

    # 2. If no explicit section, extract strong bullet points from anywhere in the text
    if not takeaways:
        for line in lines:
            l_clean = line.strip()
            if (l_clean.startswith(("- ", "* ")) and len(l_clean) > 25 and len(l_clean) < 180):
                takeaways.append(l_clean[2:].strip())
                if len(takeaways) >= 3:
                    break

    # 3. Fallback: Take first 2 sentences if nothing else
    if not takeaways:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 30:
                takeaways.append(s_clean)
                if len(takeaways) >= 2:
                    break

    return takeaways[:4]


def build_answer_docx(
    query: str,
    answer: str,
    citations: List[Dict[str, Any]],
    notebook_name: str = "Research Notebook",
    takeaways: Optional[List[str]] = None,
) -> io.BytesIO:
    """
    Builds a single-topic research memo / answer export with:
    - Title banner matching query
    - Key Takeaways Callout Box
    - Detailed Synthesized Response
    - References & Provenance Table
    """
    exporter = DocxExporter()

    # Title & Metadata
    exporter.add_title_block(
        title=query,
        subtitle="GraphRAG Research Synthesis & Answer Memo",
        notebook_name=notebook_name,
        total_sources=len(citations),
    )

    # Key Takeaways Callout Box
    points = takeaways or extract_key_takeaways_from_text(answer)
    if points:
        exporter.add_callout_box(
            title="Core Conceptual Takeaways",
            points=points,
            badge_text="KEY TAKEAWAYS"
        )

    # Main Synthesized Content
    exporter.add_heading("Detailed Analysis & Synthesis", level=1)
    exporter.add_markdown_content(answer)

    # References Table
    if citations:
        exporter.add_references_table(citations)

    return exporter.to_bytes()


def build_study_guide_docx(
    notebook_name: str,
    overview_text: str = "",
    topics: Optional[List[Dict[str, Any]]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
    overall_takeaways: Optional[List[str]] = None,
    markdown_content: Optional[str] = None,
) -> io.BytesIO:
    """
    Builds a comprehensive multi-topic study guide for an entire notebook with:
    - Cover Title & Metadata
    - Executive Takeaways Callout Box
    - Chapter-by-Chapter Topic Deep Dives
    - Glossary of Terminology Table
    - Full Consolidated References Table
    """
    exporter = DocxExporter()

    exporter.add_title_block(
        title=f"{notebook_name} — Study Guide",
        subtitle="Comprehensive Document Synthesis & Topic Mastery Guide",
        notebook_name=notebook_name,
        total_sources=len(citations or []),
    )

    # Executive Callout Box
    takeaways = overall_takeaways or [
        "Synthesizes knowledge graph relationships and semantic embeddings across all uploaded materials.",
        "Grounds every conceptual claim in verifiable inline citations from original source documents.",
        "Structured for academic revision, thesis preparation, and structured knowledge retention."
    ]
    exporter.add_callout_box(
        title="Executive Summary & Learning Goals",
        points=takeaways,
        badge_text="EXECUTIVE BRIEFING"
    )

    if markdown_content:
        # Strip duplicate executive briefing headers if present
        clean_content = re.sub(r'(?i)#+\s*Executive Briefing\s*\n.*?(?=#|$)', '', markdown_content, flags=re.DOTALL).strip()
        exporter.add_markdown_content(clean_content)
    else:
        # Overview Section
        if overview_text:
            exporter.add_heading("1. Notebook Overview", level=1)
            exporter.add_markdown_content(overview_text)

        # Topic Sections
        if topics:
            exporter.add_heading("2. Conceptual Deep Dives", level=1)
            for idx, topic in enumerate(topics, start=1):
                title = topic.get("title", f"Topic {idx}")
                content = topic.get("content", "")
                exporter.add_heading(f"2.{idx}  {title}", level=2)
                exporter.add_markdown_content(content)

    # Consolidated References Table
    if citations:
        exporter.add_references_table(citations)

    return exporter.to_bytes()

    # Consolidated References Table
    if citations:
        exporter.add_references_table(citations)

    return exporter.to_bytes()


def build_chat_transcript_docx(
    notebook_name: str,
    messages: List[Dict[str, Any]],
) -> io.BytesIO:
    """
    Builds an archive of the entire chat session with questions, answers,
    and consolidated citations.
    """
    exporter = DocxExporter()

    all_citations = []
    seen_chunk_ids = set()

    exporter.add_title_block(
        title=f"{notebook_name} — Research Transcript",
        subtitle="Chronological Q&A Session and Inquiry Record",
        notebook_name=notebook_name,
        total_sources=0, # Updated below
    )

    exporter.add_callout_box(
        title="Session Record",
        points=[
            f"Contains {len(messages)} exchange(s) from interactive research exploration.",
            "All cited claims are cross-referenced in the bibliography at the end of this document."
        ],
        badge_text="SESSION LOG"
    )

    for i, msg in enumerate(messages, start=1):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        citations = msg.get("citations", [])

        if role == "user":
            exporter.add_heading(f"Query {i}: {content}", level=2)
        else:
            exporter.add_markdown_content(content)
            if citations:
                for c in citations:
                    cid = c.get("chunk_id", str(c.get("citation_number")))
                    if cid not in seen_chunk_ids:
                        seen_chunk_ids.add(cid)
                        all_citations.append(c)

    # Append all collected citations
    if all_citations:
        exporter.add_references_table(all_citations)

    return exporter.to_bytes()
