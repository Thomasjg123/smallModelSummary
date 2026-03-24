"""Debug CLI for step-by-step testing of summarization configs."""

from __future__ import annotations

import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Optional

from config import (
    ARTICLES,
    Article,
    RUNS_DIR,
    SMALL_MODEL,
    TestConfig,
    TEST_CONFIGS,
    DoneSignalType,
)
from chunker import Chunk, create_chunks
from db import TestDatabase
from fetch_articles import fetch_article
from summarizer import (
    call_model,
    detect_done_signal,
    extract_summary_from_response,
)


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'
    
    @staticmethod
    def input_prompt(s: str) -> str:
        return f"{Colors.CYAN}{Colors.BOLD}>>> INPUT PROMPT:{Colors.ENDC}\n{s}"
    
    @staticmethod
    def response(s: str) -> str:
        return f"{Colors.GREEN}{Colors.BOLD}<<< RESPONSE:{Colors.ENDC}\n{s}"
    
    @staticmethod
    def sql_query(s: str) -> str:
        return f"{Colors.YELLOW}{Colors.BOLD}>>> SQL QUERY:{Colors.ENDC}\n{s}"
    
    @staticmethod
    def sql_response(s: str) -> str:
        return f"{Colors.BLUE}{Colors.BOLD}<<< SQL RESPONSE:{Colors.ENDC}\n{s}"
    
    @staticmethod
    def file_write(s: str) -> str:
        return f"{Colors.RED}{Colors.BOLD}>>> FILE WRITE:{Colors.ENDC}\n{s}"
    
    @staticmethod
    def file_read(s: str) -> str:
        return f"{Colors.BLUE}{Colors.BOLD}<<< FILE READ:{Colors.ENDC}\n{s}"
    
    @staticmethod
    def action(s: str) -> str:
        return f"{Colors.HEADER}{Colors.BOLD}*** ACTION:{Colors.ENDC} {s}"
    
    @staticmethod
    def step(s: str) -> str:
        return f"{Colors.BOLD}{Colors.HEADER}=== STEP:{Colors.ENDC} {s}"


def _preview_response_lines(
    response: str,
    max_lines: int = 3,
    max_width: int = 320,
) -> tuple[str, int, int, bool]:
    """Return a truncated preview plus line and char counts."""
    if not response:
        return "(no response content)", 0, 0, False
    normalized = [line.rstrip() for line in response.strip().splitlines()]
    if not normalized:
        return "(no response content)", 0, len(response), False
    preview_lines: list[str] = []
    truncated = False
    for line in normalized[:max_lines]:
        if len(line) > max_width:
            preview_lines.append(line[:max_width] + "...")
            truncated = True
            continue
        else:
            preview_lines.append(line)
    preview = "\n".join(preview_lines)
    if len(normalized) > max_lines:
        truncated = True
        preview += "\n..."
    return preview, len(normalized), len(response), truncated


def _token_summary(input_tokens: int, output_tokens: int) -> str:
    """Return formatted token statistics with ratios."""
    total = input_tokens + output_tokens
    parts = [
        f"Tokens: {input_tokens:,} in / {output_tokens:,} out",
        f"total {total:,}",
    ]
    if input_tokens > 0:
        ratio = output_tokens / input_tokens
        parts.append(f"output/in {ratio:.2f}")
    return " | ".join(parts)


def _print_sql_response(
    message: str,
    show_prompts: bool,
    max_lines: int = 2,
    note: str = "SQL response truncated; run with --show-prompts to see the full text.",
):
    """Print a potentially-truncated SQL response depending on the prompt flag."""
    if show_prompts:
        print(Colors.sql_response(message))
        return

    lines = [line.rstrip() for line in message.strip().splitlines()]
    preview = "\n".join(lines[:max_lines]) if lines else "(empty SQL response)"
    print(Colors.sql_response(preview))

    if len(lines) > max_lines:
        print(Colors.action(note))


MAX_MODEL_RETRIES = 3
TEMPERATURE_STEP = 0.05
MIN_TEMPERATURE = 0.1


