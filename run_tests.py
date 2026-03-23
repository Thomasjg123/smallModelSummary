"""Main test runner with simple 2-line display for parallel execution."""

from __future__ import annotations

import json
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple

from config import (
    ARTICLES,
    Article,
    RUNS_DIR,
    SMALL_MODEL,
    BIG_MODEL,
    ModelConfig,
    TEST_CONFIGS,
    TestConfig,
    SMALL_MODEL_CONFIGS,
    BIG_MODEL_CONFIGS,
)
from chunker import Chunk, create_chunks
from db import TestDatabase
from fetch_articles import fetch_article
from summarizer import (
    build_system_prompt,
    build_user_prompt,
    call_model,
    combine_section_summaries,
    detect_done_signal,
    extract_summary_from_response,
)


class SimpleDisplay:
    """Simple 2-line display for parallel testing."""
    
    def __init__(self):
        self.small_state = {"test": "0/0", "chunk": "0/0", "percent": 0, "time": 0.0}
        self.big_state = {"test": "0/0", "chunk": "0/0", "percent": 0, "time": 0.0}
        self.lock = threading.Lock()
    
    def clear_screen(self):
        """Clear terminal and move cursor to top."""
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    
    def make_bar(self, percent: int, width: int = 30) -> str:
        """Create a progress bar."""
        filled = int(width * percent / 100)
        return "█" * filled + "░" * (width - filled)
    
    def render(self):
        """Render the 2-line display."""
        with self.lock:
            # Move cursor to line 1
            sys.stdout.write("\033[1;1H")
            
            # Line 1: Small model
            small_bar = self.make_bar(self.small_state["percent"])
            small_line = (
                f"SMALL: Test {self.small_state['test']} | "
                f"Chunk {self.small_state['chunk']} | "
                f"[{small_bar}] {self.small_state['percent']:3}% | "
                f"{self.small_state['time']:6.1f}s"
            )
            sys.stdout.write(f"\033[K{small_line}\n")
            
            # Line 2: Big model
            big_bar = self.make_bar(self.big_state["percent"])
            if self.big_state["chunk"] == "0/0":
                big_line = "BIG:   Waiting to start..."
            else:
                big_line = (
                    f"BIG:   Test {self.big_state['test']} | "
                    f"Chunk {self.big_state['chunk']} | "
                    f"[{big_bar}] {self.big_state['percent']:3}% | "
                    f"{self.big_state['time']:6.1f}s"
                )
            sys.stdout.write(f"\033[K{big_line}\n")
            
            sys.stdout.flush()
    
    def update_small(self, test_num: int, total_tests: int, chunk_num: int, total_chunks: int, elapsed: float):
        """Update small model status."""
        with self.lock:
            self.small_state = {
                "test": f"{test_num}/{total_tests}",
                "chunk": f"{chunk_num}/{total_chunks}",
                "percent": int(100 * chunk_num / total_chunks) if total_chunks > 0 else 0,
                "time": elapsed,
            }
    
    def update_big(self, test_num: int, total_tests: int, chunk_num: int, total_chunks: int, elapsed: float):
        """Update big model status."""
        with self.lock:
            self.big_state = {
                "test": f"{test_num}/{total_tests}",
                "chunk": f"{chunk_num}/{total_chunks}",
                "percent": int(100 * chunk_num / total_chunks) if total_chunks > 0 else 0,
                "time": elapsed,
            }


# Global display instance
DISPLAY = SimpleDisplay()


