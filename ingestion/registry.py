"""
Document & Notebook Registry Module for GraphRAG Research Notebook.
Tracks notebooks, source documents, processing statuses, and metadata via SQLite storage.
"""

import sqlite3
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


class DocumentRegistry:
    """
    SQLite-backed repository tracking notebooks and uploaded documents with their ingestion statuses.
    """
    def __init__(self, db_path: str = "./data/doc_registry.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # Notebooks table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notebooks (
                    notebook_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            # Documents table with notebook_id
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    notebook_id TEXT NOT NULL DEFAULT 'default',
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    error_message TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            # Add notebook_id column if upgrading existing DB
            cursor = conn.execute("PRAGMA table_info(documents)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "notebook_id" not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN notebook_id TEXT NOT NULL DEFAULT 'default'")

            conn.commit()

    # ── Notebook Methods ──────────────────────────────────────────────────────

    def create_notebook(self, notebook_id: str, name: str, description: str = "") -> Dict[str, Any]:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO notebooks (notebook_id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (notebook_id, name, description, now),
            )
            conn.commit()
        return {"notebook_id": notebook_id, "name": name, "description": description, "created_at": now}

    def get_notebook(self, notebook_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM notebooks WHERE notebook_id = ?", (notebook_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_notebooks(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM notebooks ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    # ── Document Methods ──────────────────────────────────────────────────────

    def register_document(
        self, doc_id: str, filename: str, file_path: str, file_type: str, notebook_id: str = "default"
    ) -> Dict[str, Any]:
        """Registers a newly uploaded document in state 'uploaded'."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents 
                (doc_id, notebook_id, filename, file_path, file_type, status, chunk_count, error_message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'uploaded', 0, '', ?, ?)
                """,
                (doc_id, notebook_id, filename, file_path, file_type, now, now),
            )
            conn.commit()
        return self.get_document(doc_id)

    def update_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates the status and metadata for a document."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            query = "UPDATE documents SET status = ?, updated_at = ?"
            params = [status, now]

            if chunk_count is not None:
                query += ", chunk_count = ?"
                params.append(chunk_count)

            if error_message is not None:
                query += ", error_message = ?"
                params.append(error_message)

            query += " WHERE doc_id = ?"
            params.append(doc_id)

            conn.execute(query, params)
            conn.commit()

        return self.get_document(doc_id)

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves record for a specific document ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_documents(self, notebook_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists documents, optionally filtered by notebook_id."""
        with self._get_connection() as conn:
            if notebook_id:
                cursor = conn.execute(
                    "SELECT * FROM documents WHERE notebook_id = ? ORDER BY created_at DESC", (notebook_id,)
                )
            else:
                cursor = conn.execute("SELECT * FROM documents ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]
