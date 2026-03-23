"""Core summarization logic with context management."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from chunker import Chunk, truncate_to_tokens
from config import DoneSignalType, ModelConfig, PromptStyle, TestConfig, SMALL_MODEL
from db import TestDatabase


@dataclass
class ChunkResult:
    """Result of processing a single chunk."""
    chunk_number: int
    chunk_title: str
    summary_before: str
    section_content: str
    model_response: str
    summary_after: str
    input_tokens: int
    output_tokens: int
    done_signal_detected: bool
    success: bool
    error: Optional[str] = None


def call_model(
    messages: List[Dict[str, str]],
    config: ModelConfig,
) -> Tuple[Optional[str], int, int]:
    """
    Call the model API.
    
    Returns:
        Tuple of (response_text, input_tokens, output_tokens)
    """
    url = f"{config.base_url}/chat/completions"
    
    try:
        resp = requests.post(
            url,
            json={
                "model": config.model_name,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            },
            timeout=config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        
        content = data["choices"][0]["message"]["content"]
        
        # Estimate tokens (rough)
        input_tokens = sum(len(m["content"]) for m in messages) // 4
        output_tokens = len(content) // 4
        
        return content, input_tokens, output_tokens
    except Exception as e:
        return None, 0, 0


def build_system_prompt(test_config: TestConfig) -> str:
    """Build system prompt based on test configuration."""
    parts = []
    parts.append("You are summarizing a long article processed in sections.")
    parts.append("")
    
    # Add done signal instructions based on config
    if test_config.allow_early_completion:
        parts.append("After EACH section:")
        parts.append("- Update your running summary with new key information")
        parts.append("")
        parts.append("You may decide you have enough information to complete the summary early.")
        
        if test_config.done_signal_type == DoneSignalType.XML:
            parts.append("When you believe the summary is comprehensive enough, output:")
            parts.append("<SUMMARY_COMPLETE>")
            parts.append("[your final summary]")
            parts.append("</SUMMARY_COMPLETE>")
            parts.append("")
            parts.append("If you need more sections, just provide your updated summary without the tag.")
        elif test_config.done_signal_type == DoneSignalType.JSON:
            parts.append("When complete, respond with only:")
            parts.append('{"status": "complete", "summary": "your final summary"}')
        elif test_config.done_signal_type == DoneSignalType.NATURAL:
            parts.append("When complete, start your response with:")
            parts.append('"SUMMARY COMPLETE:" followed by the final summary.')
    else:
        parts.append("After EACH section:")
        parts.append("- Update your running summary with new key information")
        
        if test_config.done_signal_type != DoneSignalType.NONE:
            parts.append("- On the FINAL section, output your complete summary")
    
    parts.append("")
    parts.append("Rules:")
    parts.append("- Include key facts, names, dates, relationships")
    parts.append("- Be concise and factual")
    
    # Add tagged previous summary format for with-context configs
    if test_config.include_previous_summary:
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
        parts.append("OUTPUT ONLY THE THREE LINES SPECIFIED ABOVE.")
    
    return "\n".join(parts)


def build_user_prompt(
    test_config: TestConfig,
    chunk: Chunk,
    previous_summary: str,
) -> str:
    """Build user prompt for a chunk."""
    parts = []
    
    # Add previous summary if configured
    if test_config.include_previous_summary:
        if previous_summary:
            parts.append("CURRENT RUNNING SUMMARY (keep this and add new info):")
            parts.append(previous_summary)
        else:
            parts.append("CURRENT RUNNING SUMMARY:")
            parts.append("[This is the first section - start fresh]")
    
    parts.append("")
    
    # Add section info
    parts.append(f"SECTION {chunk.number}: {chunk.title}")
    if test_config.include_previous_summary:
        parts.append("Begin analyzing this section and update your summary:")
    parts.append(chunk.content)
    parts.append("")
    
    # Add instructions based on config and prompt style
    if test_config.prompt_style == PromptStyle.BASIC:
        parts.extend(_get_basic_instructions(test_config, chunk))
    elif test_config.prompt_style == PromptStyle.EXPLICIT:
        parts.extend(_get_explicit_instructions(test_config, chunk))
    elif test_config.prompt_style == PromptStyle.WITH_EXAMPLE:
        parts.extend(_get_example_instructions(test_config, chunk))
    
    return "\n".join(parts)


def _get_basic_instructions(test_config: TestConfig, chunk: Chunk) -> List[str]:
    """Get basic prompt instructions."""
    parts = []
    
    if test_config.allow_early_completion:
        if test_config.done_signal_type == DoneSignalType.XML:
            parts.append("You may output <SUMMARY_COMPLETE> if you have enough information.")
        elif test_config.done_signal_type == DoneSignalType.JSON:
            parts.append('You may output {"status": "complete", "summary": "..."} if done.')
        elif test_config.done_signal_type == DoneSignalType.NATURAL:
            parts.append('You may output "SUMMARY COMPLETE:" if done.')
    else:
        if chunk.is_last:
            parts.append("This is the FINAL section.")
            if test_config.done_signal_type == DoneSignalType.XML:
                parts.append("Provide your complete summary with <SUMMARY_COMPLETE> tags.")
            elif test_config.done_signal_type == DoneSignalType.JSON:
                parts.append('Provide {"status": "complete", "summary": "..."}.')
        else:
            parts.append("Update your summary:")
    
    return parts


def _get_explicit_instructions(test_config: TestConfig, chunk: Chunk) -> List[str]:
    """Get explicit prompt instructions."""
    parts = []
    
    parts.append("TASK: Write a summary of this section that can be combined with previous summaries.")
    parts.append("")
    parts.append("FORMAT: 2-3 paragraphs covering:")
    parts.append("- Main topics and themes")
    parts.append("- Key facts, dates, and names")
    parts.append("- Important events and their significance")
    parts.append("")
    parts.append("Do NOT repeat information from previous summaries.")
    parts.append("")
    
    if test_config.allow_early_completion:
        parts.append("You may finish early if you have enough information.")
        if test_config.done_signal_type == DoneSignalType.XML:
            parts.append("When done, output: <SUMMARY_COMPLETE>[your summary]</SUMMARY_COMPLETE>")
    else:
        if chunk.is_last:
            parts.append("This is the FINAL section - provide your complete summary.")
            if test_config.done_signal_type == DoneSignalType.XML:
                parts.append("Output: <SUMMARY_COMPLETE>[your summary]</SUMMARY_COMPLETE>")
    
    parts.append("")
    parts.append("Your summary:")
    
    return parts


def _get_example_instructions(test_config: TestConfig, chunk: Chunk) -> List[str]:
    """Get prompt instructions with example."""
    parts = []
    
    parts.append("TASK: Write a summary of this section.")
    parts.append("")
    parts.append("EXAMPLE FORMAT:")
    parts.append('"World War II (1939-1945) was a global conflict involving most nations.')
    parts.append('The war began with Germany\'s invasion of Poland and ended with Japan\'s')
    parts.append('surrender. Key events included the Battle of Stalingrad, D-Day, and')
    parts.append('the atomic bombings of Hiroshima and Nagasaki."')
    parts.append("")
    parts.append("Write your summary in this style, covering the key points:")
    parts.append("")
    
    if test_config.allow_early_completion:
        if test_config.done_signal_type == DoneSignalType.XML:
            parts.append("When done, output: <SUMMARY_COMPLETE>[your summary]</SUMMARY_COMPLETE>")
    
    return parts


def detect_done_signal(
    response: str,
    signal_type: DoneSignalType,
) -> Tuple[bool, str]:
    """
    Detect if response contains done signal.
    
    Returns:
        Tuple of (is_done, extracted_summary)
    """
    if signal_type == DoneSignalType.XML:
        match = re.search(
            r'<SUMMARY_COMPLETE>(.*?)</SUMMARY_COMPLETE>',
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            return True, match.group(1).strip()
    
    elif signal_type == DoneSignalType.JSON:
        # Look for JSON with status=complete
        match = re.search(r'\{[^}]*"status"\s*:\s*"complete"[^}]*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return True, data.get("summary", "")
            except json.JSONDecodeError:
                pass
    
    elif signal_type == DoneSignalType.NATURAL:
        if "SUMMARY COMPLETE:" in response.upper():
            match = re.search(
                r'SUMMARY COMPLETE:\s*(.*)',
                response,
                re.DOTALL | re.IGNORECASE,
            )
            if match:
                return True, match.group(1).strip()
    
    return False, ""


def extract_summary_from_response(
    response: str,
    done_signal_type: DoneSignalType,
    max_words: int = 500,
) -> str:
    """Extract summary from response (without done signal tags)."""
    # Remove done signal tags if present
    cleaned = response
    
    if done_signal_type == DoneSignalType.XML:
        cleaned = re.sub(r'<SUMMARY_COMPLETE>.*?</SUMMARY_COMPLETE>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'</?SUMMARY_COMPLETE>', '', cleaned, flags=re.IGNORECASE)
    elif done_signal_type == DoneSignalType.JSON:
        cleaned = re.sub(r'\{[^}]*"status"\s*:\s*"complete"[^}]*\}', '', cleaned, flags=re.DOTALL)
    elif done_signal_type == DoneSignalType.NATURAL:
        cleaned = re.sub(r'SUMMARY COMPLETE:.*', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Also extract from <SUMMARY_START></SUMMARY_END> tags (for with-context configs)
    match = re.search(r'<SUMMARY_START>(.*?)</SUMMARY_END>', cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    else:
        # If no tags found, clean up any残留 tags
        cleaned = re.sub(r'</?SUMMARY_START>', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'</?SUMMARY_END>', '', cleaned, flags=re.IGNORECASE)
    
    cleaned = cleaned.strip()
    
    # Only truncate if extremely long (prevent runaway responses)
    # This is a safety limit, not a content limit
    words = cleaned.split()
    if len(words) > 5000:  # Safety limit only
        cleaned = ' '.join(words[:5000])
    
    return cleaned


def combine_section_summaries(
    section_summaries: List[Dict[str, str]],
    model_config: ModelConfig,
    max_words: int = 1000,
) -> Tuple[str, int, int]:
    """
    Phase 2: Combine all section summaries into a final summary.
    
    Args:
        section_summaries: List of dicts with 'chunk_title' and 'summary_after' keys
        model_config: Model configuration
        max_words: Target word count for final summary
    
    Returns:
        Tuple of (final_summary, input_tokens, output_tokens)
    """
    if not section_summaries:
        return "", 0, 0
    
    # Build prompt with all section summaries
    sections_text = []
    for i, section in enumerate(section_summaries, 1):
        title = section.get("chunk_title", f"Section {i}")
        summary = section.get("summary_after", "")
        sections_text.append(f"Section {i}: {title}\n{summary}")
    
    combined_text = "\n\n---\n\n".join(sections_text)
    
    system_prompt = f"""You are combining multiple section summaries into a single coherent summary.
