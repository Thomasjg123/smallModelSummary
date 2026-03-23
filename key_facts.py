"""Key facts tracking for article summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class KeyFactCategory:
    """Category of key facts to check."""
    name: str
    terms: List[str]


@dataclass
class KeyFactsResult:
    """Result of checking key facts."""
    category: str
    found: List[str]
    missing: List[str]
    coverage: float  # 0-100

    @property
    def coverage_percent(self) -> int:
        return int(self.coverage)


# WW2 Key Facts
WW2_KEY_FACTS = {
    "events": KeyFactCategory(
        name="Major Events",
        terms=[
            "D-Day", "Normandy", "Pearl Harbor", "Stalingrad",
            "Hiroshima", "Nagasaki", "atomic bomb", "nuclear",
            "Holocaust", "Battle of Britain", "Midway",
            "El Alamein", "Iwo Jima", "Okinawa", "Bulge",
            "invasion of Poland", "fall of France", "Blitzkrieg"
        ]
    ),
    "dates": KeyFactCategory(
        name="Key Dates",
        terms=[
            "1939", "1945", "1941", "1942", "1943", "1944",
            "September 1", "December 7", "June 6", "May 8",
            "August 6", "August 9", "August 15"
        ]
    ),
    "countries": KeyFactCategory(
        name="Major Powers",
        terms=[
            "Germany", "Japan", "Italy", "United States",
            "United Kingdom", "Soviet Union", "Russia",
            "China", "France", "Poland", "Allies", "Axis"
        ]
    ),
    "leaders": KeyFactCategory(
        name="Key Leaders",
        terms=[
            "Hitler", "Churchill", "Roosevelt", "Stalin",
            "Hirohito", "Mussolini", "Truman", "Eisenhower",
            "MacArthur", "Rommel", "Montgomery", "Zhukov"
        ]
    ),
    "outcomes": KeyFactCategory(
        name="Outcomes & Impact",
        terms=[
            "Holocaust", "genocide", "United Nations", "Cold War",
            "decolonization", "nuclear weapons", "war crimes",
            "Nuremberg", "70 million", "50 million", "deaths",
            "occupation", "reconstruction", "Marshall Plan"
        ]
    ),
    "theaters": KeyFactCategory(
        name="War Theaters",
        terms=[
            "European", "Pacific", "Eastern Front", "Western Front",
            "North Africa", "Mediterranean", "Atlantic",
            "China", "Southeast Asia", "Balkans"
        ]
    ),
}


def check_key_facts(summary: str, facts: Dict[str, KeyFactCategory] = None) -> Dict[str, KeyFactsResult]:
    """
    Check which key facts are mentioned in a summary.
    
    Args:
        summary: The summary text to check
        facts: Dictionary of fact categories to check (default: WW2)
    
    Returns:
        Dictionary of category name to KeyFactsResult
    """
    if facts is None:
        facts = WW2_KEY_FACTS
    
    results = {}
    summary_lower = summary.lower()
    
    for key, category in facts.items():
        found = []
        missing = []
        
        for term in category.terms:
            if term.lower() in summary_lower:
                found.append(term)
            else:
                missing.append(term)
        
        coverage = (len(found) / len(category.terms)) * 100 if category.terms else 0
        
        results[key] = KeyFactsResult(
            category=category.name,
            found=found,
            missing=missing,
            coverage=coverage,
        )
    
    return results


def get_overall_coverage(results: Dict[str, KeyFactsResult]) -> float:
    """Calculate overall coverage percentage."""
    if not results:
        return 0.0
    
    total_coverage = sum(r.coverage for r in results.values())
    return total_coverage / len(results)


def format_key_facts_report(results: Dict[str, KeyFactsResult]) -> str:
    """Format key facts results as a readable report."""
    lines = []
    lines.append("## Key Facts Coverage")
    lines.append("")
    lines.append("| Category | Coverage | Found | Missing |")
    lines.append("|----------|----------|-------|---------|")
    
    for key, result in results.items():
        found_str = ", ".join(result.found[:5]) if result.found else "-"
        if len(result.found) > 5:
            found_str += f" (+{len(result.found) - 5} more)"
        
        missing_str = ", ".join(result.missing[:5]) if result.missing else "-"
        if len(result.missing) > 5:
            missing_str += f" (+{len(result.missing) - 5} more)"
        
        lines.append(
            f"| {result.category:15} | {result.coverage:5.1f}% | {found_str:30} | {missing_str:30} |"
        )
    
    overall = get_overall_coverage(results)
    lines.append("")
    lines.append(f"**Overall Coverage: {overall:.1f}%**")
    
    return "\n".join(lines)


def save_key_facts_report(
    results: Dict[str, KeyFactsResult],
    output_path,
    summary: str = "",
    config_id: str = "",
    model_name: str = "",
):
    """Save key facts report to markdown file."""
    from pathlib import Path
    
    overall = get_overall_coverage(results)
    
    content = f"""# Key Facts Analysis

**Config:** {config_id}
**Model:** {model_name}
**Overall Coverage:** {overall:.1f}%

{format_key_facts_report(results)}

## Summary Text (for reference)

{summary[:2000]}{'...' if len(summary) > 2000 else ''}
"""
    
    Path(output_path).write_text(content)
