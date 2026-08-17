"""
Groq API Answer Generator — fallback for when Gemini quota is exhausted.
Uses llama-3.1-70b-versatile (free tier: 14,400 req/day, 6,000 tokens/min).
"""

from typing import List, Dict, Any
import re

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class GroqGenerator:
    """
    Generates answers using Groq's free-tier API.
    Compatible with the same interface as AnswerGenerator.
    """

    MODEL = "llama-3.1-70b-versatile"  # Free tier model — fast + capable

    def __init__(self, api_key: str):
        if not GROQ_AVAILABLE:
            raise RuntimeError(
                "groq package not installed. Run: pip install groq"
            )
        if not api_key:
            raise ValueError("GROQ_API_KEY is empty")
        self.client = Groq(api_key=api_key)

    def generate(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generates a grounded answer with inline citations using Groq.
        Same return shape as AnswerGenerator.generate().
        """
        if not context_chunks:
            return {
                "answer_text": "No context available to answer this question.",
                "citations": [],
                "sources": [],
                "is_insufficient": True,
            }

        from generation.generator import build_generation_prompt
        prompt, sources = build_generation_prompt(query, context_chunks)

        try:
            completion = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise research assistant. "
                            "Always cite sources using bracketed numbers like [1], [2]. "
                            "Never make up information not in the provided context."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
            )
            answer_text = completion.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Groq API error: {e}") from e

        is_insufficient = answer_text.startswith("INSUFFICIENT_CONTEXT")
        cited_numbers = set(int(n) for n in re.findall(r"\[(\d+)\]", answer_text))
        citations = [s for s in sources if s["citation_number"] in cited_numbers]

        return {
            "answer_text": answer_text,
            "citations": citations,
            "sources": sources,
            "is_insufficient": is_insufficient,
        }
