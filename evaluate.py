"""Evaluation of summaries using big model."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from config import BIG_MODEL, ModelConfig
from summarizer import call_model


@dataclass
class EvaluationResult:
    """Result of evaluating a summary."""
    coherence: int
    completeness: int
    accuracy: int
    conciseness: int
    step_following: int
    early_completion_appropriate: Optional[bool]
    missing_information: str
    improvement_suggestions: str
    overall_score: float
    raw_response: str


def build_evaluation_prompt(
    article_content: str,
    summary: str,
    early_completion: bool = False,
    chunks_processed: int = 0,
    total_chunks: int = 0,
) -> str:
    """Build evaluation prompt for big model."""
    parts = []
    
    # Truncate article to first 3000 chars for comparison
    article_excerpt = article_content[:3000]
    if len(article_content) > 3000:
        article_excerpt += "\n\n[...article continues...]"
    
    parts.append("You are evaluating a summary quality. Compare the summary to the original article.")
    parts.append("")
    parts.append("ORIGINAL ARTICLE (first portion):")
    parts.append(article_excerpt)
    parts.append("")
    parts.append("SUMMARY TO EVALUATE:")
    parts.append(summary)
    parts.append("")
    
    if early_completion:
        parts.append(f"NOTE: This summary was marked as COMPLETE at chunk {chunks_processed} of {total_chunks}.")
        parts.append("The model decided it had enough information to stop early.")
        parts.append("")
    
    parts.append("Please evaluate each aspect on a scale of 1-10:")
    parts.append("")
    parts.append("1. COHERENCE - Does the summary flow logically? Is it easy to follow?")
    parts.append("2. COMPLETENESS - Are key facts from the article included?")
    parts.append("3. ACCURACY - Are the facts in the summary correct?")
    parts.append("4. CONCISENESS - Is it appropriately brief without being too sparse?")
    parts.append("5. STEP_FOLLOWING - Did it follow the summarization instructions?")
    parts.append("")
    
    if early_completion:
        parts.append("6. EARLY_COMPLETION - Was the early completion APPROPRIATE?")
        parts.append("   (yes = had enough info, no = missed important information)")
        parts.append("")
    
    parts.append("Also provide:")
    parts.append("- MISSING: List key information missing from the summary")
    parts.append("- SUGGESTIONS: How could the summary be improved?")
    parts.append("")
    parts.append("Format your response as JSON:")
    parts.append("{")
    parts.append('  "coherence": <1-10>,')
    parts.append('  "completeness": <1-10>,')
    parts.append('  "accuracy": <1-10>,')
    parts.append('  "conciseness": <1-10>,')
    parts.append('  "step_following": <1-10>,')
    if early_completion:
        parts.append('  "early_completion_appropriate": <true/false>,')
    parts.append('  "missing": "list of missing information",')
    parts.append('  "suggestions": "improvement suggestions"')
    parts.append("}")
    
    return "\n".join(parts)


def parse_evaluation_response(
    response: str,
    early_completion: bool = False,
) -> Dict[str, Any]:
    """Parse evaluation response."""
    # Try to find JSON in response
    match = re.search(r'\{[^}]+\}', response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return data
        except json.JSONDecodeError:
            pass
    
    # Fallback: parse manually
    result = {
        "coherence": 5,
        "completeness": 5,
        "accuracy": 5,
        "conciseness": 5,
        "step_following": 5,
        "missing": "Could not parse",
        "suggestions": "Could not parse",
    }
    
    if early_completion:
        result["early_completion_appropriate"] = None
    
    # Try to extract scores
    for line in response.split('\n'):
        line_lower = line.lower()
        if 'coherence' in line_lower:
            match = re.search(r'(\d+)', line)
            if match:
                result["coherence"] = int(match.group(1))
        elif 'completeness' in line_lower:
            match = re.search(r'(\d+)', line)
            if match:
                result["completeness"] = int(match.group(1))
        elif 'accuracy' in line_lower:
            match = re.search(r'(\d+)', line)
            if match:
                result["accuracy"] = int(match.group(1))
        elif 'conciseness' in line_lower:
            match = re.search(r'(\d+)', line)
            if match:
                result["conciseness"] = int(match.group(1))
        elif 'step_following' in line_lower or 'step following' in line_lower:
            match = re.search(r'(\d+)', line)
            if match:
                result["step_following"] = int(match.group(1))
    
    return result


def evaluate_summary(
    article_content: str,
    summary: str,
    early_completion: bool = False,
    chunks_processed: int = 0,
    total_chunks: int = 0,
    model_config: ModelConfig = BIG_MODEL,
    progress_callback=None,
) -> EvaluationResult:
    """Evaluate a summary using the big model."""
    
    if progress_callback:
        progress_callback(f"\n{'='*60}")
        progress_callback(f"EVALUATING SUMMARY")
        progress_callback(f"{'='*60}")
    
    # Build prompt
    prompt = build_evaluation_prompt(
        article_content=article_content,
        summary=summary,
        early_completion=early_completion,
        chunks_processed=chunks_processed,
        total_chunks=total_chunks,
    )
    
    # Call model
    messages = [
        {
            "role": "system",
            "content": "You are an expert evaluator. Provide objective, detailed evaluations in JSON format.",
        },
        {"role": "user", "content": prompt},
    ]
    
    response, _, _ = call_model(messages, model_config)
    
    if response is None:
        if progress_callback:
            progress_callback("  ERROR: Evaluation model call failed")
        return EvaluationResult(
            coherence=0,
            completeness=0,
            accuracy=0,
            conciseness=0,
            step_following=0,
            early_completion_appropriate=None,
            missing_information="Evaluation failed",
            improvement_suggestions="Evaluation failed",
            overall_score=0.0,
            raw_response="",
        )
    
    if progress_callback:
        progress_callback(f"\nEVALUATION RESPONSE:")
        progress_callback(f"{'-'*60}")
        progress_callback(response[:500])
        if len(response) > 500:
            progress_callback("...")
        progress_callback(f"{'-'*60}")
    
    # Parse response
    data = parse_evaluation_response(response, early_completion)
    
    # Calculate overall score
    scores = [
        data.get("coherence", 5),
        data.get("completeness", 5),
        data.get("accuracy", 5),
        data.get("conciseness", 5),
        data.get("step_following", 5),
    ]
    overall_score = sum(scores) / len(scores)
    
    if progress_callback:
        progress_callback(f"\nEVALUATION SCORES:")
        progress_callback(f"  Coherence:      {data.get('coherence', '?')}/10")
        progress_callback(f"  Completeness:   {data.get('completeness', '?')}/10")
        progress_callback(f"  Accuracy:       {data.get('accuracy', '?')}/10")
        progress_callback(f"  Conciseness:    {data.get('conciseness', '?')}/10")
        progress_callback(f"  Step Following: {data.get('step_following', '?')}/10")
        progress_callback(f"  Overall:        {overall_score:.1f}/10")
        if early_completion:
            appropriate = data.get("early_completion_appropriate", "?")
            progress_callback(f"  Early Completion Appropriate: {appropriate}")
    
    return EvaluationResult(
        coherence=data.get("coherence", 5),
        completeness=data.get("completeness", 5),
        accuracy=data.get("accuracy", 5),
        conciseness=data.get("conciseness", 5),
        step_following=data.get("step_following", 5),
        early_completion_appropriate=data.get("early_completion_appropriate"),
        missing_information=data.get("missing", ""),
        improvement_suggestions=data.get("suggestions", ""),
        overall_score=overall_score,
        raw_response=response,
    )


def save_evaluation(
    output_path: Path,
    evaluation: EvaluationResult,
    summary: str,
    test_config_id: str,
    article_name: str,
):
    """Save evaluation result to markdown file."""
    content = f"""# Evaluation: {article_name}

**Config:** {test_config_id}
**Overall Score:** {evaluation.overall_score:.1f}/10

## Scores

| Aspect | Score |
|--------|-------|
| Coherence | {evaluation.coherence}/10 |
| Completeness | {evaluation.completeness}/10 |
| Accuracy | {evaluation.accuracy}/10 |
| Conciseness | {evaluation.conciseness}/10 |
| Step Following | {evaluation.step_following}/10 |

## Early Completion

**Appropriate:** {evaluation.early_completion_appropriate if evaluation.early_completion_appropriate is not None else "N/A"}

## Missing Information

{evaluation.missing_information}

## Improvement Suggestions

{evaluation.improvement_suggestions}

## Raw Evaluation Response

```
{evaluation.raw_response}
```
"""
    output_path.write_text(content)
