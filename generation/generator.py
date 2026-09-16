"""
Gemini Answer Generation for GraphRAG Research Notebook.

Modes:
  - chat   : Standard Q&A with citations
  - teach  : Tutor-style -- summary, analogy, examples, key takeaways
  - quiz   : Generates structured MCQ questions from document context

Fallback chain: Gemini Flash -> LocalMiniModel (TF-IDF, offline)
"""

import json
import re
import httpx
from typing import List, Dict, Any, Optional, Tuple
from config.settings import get_settings

# Default request timeout (seconds) — prevents indefinite hangs
_GEMINI_TIMEOUT = 45
_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


# ---------------------------------------------------------------------------
# Quota / rate-limit error detection
# ---------------------------------------------------------------------------

# Any of these signals in an exception should trigger fallback to LocalMiniModel
_GEMINI_FALLBACK_SIGNALS = (
    # Rate limits
    "429", "quota", "rate limit", "resource_exhausted",
    "exhausted", "too many requests", "billing", "rateLimitExceeded",
    # Model not available / deprecated
    "404", "not_found", "no longer available", "model",
    "invalid", "permission", "not supported",
)


def _should_fallback(exc: Exception) -> bool:
    """Return True if this Gemini error should trigger LocalMiniModel fallback."""
    msg = str(exc).lower()
    return any(sig in msg for sig in _GEMINI_FALLBACK_SIGNALS)

# Keep old name for backward compat
_is_quota_error = _should_fallback


# ---------------------------------------------------------------------------
# Teaching intent detection
# ---------------------------------------------------------------------------

_TEACH_SIGNALS = (
    "teach me", "explain", "summarize", "summarise", "help me understand",
    "what is", "what are", "how does", "how do", "describe", "tell me about",
    "give me an overview", "walk me through", "break down", "simplify",
    "i don't understand", "i dont understand", "clarify", "elaborate",
    "what does", "why is", "why does", "overview of", "introduction to",
)


def _is_teaching_intent(query: str) -> bool:
    """Return True if the query is asking to be taught/explained something."""
    q = query.lower().strip()
    return any(q.startswith(sig) or sig in q for sig in _TEACH_SIGNALS)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_source_block(context_chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict]]:
    """Shared helper: builds the numbered context block and sources list."""
    sources = []
    context_parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        meta = chunk.get("metadata", {})
        doc_id = meta.get("doc_id", "unknown")
        page_num = meta.get("page_number", "?")
        section = meta.get("section_header", "")
        section_str = f" -- {section}" if section else ""
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
    return "\n\n".join(context_parts), sources


def build_generation_prompt(query: str, context_chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict]]:
    """Standard Q&A prompt with inline citations."""
    context_block, sources = _build_source_block(context_chunks)
    prompt = (
        "You are a research assistant with access to the following source documents.\n"
        "Answer the user's question using ONLY the provided context.\n"
        "For every factual claim, add a bracketed citation like [1], [2] matching the source numbers below.\n"
        "If the context does not contain enough information to answer, respond with exactly:\n"
        "\"INSUFFICIENT_CONTEXT: I could not find enough information in the provided sources to answer this question.\"\n\n"
        f"CONTEXT SOURCES:\n{context_block}\n\nQUESTION: {query}\n\nANSWER (with inline citations):"
    )
    return prompt, sources


def build_teaching_prompt(query: str, context_chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict]]:
    """Tutor-style prompt that teaches like a great human teacher."""
    context_block, sources = _build_source_block(context_chunks)
    prompt = (
        "You are an elite, world-class AI tutor. You don't just state facts—you teach with enthusiasm, clarity, and deep insight. "
        "Your goal is to make complex topics instantly click for the learner, using conversational, natural language.\n"
        "Your task is to TEACH the user about the topic in their question using ONLY the provided source documents.\n\n"
        "STRICT RULES:\n"
        "- Act like a real, conversational AI teacher. Be encouraging, warm, and highly engaging!\n"
        "- Cite every factual claim with bracketed numbers like [1], [2] at the end of the sentence.\n"
        "- If a section cannot be supported by the sources, omit it -- do NOT invent information.\n"
        "- If the sources contain no relevant information at all, respond with exactly:\n"
        "  \"INSUFFICIENT_CONTEXT: I could not find enough information in the provided sources to answer this question.\"\n\n"
        "TEACHING FORMAT -- use ALL of these sections with proper markdown headers:\n\n"
        "## Overview\n"
        "Give a warm, engaging introduction (2-3 sentences). Explain the core concept in plain, simple English without jargon.\n\n"
        "## Real-World Analogy\n"
        "Craft ONE brilliant, relatable analogy that makes the concept intuitive. Start with \"Think of it like...\"\n\n"
        "## How It Works\n"
        "Break down the mechanics or key ideas into 3-5 clear, easy-to-digest bullet points with citations. Explain the 'why', not just the 'what'.\n\n"
        "## Concrete Example\n"
        "Walk through 1-2 specific, practical examples from the source material to ground the theory in reality.\n\n"
        "## Key Takeaways\n"
        "List 3-5 punchy bullet points the learner must remember. Use **bold** for the key term in each.\n\n"
        "---\n\n"
        f"CONTEXT SOURCES:\n{context_block}\n\n"
        f"TOPIC TO TEACH: {query}\n\n"
        "TEACH ME (use the engaging format above, with inline citations):"
    )
    return prompt, sources