Your task is to merge these summaries while:
- Consolidating redundant information
- Maintaining chronological order where applicable
- Creating a flowing narrative
- Including all key facts, names, dates, and events
- Be concise and factual"""

    user_prompt = f"""Here are the summaries from each section of the article:

{combined_text}

Please combine these into a single coherent summary that incorporates all key information from the article."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    response, input_tokens, output_tokens = call_model(messages, model_config)
    
    if response is None:
        return "", input_tokens, output_tokens
    
    return response.strip(), input_tokens, output_tokens


def process_chunk(
    test_run_id: int,
    chunk: Chunk,
    previous_summary: str,
    test_config: TestConfig,
    model_config: ModelConfig,
    db: TestDatabase,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> ChunkResult:
    """Process a single chunk."""
    
    # Check if already completed (crash recovery)
    existing = db.get_chunk_progress(test_run_id, chunk.number)
    if existing and existing.get("status") == "completed":
        if progress_callback:
            progress_callback(f"  Chunk {chunk.number} already completed (resuming)")
        return ChunkResult(
            chunk_number=chunk.number,
            chunk_title=chunk.title,
            summary_before=existing.get("summary_before", ""),
            section_content=existing.get("section_content", ""),
            model_response=existing.get("model_response", ""),
            summary_after=existing.get("summary_after", ""),
            input_tokens=existing.get("input_tokens", 0),
            output_tokens=existing.get("output_tokens", 0),
            done_signal_detected=bool(existing.get("done_signal_detected")),
            success=True,
        )
    
    # Build prompts
    system_prompt = build_system_prompt(test_config)
    user_prompt = build_user_prompt(test_config, chunk, previous_summary)
    
    # Save before sending (for crash recovery)
    db.save_chunk_progress(
        test_run_id=test_run_id,
        chunk_number=chunk.number,
        chunk_title=chunk.title,
        summary_before=previous_summary,
        section_content=chunk.content,
        status="in_progress",
    )
    
    if progress_callback:
        progress_callback(f"\n{'='*60}")
        progress_callback(f"SENDING CHUNK {chunk.number}/{chunk.title}")
        progress_callback(f"{'='*60}")
        progress_callback(f"System prompt: {system_prompt[:200]}...")
        progress_callback(f"User prompt: {user_prompt[:300]}...")
    
    # Call model
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    response, input_tokens, output_tokens = call_model(messages, model_config)
    
    if response is None:
        if progress_callback:
            progress_callback(f"  ERROR: Model call failed")
        return ChunkResult(
            chunk_number=chunk.number,
            chunk_title=chunk.title,
            summary_before=previous_summary,
            section_content=chunk.content,
            model_response="",
            summary_after=previous_summary,  # Keep previous
            input_tokens=0,
            output_tokens=0,
            done_signal_detected=False,
            success=False,
            error="Model call failed",
        )
    
    if progress_callback:
        progress_callback(f"\nRECEIVED RESPONSE:")
        progress_callback(f"{'-'*60}")
        progress_callback(response[:500])
        if len(response) > 500:
            progress_callback(f"... [{len(response)} chars total]")
        progress_callback(f"{'-'*60}")
    
    # Parse response
    done_signal_detected, final_summary = detect_done_signal(
        response, test_config.done_signal_type
    )
    
    if done_signal_detected:
        summary_after = final_summary
        if progress_callback:
            progress_callback(f"\n✓ DONE SIGNAL DETECTED at chunk {chunk.number}")
    else:
        summary_after = extract_summary_from_response(
            response, test_config.done_signal_type, test_config.max_words
        )
    
    # Save after receiving response
    db.save_chunk_progress(
        test_run_id=test_run_id,
        chunk_number=chunk.number,
        chunk_title=chunk.title,
        summary_before=previous_summary,
        section_content=chunk.content,
        model_response=response,
        summary_after=summary_after,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        done_signal_detected=done_signal_detected,
        status="completed",
    )
    
    if progress_callback:
        progress_callback(f"\nSummary after chunk {chunk.number}:")
        progress_callback(f"  {summary_after[:200]}...")
        progress_callback(f"  Tokens: {input_tokens} in, {output_tokens} out")
    
    return ChunkResult(
        chunk_number=chunk.number,
        chunk_title=chunk.title,
        summary_before=previous_summary,
        section_content=chunk.content,
        model_response=response,
        summary_after=summary_after,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        done_signal_detected=done_signal_detected,
        success=True,
    )


def summarize_article(
    article_name: str,
    chunks: List[Chunk],
    test_config: TestConfig,
    model_config: ModelConfig = SMALL_MODEL,
    db: Optional[TestDatabase] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Summarize an article using chunk-based processing.
    
    Returns:
        Dict with results including final summary
    """
    if db is None:
        db = TestDatabase()
        db.init_schema()
    
    # Check for existing test run
    existing_run = db.get_test_run(article_name, test_config.config_id)
    if existing_run:
        test_run_id = existing_run["id"]
        if existing_run["status"] == "completed":
            if progress_callback:
                progress_callback(f"Test run already completed for {article_name}/{test_config.config_id}")
            last_chunk = db.get_last_completed_chunk(test_run_id)
            return {
                "test_run_id": test_run_id,
                "status": "already_completed",
                "summary": last_chunk.get("summary_after", "") if last_chunk else "",
            }
        # Resume from last completed chunk
        last_chunk = db.get_last_completed_chunk(test_run_id)
        if last_chunk:
            start_chunk = last_chunk["chunk_number"]
            current_summary = last_chunk["summary_after"]
            if progress_callback:
                progress_callback(f"Resuming from chunk {start_chunk}")
        else:
            start_chunk = 0
            current_summary = ""
    else:
        # Create new test run
        test_run_id = db.create_test_run(
            article_name=article_name,
            config_id=test_config.config_id,
            total_chunks=len(chunks),
        )
        start_chunk = 0
        current_summary = ""
    
    # Process chunks
    total_input_tokens = 0
    total_output_tokens = 0
    early_completion = False
    completion_chunk = len(chunks)
    
    for i, chunk in enumerate(chunks):
        if i < start_chunk:
            continue  # Skip already completed chunks
        
        if progress_callback:
            progress_callback(f"\nProcessing chunk {chunk.number}/{len(chunks)}: {chunk.title}")
        
        # Update test run progress
        db.update_test_run(test_run_id, chunks_completed=i)
        
        # Process chunk
        result = process_chunk(
            test_run_id=test_run_id,
            chunk=chunk,
            previous_summary=current_summary,
            test_config=test_config,
            model_config=model_config,
            db=db,
            progress_callback=progress_callback,
        )
        
        if not result.success:
            if progress_callback:
                progress_callback(f"  Failed: {result.error}")
            continue
        
        total_input_tokens += result.input_tokens
        total_output_tokens += result.output_tokens
        
        # Check for done signal
        if result.done_signal_detected:
            early_completion = True
            completion_chunk = chunk.number
            current_summary = result.summary_after
            if progress_callback:
                progress_callback(f"\nEARLY COMPLETION at chunk {chunk.number}")
            break
        
        # Update summary
        current_summary = result.summary_after
    
    # Update test run with final status
    db.update_test_run(
        test_run_id=test_run_id,
        chunks_completed=min(completion_chunk, len(chunks)),
        early_completion=early_completion,
        completion_chunk=completion_chunk,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        summary_word_count=len(current_summary.split()),
        status="completed",
    )
    
    if progress_callback:
        progress_callback(f"\n{'='*60}")
        progress_callback(f"SUMMARIZATION COMPLETE")
        progress_callback(f"{'='*60}")
        progress_callback(f"Chunks processed: {completion_chunk}/{len(chunks)}")
        if early_completion:
            progress_callback(f"Completed EARLY at chunk {completion_chunk}")
        progress_callback(f"Total tokens: {total_input_tokens:,} in, {total_output_tokens:,} out")
        progress_callback(f"Summary word count: {len(current_summary.split())}")
    
    return {
        "test_run_id": test_run_id,
        "status": "completed",
        "summary": current_summary,
        "chunks_processed": completion_chunk,
        "total_chunks": len(chunks),
        "early_completion": early_completion,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
    }