def run_single_test(
    side: str,
    article: Article,
    test_config: TestConfig,
    model_config: ModelConfig,
    db: TestDatabase,
    run_dir: Path,
    test_num: int,
    total_tests: int,
) -> Optional[Dict[str, Any]]:
    """Run a single test, updating the display."""
    
    def update_display(chunk_num: int, total_chunks: int, elapsed: float):
        if side == "small":
            DISPLAY.update_small(test_num, total_tests, chunk_num, total_chunks, elapsed)
        else:
            DISPLAY.update_big(test_num, total_tests, chunk_num, total_chunks, elapsed)
        DISPLAY.render()
    
    # Check if already completed
    config_id = f"{model_config.display_name}_{test_config.config_id}"
    existing = db.get_test_run(article.name, config_id)
    if existing and existing.get("status") == "completed":
        return None
    
    # Setup output directory
    output_dir = run_dir / article.name / config_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch article
    content, token_estimate = fetch_article(article)
    if not content:
        return None
    
    # Create chunks
    chunks = create_chunks(
        content,
        test_config.chunking_method,
        test_config.fixed_chunk_size or 2000,
    )
    
    # Initialize
    test_run_id = None
    current_summary = ""
    total_input_tokens = 0
    total_output_tokens = 0
    early_completion = False
    completion_chunk = len(chunks)
    start_time = time.time()
    
    # Check for existing run
    existing_run = db.get_test_run(article.name, config_id)
    if existing_run:
        test_run_id = existing_run["id"]
        last_chunk = db.get_last_completed_chunk(test_run_id)
        if last_chunk:
            current_summary = last_chunk.get("summary_after", "")
            start_chunk = last_chunk["chunk_number"]
        else:
            start_chunk = 0
    else:
        test_run_id = db.create_test_run(
            article_name=article.name,
            config_id=config_id,
            total_chunks=len(chunks),
        )
        start_chunk = 0
    
    # Process chunks
    for i, chunk in enumerate(chunks):
        if i < start_chunk:
            continue
        
        elapsed = time.time() - start_time
        update_display(chunk.number, len(chunks), elapsed)
        
        # Save before processing
        db.save_chunk_progress(
            test_run_id=test_run_id,
            chunk_number=chunk.number,
            chunk_title=chunk.title,
            summary_before=current_summary,
            section_content=chunk.content,
            status="in_progress",
        )
        
        # Build prompts and call model
        system_prompt = build_system_prompt(test_config)
        user_prompt = build_user_prompt(test_config, chunk, current_summary)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response, input_tokens, output_tokens = call_model(messages, model_config)
        
        if response is None:
            continue
        
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        
        # Parse response
        done_signal_detected, final_summary = detect_done_signal(
            response, test_config.done_signal_type
        )
        
        original_summary_before = current_summary  # Store before updating
        
        if done_signal_detected:
            current_summary = final_summary
            early_completion = True
            completion_chunk = chunk.number
            break
        else:
            current_summary = extract_summary_from_response(
                response, test_config.done_signal_type, test_config.max_words
            )
        
        # Save after processing
        db.save_chunk_progress(
            test_run_id=test_run_id,
            chunk_number=chunk.number,
            chunk_title=chunk.title,
            summary_before=original_summary_before,
            section_content=chunk.content,
            model_response=response,
            summary_after=current_summary,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            done_signal_detected=done_signal_detected,
            status="completed",
        )
        
        db.update_test_run(test_run_id, chunks_completed=chunk.number)
    
    # Phase 2: For two_phase_summary configs, combine all section summaries
    if test_config.two_phase_summary and chunks:
        all_chunks = db.get_all_chunks(test_run_id)
        section_summaries = [
            {"chunk_title": c["chunk_title"], "summary_after": c["summary_after"]}
            for c in all_chunks
            if c.get("summary_after") and c.get("status") == "completed"
        ]
        if section_summaries:
            final_summary, combine_in_tokens, combine_out_tokens = combine_section_summaries(
                section_summaries, model_config, test_config.max_words
            )
            if final_summary:
                total_input_tokens += combine_in_tokens
                total_output_tokens += combine_out_tokens
                current_summary = final_summary
    
    # Final update
    elapsed = time.time() - start_time
    update_display(len(chunks), len(chunks), elapsed)
    
    # Save summary
    summary_path = output_dir / "summary.md"
    summary_content = f"""# Summary: {article.name}

**Config:** {test_config.name}
**Config ID:** {test_config.config_id}
**Model:** {model_config.display_name}
**Chunks:** {completion_chunk}/{len(chunks)} ({"Early" if early_completion else "Full"})
**Tokens:** {total_input_tokens:,} in / {total_output_tokens:,} out
**Time:** {elapsed:.1f}s
**Words:** {len(current_summary.split())}

## Summary

{current_summary}
"""
    summary_path.write_text(summary_content)
    
    # Update database
    db.update_test_run(
        test_run_id=test_run_id,
        chunks_completed=completion_chunk,
        early_completion=early_completion,
        completion_chunk=completion_chunk,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        summary_word_count=len(current_summary.split()),
        status="completed",
    )
    
    return {
        "article": article.name,
        "config": config_id,
        "chunks_processed": completion_chunk,
        "total_chunks": len(chunks),
        "early_completion": early_completion,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "summary_word_count": len(current_summary.split()),
        "elapsed_seconds": elapsed,
    }


def worker_thread(
    side: str,
    article: Article,
    configs: List[Tuple[TestConfig, ModelConfig]],
    db_path: Path,
    run_dir: Path,
    result_queue: Queue,
):
    """Worker thread for processing tests."""
    db = TestDatabase(db_path)
    db.init_schema()
    
    for i, (config, model) in enumerate(configs):
        result = run_single_test(
            side=side,
            article=article,
            test_config=config,
            model_config=model,
            db=db,
            run_dir=run_dir,
            test_num=i + 1,
            total_tests=len(configs),
        )
        if result:
            result_queue.put((side, result))
    
    db.close()


def run_parallel_tests():
    """Run tests in parallel with simple 2-line display."""
    
    DISPLAY.clear_screen()
    
    # Create run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize database
    db = TestDatabase()
    db.init_schema()
    db.close()
    
    # Use WW2 article
    article = ARTICLES[0]
    
    # Create config/model pairs
    small_tests = [
        (config, SMALL_MODEL)
        for config in TEST_CONFIGS
        if config.id in SMALL_MODEL_CONFIGS
    ]
    
    big_tests = [
        (config, BIG_MODEL)
        for config in TEST_CONFIGS
        if config.id in BIG_MODEL_CONFIGS
    ]
    
    # Result queue
    result_queue = Queue()
    
    # Start worker threads
    left_thread = threading.Thread(
        target=worker_thread,
        args=("small", article, small_tests, db.db_path, run_dir, result_queue),
    )
    right_thread = threading.Thread(
        target=worker_thread,
        args=("big", article, big_tests, db.db_path, run_dir, result_queue),
    )
    
    left_thread.start()
    right_thread.start()
    
    # Wait for both to finish
    left_thread.join()
    right_thread.join()
    
    # Collect results
    results = []
    while not result_queue.empty():
        _, result = result_queue.get()
        results.append(result)
    
    # Final display
    print("\n\nAll tests complete!")
    print(f"Results in: {run_dir}")


if __name__ == "__main__":
    run_parallel_tests()