def call_model_with_retry(
    messages: list[dict[str, str]],
    model_config,
) -> tuple[Optional[str], int, int]:
    """Call the model up to `MAX_MODEL_RETRIES`, dropping responses when output > input."""

    attempts = 0
    current_config = model_config

    while attempts < MAX_MODEL_RETRIES:
        attempts += 1
        response, input_tokens, output_tokens = call_model(messages, current_config)

        if response is None:
            return None, 0, 0

        if output_tokens > input_tokens:
            print(Colors.action(f"Response tokens ({output_tokens}) exceed prompt tokens ({input_tokens}); discarding attempt {attempts}/{MAX_MODEL_RETRIES}"))
            if attempts >= MAX_MODEL_RETRIES:
                print(Colors.action("Max retries reached; aborting model call"))
                return None, 0, 0

            next_temperature = max(MIN_TEMPERATURE, current_config.temperature - TEMPERATURE_STEP)
            if next_temperature < current_config.temperature:
                current_config = replace(current_config, temperature=next_temperature)
            print(Colors.action(f"Retrying with temperature {current_config.temperature:.2f} (next attempt {attempts + 1})"))
            continue

        return response, input_tokens, output_tokens

    return None, 0, 0


def wait_for_enter(prompt: str = "Press ENTER to continue (q to quit, s to skip to end): "):
        return "continue"


def debug_single_config(
    article: Article,
    test_config: TestConfig,
    max_chunks: int = 2,
    show_prompts: bool = False,
):
    """Debug a single config step by step."""
    
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"DEBUGGING CONFIG: {test_config.name} (ID: {test_config.id})")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    wait_for_enter(">>> Press ENTER to fetch article...")
    
    # Step 1: Fetch article
    print(Colors.action("Fetching article from Wikipedia..."))
    content, token_estimate = fetch_article(article)
    if not content:
        print(Colors.RED + "ERROR: Could not fetch article" + Colors.ENDC)
        return
    
    print(f"Article fetched: {len(content)} chars, ~{token_estimate} tokens")
    _print_sql_response(
        f"content preview: {content[:500]}...",
        show_prompts=show_prompts,
        max_lines=2,
    )
    
    wait_for_enter()
    
    # Step 2: Create chunks
    print(Colors.action("Creating chunks..."))
    chunks = create_chunks(
        content,
        test_config.chunking_method,
        test_config.fixed_chunk_size or 2000,
    )
    print(f"Created {len(chunks)} chunks")
    
    # Show chunk titles
    chunk_list = "\n".join(f"  {i+1}. {c.title}" for i, c in enumerate(chunks[:max_chunks]))
    if len(chunks) > max_chunks:
        chunk_list += f"\n  ... and {len(chunks) - max_chunks} more"
    _print_sql_response(
        chunk_list,
        show_prompts=show_prompts,
        max_lines=3,
    )
    
    # Show total article content size
    _print_sql_response(
        f"Total article: {len(content)} chars",
        show_prompts=show_prompts,
        max_lines=1,
    )
    
    wait_for_enter()
    
    # Step 3: Initialize DB
    print(Colors.action("Initializing database..."))
    db = TestDatabase()
    db.init_schema()
    
    config_id = f"{SMALL_MODEL.display_name}_{test_config.config_id}"
    print(Colors.sql_query(f"SELECT * FROM test_runs WHERE article_name = '{article.name}' AND config_id = '{config_id}'"))
    
    existing = db.get_test_run(article.name, config_id)
    if existing:
        _print_sql_response(
            f"Found existing run: {existing}",
            show_prompts=show_prompts,
            max_lines=2,
        )
    else:
        _print_sql_response(
            "No existing run found",
            show_prompts=show_prompts,
            max_lines=1,
        )
    
    # Create or get test run
    test_run_id = existing["id"] if existing else db.create_test_run(
        article_name=article.name,
        config_id=config_id,
        total_chunks=len(chunks),
    )
    _print_sql_response(
        f"test_run_id: {test_run_id}",
        show_prompts=show_prompts,
        max_lines=1,
    )
    
    current_summary = ""
    
    wait_for_enter()
    
    # Step 4: Process chunks (limited to max_chunks)
    chunks_to_process = chunks[:max_chunks]
    all_chunk_summaries = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_input_words = 0
    
    for i, chunk in enumerate(chunks_to_process):
        print(f"\n{Colors.BOLD}{'='*40}")
        print(f"CHUNK {chunk.number}/{len(chunks)}: {chunk.title}")
        print(f"{'='*40}{Colors.ENDC}")
        
        # Show chunk content size
        _print_sql_response(
            f"Section content: {len(chunk.content)} chars",
            show_prompts=show_prompts,
            max_lines=1,
        )
        
