"""
Ollama Knowledge Injection Trainer for GraphRAG Research Notebook.

Extracts summaries, entities, and key facts from document chunks using TF-IDF
(zero API cost), persists them in SQLite, and creates/updates a per-notebook
Ollama Modelfile with a SYSTEM prompt containing the accumulated knowledge.

This gives the Ollama model persistent "memory" of uploaded documents.
"""

import re
import math
import json
import requests
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

from ingestion.registry import DocumentRegistry


# ---------------------------------------------------------------------------
# TF-IDF helpers (same logic as local_mini_model.py, standalone here)
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
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _sentence_split(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.split()) >= 4]


# ---------------------------------------------------------------------------
# Knowledge Extractor (TF-IDF based, zero API cost)
# ---------------------------------------------------------------------------

class KnowledgeExtractor:
    """Extracts structured knowledge from text chunks using TF-IDF scoring."""

    def extract_from_chunks(self, chunks: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
        """
        Extract summaries, entities, concepts, and facts from chunks.
        Returns list of {type, content, metadata} dicts.
        """
        knowledge_items: List[Dict[str, Any]] = []
        all_text = " ".join(c.get("text", "") for c in chunks)
        all_sentences = _sentence_split(all_text)

        if not all_sentences:
            return knowledge_items

        # Build IDF
        doc_freqs: Counter = Counter()
        tokenised_sentences = []
        for sent in all_sentences:
            tokens = _tokenise(sent)
            tokenised_sentences.append(tokens)
            doc_freqs.update(set(tokens))

        total_docs = len(all_sentences) or 1
        idf = {t: math.log((total_docs + 1) / (freq + 1)) + 1.0 for t, freq in doc_freqs.items()}

        # 1. Summary — top 5 most "central" sentences
        sentence_scores = []
        for i, (sent, tokens) in enumerate(zip(all_sentences, tokenised_sentences)):
            if not tokens:
                continue
            tf = Counter(tokens)
            total = len(tokens)
            score = sum((tf[t] / total) * idf.get(t, 1.0) for t in tf)
            sentence_scores.append((score, sent))

        sentence_scores.sort(key=lambda x: -x[0])
        summary_sents = [s for _, s in sentence_scores[:5]]
        if summary_sents:
            knowledge_items.append({
                "type": "summary",
                "content": " ".join(summary_sents),
                "metadata": {"doc_id": doc_id, "sentence_count": len(summary_sents)},
            })

        # 2. Entities — capitalized multi-word phrases (proper nouns)
        entity_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
        entity_counts: Counter = Counter()
        for sent in all_sentences:
            for match in entity_pattern.finditer(sent):
                entity = match.group(0).strip()
                if len(entity) > 3 and entity.lower() not in _STOPWORDS:
                    entity_counts[entity] += 1

        for entity, count in entity_counts.most_common(30):
            # Classify entity type heuristically
            entity_type = _classify_entity(entity)
            knowledge_items.append({
                "type": "entity",
                "content": entity,
                "metadata": {"entity_type": entity_type, "frequency": count, "doc_id": doc_id},
            })

        # 3. Key concepts — high-IDF single tokens (domain terms)
        term_scores = []
        term_freq: Counter = Counter()
        for tokens in tokenised_sentences:
            term_freq.update(tokens)

        for term, freq in term_freq.items():
            if freq >= 2 and len(term) > 3:
                score = freq * idf.get(term, 1.0)
                term_scores.append((score, term, freq))

        term_scores.sort(key=lambda x: -x[0])
        for score, term, freq in term_scores[:20]:
            knowledge_items.append({
                "type": "concept",
                "content": term,
                "metadata": {"score": round(score, 2), "frequency": freq, "doc_id": doc_id},
            })

        # 4. Key facts — top-scoring sentences that contain entities
        entity_names = {e.lower() for e, _ in entity_counts.most_common(20)}
        fact_candidates = []
        for score, sent in sentence_scores:
            sent_lower = sent.lower()
            if any(ent in sent_lower for ent in entity_names):
                fact_candidates.append((score, sent))

        for _, fact in fact_candidates[:10]:
            knowledge_items.append({
                "type": "fact",
                "content": fact,
                "metadata": {"doc_id": doc_id},
            })

        return knowledge_items


def _classify_entity(name: str) -> str:
    """Simple heuristic entity type classification."""
    name_lower = name.lower()
    org_hints = ["university", "institute", "company", "corporation", "inc", "ltd", "group", "foundation", "organization"]
    loc_hints = ["city", "country", "state", "river", "mountain", "island", "ocean", "sea", "lake"]

    if any(h in name_lower for h in org_hints):
        return "ORGANIZATION"
    if any(h in name_lower for h in loc_hints):
        return "LOCATION"
    # Default to CONCEPT for multi-word capitalized phrases
    return "CONCEPT"


# ---------------------------------------------------------------------------
# Ollama Modelfile Builder & Trainer
# ---------------------------------------------------------------------------

class OllamaTrainer:
    """
    Manages per-notebook Ollama model training via knowledge injection.

    Flow:
    1. Extract knowledge from document chunks (TF-IDF, zero cost)
    2. Persist to SQLite notebook_knowledge table
    3. Build an Ollama Modelfile with SYSTEM prompt containing knowledge
    4. Register/update the custom model with Ollama API
    """

    BASE_MODEL = "qwen2.5:0.5b"

    def __init__(self, ollama_host: Optional[str] = None):
        default_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_host = (ollama_host or default_host).rstrip("/")
        self.registry = DocumentRegistry()
        self.extractor = KnowledgeExtractor()

    def train_on_chunks(
        self,
        notebook_id: str,
        doc_id: str,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Extract knowledge from chunks and persist to database.
        Then create/update the Ollama custom model.

        Returns: {"items_extracted": int, "model_registered": bool}
        """
        print(f"[ollama_trainer] Extracting knowledge from doc '{doc_id}' for notebook '{notebook_id}'...")

        # Extract knowledge items
        items = self.extractor.extract_from_chunks(chunks, doc_id)

        if not items:
            print(f"[ollama_trainer] No knowledge extracted from doc '{doc_id}'.")
            return {"items_extracted": 0, "model_registered": False}

        # Persist to SQLite
        self.registry.save_knowledge_batch(notebook_id, doc_id, items)
        print(f"[ollama_trainer] Saved {len(items)} knowledge items for notebook '{notebook_id}'.")

        # Try to register model with Ollama
        model_registered = self.register_model(notebook_id)

        return {"items_extracted": len(items), "model_registered": model_registered}

    def build_modelfile(self, notebook_id: str) -> str:
        """Build an Ollama Modelfile SYSTEM prompt from accumulated knowledge."""
        knowledge = self.registry.get_knowledge(notebook_id)

        if not knowledge:
            return ""

        # Group by type
        summaries = [k["content"] for k in knowledge if k["knowledge_type"] == "summary"]
        entities = [k for k in knowledge if k["knowledge_type"] == "entity"]
        concepts = [k["content"] for k in knowledge if k["knowledge_type"] == "concept"]
        facts = [k["content"] for k in knowledge if k["knowledge_type"] == "fact"]

        # Build SYSTEM prompt
        parts = [
            "You are a knowledgeable AI assistant that has been trained on specific documents.",
            "You have deep knowledge about the following topics from the user's uploaded documents.",
            "Use this knowledge to answer questions accurately. Always cite your knowledge when relevant.",
            "",
        ]

        if summaries:
            parts.append("## Document Summaries")
            for i, s in enumerate(summaries, 1):
                parts.append(f"{i}. {s}")
            parts.append("")

        if entities:
            parts.append("## Key Entities")
            entity_strs = []
            for e in entities[:25]:
                meta = e.get("metadata", {})
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                etype = meta.get("entity_type", "CONCEPT")
                entity_strs.append(f"- {e['content']} ({etype})")
            parts.extend(entity_strs)
            parts.append("")

        if concepts:
            parts.append("## Key Concepts")
            parts.append(", ".join(concepts[:20]))
            parts.append("")

        if facts:
            parts.append("## Key Facts")
            for f in facts[:15]:
                parts.append(f"- {f}")
            parts.append("")

        system_prompt = "\n".join(parts)

        # Construct Modelfile
        modelfile = f'FROM {self.BASE_MODEL}\nSYSTEM """\n{system_prompt}\n"""\n'
        return modelfile

    def register_model(self, notebook_id: str) -> bool:
        """Create/update the Ollama model for this notebook."""
        modelfile = self.build_modelfile(notebook_id)
        if not modelfile:
            return False

        model_name = f"graphrag-{notebook_id}"

        try:
            response = requests.post(
                f"{self.ollama_host}/api/create",
                json={"name": model_name, "modelfile": modelfile},
                timeout=60,
            )
            if response.status_code == 200:
                print(f"[ollama_trainer] Model '{model_name}' registered/updated successfully.")
                return True
            else:
                print(f"[ollama_trainer] Failed to register model: {response.status_code} {response.text[:200]}")
                return False
        except requests.ConnectionError:
            print(f"[ollama_trainer] Ollama not reachable at {self.ollama_host}. Model not registered.")
            return False
        except Exception as e:
            print(f"[ollama_trainer] Error registering model: {e}")
            return False

    def get_model_name(self, notebook_id: str) -> Optional[str]:
        """Returns the custom model name if it exists in Ollama, else None."""
        model_name = f"graphrag-{notebook_id}"
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get("models", [])
                for m in models:
                    if m.get("name", "").startswith(model_name):
                        return model_name
            return None
        except Exception:
            return None

    def get_system_prompt(self, notebook_id: str) -> str:
        """Returns the current SYSTEM prompt that would be injected (for UI transparency)."""
        modelfile = self.build_modelfile(notebook_id)
        if not modelfile:
            return "No knowledge has been extracted yet. Upload a document to train the AI."
        # Extract just the SYSTEM portion
        match = re.search(r'SYSTEM """\n(.*?)\n"""', modelfile, re.DOTALL)
        return match.group(1) if match else ""
