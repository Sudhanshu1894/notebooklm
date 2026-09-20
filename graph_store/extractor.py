"""
Gemini Entity & Relationship Extractor for GraphRAG Research Notebook.
Extracts structured entity nodes and relationship edges from document text chunks.

Fallback chain:
  1. Gemini Flash (best quality, needs API quota)
  2. Local TF-IDF extractor (zero cost, always available)
"""

import json
import re
import math
from collections import Counter
from typing import Dict, Any, List, Optional
from config.settings import get_settings


EXTRACTION_SYSTEM_PROMPT = """You are an expert Knowledge Graph Extraction system.
Your task is to analyze the provided text chunk and extract key entities and relationships between them.

OUTPUT FORMAT REQUIREMENTS:
You MUST respond with ONLY a valid JSON object matching the following structure:
{
  "entities": [
    {
      "name": "Entity Name",
      "type": "PERSON | ORGANIZATION | CONCEPT | LOCATION | EVENT | PRODUCT"
    }
  ],
  "relationships": [
    {
      "source_name": "Source Entity Name",
      "source_type": "Entity Type",
      "target_name": "Target Entity Name",
      "target_type": "Entity Type",
      "relation_type": "SHORT_UPPERCASE_RELATION_NAME",
      "description": "Brief summary of how they are related"
    }
  ]
}

FEW-SHOT EXAMPLE:
Input Text: "Scott Derrickson (born July 16, 1966) is an American director who directed Doctor Strange."
Output JSON:
{
  "entities": [
    {"name": "Scott Derrickson", "type": "PERSON"},
    {"name": "American", "type": "LOCATION"},
    {"name": "Doctor Strange", "type": "CONCEPT"}
  ],
  "relationships": [
    {
      "source_name": "Scott Derrickson",
      "source_type": "PERSON",
      "target_name": "American",
      "target_type": "LOCATION",
      "relation_type": "NATIONALITY_OF",
      "description": "Scott Derrickson is an American citizen."
    },
    {
      "source_name": "Scott Derrickson",
      "source_type": "PERSON",
      "target_name": "Doctor Strange",
      "target_type": "CONCEPT",
      "relation_type": "DIRECTED",
      "description": "Scott Derrickson directed the movie Doctor Strange."
    }
  ]
}
"""

# ---------------------------------------------------------------------------
# Local TF-IDF Fallback Extractor (zero API cost, always available)
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
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]


def _classify_entity(name: str) -> str:
    name_lower = name.lower()
    org_hints = ["university", "institute", "company", "corporation", "inc", "ltd",
                 "group", "foundation", "organization", "department", "ministry"]
    loc_hints = ["city", "country", "state", "river", "mountain", "island",
                 "ocean", "sea", "lake", "district", "region", "province"]
    person_hints = ["mr", "dr", "prof", "professor", "minister", "president",
                    "director", "officer", "manager", "engineer"]
    if any(h in name_lower for h in org_hints):
        return "ORGANIZATION"
    if any(h in name_lower for h in loc_hints):
        return "LOCATION"
    if any(h in name_lower for h in person_hints):
        return "PERSON"
    return "CONCEPT"


