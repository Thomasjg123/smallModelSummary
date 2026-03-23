"""Generate comparison reports from test results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import TEST_CONFIGS


def generate_comparison_report(
    results: List[Dict[str, Any]],
    output_path: Path,
):
    """Generate a comparison report from test results."""
    
    if not results:
        content = "# Comparison Report\n\nNo results to compare."
        output_path.write_text(content)
        return
    
    # Group by config
    by_config: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        config_id = r.get("config", "unknown")
        if config_id not in by_config:
            by_config[config_id] = []
        by_config[config_id].append(r)
    
    # Calculate averages by config
    config_stats: Dict[str, Dict[str, Any]] = {}
    for config_id, config_results in by_config.items():
        stats = {
            "count": len(config_results),
            "avg_chunks_processed": 0,
            "early_completion_rate": 0,
            "avg_input_tokens": 0,
            "avg_output_tokens": 0,
            "avg_summary_words": 0,
            "avg_score": 0,
            "score_count": 0,
        }
        
        for r in config_results:
            stats["avg_chunks_processed"] += r.get("chunks_processed", 0)
            if r.get("early_completion"):
                stats["early_completion_rate"] += 1
            stats["avg_input_tokens"] += r.get("total_input_tokens", 0)
            stats["avg_output_tokens"] += r.get("total_output_tokens", 0)
            stats["avg_summary_words"] += r.get("summary_word_count", 0)
            if r.get("overall_score") is not None:
                stats["avg_score"] += r["overall_score"]
                stats["score_count"] += 1
        
        n = len(config_results)
        stats["avg_chunks_processed"] /= n
        stats["early_completion_rate"] = (stats["early_completion_rate"] / n) * 100
        stats["avg_input_tokens"] /= n
        stats["avg_output_tokens"] /= n
        stats["avg_summary_words"] /= n
        if stats["score_count"] > 0:
            stats["avg_score"] /= stats["score_count"]
        
        config_stats[config_id] = stats
    
    # Build report
    lines = []
    lines.append("# Context Refinement Test Results")
    lines.append("")
    lines.append(f"**Total tests:** {len(results)}")
    lines.append(f"**Configurations tested:** {len(by_config)}")
    lines.append("")
    
    # Summary table
    lines.append("## Summary by Configuration")
    lines.append("")
    lines.append("| Config | Tests | Chunks | Early % | Tokens In | Tokens Out | Words | Score |")
    lines.append("|--------|-------|--------|---------|-----------|------------|-------|-------|")
    
    for config_id in sorted(config_stats.keys()):
        stats = config_stats[config_id]
        score = f"{stats['avg_score']:.1f}" if stats['score_count'] > 0 else "N/A"
        lines.append(
            f"| {config_id[:30]:30} | {stats['count']:5} | "
            f"{stats['avg_chunks_processed']:6.1f} | "
            f"{stats['early_completion_rate']:7.1f}% | "
            f"{stats['avg_input_tokens']:9.0f} | "
            f"{stats['avg_output_tokens']:10.0f} | "
            f"{stats['avg_summary_words']:5.0f} | "
            f"{score:5} |"
        )
    
    lines.append("")
    
    # Key findings
    lines.append("## Key Findings")
    lines.append("")
    
    # Find best config by score
    best_config = None
    best_score = 0
    for config_id, stats in config_stats.items():
        if stats['score_count'] > 0 and stats['avg_score'] > best_score:
            best_score = stats['avg_score']
            best_config = config_id
    
    if best_config:
        lines.append(f"**Best performing configuration:** {best_config} (score: {best_score:.1f})")
    
    # Find configs with highest early completion rate
    early_configs = [
        (cid, s['early_completion_rate'])
        for cid, s in config_stats.items()
        if s['early_completion_rate'] > 0
    ]
    if early_configs:
        early_configs.sort(key=lambda x: x[1], reverse=True)
        lines.append(f"\n**Highest early completion rate:** {early_configs[0][0]} ({early_configs[0][1]:.1f}%)")
    
    # Context injection comparison
    lines.append("")
    lines.append("## Context Injection Impact")
    lines.append("")
    
    # Compare with vs without context
    with_ctx = [c for c in config_stats.keys() if 'with_ctx' in c or 'ctx' in c]
    no_ctx = [c for c in config_stats.keys() if 'no_ctx' in c]
    
    if with_ctx and no_ctx:
        avg_with = sum(config_stats[c]['avg_score'] for c in with_ctx if config_stats[c]['score_count'] > 0) / len(with_ctx)
        avg_no = sum(config_stats[c]['avg_score'] for c in no_ctx if config_stats[c]['score_count'] > 0) / len(no_ctx)
        
        lines.append(f"**With context injection:** Average score {avg_with:.1f}")
        lines.append(f"**Without context injection:** Average score {avg_no:.1f}")
        
        if avg_with > avg_no:
            improvement = ((avg_with - avg_no) / avg_no) * 100
            lines.append(f"\nContext injection improved scores by {improvement:.1f}%")
    
    # Early completion analysis
    lines.append("")
    lines.append("## Early Completion Analysis")
    lines.append("")
    
    early_enabled = [c for c in config_stats.keys() if 'early' in c]
    early_disabled = [c for c in config_stats.keys() if 'full' in c]
    
    if early_enabled:
        lines.append("**Early completion enabled configurations:**")
        for c in early_enabled:
            stats = config_stats[c]
            lines.append(f"  - {c}: {stats['early_completion_rate']:.1f}% early rate")
    
    if early_disabled:
        lines.append("\n**Early completion disabled configurations:**")
        for c in early_disabled:
            stats = config_stats[c]
            lines.append(f"  - {c}: {stats['early_completion_rate']:.1f}% early rate")
    
    # Detailed results by article
    lines.append("")
    lines.append("## Detailed Results by Article")
    lines.append("")
    
    by_article: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        article = r.get("article", "unknown")
        if article not in by_article:
            by_article[article] = []
        by_article[article].append(r)
    
    for article, article_results in sorted(by_article.items()):
        lines.append(f"### {article}")
        lines.append("")
        lines.append("| Config | Chunks | Early | Score |")
        lines.append("|--------|--------|-------|-------|")
        
        for r in article_results:
            early = "✓" if r.get("early_completion") else "✗"
            score = f"{r['overall_score']:.1f}" if r.get('overall_score') is not None else "N/A"
            lines.append(
                f"| {r.get('config', '?')[:30]:30} | "
                f"{r.get('chunks_processed', 0)}/{r.get('total_chunks', 0)} | "
                f"{early} | {score} |"
            )
        
        lines.append("")
    
    # Recommendations
    lines.append("## Recommendations for LazerForge")
    lines.append("")
    
    if best_config:
        lines.append(f"Based on these results, consider using configuration similar to **{best_config}**")
    
    lines.append("")
    lines.append("Key takeaways:")
    lines.append("1. Context injection helps maintain coherence across chunks")
    lines.append("2. Section-based chunking respects document structure")
    lines.append("3. Early completion can save tokens but may miss information")
    lines.append("4. Summary compression helps manage context window")
    
    # Write report
    content = "\n".join(lines)
    output_path.write_text(content)


def load_results_from_dir(run_dir: Path) -> List[Dict[str, Any]]:
    """Load results from a run directory."""
    results = []
    
    for article_dir in run_dir.iterdir():
        if not article_dir.is_dir() or article_dir.name.startswith('.'):
            continue
        
        for config_dir in article_dir.iterdir():
            if not config_dir.is_dir():
                continue
            
            # Check for summary
            summary_path = config_dir / "summary.md"
            if not summary_path.exists():
                continue
            
            # Try to load evaluation
            eval_path = config_dir / "evaluation.json"
            score = None
            if eval_path.exists():
                try:
                    eval_data = json.loads(eval_path.read_text())
                    # Try to extract score from evaluation
                except:
                    pass
            
            results.append({
                "article": article_dir.name,
                "config": config_dir.name,
                "summary_path": str(summary_path),
                "overall_score": score,
            })
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        run_dir = Path(sys.argv[1])
        if run_dir.exists():
            results = load_results_from_dir(run_dir)
            generate_comparison_report(results, run_dir / "comparison.md")
            print(f"Generated comparison report at {run_dir / 'comparison.md'}")
        else:
            print(f"Directory not found: {run_dir}")
    else:
        print("Usage: python compare.py <run_directory>")
