"""Database operations for context refinement tests."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

DB_PATH = Path(
    os.getenv(
        "DEBUGCLI_DB_PATH",
        str(Path(__file__).parent / "data" / "context_tests.db"),
    )
)

SCHEMA_SQL = """
-- Test run tracking
CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_name TEXT NOT NULL,
    config_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    total_chunks INTEGER,
    chunks_completed INTEGER DEFAULT 0,
    early_completion INTEGER DEFAULT 0,
    completion_chunk INTEGER,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    summary_word_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(article_name, config_id)
);

-- Chunk progress for crash recovery
CREATE TABLE IF NOT EXISTS chunk_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id INTEGER NOT NULL,
    chunk_number INTEGER NOT NULL,
    chunk_title TEXT,
    status TEXT DEFAULT 'pending',
    summary_before TEXT,
    section_content TEXT,
    model_response TEXT,
    summary_after TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    done_signal_detected INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(id),
    UNIQUE(test_run_id, chunk_number)
);
"""


class TestDatabase:
    """Database for tracking context refinement tests."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = DB_PATH
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def init_schema(self):
        """Create tables if they don't exist."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    # ── Test Run Operations ──────────────────────────────────────────

    def create_test_run(
        self,
        article_name: str,
        config_id: str,
        total_chunks: int,
    ) -> int:
        """Create a new test run, return its ID."""
        with self.transaction() as cur:
            cur.execute(
                """INSERT INTO test_runs 
                   (article_name, config_id, total_chunks, status, started_at)
                   VALUES (?, ?, ?, 'running', ?)""",
                (article_name, config_id, total_chunks, datetime.now()),
            )
            return cur.lastrowid

    def get_test_run(
        self,
        article_name: str,
        config_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get existing test run."""
        row = self.conn.execute(
            """SELECT * FROM test_runs 
               WHERE article_name = ? AND config_id = ?""",
            (article_name, config_id),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def update_test_run(
        self,
        test_run_id: int,
        chunks_completed: Optional[int] = None,
        early_completion: Optional[bool] = None,
        completion_chunk: Optional[int] = None,
        total_input_tokens: Optional[int] = None,
        total_output_tokens: Optional[int] = None,
        summary_word_count: Optional[int] = None,
        status: Optional[str] = None,
    ):
        """Update test run progress."""
        updates = []
        params = []

        if chunks_completed is not None:
            updates.append("chunks_completed = ?")
            params.append(chunks_completed)
        if early_completion is not None:
            updates.append("early_completion = ?")
            params.append(1 if early_completion else 0)
        if completion_chunk is not None:
            updates.append("completion_chunk = ?")
            params.append(completion_chunk)
        if total_input_tokens is not None:
            updates.append("total_input_tokens = ?")
            params.append(total_input_tokens)
        if total_output_tokens is not None:
            updates.append("total_output_tokens = ?")
            params.append(total_output_tokens)
        if summary_word_count is not None:
            updates.append("summary_word_count = ?")
            params.append(summary_word_count)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
            if status in ("completed", "failed"):
                updates.append("completed_at = ?")
                params.append(datetime.now())

        if not updates:
            return

        params.append(test_run_id)
        with self.transaction() as cur:
            cur.execute(
                f"UPDATE test_runs SET {', '.join(updates)} WHERE id = ?",
                params,
            )

    def get_incomplete_runs(self) -> List[Dict[str, Any]]:
        """Get all incomplete test runs for resuming."""
        rows = self.conn.execute(
            """SELECT * FROM test_runs 
               WHERE status IN ('pending', 'running')
               ORDER BY started_at""",
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Chunk Progress Operations ────────────────────────────────────

    def save_chunk_progress(
        self,
        test_run_id: int,
        chunk_number: int,
        chunk_title: Optional[str] = None,
        summary_before: Optional[str] = None,
        section_content: Optional[str] = None,
        model_response: Optional[str] = None,
        summary_after: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        done_signal_detected: bool = False,
        status: str = "completed",
    ):
        """Save or update chunk progress."""
        with self.transaction() as cur:
            cur.execute(
                """INSERT INTO chunk_progress 
                   (test_run_id, chunk_number, chunk_title, summary_before,
                    section_content, model_response, summary_after,
                    input_tokens, output_tokens, done_signal_detected,
                    status, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(test_run_id, chunk_number) DO UPDATE SET
                   chunk_title = COALESCE(excluded.chunk_title, chunk_title),
                   summary_before = COALESCE(excluded.summary_before, summary_before),
                   section_content = COALESCE(excluded.section_content, section_content),
                   model_response = COALESCE(excluded.model_response, model_response),
                   summary_after = COALESCE(excluded.summary_after, summary_after),
                   input_tokens = excluded.input_tokens,
                   output_tokens = excluded.output_tokens,
                   done_signal_detected = excluded.done_signal_detected,
                   status = excluded.status,
                   completed_at = excluded.completed_at""",
                (
                    test_run_id, chunk_number, chunk_title, summary_before,
                    section_content, model_response, summary_after,
                    input_tokens, output_tokens, 1 if done_signal_detected else 0,
                    status, datetime.now(),
                ),
            )

    def get_chunk_progress(
        self,
        test_run_id: int,
        chunk_number: int,
    ) -> Optional[Dict[str, Any]]:
        """Get chunk progress."""
        row = self.conn.execute(
            """SELECT * FROM chunk_progress 
               WHERE test_run_id = ? AND chunk_number = ?""",
            (test_run_id, chunk_number),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_last_completed_chunk(self, test_run_id: int) -> Optional[Dict[str, Any]]:
        """Get the last completed chunk for resuming."""
        row = self.conn.execute(
            """SELECT * FROM chunk_progress 
               WHERE test_run_id = ? AND status = 'completed'
               ORDER BY chunk_number DESC LIMIT 1""",
            (test_run_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_all_chunks(self, test_run_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a test run."""
        rows = self.conn.execute(
            """SELECT * FROM chunk_progress 
               WHERE test_run_id = ?
               ORDER BY chunk_number""",
            (test_run_id,),
        ).fetchall()
        return [dict(r) for r in rows]
