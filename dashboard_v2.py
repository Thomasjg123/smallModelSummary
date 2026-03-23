"""Real-time dashboard v2 with cache layer and long polling."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, render_template

DB_PATH = Path(__file__).parent / "data" / "context_tests.db"

try:
    import sqlite3
except ImportError:
    sqlite3 = None


class Cache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: float = 2.0):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0, "invalidations": 0}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if time.time() < expires_at:
                    self._stats["hits"] += 1
                    return value
                else:
                    del self._cache[key]
            self._stats["misses"] += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            self._cache[key] = (value, time.time() + ttl)

    def invalidate(self, key: str) -> None:
        """Remove key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["invalidations"] += 1

    def invalidate_prefix(self, prefix: str) -> None:
        """Remove all keys starting with prefix."""
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
                self._stats["invalidations"] += 1

    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            return {
                **self._stats,
                "size": len(self._cache),
                "hit_rate": round(hit_rate, 1),
            }


cache = Cache(default_ttl=2.0)


def get_db() -> "TestDatabase":
    """Get database connection."""
    return TestDatabase(DB_PATH)


class TestDatabase:
    """Database wrapper for context refinement tests."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            self._conn = conn
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_last_completed_chunk(self, test_run_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recently completed chunk."""
        row = self.conn.execute(
            """SELECT * FROM chunk_progress 
               WHERE test_run_id = ? AND status = 'completed'
               ORDER BY chunk_number DESC LIMIT 1""",
            (test_run_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_chunk_times(self, test_run_id: int) -> list[Dict[str, Any]]:
        """Get timing data for all completed chunks."""
        rows = self.conn.execute(
            """SELECT chunk_number, completed_at, input_tokens, output_tokens
               FROM chunk_progress 
               WHERE test_run_id = ? AND status = 'completed'
               ORDER BY chunk_number ASC""",
            (test_run_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_test_runs_for_run_id(self, run_prefix: str) -> list[Dict[str, Any]]:
        """Get all test runs matching run prefix."""
        rows = self.conn.execute(
            """SELECT * FROM test_runs
               WHERE config_id LIKE ?
               ORDER BY started_at DESC""",
            (f"%{run_prefix}%",),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_all_test_runs(self) -> list[Dict[str, Any]]:
        """Get all test runs."""
        rows = self.conn.execute(
            """SELECT * FROM test_runs
               ORDER BY started_at DESC""",
        ).fetchall()
        return [dict(row) for row in rows]

    def get_recent_test_runs(self, limit: int = 20) -> list[Dict[str, Any]]:
        """Get most recent test runs for both models."""
        rows = self.conn.execute(
            """SELECT * FROM test_runs
               WHERE status IN ('running', 'completed')
               ORDER BY started_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_token_totals(self, test_run_id: int) -> Dict[str, Any]:
        """Get cumulative token totals and breakdown from chunk_progress."""
        rows = self.conn.execute(
            """SELECT chunk_number, input_tokens, output_tokens, 
                      LENGTH(section_content) as section_len,
                      summary_after
               FROM chunk_progress 
               WHERE test_run_id = ? AND status = 'completed'
               ORDER BY chunk_number ASC""",
            (test_run_id,),
        ).fetchall()

        if not rows:
            return {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_section_tokens": 0,
                "final_summary_tokens": 0,
                "chunks_completed": 0,
                "avg_input_per_chunk": 0,
                "avg_output_per_chunk": 0,
                "condensation_ratio": 0,
            }

        chunks = [dict(row) for row in rows]
        total_input = sum(c["input_tokens"] for c in chunks)
        total_output = sum(c["output_tokens"] for c in chunks)
        total_section_tokens = sum(c["section_len"] // 4 for c in chunks)
        
        final_summary_tokens = 0
        if chunks and chunks[-1].get("summary_after"):
            final_summary_tokens = len(chunks[-1]["summary_after"]) // 4

        condensation_ratio = round(final_summary_tokens / total_section_tokens, 2) if total_section_tokens > 0 else 0

        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_section_tokens": total_section_tokens,
            "final_summary_tokens": final_summary_tokens,
            "chunks_completed": len(chunks),
            "avg_input_per_chunk": round(total_input / len(chunks), 1) if chunks else 0,
            "avg_output_per_chunk": round(total_output / len(chunks), 1) if chunks else 0,
            "condensation_ratio": condensation_ratio,
        }


def create_dashboard_v2(db_path: Optional[Path] = None) -> Flask:
    """Create Flask app for dashboard v2."""
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )

    if db_path:
        global DB_PATH
        DB_PATH = db_path

    @app.route("/")
    def index():
        return render_template("dashboard_v2.html")

    @app.route("/api/cache/stats")
    def api_cache_stats():
        """Get cache statistics."""
        return jsonify(cache.get_stats())

    @app.route("/api/cache/clear", methods=["POST"])
    def api_cache_clear():
        """Clear cache."""
        cache.clear()
        return jsonify({"status": "cleared"})

    @app.route("/api/runs")
    def api_runs():
        """List available run directories."""
        runs_dir = Path(__file__).parent / "runs"
        run_dirs = []
        if runs_dir.exists():
            for d in sorted(runs_dir.iterdir(), reverse=True):
                if d.is_dir() and d.name.startswith("run_"):
                    run_dirs.append(d.name)
        return jsonify(run_dirs)

    @app.route("/api/all-current")
    def api_all_current():
        """Get current status for all models (no run_id filter)."""
        cache_key = "all:current"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        db = get_db()
        try:
            rows = db.get_recent_test_runs(50)
            small_runs = [r for r in rows if "Small" in r.get("config_id", "")]
            big_runs = [r for r in rows if "Big" in r.get("config_id", "")]

            small_current = next((r for r in small_runs if r["status"] == "running"), None)
            big_current = next((r for r in big_runs if r["status"] == "running"), None)

            small_totals = db.get_token_totals(small_current["id"]) if small_current else {}
            big_totals = db.get_token_totals(big_current["id"]) if big_current else {}

            if small_current:
                chunk = db.get_last_completed_chunk(small_current["id"])
                small_current["last_chunk"] = chunk
            if big_current:
                chunk = db.get_last_completed_chunk(big_current["id"])
                big_current["last_chunk"] = chunk

            result = {
                "small": {
                    "running": small_current is not None,
                    "test_num": len(small_runs),
                    "total_tests": len(small_runs),
                    "config_name": _get_config_name(small_current),
                    "chunk_num": small_current["chunks_completed"] if small_current else 0,
                    "total_chunks": small_current["total_chunks"] if small_current else 0,
                    "words": small_current["summary_word_count"] if small_current else 0,
                    "total_section_tokens": small_totals.get("total_section_tokens", 0),
                    "final_summary_tokens": small_totals.get("final_summary_tokens", 0),
                    "avg_input_per_chunk": small_totals.get("avg_input_per_chunk", 0),
                    "avg_output_per_chunk": small_totals.get("avg_output_per_chunk", 0),
                    "condensation_ratio": small_totals.get("condensation_ratio", 0),
                    "started_at": small_current["started_at"] if small_current else None,
                },
                "big": {
                    "running": big_current is not None,
                    "test_num": len(big_runs),
                    "total_tests": len(big_runs),
                    "config_name": _get_config_name(big_current),
                    "chunk_num": big_current["chunks_completed"] if big_current else 0,
                    "total_chunks": big_current["total_chunks"] if big_current else 0,
                    "words": big_current["summary_word_count"] if big_current else 0,
                    "total_section_tokens": big_totals.get("total_section_tokens", 0),
                    "final_summary_tokens": big_totals.get("final_summary_tokens", 0),
                    "avg_input_per_chunk": big_totals.get("avg_input_per_chunk", 0),
                    "avg_output_per_chunk": big_totals.get("avg_output_per_chunk", 0),
                    "condensation_ratio": big_totals.get("condensation_ratio", 0),
                    "started_at": big_current["started_at"] if big_current else None,
                },
                "timestamp": datetime.now().isoformat(),
            }
            cache.set(cache_key, result, ttl=2.0)
            return jsonify(result)
        finally:
            db.close()

    @app.route("/api/current/<run_id>")
    def api_current(run_id: str):
        """Get current status for both models (cached)."""
        cache_key = f"current:{run_id}"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        db = get_db()
        try:
            rows = db.get_test_runs_for_run_id(run_id)
            small_runs = [r for r in rows if "Small" in r.get("config_id", "")]
            big_runs = [r for r in rows if "Big" in r.get("config_id", "")]

            small_current = next((r for r in small_runs if r["status"] == "running"), None)
            big_current = next((r for r in big_runs if r["status"] == "running"), None)

            if small_current:
                chunk = db.get_last_completed_chunk(small_current["id"])
                small_current["last_chunk"] = chunk
            if big_current:
                chunk = db.get_last_completed_chunk(big_current["id"])
                big_current["last_chunk"] = chunk

            result = {
                "small": {
                    "running": small_current is not None,
                    "test_num": len(small_runs),
                    "total_tests": len(small_runs),
                    "config_name": _get_config_name(small_current),
                    "chunk_num": small_current["chunks_completed"] if small_current else 0,
                    "total_chunks": small_current["total_chunks"] if small_current else 0,
                    "words": small_current["summary_word_count"] if small_current else 0,
                    "input_tokens": small_current["total_input_tokens"] if small_current else 0,
                    "output_tokens": small_current["total_output_tokens"] if small_current else 0,
                    "started_at": small_current["started_at"] if small_current else None,
                },
                "big": {
                    "running": big_current is not None,
                    "test_num": len(big_runs),
                    "total_tests": len(big_runs),
                    "config_name": _get_config_name(big_current),
                    "chunk_num": big_current["chunks_completed"] if big_current else 0,
                    "total_chunks": big_current["total_chunks"] if big_current else 0,
                    "words": big_current["summary_word_count"] if big_current else 0,
                    "input_tokens": big_current["total_input_tokens"] if big_current else 0,
                    "output_tokens": big_current["total_output_tokens"] if big_current else 0,
                    "started_at": big_current["started_at"] if big_current else None,
                },
                "timestamp": datetime.now().isoformat(),
            }
            cache.set(cache_key, result, ttl=2.0)
            return jsonify(result)
        finally:
            db.close()

    @app.route("/api/speed-comparison/<run_id>")
    def api_speed_comparison(run_id: str):
        """Get speed comparison (time per chunk) for both models."""
        cache_key = f"speed:{run_id}"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        db = get_db()
        try:
            rows = db.get_test_runs_for_run_id(run_id)
            small_runs = [r for r in rows if "Small" in r.get("config_id", "")]
            big_runs = [r for r in rows if "Big" in r.get("config_id", "")]

            result = {
                "small": _calc_speed_metrics(small_runs, db),
                "big": _calc_speed_metrics(big_runs, db),
                "timestamp": datetime.now().isoformat(),
            }
            cache.set(cache_key, result, ttl=3.0)
            return jsonify(result)
        finally:
            db.close()

    @app.route("/api/all-speed")
    def api_all_speed():
        """Get speed comparison for all test runs (no run_id filter)."""
        cache_key = "all:speed"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        db = get_db()
        try:
            rows = db.get_all_test_runs()
            small_runs = [r for r in rows if "Small" in r.get("config_id", "")]
            big_runs = [r for r in rows if "Big" in r.get("config_id", "")]

            result = {
                "small": _calc_speed_metrics(small_runs, db),
                "big": _calc_speed_metrics(big_runs, db),
                "timestamp": datetime.now().isoformat(),
            }
            cache.set(cache_key, result, ttl=3.0)
            return jsonify(result)
        finally:
            db.close()

    @app.route("/api/all-results")
    def api_all_results():
        """Get all completed results for all test runs."""
        cache_key = "all:results"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        db = get_db()
        try:
            rows = db.get_all_test_runs()

            results = []
            for row in rows:
                if row["status"] != "completed":
                    continue

                chunks = db.get_chunk_times(row["id"])
                avg_time = _calc_avg_time_per_chunk(chunks)
                total_time = _calc_total_time(chunks)
                tokens = db.get_token_totals(row["id"])

                model = "Small" if "Small" in row.get("config_id", "") else "Big"

                results.append({
                    "config_id": row["config_id"],
                    "config_name": _get_config_name(row),
                    "model": model,
                    "chunks_processed": row["chunks_completed"],
                    "total_chunks": row["total_chunks"],
                    "early_completion": bool(row["early_completion"]),
                    "words": row["summary_word_count"],
                    "total_section_tokens": tokens.get("total_section_tokens", 0),
                    "final_summary_tokens": tokens.get("final_summary_tokens", 0),
                    "avg_input_per_chunk": tokens.get("avg_input_per_chunk", 0),
                    "avg_output_per_chunk": tokens.get("avg_output_per_chunk", 0),
                    "condensation_ratio": tokens.get("condensation_ratio", 0),
                    "avg_time_per_chunk": avg_time,
                    "total_time": total_time,
                    "completed_at": row["completed_at"],
                })

            result = {
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }
            cache.set(cache_key, result, ttl=5.0)
            return jsonify(result)
        finally:
            db.close()

    @app.route("/api/poll-all")
    def api_poll_all():
        """Long polling endpoint for all models - waits for updates."""
        timeout = 30
        poll_interval = 0.5
        elapsed = 0

        last_chunk_small = None
        last_chunk_big = None

        db = get_db()
        try:
            rows = db.get_all_test_runs()
            for r in rows:
                if "Small" in r.get("config_id", ""):
                    chunk = db.get_last_completed_chunk(r["id"])
                    if chunk:
                        last_chunk_small = chunk.get("completed_at")
                elif "Big" in r.get("config_id", ""):
                    chunk = db.get_last_completed_chunk(r["id"])
                    if chunk:
                        last_chunk_big = chunk.get("completed_at")
        finally:
            db.close()

        last_check_small = last_chunk_small
        last_check_big = last_chunk_big

        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval

            db = get_db()
            try:
                rows = db.get_all_test_runs()
                new_small = None
                new_big = None

                for r in rows:
                    if "Small" in r.get("config_id", ""):
                        chunk = db.get_last_completed_chunk(r["id"])
                        if chunk:
                            new_time = chunk.get("completed_at")
                            if new_time and new_time != last_check_small:
                                new_small = {
                                    "config_id": r["config_id"],
                                    "chunk": r["chunks_completed"],
                                    "total": r["total_chunks"],
                                    "completed_at": new_time,
                                }
                    elif "Big" in r.get("config_id", ""):
                        chunk = db.get_last_completed_chunk(r["id"])
                        if chunk:
                            new_time = chunk.get("completed_at")
                            if new_time and new_time != last_check_big:
                                new_big = {
                                    "config_id": r["config_id"],
                                    "chunk": r["chunks_completed"],
                                    "total": r["total_chunks"],
                                    "completed_at": new_time,
                                }

                if new_small or new_big or elapsed >= timeout:
                    cache.invalidate_prefix("all:")
                    cache.invalidate_prefix("poll:")

                    return jsonify({
                        "updated": new_small is not None or new_big is not None,
                        "small_update": new_small,
                        "big_update": new_big,
                        "timestamp": datetime.now().isoformat(),
                        "timeout": elapsed >= timeout,
                    })
            finally:
                db.close()

        return jsonify({
            "updated": False,
            "small_update": None,
            "big_update": None,
            "timestamp": datetime.now().isoformat(),
            "timeout": True,
        })

    @app.route("/api/poll/<run_id>")
    def api_poll(run_id: str):
        """Long polling endpoint - waits for updates."""
        timeout = 30
        poll_interval = 0.5
        elapsed = 0

        last_chunk_small = None
        last_chunk_big = None

        db = get_db()
        try:
            rows = db.get_test_runs_for_run_id(run_id)
            for r in rows:
                if "Small" in r.get("config_id", ""):
                    chunk = db.get_last_completed_chunk(r["id"])
                    if chunk:
                        last_chunk_small = chunk.get("completed_at")
                elif "Big" in r.get("config_id", ""):
                    chunk = db.get_last_completed_chunk(r["id"])
                    if chunk:
                        last_chunk_big = chunk.get("completed_at")
        finally:
            db.close()

        last_check_small = last_chunk_small
        last_check_big = last_chunk_big

        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval

            db = get_db()
            try:
                rows = db.get_test_runs_for_run_id(run_id)
                new_small = None
                new_big = None

                for r in rows:
                    if "Small" in r.get("config_id", ""):
                        chunk = db.get_last_completed_chunk(r["id"])
                        if chunk:
                            new_time = chunk.get("completed_at")
                            if new_time and new_time != last_check_small:
                                new_small = {
                                    "config_id": r["config_id"],
                                    "chunk": r["chunks_completed"],
                                    "total": r["total_chunks"],
                                    "completed_at": new_time,
                                }
                    elif "Big" in r.get("config_id", ""):
                        chunk = db.get_last_completed_chunk(r["id"])
                        if chunk:
                            new_time = chunk.get("completed_at")
                            if new_time and new_time != last_check_big:
                                new_big = {
                                    "config_id": r["config_id"],
                                    "chunk": r["chunks_completed"],
                                    "total": r["total_chunks"],
                                    "completed_at": new_time,
                                }

                if new_small or new_big or elapsed >= timeout:
                    cache.invalidate_prefix(f"current:{run_id}")
                    cache.invalidate_prefix(f"speed:{run_id}")
                    cache.invalidate_prefix(f"poll:{run_id}")

                    return jsonify({
                        "updated": new_small is not None or new_big is not None,
                        "small_update": new_small,
                        "big_update": new_big,
                        "timestamp": datetime.now().isoformat(),
                        "timeout": elapsed >= timeout,
                    })
            finally:
                db.close()

        return jsonify({
            "updated": False,
            "small_update": None,
            "big_update": None,
            "timestamp": datetime.now().isoformat(),
            "timeout": True,
        })

    @app.route("/api/all-results/<run_id>")
    def api_all_results_by_run(run_id: str):
        """Get all results for a run."""
        cache_key = f"results:{run_id}"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        db = get_db()
        try:
            rows = db.get_test_runs_for_run_id(run_id)

            results = []
            for row in rows:
                if row["status"] != "completed":
                    continue

                chunk = db.get_last_completed_chunk(row["id"])
                chunks = db.get_chunk_times(row["id"])

                avg_time = _calc_avg_time_per_chunk(chunks)
                time_total = _calc_total_time(chunks)

                model = "Small" if "Small" in row.get("config_id", "") else "Big"

                results.append({
                    "config_id": row["config_id"],
                    "config_name": _get_config_name(row),
                    "model": model,
                    "chunks_processed": row["chunks_completed"],
                    "total_chunks": row["total_chunks"],
                    "early_completion": bool(row["early_completion"]),
                    "words": row["summary_word_count"],
                    "input_tokens": row["total_input_tokens"],
                    "output_tokens": row["total_output_tokens"],
                    "avg_time_per_chunk": avg_time,
                    "total_time": time_total,
                    "completed_at": row["completed_at"],
                })

            result = {
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }
            cache.set(cache_key, result, ttl=5.0)
            return jsonify(result)
        finally:
            db.close()

    return app


def _get_config_name(run: Optional[Dict]) -> str:
    """Extract config name from run data."""
    if not run:
        return "N/A"
    config_id = run.get("config_id", "")
    parts = config_id.split("_", 1)
    if len(parts) > 1:
        return parts[1].replace("_", " ").title()
    return config_id


def _calc_speed_metrics(runs: list[Dict], db: "TestDatabase") -> Dict[str, Any]:
    """Calculate speed metrics for a list of runs."""
    if not runs:
        return {
            "avg_time_per_chunk": 0,
            "min_time_per_chunk": 0,
            "max_time_per_chunk": 0,
            "total_chunks": 0,
            "completed_runs": 0,
            "runs": [],
        }

    all_chunk_times = []
    run_metrics = []

    for run in runs:
        if run["status"] != "completed":
            continue

        chunks = db.get_chunk_times(run["id"])
        avg_time = _calc_avg_time_per_chunk(chunks)
        total_time = _calc_total_time(chunks)

        all_chunk_times.extend([c.get("time_per_chunk", 0) for c in chunks if c.get("time_per_chunk")])

        run_metrics.append({
            "config_id": run["config_id"],
            "chunks": len(chunks),
            "avg_time": avg_time,
            "total_time": total_time,
        })

    if not all_chunk_times:
        return {
            "avg_time_per_chunk": 0,
            "min_time_per_chunk": 0,
            "max_time_per_chunk": 0,
            "total_chunks": len(all_chunk_times),
            "completed_runs": len(run_metrics),
            "runs": run_metrics,
        }

    return {
        "avg_time_per_chunk": round(sum(all_chunk_times) / len(all_chunk_times), 2),
        "min_time_per_chunk": round(min(all_chunk_times), 2) if all_chunk_times else 0,
        "max_time_per_chunk": round(max(all_chunk_times), 2) if all_chunk_times else 0,
        "total_chunks": len(all_chunk_times),
        "completed_runs": len(run_metrics),
        "runs": run_metrics,
    }


def _calc_avg_time_per_chunk(chunks: list[Dict[str, Any]]) -> float:
    """Calculate average time per chunk from timestamps."""
    if len(chunks) < 2:
        return 0.0

    times = []
    for i in range(1, len(chunks)):
        prev_time = _parse_timestamp(chunks[i - 1].get("completed_at"))
        curr_time = _parse_timestamp(chunks[i].get("completed_at"))

        if prev_time and curr_time:
            diff = (curr_time - prev_time).total_seconds()
            if diff > 0 and diff < 300:
                times.append(diff)

    return round(sum(times) / len(times), 2) if times else 0.0


def _calc_total_time(chunks: list[Dict[str, Any]]) -> float:
    """Calculate total processing time from first to last chunk."""
    if len(chunks) < 2:
        return 0.0

    first_time = _parse_timestamp(chunks[0].get("completed_at"))
    last_time = _parse_timestamp(chunks[-1].get("completed_at"))

    if first_time and last_time:
        return round((last_time - first_time).total_seconds(), 1)
    return 0.0


def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    """Parse timestamp string to datetime."""
    if not ts:
        return None
    try:
        if isinstance(ts, str):
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue
        return None
    except Exception:
        return None


if __name__ == "__main__":
    app = create_dashboard_v2()
    print("Starting dashboard v2 on http://localhost:8088")
    app.run(host="0.0.0.0", port=8088, debug=False, threaded=True)
