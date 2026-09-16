"""
Web Search Fallback using duckduckgo-search.
"""

from typing import List, Dict, Any
from duckduckgo_search import DDGS
import uuid

class WebSearcher:
    """
    Executes a web search and formats results into context chunks.
    """
    
    def __init__(self, max_results: int = 3):
        self.max_results = max_results
        
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches the web and returns context_chunks.
        """
        chunks = []
        try:
            results = list(DDGS().text(query, max_results=self.max_results))
                
            for res in results:
                chunks.append({
                    "chunk_id": f"web_{uuid.uuid4().hex[:8]}",
                    "text": res.get("body", ""),
                    "metadata": {
                        "doc_id": res.get("href", ""),
                        "page_number": "web",
                        "section_header": res.get("title", ""),
                        "source": "web_search"
                    }
                })
        except Exception as e:
            print(f"[WebSearcher] Error: {e}")
            
        return chunks
