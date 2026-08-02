"""
Configuration module for GraphRAG Research Notebook.
Loads and validates required environment variables for free-tier services.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Load .env file if present
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings and environment variable schema.
    Fails with descriptive error messages if required credentials are missing.
    """
    # Gemini API Key (Google AI Studio Free Tier)
    gemini_api_key: str = Field(
        default=os.getenv("GEMINI_API_KEY", ""),
        alias="GEMINI_API_KEY",
        description="Gemini API Key from Google AI Studio"
    )

    # Neo4j AuraDB Free Tier credentials
    neo4j_uri: str = Field(
        default=os.getenv("NEO4J_URI", ""),
        alias="NEO4J_URI",
        description="Neo4j AuraDB Connection URI (neo4j+s://...)"
    )
    neo4j_user: str = Field(
        default=os.getenv("NEO4J_USER", "neo4j"),
        alias="NEO4J_USER",
        description="Neo4j AuraDB Username"
    )
    neo4j_password: str = Field(
        default=os.getenv("NEO4J_PASSWORD", ""),
        alias="NEO4J_PASSWORD",
        description="Neo4j AuraDB Password"
    )

    # ChromaDB Vector Store settings (Local Embedded)
    chroma_persist_dir: str = Field(
        default=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db"),
        alias="CHROMA_PERSIST_DIR",
        description="Directory for local ChromaDB persistent storage"
    )

    # Supabase Free Tier credentials
    supabase_url: str = Field(
        default=os.getenv("SUPABASE_URL", ""),
        alias="SUPABASE_URL",
        description="Supabase Project URL"
    )
    supabase_key: str = Field(
        default=os.getenv("SUPABASE_KEY", ""),
        alias="SUPABASE_KEY",
        description="Supabase Anon/Service Key"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_required_keys(self) -> None:
        """
        Explicit check for missing environment variables with detailed error messages.
        """
        missing = []
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.neo4j_uri:
            missing.append("NEO4J_URI")
        if not self.neo4j_password:
            missing.append("NEO4J_PASSWORD")
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_key:
            missing.append("SUPABASE_KEY")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Please configure them in your .env file (see .env.example)."
            )


# Global settings instance
def get_settings() -> Settings:
    load_dotenv(override=True)
    return Settings()
