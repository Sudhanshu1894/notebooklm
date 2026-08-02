"""
FastAPI Backend Entrypoint for GraphRAG Research Notebook.
DA1 Phase: Scaffold & Dataset Verification Endpoints.
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from data_loading.loader import load_local_sample

app = FastAPI(
    title="GraphRAG Research Notebook API",
    description="Hybrid RAG + Knowledge Graph Research System (Free-Tier Stack)",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    status: str
    phase: str
    version: str


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint confirming API availability."""
    return HealthResponse(
        status="healthy",
        phase="DA1 (Project Setup & Dataset Loading)",
        version="0.1.0",
    )


@app.get("/api/dataset/sample-stats")
def get_sample_stats() -> Dict[str, Any]:
    """Returns metadata and statistics for the loaded HotpotQA sample subset."""
    sample_path = os.path.join("data", "sample_hotpotqa.json")
    if not os.path.exists(sample_path):
        raise HTTPException(
            status_code=404,
            detail="Sample dataset not found. Run 'python -m data_loading.loader' first.",
        )
    data = load_local_sample(sample_path)
    return data.get("metadata", {})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
