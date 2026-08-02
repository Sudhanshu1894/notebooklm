"""
Embedding Model Wrapper for GraphRAG Research Notebook.
Wraps local sentence-transformers models to produce vector embeddings.
"""

from typing import List, Union
from sentence_transformers import SentenceTransformer
from config.settings import get_settings


class EmbeddingModel:
    """
    Singleton wrapper for sentence-transformers to avoid reloading weights on every call.
    """
    _instance = None

    def __new__(cls, model_name: str = None):
        if cls._instance is None:
            cls._instance = super(EmbeddingModel, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = None):
        if self._initialized:
            return

        settings = get_settings()
        self.model_name = model_name or getattr(settings, "embedding_model", "all-MiniLM-L6-v2")
        print(f"[embedding] Loading SentenceTransformer model '{self.model_name}'...")
        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self._initialized = True
        print(f"[embedding] Model loaded successfully (dimension: {self.dimension}).")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of text strings into vector representations.

        Args:
            texts: List of text passages.

        Returns:
            List of floating point embedding vectors.
        """
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """
        Embeds a single search query string.
        """
        return self.embed_texts([query])[0]


# Global convenience helper function
def embed_texts(texts: List[str], model_name: str = "all-MiniLM-L6-v2") -> List[List[float]]:
    model = EmbeddingModel(model_name=model_name)
    return model.embed_texts(texts)


def embed_query(query: str, model_name: str = "all-MiniLM-L6-v2") -> List[float]:
    model = EmbeddingModel(model_name=model_name)
    return model.embed_query(query)