# Step 4a: Build prompts locally to see full content
        print(Colors.action("Building prompts locally..."))
        
        # Build system prompt directly (not from summarizer.py)
        parts = []
        parts.append("You are summarizing a long article processed in sections.")
        parts.append("")
        parts.append("After EACH section:")
        parts.append("- Update your running summary with new key information")
        
        parts.append("")
        parts.append("Rules:")
        parts.append("- Include key facts, names, dates, relationships")
        
        if test_config.include_previous_summary:
            parts.append("- Be concise and factual")
            parts.append("")
            parts.append("CRITICAL: Your response must be EXACTLY this format with NO additions:")
            parts.append("<SUMMARY_START>")
            parts.append("[Your summary text here - ONLY the summary, nothing else]")
            parts.append("</SUMMARY_END>")
            parts.append("")
            parts.append("EXAMPLE:")
            parts.append("<SUMMARY_START>")
            parts.append("World War II was a global conflict from 1939-1945.")
            parts.append("</SUMMARY_END>")
            parts.append("")
            parts.append("DO NOT add any text before, after, or between these lines.")
            parts.append("DO NOT include line numbers, explanations, or any extra commentary.")
            parts.append("OUTPUT MUST BE SMALLER THAN THE INPUT")
        else:
            parts.append("- Be concise and factual")
            parts.append("- Do not repeat any information already included - keep updates concise")
            parts.append("")
            parts.append("Focus only on key facts, names, dates, and relationships from THIS section.")
        
        system_prompt = "\n".join(parts)
        
        # Build user prompt directly in debug_cli
        user_parts = []
        
        if test_config.include_previous_summary:
            user_parts.append("Please update the summary with the information from the following section.")
            user_parts.append("")
            user_parts.append("Current summary:")
            user_parts.append(current_summary if current_summary else "[This is the first section - start fresh]")
            user_parts.append("")
            user_parts.append("New section:")
            user_parts.append(f"SECTION {chunk.number}: {chunk.title}")
            user_parts.append("")
            user_parts.append(chunk.content)
        else:
            user_parts.append("Please summarize the following section.")
            user_parts.append("")
            user_parts.append(f"SECTION {chunk.number}: {chunk.title}")
            user_parts.append("")
            user_parts.append(chunk.content)
        
        user_parts.append("")
        
        # Add instructions
        if test_config.allow_early_completion:
            if test_config.done_signal_type == DoneSignalType.XML:
                user_parts.append("You may output <SUMMARY_COMPLETE> if you have enough information.")
            elif test_config.done_signal_type == DoneSignalType.JSON:
                user_parts.append('You may output {"status": "complete", "summary": "..."} if done.')
            elif test_config.done_signal_type == DoneSignalType.NATURAL:
                user_parts.append('You may output "SUMMARY COMPLETE:" if done.')
        else:
            if chunk.is_last:
                user_parts.append("This is the FINAL section.")
        
        user_prompt = "\n".join(user_parts)
        
        if show_prompts:
            print(Colors.input_prompt(f"SYSTEM PROMPT:\n{system_prompt}\n\n---\n\nUSER PROMPT:\n{user_prompt}"))
        wait_for_enter()
        
        # Step 4b: Save before processing
        print(Colors.action("Saving chunk progress (in_progress)..."))
        db.save_chunk_progress(
            test_run_id=test_run_id,
            chunk_number=chunk.number,
            chunk_title=chunk.title,
            summary_before=current_summary,
            section_content=chunk.content,
            status="in_progress",
        )
        
        print(Colors.sql_query(f"INSERT INTO chunk_progress (test_run_id, chunk_number, status) VALUES ({test_run_id}, {chunk.number}, 'in_progress')"))
        _print_sql_response(
            "OK",
            show_prompts=show_prompts,
            max_lines=1,
        )
        
        wait_for_enter()
        
        # Step 4c: Call model
        print(Colors.action("Calling model..."))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response, input_tokens, output_tokens = call_model_with_retry(messages, SMALL_MODEL)
        
        if response is None:
            print(Colors.RED + "ERROR: Model call failed" + Colors.ENDC)
            continue
        
        preview, total_lines, total_chars, truncated = _preview_response_lines(response)
        if total_lines == 0:
            label = "Response preview (empty)"
        else:
            shown = min(3, total_lines)
            label = f"Response preview (first {shown} of {total_lines} lines)"
        if not show_prompts:
            print("<< RESPONSE:")
        print(Colors.response(f"{label}\n{preview}"))
        if truncated:
            print(Colors.action(
                f"(response preview truncated; {total_lines} lines, {total_chars} chars total)")
            )
        _print_sql_response(
            _token_summary(input_tokens, output_tokens),
            show_prompts=show_prompts,
            max_lines=1,
        )
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        total_input_words += len(chunk.content.split())
        
        wait_for_enter()
        
        # Step 4d: Parse response
        print(Colors.action("Parsing response..."))
        done_signal_detected, final_summary = detect_done_signal(
            response, test_config.done_signal_type
        )
        
        original_summary_before = current_summary  # Store before updating
        
        if done_signal_detected:
            _print_sql_response(
                "Done signal detected! Final summary:",
                show_prompts=show_prompts,
                max_lines=1,
            )
            print(Colors.response(final_summary))
            current_summary = final_summary
            all_chunk_summaries.append({
                "chunk_title": chunk.title,
                "summary_after": final_summary,
            })
            break
        else:
            current_summary = extract_summary_from_response(
                response, test_config.done_signal_type, test_config.max_words
            )
            _print_sql_response(
                "Extracted summary:",
                show_prompts=show_prompts,
                max_lines=1,
            )
            print(Colors.response(current_summary))
            all_chunk_summaries.append({
                "chunk_title": chunk.title,
                "summary_after": current_summary,
            })
        
        wait_for_enter()
        
        # Step 4e: Save after processing
        print(Colors.action("Saving chunk progress (completed)..."))
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
        
        print(Colors.sql_query(f"UPDATE chunk_progress SET summary_after='[full content]', status='completed' WHERE test_run_id={test_run_id} AND chunk_number={chunk.number}"))
        _print_sql_response(
            "OK",
            show_prompts=show_prompts,
            max_lines=1,
        )
        
        wait_for_enter()
    
    # Step 5: Phase 2 - Combine (if two_phase_summary)
    if test_config.two_phase_summary and all_chunk_summaries:
        print(f"\n{Colors.BOLD}{'='*40}")
        print("PHASE 2: Combining section summaries")
        print(f"{'='*40}{Colors.ENDC}")
        
        print(Colors.action("Fetching all chunk summaries from DB..."))
        all_chunks = db.get_all_chunks(test_run_id)
        
        print(Colors.sql_query(f"SELECT chunk_number, chunk_title, summary_before, summary_after, status FROM chunk_progress WHERE test_run_id={test_run_id} ORDER BY chunk_number"))
        
        section_summaries = [
            {"chunk_title": c["chunk_title"], "summary_after": c["summary_after"]}
            for c in all_chunks
            if c.get("summary_after") and c.get("status") == "completed"
        ]
        _print_sql_response(
            f"Found {len(section_summaries)} section summaries",
            show_prompts=show_prompts,
            max_lines=1,
        )
        
        for c in all_chunks:
            print(f"\n{'='*40}")
            print(f"Chunk {c['chunk_number']}: {c['chunk_title']}")
            print(f"{'='*40}")
            print(f"Status: {c.get('status', 'unknown')}")
            print(f"\n--- summary_before ---")
            _print_sql_response(
                c.get('summary_before', '') or '(empty)',
                show_prompts=show_prompts,
                max_lines=2,
            )
            print(f"\n--- summary_after ---")
            _print_sql_response(
                c.get('summary_after', '') or '(empty)',
                show_prompts=show_prompts,
                max_lines=2,
            )
        
        wait_for_enter()
        
        # Build and show combine prompts
        print(Colors.action("Building combine prompts..."))
        
        sections_text = []
        for i, section in enumerate(section_summaries, 1):
            title = section.get("chunk_title", f"Section {i}")
            summary = section.get("summary_after", "")
            sections_text.append(f"Section {i}: {title}\n{summary}")
        
        combined_text = "\n\n---\n\n".join(sections_text)
        
        combine_system_prompt = f"""You are combining multiple section summaries into a single coherent summary.
Your task is to merge these summaries while:
- Consolidating redundant information
- Maintaining chronological order where applicable
- Creating a flowing narrative
- Including all key facts, names, dates, and events
- Be concise and factual"""
        
        combine_user_prompt = f"""Here are the summaries from each section of the article:

{combined_text}

Please combine these into a single coherent summary that incorporates all key information from the article."""
        
        if show_prompts:
            print(Colors.input_prompt(f"COMBINE SYSTEM PROMPT:\n{combine_system_prompt}\n\n---\n\nCOMBINE USER PROMPT:\n{combine_user_prompt}"))
        wait_for_enter()
        print(Colors.action("Calling combine model directly..."))
        
        messages = [
            {"role": "system", "content": combine_system_prompt},
            {"role": "user", "content": combine_user_prompt},
        ]
        
        combine_response, combine_in, combine_out = call_model_with_retry(messages, SMALL_MODEL)
        
        if combine_response:
            final_summary = combine_response.strip()
            if not show_prompts:
                print("<< RESPONSE:")
            print(Colors.response(final_summary))
            token_line = _token_summary(combine_in, combine_out)
            _print_sql_response(
                token_line.replace("Tokens:", "Combine tokens:", 1),
                show_prompts=show_prompts,
                max_lines=1,
            )
            total_input_tokens += combine_in
            total_output_tokens += combine_out
            current_summary = final_summary
        else:
            print(Colors.RED + "Combine failed, using last chunk summary" + Colors.ENDC)
        
        wait_for_enter()
    
    final_summary_words = len(current_summary.split())
    compression_ratio = (total_input_words / final_summary_words) if final_summary_words else 0
    _print_sql_response(
        f"Total tokens: {total_input_tokens:,} in / {total_output_tokens:,} out | "
        f"Input words: {total_input_words:,} | Summary words: {final_summary_words:,} | "
        f"Compression (input words per summary word): {compression_ratio:.2f}",
        show_prompts=show_prompts,
        max_lines=2,
    )

    # Step 6: Save final summary
    print(Colors.action("Saving final summary to file..."))
    run_dir = RUNS_DIR / f"debug_{int(time.time())}" / article.name / config_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    summary_path = run_dir / "summary.md"
    summary_content = f"""# Summary: {article.name}

**Config:** {test_config.name}
**Config ID:** {test_config.config_id}
**Model:** {SMALL_MODEL.display_name}
**Chunks:** {len(all_chunk_summaries)}/{len(chunks)} (Debug limited)
**Words:** {len(current_summary.split())}

## Summary

{current_summary}
"""
    summary_path.write_text(summary_content)
    
    print(Colors.file_write(f"Written to: {summary_path}"))
    _print_sql_response(
        f"File content preview: {summary_content[:300]}...",
        show_prompts=show_prompts,
        max_lines=2,
    )
    
    # Step 7: Update test run
    print(Colors.action("Updating test run status..."))
    db.update_test_run(
        test_run_id=test_run_id,
        chunks_completed=len(all_chunk_summaries),
        summary_word_count=len(current_summary.split()),
        status="completed",
    )
    
    print(Colors.sql_query(f"UPDATE test_runs SET status='completed', chunks_completed={len(all_chunk_summaries)} WHERE id={test_run_id}"))
    _print_sql_response(
        "OK",
        show_prompts=show_prompts,
        max_lines=1,
    )
    
    db.close()
    
    print(f"\n{Colors.BOLD}DEBUG COMPLETE{Colors.ENDC}")
    print(f"Summary saved to: {summary_path}")