def _local_extract(text: str, chunk_id: str) -> Dict[str, Any]:
    """
    TF-IDF based local entity extractor. No API calls needed.
    Extracts capitalized multi-word phrases as entities and infers
    simple co-occurrence relationships between them.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.split()) >= 4]

    if not sentences:
        return {"entities": [], "relationships": []}

    # --- Entity extraction: capitalized multi-word phrases ---
    entity_pattern = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\b")
    entity_counts: Counter = Counter()
    entity_sentence_map: Dict[str, List[int]] = {}

    for i, sent in enumerate(sentences):
        for match in entity_pattern.finditer(sent):
            ent = match.group(0).strip()
            if len(ent) > 3 and ent.lower() not in _STOPWORDS:
                entity_counts[ent] += 1
                entity_sentence_map.setdefault(ent, []).append(i)

    # Keep top entities by frequency
    top_entities = [e for e, _ in entity_counts.most_common(20)]

    entities = []
    for ent in top_entities:
        entities.append({
            "name": ent,
            "type": _classify_entity(ent),
            "chunk_id": chunk_id,
        })

    # --- Relationship extraction: entities co-occurring in same sentence ---
    relationships = []
    seen_pairs = set()

    for sent_idx, sent in enumerate(sentences):
        ents_in_sent = [e for e in top_entities if e in sent]
        for i in range(len(ents_in_sent)):
            for j in range(i + 1, len(ents_in_sent)):
                src, tgt = ents_in_sent[i], ents_in_sent[j]
                pair_key = tuple(sorted([src, tgt]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    relationships.append({
                        "source_name": src,
                        "source_type": _classify_entity(src),
                        "target_name": tgt,
                        "target_type": _classify_entity(tgt),
                        "relation_type": "RELATED_TO",
                        "description": f"'{src}' and '{tgt}' are mentioned together in the same context.",
                        "chunk_id": chunk_id,
                    })

    # Cap relationships to avoid noise
    relationships = relationships[:30]

    return {"entities": entities, "relationships": relationships}


# ---------------------------------------------------------------------------
# Main Graph Extractor (Gemini → Local TF-IDF fallback)
# ---------------------------------------------------------------------------

_GEMINI_QUOTA_SIGNALS = ("429", "quota", "resource_exhausted", "exhausted",
                          "too many requests", "rate limit", "billing")


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(sig in msg for sig in _GEMINI_QUOTA_SIGNALS)


class GraphExtractor:
    """
    Extracts structured entities and relationships from text.
    Primary: Gemini Flash. Fallback: Local TF-IDF (zero cost, always works).
    """
    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self._gemini_client = None
        self._gemini_disabled = False  # Set True after quota hit to skip retries

        if self.api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[extractor] Gemini client init failed: {e}. Will use local extractor.")

    def extract_from_text(self, text: str, chunk_id: str) -> Dict[str, Any]:
        """
        Extracts entities and relationships from a text chunk.
        Tries Gemini first, falls back to local TF-IDF on quota/error.
        """
        if not text.strip():
            return {"entities": [], "relationships": []}

        # Try Gemini if available and not quota-disabled
        if self._gemini_client and not self._gemini_disabled:
            result = self._try_gemini(text, chunk_id)
            if result is not None:
                return result

        # Local TF-IDF fallback
        print(f"[extractor] Using local TF-IDF extractor for chunk '{chunk_id}'")
        return _local_extract(text, chunk_id)

    def _try_gemini(self, text: str, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Attempts Gemini extraction. Returns None on failure (triggers fallback).
        Sets self._gemini_disabled=True on quota errors to skip future attempts.
        """
        user_prompt = f"Extract all key entities and relationships from this text:\n\n\"{text}\""

        response_text = self._call_gemini(user_prompt)
        if response_text is None:
            return None  # quota/error → use fallback

        parsed = self._parse_json(response_text)

        if parsed is None:
            # Retry once with stricter prompt
            print(f"[extractor] JSON parsing failed for chunk '{chunk_id}'. Retrying...")
            strict_prompt = (
                f"{user_prompt}\n\n"
                "CRITICAL: Your previous response contained invalid JSON syntax. "
                "Respond WITH ONLY VALID RAW JSON. No markdown code blocks, no trailing commas, no extra text."
            )
            response_text_retry = self._call_gemini(strict_prompt)
            if response_text_retry is None:
                return None
            parsed = self._parse_json(response_text_retry)

        if parsed is None:
            print(f"[extractor] Extraction failed after retry for chunk '{chunk_id}'. Falling back to local.")
            return None

        # Tag each item with source chunk ID
        for entity in parsed.get("entities", []):
            entity["chunk_id"] = chunk_id
        for rel in parsed.get("relationships", []):
            rel["chunk_id"] = chunk_id

        return parsed

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Calls Gemini Flash. Returns None on quota/network error."""
        try:
            response = self._gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=f"{EXTRACTION_SYSTEM_PROMPT}\n\n{prompt}",
            )
            return response.text if response and response.text else ""
        except Exception as e:
            if _is_quota_error(e):
                print(f"[extractor] Gemini quota exhausted. Switching to local TF-IDF for all remaining chunks.")
                self._gemini_disabled = True
            else:
                print(f"[extractor] Gemini API error: {e}")
            return None

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Parses JSON from response text, stripping markdown code fences if present."""
        if not text:
            return None
        cleaned = text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "entities" in data:
                return data
        except Exception:
            pass
        return None
