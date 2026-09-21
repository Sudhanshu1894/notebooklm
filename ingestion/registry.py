"""
Document & Notebook Registry Module for GraphRAG Research Notebook.
Tracks notebooks, source documents, processing statuses, and metadata via SQLite storage.
"""

import sqlite3
import os
from typing import Dict, Any, List, Optional
import json
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
                    user_id TEXT NOT NULL DEFAULT 'anonymous',
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    is_pinned INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            # Add columns if upgrading existing DB
            cursor = conn.execute("PRAGMA table_info(notebooks)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "user_id" not in columns:
                conn.execute("ALTER TABLE notebooks ADD COLUMN user_id TEXT NOT NULL DEFAULT 'anonymous'")
            if "is_pinned" not in columns:
                conn.execute("ALTER TABLE notebooks ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0")

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

            # Messages table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    notebook_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations TEXT DEFAULT '[]',
                    route TEXT,
                    is_insufficient INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )

            # Knowledge table — stores extracted summaries, entities, facts per notebook
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notebook_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notebook_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    knowledge_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    UNIQUE(notebook_id, doc_id, knowledge_type, content)
                )
                """
            )

            # Quiz Mastery table - tracks user performance on quiz topics
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_mastery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notebook_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            conn.commit()

    # ── Notebook Methods ──────────────────────────────────────────────────────

    def create_notebook(self, notebook_id: str, name: str, description: str = "", user_id: str = "anonymous") -> Dict[str, Any]:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO notebooks (notebook_id, user_id, name, description, created_at) VALUES (?, ?, ?, ?, ?)",
                (notebook_id, user_id, name, description, now),
            )
            conn.commit()
        return {"notebook_id": notebook_id, "user_id": user_id, "name": name, "description": description, "created_at": now}

    def get_notebook(self, notebook_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM notebooks WHERE notebook_id = ?", (notebook_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_notebook_name(self, notebook_id: str, new_name: str):
        with self._get_connection() as conn:
            conn.execute("UPDATE notebooks SET name = ? WHERE notebook_id = ?", (new_name, notebook_id))
            conn.commit()

    def pin_notebook(self, notebook_id: str, pinned: bool):
        """Sets the pinned state of a notebook."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE notebooks SET is_pinned = ? WHERE notebook_id = ?",
                (1 if pinned else 0, notebook_id),
            )
            conn.commit()

    def delete_notebook(self, notebook_id: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM notebooks WHERE notebook_id = ?", (notebook_id,))
            conn.execute("DELETE FROM messages WHERE notebook_id = ?", (notebook_id,))
            conn.execute("DELETE FROM documents WHERE notebook_id = ?", (notebook_id,))
            conn.commit()

    def list_notebooks(self, user_id: str = "anonymous") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            # Pinned notebooks first, then by created_at DESC
            cursor = conn.execute(
                "SELECT * FROM notebooks WHERE user_id = ? ORDER BY is_pinned DESC, created_at DESC",
                (user_id,),
            )
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

    def delete_document(self, doc_id: str):
        """Deletes a document from the registry."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()

    # ── Message Methods ───────────────────────────────────────────────────────

    def save_message(
        self,
        message_id: str,
        notebook_id: str,
        role: str,
        content: str,
        citations: List[Dict[str, Any]] = None,
        route: Optional[str] = None,
        is_insufficient: bool = False,
    ):
        now = datetime.now().isoformat()
        citations_json = json.dumps(citations) if citations else "[]"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (message_id, notebook_id, role, content, citations, route, is_insufficient, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, notebook_id, role, content, citations_json, route, int(is_insufficient), now),
            )
            conn.commit()

    def list_messages(self, notebook_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM messages WHERE notebook_id = ? ORDER BY created_at ASC", (notebook_id,)
            )
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                msg = dict(row)
                msg["citations"] = json.loads(msg["citations"]) if msg["citations"] else []
                msg["is_insufficient"] = bool(msg["is_insufficient"])
                messages.append(msg)
            return messages

    # ── Knowledge Methods ─────────────────────────────────────────────────────

    def save_knowledge(
        self,
        notebook_id: str,
        doc_id: str,
        knowledge_type: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ):
        """Saves a knowledge item. Ignores duplicates (UNIQUE constraint)."""
        now = datetime.now().isoformat()
        meta_json = json.dumps(metadata) if metadata else "{}"
        with self._get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO notebook_knowledge
                    (notebook_id, doc_id, knowledge_type, content, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (notebook_id, doc_id, knowledge_type, content, meta_json, now),
                )
                conn.commit()
            except Exception:
                pass  # Silently ignore duplicates

    def save_knowledge_batch(
        self,
        notebook_id: str,
        doc_id: str,
        items: List[Dict[str, Any]],
    ):
        """Batch insert knowledge items. Each item: {type, content, metadata?}."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            for item in items:
                meta_json = json.dumps(item.get("metadata", {}))
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO notebook_knowledge
                        (notebook_id, doc_id, knowledge_type, content, metadata, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (notebook_id, doc_id, item["type"], item["content"], meta_json, now),
                    )
                except Exception:
                    pass
            conn.commit()

    def get_knowledge(
        self, notebook_id: str, knowledge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns knowledge items for a notebook, optionally filtered by type."""
        with self._get_connection() as conn:
            if knowledge_type:
                cursor = conn.execute(
                    "SELECT * FROM notebook_knowledge WHERE notebook_id = ? AND knowledge_type = ? ORDER BY created_at DESC",
                    (notebook_id, knowledge_type),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM notebook_knowledge WHERE notebook_id = ? ORDER BY knowledge_type, created_at DESC",
                    (notebook_id,),
                )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["metadata"] = json.loads(item["metadata"]) if item["metadata"] else {}
                results.append(item)
            return results

    def get_knowledge_stats(self, notebook_id: str) -> Dict[str, Any]:
        """Returns counts of knowledge items by type for a notebook."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT knowledge_type, COUNT(*) as count FROM notebook_knowledge WHERE notebook_id = ? GROUP BY knowledge_type",
                (notebook_id,),
            )
            type_counts = {row["knowledge_type"]: row["count"] for row in cursor.fetchall()}

            cursor2 = conn.execute(
                "SELECT COUNT(DISTINCT doc_id) as doc_count FROM notebook_knowledge WHERE notebook_id = ?",
                (notebook_id,),
            )
            doc_count = cursor2.fetchone()["doc_count"]

            return {
                "notebook_id": notebook_id,
                "documents_trained": doc_count,
                "total_items": sum(type_counts.values()),
                "by_type": type_counts,
            }

    def delete_knowledge(self, notebook_id: str, doc_id: Optional[str] = None):
        """Deletes knowledge for a notebook (optionally scoped to a specific doc)."""
        with self._get_connection() as conn:
            if doc_id:
                conn.execute(
                    "DELETE FROM notebook_knowledge WHERE notebook_id = ? AND doc_id = ?",
                    (notebook_id, doc_id),
                )
            else:
                conn.execute(
                    "DELETE FROM notebook_knowledge WHERE notebook_id = ?",
                    (notebook_id,),
                )
            conn.commit()

    # ── Quiz Mastery Methods ──────────────────────────────────────────────────

    def save_quiz_result(self, notebook_id: str, topic: str, is_correct: bool):
        """Saves a user's answer outcome for a specific topic."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO quiz_mastery (notebook_id, topic, is_correct, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (notebook_id, topic, int(is_correct), now),
            )
            conn.commit()

    def get_mastery_stats(self, notebook_id: str) -> List[Dict[str, Any]]:
        """Returns aggregated mastery statistics per topic for a notebook."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT 
                    topic, 
                    COUNT(*) as total_attempts, 
                    SUM(is_correct) as correct_attempts
                FROM quiz_mastery 
                WHERE notebook_id = ? 
                GROUP BY topic
                ORDER BY total_attempts DESC
                """,
                (notebook_id,)
            )
            stats = []
            for row in cursor.fetchall():
                topic_stat = dict(row)
                topic_stat["mastery_percentage"] = (topic_stat["correct_attempts"] / topic_stat["total_attempts"]) * 100
                stats.append(topic_stat)
            return stats

