"""
Gemini Answer Generation with Bracketed Citations for GraphRAG Research Notebook.
"""

import re
from typing import List, Dict, Any, Optional
from google import genai
from config.settings import get_settings


def build_generation_prompt(query: str, context_chunks: List[Dict[str, Any]]) -> tuple[str, List[Dict]]:
    """
    Builds a grounded generation prompt with numbered source references.
    Returns the prompt string and the citation map list.
    """
    sources = []
    context_parts = []

    for i, chunk in enumerate(context_chunks, start=1):
        meta = chunk.get("metadata", {})
        doc_id = meta.get("doc_id", "unknown")
        page_num = meta.get("page_number", "?")
        section = meta.get("section_header", "")
        section_str = f" — {section}" if section else ""
        text = chunk.get("text", "").strip()

        context_parts.append(f"[{i}] (Source: {doc_id}, Page {page_num}{section_str})\n{text}")
        sources.append({
            "citation_number": i,
            "chunk_id": chunk.get("chunk_id", ""),
            "doc_id": doc_id,
            "page_number": page_num,
            "section_header": section,
            "text_preview": text[:150],
        })

    context_block = "\n\n".join(context_parts)

    prompt = f"""You are a research assistant with access to the following source documents.
Answer the user's question using ONLY the provided context.
For every factual claim, add a bracketed citation like [1], [2] matching the source numbers below.
If the context does not contain enough information to answer, respond with exactly:
"INSUFFICIENT_CONTEXT: I could not find enough information in the provided sources to answer this question."

CONTEXT SOURCES:
{context_block}

QUESTION: {query}

ANSWER (with inline citations):"""

    return prompt, sources


class AnswerGenerator:
    """Generates cited answers using Gemini Flash."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in .env")
        self.client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generates a grounded answer with citation markers and source mapping.

        Returns:
            Dict with: answer_text, citations, is_insufficient, sources
        """
        if not context_chunks:
            return {
                "answer_text": "No context available to answer this question.",
                "citations": [],
                "sources": [],
                "is_insufficient": True,
            }

        prompt, sources = build_generation_prompt(query, context_chunks)

        try:
            response = self.client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt,
            )
            answer_text = response.text.strip() if response and response.text else ""
        except Exception as e:
            answer_text = f"[Gemini API Error]: {str(e)}"

        is_insufficient = answer_text.startswith("INSUFFICIENT_CONTEXT")

        # Extract citation numbers referenced in answer
        cited_numbers = set(int(n) for n in re.findall(r"\[(\d+)\]", answer_text))
        citations = [s for s in sources if s["citation_number"] in cited_numbers]

        return {
            "answer_text": answer_text,
            "citations": citations,
            "sources": sources,
            "is_insufficient": is_insufficient,
        }
