"""
Gemini Entity & Relationship Extractor for GraphRAG Research Notebook.
Extracts structured entity nodes and relationship edges from document text chunks.
"""

import json
import re
from typing import Dict, Any, List, Optional
from google import genai
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


class GraphExtractor:
    """
    Extracts structured entities and relationships from text using Gemini Flash.
    """
    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in .env"
            )
        self.client = genai.Client(api_key=self.api_key)

    def extract_from_text(self, text: str, chunk_id: str) -> Dict[str, Any]:
        """
        Extracts entities and relationships from a text chunk. Retries once if JSON parsing fails.
        """
        if not text.strip():
            return {"entities": [], "relationships": []}

        user_prompt = f"Extract all key entities and relationships from this text:\n\n\"{text}\""

        # Initial attempt
        response_text = self._call_gemini(user_prompt, is_retry=False)
        parsed = self._parse_json(response_text)

        if parsed is None:
            print(f"[extractor] JSON parsing failed for chunk '{chunk_id}'. Retrying with strict instruction...")
            strict_prompt = (
                f"{user_prompt}\n\n"
                "CRITICAL: Your previous response contained invalid JSON syntax. "
                "Respond WITH ONLY VALID RAW JSON. No markdown code blocks, no trailing commas, no extra text."
            )
            response_text_retry = self._call_gemini(strict_prompt, is_retry=True)
            parsed = self._parse_json(response_text_retry)

        if parsed is None:
            print(f"[extractor] Extraction failed after retry for chunk '{chunk_id}'. Returning empty graph.")
            return {"entities": [], "relationships": []}

        # Tag each item with source chunk ID
        for entity in parsed.get("entities", []):
            entity["chunk_id"] = chunk_id
        for rel in parsed.get("relationships", []):
            rel["chunk_id"] = chunk_id

        return parsed

    def _call_gemini(self, prompt: str, is_retry: bool = False) -> str:
        """Helper calling Gemini Flash API."""
        try:
            response = self.client.models.generate_content(
                model="gemini-flash-latest",
                contents=f"{EXTRACTION_SYSTEM_PROMPT}\n\n{prompt}",
            )
            return response.text if response and response.text else ""
        except Exception as e:
            print(f"[extractor] Gemini API error: {e}")
            return ""

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Parses JSON from response text, stripping markdown code fences if present."""
        if not text:
            return None

        # Clean markdown code fences if LLM wrapped output in ```json ... ```
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
