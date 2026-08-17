"""
Local Mini AI Model - Zero-dependency fallback when all API keys are exhausted.

Strategy: TF-IDF extractive summarization
  - Tokenise query and all context sentences.
  - Score each sentence by cosine similarity to the query vector.
  - Select the top-N most relevant sentences, preserving source citations.
  - Assemble into a cited answer.

Modes:
  - generate()       : Standard cited extractive QA
  - generate_teach() : Structured teaching response (Overview, How It Works, Examples, Takeaways)
  - generate_quiz()  : 5-question MCQ quiz derived from document sentences

No network calls, no extra packages - only Python stdlib (math, re, collections).
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# TF-IDF helpers
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would could should may might shall can of in on at to for "
    "with by from up about into than through during before after above "
    "below between each and or but not no nor so yet both either "
    "neither once just also this that these those i me my we us our "
    "you your he him his she her it its they them their what which who "
    "whom when where why how all any few more most other some such".split()
)


def _tokenise(text: str) -> List[str]:
    """Lower-case, split on non-alphanumeric chars, remove stopwords."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = Counter(tokens)
    total = len(tokens) or 1
    return {t: (count / total) * idf.get(t, 1.0) for t, count in tf.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _sentence_split(text: str) -> List[str]:
    """Naive sentence splitter for most English text."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.split()) >= 4]


def _build_idf_and_score(
    query: str,
    all_sentences: List[Tuple[str, int]],
) -> List[Tuple[float, str, int]]:
    """Build IDF from corpus, score each sentence against query."""
    doc_freqs: Counter = Counter()
    tokenised_sentences: List[List[str]] = []
    for sent, _ in all_sentences:
        tokens = _tokenise(sent)
        tokenised_sentences.append(tokens)
        doc_freqs.update(set(tokens))

    total_docs = len(all_sentences) or 1
    idf = {
        t: math.log((total_docs + 1) / (freq + 1)) + 1.0
        for t, freq in doc_freqs.items()
    }

    query_tokens = _tokenise(query)
    query_vec = _tfidf_vector(query_tokens, idf)

    scored: List[Tuple[float, str, int]] = []
    for (sent, citation_num), tokens in zip(all_sentences, tokenised_sentences):
        sent_vec = _tfidf_vector(tokens, idf)
        score = _cosine(query_vec, sent_vec)
        scored.append((score, sent, citation_num))

    scored.sort(key=lambda x: -x[0])
    return scored


# ---------------------------------------------------------------------------
# Main model class
# ---------------------------------------------------------------------------

class LocalMiniModel:
    """
    Extractive QA / Teaching / Quiz model using TF-IDF sentence scoring.

    Drop-in replacement for AnswerGenerator / GroqGenerator.
    Uses Python stdlib only - no network, no extra packages needed.
    """

    def __init__(self, max_sentences: int = 6):
        """
        Args:
            max_sentences: Maximum sentences to extract for the standard answer.
        """
        self.max_sentences = max_sentences

    def _build_sources_and_sentences(
        self, context_chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[str, int]]]:
        """Shared helper: build sources list + flat sentence corpus."""
        sources: List[Dict[str, Any]] = []
        all_sentences: List[Tuple[str, int]] = []
        for i, chunk in enumerate(context_chunks, start=1):
            meta = chunk.get("metadata", {})
            text = chunk.get("text", "").strip()
            sources.append(
                {
                    "citation_number": i,
                    "chunk_id": chunk.get("chunk_id", ""),
                    "doc_id": meta.get("doc_id", "unknown"),
                    "page_number": meta.get("page_number", "?"),
                    "section_header": meta.get("section_header", ""),
                    "text_preview": text[:150],
                }
            )
            for sent in _sentence_split(text):
                all_sentences.append((sent, i))
        return sources, all_sentences

    # ------------------------------------------------------------------
    # Standard cited QA
    # ------------------------------------------------------------------

    def generate(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a cited extractive answer from context chunks.

        Returns dict with keys: answer_text, citations, sources, is_insufficient, mode_used.
        Identical return shape to AnswerGenerator.generate().
        """
        if not context_chunks:
            return {
                "answer_text": "No context available to answer this question.",
                "citations": [],
                "sources": [],
                "is_insufficient": True,
                "mode_used": "chat",
            }

        sources, all_sentences = self._build_sources_and_sentences(context_chunks)

        if not all_sentences:
            return self._fallback_preview(sources, context_chunks)

        scored = _build_idf_and_score(query, all_sentences)
        top = scored[: self.max_sentences]
        top_filtered = [(score, s, c) for score, s, c in top if score >= 0.01]

        if not top_filtered:
            return self._fallback_preview(sources, context_chunks)

        # Re-order by original position for readability
        order_map: Dict[Tuple[str, int], int] = {
            (s, c): idx for idx, (s, c) in enumerate(all_sentences)
        }
        ordered = sorted(
            [(s, c) for _, s, c in top_filtered],
            key=lambda x: order_map.get(x, 9999),
        )

        used_citation_nums: set = set()
        answer_sentences: List[str] = []
        seen: set = set()
        for sent, citation_num in ordered:
            if sent not in seen:
                answer_sentences.append(f"{sent} [{citation_num}]")
                used_citation_nums.add(citation_num)
                seen.add(sent)

        answer_text = "[LOCAL MODEL] " + " ".join(answer_sentences)
        citations = [s for s in sources if s["citation_number"] in used_citation_nums]

        return {
            "answer_text": answer_text,
            "citations": citations,
            "sources": sources,
            "is_insufficient": False,
            "mode_used": "chat",
        }

    # ------------------------------------------------------------------
    # Teaching mode
    # ------------------------------------------------------------------

    def generate_teach(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a structured teaching response with markdown sections.

        Sections: Overview, Real-World Analogy, How It Works, Concrete Example, Key Takeaways.
        Returns same shape as AnswerGenerator.generate() but with mode_used='teach'.
        """
        if not context_chunks:
            return {
                "answer_text": "No documents available to teach from. Please upload a document first.",
                "citations": [],
                "sources": [],
                "is_insufficient": True,
                "mode_used": "teach",
            }

        sources, all_sentences = self._build_sources_and_sentences(context_chunks)

        if not all_sentences:
            return self._fallback_preview(sources, context_chunks)

        scored = _build_idf_and_score(query, all_sentences)
        # We need a larger pool for the different sections
        top_pool = [(score, s, c) for score, s, c in scored if score >= 0.01]

        if not top_pool:
            # Fall back to top sentences regardless of score
            top_pool = scored[:12]

        used_nums: set = set()
        seen_sents: set = set()

        def _pick(n: int, start: int = 0) -> List[Tuple[str, int]]:
            """Pick n unique sentences from the scored pool starting at index `start`."""
            result = []
            for _, s, c in top_pool[start:]:
                if s not in seen_sents and len(result) < n:
                    result.append((s, c))
                    seen_sents.add(s)
                    used_nums.add(c)
            return result

        # ── Overview: top 2 sentences
        overview_sents = _pick(2)
        overview_lines = " ".join(f"{s} [{c}]" for s, c in overview_sents)
        overview = overview_lines if overview_lines else "_No overview could be extracted from the document._"

        # ── Analogy: heuristic — look for sentences containing analogy keywords
        analogy_keywords = ["like", "similar", "analogy", "imagine", "think of", "compare", "just as"]
        analogy_candidates = [
            (score, s, c) for score, s, c in scored
            if any(kw in s.lower() for kw in analogy_keywords) and s not in seen_sents
        ]
        if analogy_candidates:
            _, best_analogy, best_c = analogy_candidates[0]
            analogy = f"Think of it like... {best_analogy} [{best_c}]"
            seen_sents.add(best_analogy)
            used_nums.add(best_c)
        else:
            # Use next best sentence and prefix it
            next_sents = _pick(1)
            if next_sents:
                s, c = next_sents[0]
                analogy = f"Think of it like... {s} [{c}]"
            else:
                analogy = "_No analogy could be extracted from the document._"

        # ── How It Works: next 3 sentences as bullet points
        how_sents = _pick(3)
        how_bullets = "\n".join(f"- {s} [{c}]" for s, c in how_sents)
        if not how_bullets:
            how_bullets = "_Mechanism details not found in the document._"

        # ── Concrete Example: pick from a different source chunk for diversity
        example_candidates = [
            (score, s, c) for score, s, c in scored
            if s not in seen_sents
        ]
        example_sents: List[Tuple[str, int]] = []
        for _, s, c in example_candidates:
            if len(example_sents) >= 2:
                break
            example_sents.append((s, c))
            seen_sents.add(s)
            used_nums.add(c)

        example_text = "\n\n".join(f"{s} [{c}]" for s, c in example_sents)
        if not example_text:
            example_text = "_No concrete examples found in the document._"

        # ── Key Takeaways: pick 3 more unique sentences, bold first word
        takeaway_sents = _pick(3)

        def _bold_first_term(sent: str) -> str:
            words = sent.split()
            if not words:
                return sent
            # Find first meaningful word (skip stopwords)
            for i, w in enumerate(words):
                clean = re.sub(r"[^a-z]", "", w.lower())
                if clean and clean not in _STOPWORDS and len(clean) > 2:
                    words[i] = f"**{w}**"
                    return " ".join(words)
            return sent

        takeaway_lines = "\n".join(
            f"- {_bold_first_term(s)} [{c}]" for s, c in takeaway_sents
        )
        if not takeaway_lines:
            takeaway_lines = "_Key takeaways could not be determined from the document._"

        # ── Assemble markdown
        topic = query.strip().rstrip("?").title()
        answer_text = (
            f"> ⚠️ **[LOCAL MODEL]** — Offline TF-IDF mode. No Gemini API key detected. "
            f"Responses are extracted from source text, not generated.\n\n"
            f"## 📋 Overview\n\n{overview}\n\n"
            f"## 💡 Real-World Analogy\n\n{analogy}\n\n"
            f"## ⚙️ How It Works\n\n{how_bullets}\n\n"
            f"## 🎯 Concrete Example\n\n{example_text}\n\n"
            f"## ✅ Key Takeaways\n\n{takeaway_lines}"
        )

        citations = [s for s in sources if s["citation_number"] in used_nums]

        return {
            "answer_text": answer_text,
            "citations": citations,
            "sources": sources,
            "is_insufficient": False,
            "mode_used": "teach",
        }

    # ------------------------------------------------------------------
    # Quiz mode
    # ------------------------------------------------------------------

    def generate_quiz(
        self,
        context_chunks: List[Dict[str, Any]],
        topic: str = "",
        n_questions: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate a basic MCQ quiz from document context using TF-IDF.

        Each question uses a high-scoring sentence as the 'stem' with the
        key term blanked out; distractors are other high-scoring terms from
        the corpus. Returns same JSON schema as AnswerGenerator.generate_quiz().
        """
        if not context_chunks:
            return {"error": "No documents available to generate a quiz from."}

        query = topic if topic else "important concept definition key term"
        sources, all_sentences = self._build_sources_and_sentences(context_chunks)

        if len(all_sentences) < 5:
            return {"error": "Not enough text in documents to generate quiz questions. Please upload a longer document."}

        scored = _build_idf_and_score(query, all_sentences)
        # Filter to reasonable sentences (long enough, has a score)
        candidates = [
            (score, s, c) for score, s, c in scored
            if score >= 0.005 and 8 <= len(s.split()) <= 60
        ]

        if len(candidates) < n_questions:
            candidates = scored[:max(n_questions * 2, 10)]

        # Pick n_questions diverse sentences (one per source chunk if possible)
        chosen: List[Tuple[float, str, int]] = []
        seen_chunks: set = set()
        # First pass: one per chunk
        for score, s, c in candidates:
            if c not in seen_chunks and len(chosen) < n_questions:
                chosen.append((score, s, c))
                seen_chunks.add(c)
        # Fill remaining from top candidates
        for score, s, c in candidates:
            if len(chosen) >= n_questions:
                break
            if (score, s, c) not in chosen:
                chosen.append((score, s, c))

        chosen = chosen[:n_questions]

        # Build a corpus of key terms for distractor generation
        all_key_terms: List[str] = []
        for _, s, _ in scored[:30]:
            tokens = [
                t for t in s.split()
                if len(t) > 4 and re.sub(r"[^a-z]", "", t.lower()) not in _STOPWORDS
            ]
            all_key_terms.extend(tokens[:3])

        # Deduplicate while preserving order
        seen_terms: set = set()
        unique_terms: List[str] = []
        for t in all_key_terms:
            clean = t.lower().rstrip(".,;:")
            if clean not in seen_terms:
                unique_terms.append(t.rstrip(".,;:"))
                seen_terms.add(clean)

        questions = []
        difficulties = ["easy", "easy", "medium", "medium", "hard"]

        for idx, (score, sentence, citation_num) in enumerate(chosen):
            # Find the most "important" term in the sentence to blank out
            words = sentence.split()
            key_term: Optional[str] = None
            key_term_idx: int = -1
            for i, w in enumerate(words):
                clean = re.sub(r"[^a-z0-9]", "", w.lower())
                if clean and clean not in _STOPWORDS and len(clean) > 3:
                    key_term = w.rstrip(".,;:")
                    key_term_idx = i
                    break

            if not key_term or key_term_idx < 0:
                # Can't blank a term — use full sentence as a true/false style question
                question_text = f"Which of the following best describes the content of this passage: \"{sentence[:120]}...\""
                correct_option = "The passage accurately describes the concept above."
                distractors = [
                    "The passage is discussing an unrelated topic.",
                    "The passage contradicts the concept above.",
                    "The passage is a definition of a different term.",
                ]
            else:
                # Create fill-in-the-blank style question
                blanked = words.copy()
                blanked[key_term_idx] = "______"
                blanked_sentence = " ".join(blanked)
                question_text = f"Fill in the blank: \"{blanked_sentence}\""
                correct_option = key_term

                # Distractors: other key terms from the corpus that aren't the answer
                distractor_pool = [
                    t for t in unique_terms
                    if t.lower().rstrip(".,;:") != key_term.lower().rstrip(".,;:")
                ]
                random.shuffle(distractor_pool)
                distractors = distractor_pool[:3]
                # Pad if not enough distractors
                fallback_options = ["none of the above", "all of the above", "not applicable"]
                while len(distractors) < 3:
                    distractors.append(fallback_options[len(distractors) - 3])

            # Shuffle options and track correct index
            all_options = [correct_option] + distractors
            random.shuffle(all_options)
            correct_index = all_options.index(correct_option)

            source_hint = sources[citation_num - 1]["doc_id"] if citation_num <= len(sources) else ""
            questions.append({
                "question": question_text,
                "options": all_options,
                "correct_index": correct_index,
                "explanation": f"This answer comes from: \"{sentence[:200]}\"",
                "source_hint": source_hint,
                "difficulty": difficulties[idx] if idx < len(difficulties) else "medium",
            })

        return {"questions": questions}

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_preview(
        self,
        sources: List[Dict[str, Any]],
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Last resort: return the top chunk previews with citations."""
        previews = []
        for i, chunk in enumerate(context_chunks[:3], start=1):
            text = chunk.get("text", "").strip()[:300]
            previews.append(f"[{i}] {text}...")

        answer_text = (
            "[LOCAL MODEL] The query could not be matched to specific sentences. "
            "Here are the most relevant source excerpts:\n\n"
            + "\n\n".join(previews)
        )
        used_nums = set(range(1, min(4, len(context_chunks) + 1)))
        citations = [s for s in sources if s["citation_number"] in used_nums]
        return {
            "answer_text": answer_text,
            "citations": citations,
            "sources": sources,
            "is_insufficient": False,
            "mode_used": "chat",
        }