def main():
    """Main entry point."""
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("="*60)
    print("  CONTEXT REFINEMENT DEBUGGER")
    print("  Step-by-step CLI for testing configs")
    print("="*60)
    print(f"{Colors.ENDC}")
    
    # Parse command line for config ID
    import argparse
    parser = argparse.ArgumentParser(description="Debug CLI for testing summarization configs")
    parser.add_argument("config_id", nargs="?", default="01", help="Config ID to test (default: 01)")
    parser.add_argument("max_chunks", nargs="?", type=int, default=2, help="Max chunks to process (default: 2)")
    parser.add_argument(
        "--show-prompts",
        action="store_true",
        help="Show the system + user prompts before each chunk (off by default).",
    )
    args = parser.parse_args()
    
    # Select config
    config_id = args.config_id
    max_chunks = args.max_chunks
    show_prompts = args.show_prompts
    
    small_configs = [c for c in TEST_CONFIGS if c.id in ["01", "02", "03"]]
    
    # Find the requested config
    test_config = None
    for c in TEST_CONFIGS:
        if c.id == config_id:
            test_config = c
            break
    
    if test_config is None:
        print(f"Config ID '{config_id}' not found. Available IDs: 01, 02, 03")
        print("\nAvailable configs:")
        for c in small_configs:
            two_phase = " [TWO-PHASE]" if c.two_phase_summary else ""
            print(f"  {c.id}. {c.name}{two_phase}")
        return
    
    two_phase = " [TWO-PHASE]" if test_config.two_phase_summary else ""
    print(f"\nArticle: {ARTICLES[0].title}")
    print(f"Config: {test_config.name} (id: {test_config.id}){two_phase}")
    print(f"Max chunks: {max_chunks}")
    print("")
    
    wait_for_enter("Press ENTER to start debugging...\n")
    
    debug_single_config(
        ARTICLES[0],
        test_config,
        max_chunks=max_chunks,
        show_prompts=show_prompts,
    )


if __name__ == "__main__":
    main()