def build_quiz_prompt(context_chunks: List[Dict[str, Any]], topic: str = "") -> str:
    """Generates a prompt for structured MCQ quiz output."""
    context_block, _ = _build_source_block(context_chunks)
    topic_line = f"Focus on: {topic}" if topic else "Cover the most important concepts from the sources."
    prompt = (
        "You are an expert educator creating a quiz to test understanding of study material.\n"
        f"Based ONLY on the source documents below, generate exactly 5 multiple-choice questions.\n"
        f"{topic_line}\n\n"
        "STRICT OUTPUT FORMAT -- respond with ONLY valid JSON, no markdown fences, no extra text:\n"
        '{\n'
        '  "questions": [\n'
        '    {\n'
        '      "question": "Clear question text here?",\n'
        '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '      "correct_index": 0,\n'
        '      "explanation": "Brief explanation citing the source.",\n'
        '      "source_hint": "doc_id or section name"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "Rules:\n"
        "- Each question must have exactly 4 options.\n"
        "- correct_index is 0-based (0=A, 1=B, 2=C, 3=D).\n"
        "- Questions should test understanding, not just memorisation.\n"
        "- Vary difficulty: 2 easy, 2 medium, 1 hard.\n"
        "- Do NOT include questions about information not in the sources.\n\n"
        f"CONTEXT SOURCES:\n{context_block}\n\nJSON OUTPUT:"
    )
    return prompt


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------

