"""Fetch Wikipedia articles for context refinement tests."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from config import Article, ARTICLES, ARTICLES_DIR

# Wikipedia requires a User-Agent header
HEADERS = {
    "User-Agent": "ContextRefinementTest/1.0 (Educational research project; contact@example.com)"
}


def fetch_wikipedia_api(title: str) -> Optional[str]:
    """Fetch article using Wikipedia API (returns plain text)."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "explaintext": True,
        "format": "json",
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id == "-1":
                return None
            return page_data.get("extract")

        return None
    except Exception as e:
        print(f"API error for {title}: {e}")
        return None


def fetch_wikipedia_sections_api(title: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch article sections using Wikipedia API."""
    # First get section structure
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": title,
        "prop": "sections",
        "format": "json",
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        sections = data.get("parse", {}).get("sections", [])
        if not sections:
            return None

        # Now fetch content for each section
        result = []
        for section in sections:
            section_id = section.get("index")
            section_title = section.get("line", "Introduction")

            # Fetch section content
            params = {
                "action": "parse",
                "page": title,
                "prop": "wikitext",
                "section": section_id,
                "format": "json",
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                section_data = resp.json()
                content = section_data.get("parse", {}).get("wikitext", {}).get("*", "")
                if content:
                    # Clean up wikitext
                    content = clean_wikitext(content)
                    if len(content) > 100:  # Skip very short sections
                        result.append({
                            "title": section_title,
                            "content": content,
                        })

            time.sleep(0.1)  # Rate limiting

        return result if result else None
    except Exception as e:
        print(f"Section API error for {title}: {e}")
        return None


def clean_wikitext(text: str) -> str:
    """Clean wikitext to plain text."""
    # Remove templates
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # Remove references
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ref[^>]*/>', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove wiki links but keep text
    text = re.sub(r'\[\[([^|\]]*\|)?([^\]]+)\]\]', r'\2', text)
    # Remove external links
    text = re.sub(r'\[https?://[^\s]+ ([^\]]+)\]', r'\1', text)
    # Remove bold/italic markers
    text = re.sub(r"'{2,5}", '', text)
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def fetch_article_by_scraping(title: str) -> Optional[str]:
    """Fetch article by scraping the HTML page."""
    url = f"https://en.wikipedia.org/wiki/{quote(title)}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        # Extract text from paragraphs
        # Simple extraction - get text between <p> tags
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', resp.text, re.DOTALL)

        # Clean HTML
        clean_paragraphs = []
        for p in paragraphs:
            # Remove tags
            text = re.sub(r'<[^>]+>', '', p)
            # Decode entities
            text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            text = text.replace('&#91;', '[').replace('&#93;', ']')
            text = text.replace('&quot;', '"').replace('&#39;', "'")
            # Clean up
            text = text.strip()
            if len(text) > 50:
                clean_paragraphs.append(text)

        return '\n\n'.join(clean_paragraphs) if clean_paragraphs else None
    except Exception as e:
        print(f"Scraping error for {title}: {e}")
        return None


def fetch_article(article: Article, force_refetch: bool = False) -> Tuple[str, int]:
    """
    Fetch an article, using cache if available.
    
    Returns:
        Tuple of (content, actual_token_estimate)
    """
    output_path = ARTICLES_DIR / f"{article.name}.md"

    # Check cache
    if output_path.exists() and not force_refetch:
        content = output_path.read_text()
        token_estimate = len(content) // 4  # Rough estimate
        print(f"  Loaded from cache: {article.name} ({token_estimate:,} tokens)")
        return content, token_estimate

    print(f"  Fetching: {article.title}...")

    # Try API first
    content = fetch_wikipedia_api(article.title)
    method = "api"

    # If API gave short content, try sections
    if content and len(content) < 50000:
        print(f"    API gave {len(content)} chars, trying sections...")
        sections = fetch_wikipedia_sections_api(article.title)
        if sections and len(sections) > 3:
            # Combine sections
            full_content = []
            for section in sections:
                full_content.append(f"## {section['title']}\n\n{section['content']}")
            section_content = '\n\n'.join(full_content)
            if len(section_content) > len(content):
                content = section_content
                method = "sections"

    # If still short, try scraping
    if not content or len(content) < 50000:
        print(f"    Trying scraping...")
        scraped = fetch_article_by_scraping(article.title)
        if scraped and (not content or len(scraped) > len(content)):
            content = scraped
            method = "scraping"

    if not content:
        print(f"    Failed to fetch: {article.title}")
        return "", 0

    # Format as markdown
    md_content = f"""# {article.title}

{content}
"""
    # Save to cache
    output_path.write_text(md_content)

    token_estimate = len(md_content) // 4
    print(f"    Fetched via {method}: {len(md_content):,} chars (~{token_estimate:,} tokens)")

    return md_content, token_estimate


def fetch_all_articles(articles: Optional[List[Article]] = None, force_refetch: bool = False):
    """Fetch all articles."""
    if articles is None:
        articles = ARTICLES

    print("Fetching Wikipedia articles...")
    print("=" * 60)

    results = {}
    for article in articles:
        content, tokens = fetch_article(article, force_refetch)
        results[article.name] = {
            "content": content,
            "tokens": tokens,
            "success": len(content) > 0,
        }
        time.sleep(0.5)  # Rate limiting

    print("\n" + "=" * 60)
    print("Fetch Summary:")
    print("-" * 60)
    for name, data in results.items():
        status = "✓" if data["success"] else "✗"
        tokens = f"{data['tokens']:,}" if data["success"] else "FAILED"
        print(f"  {status} {name}: {tokens} tokens")

    return results


if __name__ == "__main__":
    fetch_all_articles()
