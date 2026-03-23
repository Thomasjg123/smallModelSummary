"""Web dashboard for context refinement tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request

from db import TestDatabase
from key_facts import WW2_KEY_FACTS, check_key_facts, get_overall_coverage


def create_dashboard_app(db_path: Optional[Path] = None) -> Flask:
    """Create Flask app for the dashboard."""
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )

    def get_db() -> TestDatabase:
        """Get database connection."""
        db = TestDatabase(db_path)
        db.init_schema()
        return db

    # ── Page Routes ──────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/grading/<config_id>")
    def grading(config_id):
        return render_template("grading.html", config_id=config_id)

    # ── API Endpoints ──────────────────────────────────────────────

    @app.route("/api/runs")
    def api_runs():
        """List all test runs."""
        db = get_db()
        try:
            rows = db.conn.execute("""
                SELECT DISTINCT 
                    substr(config_id, 1, instr(config_id, '_') - 1) as run_prefix,
                    article_name,
                    COUNT(*) as test_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    MIN(started_at) as started
                FROM test_runs
                GROUP BY run_prefix, article_name
                ORDER BY started DESC
            """).fetchall()

            # Get unique run directories
            runs_dir = Path(__file__).parent / "runs"
            run_dirs = []
            if runs_dir.exists():
                for d in sorted(runs_dir.iterdir(), reverse=True):
                    if d.is_dir() and d.name.startswith("run_"):
                        run_dirs.append(d.name)

            return jsonify(run_dirs)
        finally:
            db.close()

    @app.route("/api/current/<run_id>")
    def api_current(run_id: str):
        """Get current status for both models in a run."""
        db = get_db()
        try:
            # Get all test runs for this run
            rows = db.conn.execute("""
                SELECT * FROM test_runs
                WHERE config_id LIKE ?
                ORDER BY started_at DESC
            """, (f"%{run_id}%",)).fetchall()

            small_runs = []
            big_runs = []

            for row in rows:
                r = dict(row)
                if "Small" in r.get("config_id", ""):
                    small_runs.append(r)
                elif "Big" in r.get("config_id", ""):
                    big_runs.append(r)

            # Get current running tests
            small_current = next((r for r in small_runs if r["status"] == "running"), None)
            big_current = next((r for r in big_runs if r["status"] == "running"), None)

            # Get chunk progress for current tests
            small_chunk = None
            big_chunk = None
            
            if small_current:
                chunk = db.get_last_completed_chunk(small_current["id"])
                if chunk:
                    small_chunk = chunk
            
            if big_current:
                chunk = db.get_last_completed_chunk(big_current["id"])
                if chunk:
                    big_chunk = chunk

            return jsonify({
                "small": {
                    "running": small_current is not None,
                    "test_num": _get_test_num(small_runs, small_current),
                    "total_tests": len(small_runs),
                    "config_name": _get_config_name(small_current),
                    "chunk_num": small_current["chunks_completed"] if small_current else 0,
                    "total_chunks": small_current["total_chunks"] if small_current else 0,
                    "words": small_current["summary_word_count"] if small_current else 0,
                    "input_tokens": small_current["total_input_tokens"] if small_current else 0,
                    "output_tokens": small_current["total_output_tokens"] if small_current else 0,
                },
                "big": {
                    "running": big_current is not None,
                    "test_num": _get_test_num(big_runs, big_current),
                    "total_tests": len(big_runs),
                    "config_name": _get_config_name(big_current),
                    "chunk_num": big_current["chunks_completed"] if big_current else 0,
                    "total_chunks": big_current["total_chunks"] if big_current else 0,
                    "words": big_current["summary_word_count"] if big_current else 0,
                    "input_tokens": big_current["total_input_tokens"] if big_current else 0,
                    "output_tokens": big_current["total_output_tokens"] if big_current else 0,
                },
            })
        finally:
            db.close()

    @app.route("/api/results/<run_id>")
    def api_results(run_id: str):
        """Get all results for a run."""
        db = get_db()
        try:
            rows = db.conn.execute("""
                SELECT * FROM test_runs
                WHERE config_id LIKE ? AND status = 'completed'
                ORDER BY completed_at DESC
            """, (f"%{run_id}%",)).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                # Get last chunk for summary
                chunk = db.get_last_completed_chunk(r["id"])
                summary = chunk.get("summary_after", "") if chunk else ""
                
                # Check key facts
                key_facts = check_key_facts(summary, WW2_KEY_FACTS)
                coverage = get_overall_coverage(key_facts)
                
                results.append({
                    "config_id": r["config_id"],
                    "chunks_processed": r["chunks_completed"],
                    "total_chunks": r["total_chunks"],
                    "early_completion": bool(r["early_completion"]),
                    "words": r["summary_word_count"],
                    "coverage": coverage,
                    "input_tokens": r["total_input_tokens"],
                    "output_tokens": r["total_output_tokens"],
                    "completed_at": r["completed_at"],
                })

            return jsonify(results)
        finally:
            db.close()

    @app.route("/api/key-facts/<config_id>")
    def api_key_facts(config_id: str):
        """Get key facts breakdown for a config."""
        db = get_db()
        try:
            # Get test run
            row = db.conn.execute(
                "SELECT * FROM test_runs WHERE config_id = ?",
                (config_id,)
            ).fetchone()

            if not row:
                return jsonify({"error": "Not found"}), 404

            # Get summary
            chunk = db.get_last_completed_chunk(row["id"])
            summary = chunk.get("summary_after", "") if chunk else ""

            # Check key facts
            key_facts = check_key_facts(summary, WW2_KEY_FACTS)
            
            result = {}
            for key, kf_result in key_facts.items():
                result[key] = {
                    "category": kf_result.category,
                    "found": kf_result.found,
                    "missing": kf_result.missing,
                    "coverage": kf_result.coverage,
                }

            return jsonify(result)
        finally:
            db.close()

    @app.route("/api/chunk-history/<config_id>")
    def api_chunk_history(config_id: str):
        """Get chunk processing history over time."""
        db = get_db()
        try:
            row = db.conn.execute(
                "SELECT * FROM test_runs WHERE config_id = ?",
                (config_id,)
            ).fetchone()

            if not row:
                return jsonify({"error": "Not found"}), 404

            chunks = db.get_all_chunks(row["id"])
            
            history = []
            for chunk in chunks:
                if chunk["status"] == "completed":
                    history.append({
                        "chunk": chunk["chunk_number"],
                        "completed_at": chunk["completed_at"],
                        "input_tokens": chunk["input_tokens"],
                        "output_tokens": chunk["output_tokens"],
                    })

            return jsonify(history)
        finally:
            db.close()

    @app.route("/api/summary/<config_id>")
    def api_summary(config_id: str):
        """Get full summary text."""
        db = get_db()
        try:
            row = db.conn.execute(
                "SELECT * FROM test_runs WHERE config_id = ?",
                (config_id,)
            ).fetchone()

            if not row:
                return jsonify({"error": "Not found"}), 404

            chunk = db.get_last_completed_chunk(row["id"])
            summary = chunk.get("summary_after", "") if chunk else ""

            return jsonify({
                "config_id": config_id,
                "summary": summary,
                "words": len(summary.split()),
            })
        finally:
            db.close()

    @app.route("/api/logs/<run_id>")
    def api_logs(run_id: str):
        """Get activity log entries."""
        db = get_db()
        try:
            # Get recent chunk completions
            rows = db.conn.execute("""
                SELECT 
                    cp.completed_at,
                    tr.config_id,
                    cp.chunk_number,
                    cp.chunk_title,
                    cp.done_signal_detected,
                    LENGTH(cp.summary_after) as summary_length
                FROM chunk_progress cp
                JOIN test_runs tr ON tr.id = cp.test_run_id
                WHERE tr.config_id LIKE ? AND cp.status = 'completed'
                ORDER BY cp.completed_at DESC
                LIMIT 50
            """, (f"%{run_id}%",)).fetchall()

            logs = []
            for row in rows:
                r = dict(row)
                model = "small" if "Small" in r["config_id"] else "big"
                logs.append({
                    "time": r["completed_at"],
                    "model": model,
                    "message": f"Chunk {r['chunk_number']} complete",
                })

            return jsonify(logs)
        finally:
            db.close()

    @app.route("/api/grading/<config_id>")
    def api_grading(config_id: str):
        """Get full grading data for a config."""
        db = get_db()
        try:
            row = db.conn.execute(
                "SELECT * FROM test_runs WHERE config_id = ?",
                (config_id,)
            ).fetchone()

            if not row:
                return jsonify({"error": "Not found"}), 404

            # Get summary
            chunk = db.get_last_completed_chunk(row["id"])
            summary = chunk.get("summary_after", "") if chunk else ""

            # Get all chunks for article content
            all_chunks = db.get_all_chunks(row["id"])
            article_content = ""
            for c in all_chunks:
                if c.get("section_content"):
                    article_content += c["section_content"] + "\n\n"

            # Check key facts
            key_facts = check_key_facts(summary, WW2_KEY_FACTS)
            
            facts_data = {}
            for key, kf_result in key_facts.items():
                facts_data[key] = {
                    "category": kf_result.category,
                    "found": kf_result.found,
                    "missing": kf_result.missing,
                    "coverage": kf_result.coverage,
                }

            return jsonify({
                "config_id": config_id,
                "config_name": _get_config_name(dict(row)),
                "model": "Small (0.8B)" if "Small" in config_id else "Big (Llama)",
                "chunks_processed": row["chunks_completed"],
                "total_chunks": row["total_chunks"],
                "early_completion": bool(row["early_completion"]),
                "words": row["summary_word_count"],
                "coverage": get_overall_coverage(key_facts),
                "input_tokens": row["total_input_tokens"],
                "output_tokens": row["total_output_tokens"],
                "summary": summary,
                "article_content": article_content[:10000],  # First 10k chars
                "key_facts": facts_data,
            })
        finally:
            db.close()

    @app.route("/api/chunk-status/<run_id>")
    def api_chunk_status(run_id: str):
        """Get current chunk status for both models (for real-time updates)."""
        db = get_db()
        try:
            # Get the most recent running test runs for each model
            rows = db.conn.execute("""
                SELECT * FROM test_runs
                WHERE status IN ('running', 'completed')
                ORDER BY 
                    CASE WHEN status = 'running' THEN 0 ELSE 1 END,
                    started_at DESC
                LIMIT 20
            """).fetchall()

            small_running = None
            small_completed = None
            big_running = None
            big_completed = None

            for row in rows:
                r = dict(row)
                if "Small" in r.get("config_id", ""):
                    if r["status"] == "running" and small_running is None:
                        small_running = r
                    elif r["status"] == "completed" and small_completed is None:
                        small_completed = r
                elif "Big" in r.get("config_id", ""):
                    if r["status"] == "running" and big_running is None:
                        big_running = r
                    elif r["status"] == "completed" and big_completed is None:
                        big_completed = r

            # Prefer running tests, fall back to completed
            small_status = small_running or small_completed
            big_status = big_running or big_completed

            def get_chunk_info(run_data):
                if not run_data:
                    return {"chunk": 0, "total": 0, "words": 0, "timestamp": None}
                
                chunk = db.get_last_completed_chunk(run_data["id"])
                return {
                    "chunk": run_data["chunks_completed"],
                    "total": run_data["total_chunks"],
                    "words": run_data["summary_word_count"],
                    "timestamp": chunk.get("completed_at") if chunk else run_data.get("started_at"),
                }

            return jsonify({
                "small": get_chunk_info(small_status),
                "big": get_chunk_info(big_status),
                "timestamp": datetime.now().isoformat(),
            })
        finally:
            db.close()

    @app.route("/api/all-results")
    def api_all_results():
        """Get all completed test results with cumulative stats."""
        db = get_db()
        try:
            rows = db.conn.execute("""
                SELECT 
                    tr.*,
                    (SELECT COUNT(*) FROM chunk_progress cp 
                     WHERE cp.test_run_id = tr.id AND cp.status = 'completed') as chunks_done
                FROM test_runs tr
                WHERE tr.status = 'completed'
                ORDER BY tr.completed_at DESC
            """).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                # Get last chunk for summary
                chunk = db.get_last_completed_chunk(r["id"])
                summary = chunk.get("summary_after", "") if chunk else ""
                
                # Check key facts
                key_facts = check_key_facts(summary, WW2_KEY_FACTS)
                coverage = get_overall_coverage(key_facts)
                
                results.append({
                    "config_id": r["config_id"],
                    "config_name": _get_config_name(r),
                    "model": "Small" if "Small" in r["config_id"] else "Big",
                    "chunks_processed": r["chunks_completed"],
                    "total_chunks": r["total_chunks"],
                    "early_completion": bool(r["early_completion"]),
                    "words": r["summary_word_count"],
                    "coverage": round(coverage, 1),
                    "input_tokens": r["total_input_tokens"],
                    "output_tokens": r["total_output_tokens"],
                    "total_tokens": r["total_input_tokens"] + r["total_output_tokens"],
                    "completed_at": r["completed_at"],
                    "summary_preview": summary[:200] + "..." if len(summary) > 200 else summary,
                })

            # Calculate cumulative stats
            small_results = [r for r in results if r["model"] == "Small"]
            big_results = [r for r in results if r["model"] == "Big"]
            
            def calc_stats(res_list):
                if not res_list:
                    return {"count": 0, "avg_coverage": 0, "avg_words": 0, "total_tokens": 0}
                return {
                    "count": len(res_list),
                    "avg_coverage": round(sum(r["coverage"] for r in res_list) / len(res_list), 1),
                    "avg_words": round(sum(r["words"] for r in res_list) / len(res_list)),
                    "total_tokens": sum(r["total_tokens"] for r in res_list),
                }

            return jsonify({
                "results": results,
                "stats": {
                    "small": calc_stats(small_results),
                    "big": calc_stats(big_results),
                }
            })
        finally:
            db.close()

    @app.route("/api/summary-content/<config_id>")
    def api_summary_content(config_id: str):
        """Get the full summary content from the markdown file."""
        runs_dir = Path(__file__).parent / "runs"
        
        # Find the summary file
        for run_dir in sorted(runs_dir.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            for article_dir in run_dir.iterdir():
                if not article_dir.is_dir():
                    continue
                config_dir = article_dir / config_id
                if config_dir.exists():
                    summary_file = config_dir / "summary.md"
                    if summary_file.exists():
                        return jsonify({
                            "config_id": config_id,
                            "content": summary_file.read_text(),
                            "path": str(summary_file.relative_to(runs_dir)),
                        })
        
        return jsonify({"error": "Summary not found"}), 404

    return app


def _get_test_num(runs: List[Dict], current: Optional[Dict]) -> int:
    """Get test number for current run."""
    if not current:
        return 0
    for i, r in enumerate(runs):
        if r["id"] == current["id"]:
            return i + 1
    return 0


def _get_config_name(run: Optional[Dict]) -> str:
    """Extract config name from run data."""
    if not run:
        return "N/A"
    config_id = run.get("config_id", "")
    # Remove model prefix
    parts = config_id.split("_", 1)
    if len(parts) > 1:
        return parts[1].replace("_", " ").title()
    return config_id


if __name__ == "__main__":
    app = create_dashboard_app()
    print("Starting dashboard on http://localhost:8087")
    app.run(host="0.0.0.0", port=8087, debug=False, threaded=True)