class AnswerGenerator:
    """Generates cited answers (chat or teach mode) using Gemini Flash."""

    MODEL = "gemini-3.5-flash"
    # Ordered fallback list — tested against this API key:
    # gemini-flash-latest  => ReadTimeout (hangs)
    # gemini-3.6-flash     => 429 quota exceeded
    # gemini-3.5-flash     => OK ~8s ✓
    _FALLBACK_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
    ]

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in .env")
        # Use direct httpx to avoid google-genai SDK timeout issues
        self._http = httpx.Client(
            headers={"x-goog-api-key": self.api_key},
            timeout=_GEMINI_TIMEOUT,
        )

    def _call(self, prompt: str) -> str:
        """Call Gemini REST API directly with httpx (no SDK retry loop)."""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        last_err = None

        for m in self._FALLBACK_MODELS:
            url = f"{_GEMINI_API_BASE}/{m}:generateContent"
            try:
                resp = self._http.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    text = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    if text:
                        print(f"[generator] Model used: {m}")
                        return text.strip()
                elif resp.status_code in (404, 410):
                    # Model deprecated — try next
                    print(f"[generator] Model {m} not available (404/410), trying next")
                    continue
                elif resp.status_code == 429:
                    print(f"[generator] Model {m} quota exceeded (429), trying next")
                    last_err = Exception(f"429 quota exceeded for {m}")
                    continue
                else:
                    err_body = resp.text[:200]
                    print(f"[generator] Model {m} error {resp.status_code}: {err_body}")
                    last_err = Exception(f"HTTP {resp.status_code}: {err_body}")
                    break  # Non-retriable error
            except httpx.TimeoutException as e:
                print(f"[generator] Model {m} timed out, trying next")
                last_err = e
                continue
            except Exception as e:
                print(f"[generator] Model {m} unexpected error: {e}")
                last_err = e
                break

        if last_err:
            raise last_err
        return ""

    def generate(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        mode: str = "auto",
    ) -> Dict[str, Any]:
        """
        Generate a grounded answer.
        mode: "auto" detects intent, "teach" forces teaching, "chat" forces Q&A.
        Returns dict with: answer_text, citations, sources, is_insufficient, mode_used
        """
        if not context_chunks:
            return {
                "answer_text": "No context available to answer this question.",
                "citations": [], "sources": [], "is_insufficient": True, "mode_used": mode,
            }

        if mode == "auto":
            resolved_mode = "teach" if _is_teaching_intent(query) else "chat"
        else:
            resolved_mode = mode

        if resolved_mode == "teach":
            prompt, sources = build_teaching_prompt(query, context_chunks)
        else:
            prompt, sources = build_generation_prompt(query, context_chunks)

        try:
            answer_text = self._call(prompt)
        except Exception as e:
            # Surface the error in the answer text — caller (generate_with_fallback)
            # will decide whether to fall back to LocalMiniModel.
            raise

        is_insufficient = answer_text.startswith("INSUFFICIENT_CONTEXT")
        cited_numbers = set(int(n) for n in re.findall(r"\[(\d+)\]", answer_text))
        citations = [s for s in sources if s["citation_number"] in cited_numbers]

        return {
            "answer_text": answer_text,
            "citations": citations,
            "sources": sources,
            "is_insufficient": is_insufficient,
            "mode_used": resolved_mode,
        }

    def generate_quiz(self, context_chunks: List[Dict[str, Any]], topic: str = "") -> Dict[str, Any]:
        """Generate a 5-question MCQ quiz from document context."""
        if not context_chunks:
            return {"error": "No documents available to generate a quiz from."}
        prompt = build_quiz_prompt(context_chunks, topic)
        try:
            raw = self._call(prompt)
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            raw = re.sub(r"\s*```$", "", raw.strip())
            return json.loads(raw)
        except json.JSONDecodeError as e:
            return {"error": f"Quiz generation failed (JSON parse error): {e}"}
        except Exception as e:
            if _is_quota_error(e):
                raise
            return {"error": f"Quiz generation failed: {e}"}


# ---------------------------------------------------------------------------
# Cascading fallback: Gemini -> LocalMiniModel
# ---------------------------------------------------------------------------

def generate_with_fallback(
    query: str,
    context_chunks: List[Dict[str, Any]],
    mode: str = "auto",
    model_preference: str = "auto",
    notebook_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Try generators in order, falling back on quota/rate-limit errors:
      1. Gemini Flash (primary) -- supports chat, teach, auto modes
      2. LocalMiniModel (offline TF-IDF) -- extractive, always available
    Respects model_preference: 'auto' (cascade), 'gemini' (force Gemini), 'local' (force Ollama).
    """
    settings = get_settings()
    tried: list = []

    # If preference is explicitly 'local', skip Gemini
    if model_preference != "local" and settings.gemini_api_key:
        try:
            gen = AnswerGenerator(api_key=settings.gemini_api_key)
            result = gen.generate(query, context_chunks, mode=mode)
            result["_generator"] = "gemini"
            return result
        except Exception as e:
            tried.append(f"Gemini: {e}")
            print(f"[generate_with_fallback] Gemini failed ({e}), falling back to local...")
            # If user explicitly requested gemini but it failed, we still fallback unless we shouldn't? 
            # Usually fallback is better than error, but let's just log it.
    elif model_preference == "gemini" and not settings.gemini_api_key:
        tried.append("Gemini: no API key")

    # Local fallback or forced local
    from generation.ollama_slm import OllamaSLM
    print(f"[generate_with_fallback] Using OllamaSLM (Local Ollama API).")
    try:
        local = OllamaSLM(notebook_id=notebook_id)
        # Honour the mode: use structured teaching if requested
        if mode == "teach" or (mode == "auto" and _is_teaching_intent(query)):
            result = local.generate_teach(query, context_chunks)
        else:
            result = local.generate(query, context_chunks)
        result["_generator"] = "ollama_slm"
    except Exception as e:
        print(f"[generate_with_fallback] OllamaSLM failed: {e}")
        result = {
            "answer_text": f"Error: Local model unavailable ({e})",
            "citations": [],
            "sources": [],
            "is_insufficient": True,
            "mode_used": mode,
            "_generator": "none"
        }

    result["_fallback_reason"] = " | ".join(tried)
    return result

