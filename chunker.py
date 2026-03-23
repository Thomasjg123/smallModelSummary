"""Chunking strategies for long articles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from config import ChunkingMethod


@dataclass
class Chunk:
    """A chunk of text to process."""
    number: int
    title: str
    content: str
    is_last: bool = False

    @property
    def token_estimate(self) -> int:
        """Rough token estimate (4 chars = 1 token)."""
        return len(self.content) // 4


def chunk_by_sections(content: str) -> List[Chunk]:
    """
    Split content into chunks based on headers.
    
    Looks for ## or == headers as section dividers.
    """
    chunks = []
    
    # Split by headers (## or ==)
    # Pattern matches ## or == followed by text
    pattern = r'^(#{1,3} .+|={2,} .+ ={2,}|=.+ =)$'
    lines = content.split('\n')
    
    current_title = "Introduction"
    current_content = []
    
    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            # Save previous section
            if current_content:
                text = '\n'.join(current_content).strip()
                if text:
                    chunks.append(Chunk(
                        number=len(chunks) + 1,
                        title=current_title,
                        content=text,
                    ))
            
            # Start new section
            # Clean up the title
            title = match.group(1)
            title = title.replace('## ', '').replace('== ', '').replace(' ==', '').replace('= ', '').replace(' =', '')
            current_title = title.strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Save last section
    if current_content:
        text = '\n'.join(current_content).strip()
        if text:
            chunks.append(Chunk(
                number=len(chunks) + 1,
                title=current_title,
                content=text,
            ))
    
    # If no sections found, treat whole content as one chunk
    if not chunks:
        chunks.append(Chunk(
            number=1,
            title="Full Article",
            content=content,
        ))
    
    # Mark last chunk
    if chunks:
        chunks[-1].is_last = True
    
    return chunks


def chunk_by_fixed_size(
    content: str,
    chunk_size_chars: int = 8000,
    overlap_chars: int = 200,
) -> List[Chunk]:
    """
    Split content into fixed-size chunks.
    
    Tries to break at paragraph boundaries when possible.
    """
    chunks = []
    
    # Split into paragraphs first
    paragraphs = content.split('\n\n')
    
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para)
        
        # If adding this paragraph exceeds chunk size
        if current_size + para_size > chunk_size_chars and current_chunk:
            # Save current chunk
            text = '\n\n'.join(current_chunk)
            chunks.append(Chunk(
                number=len(chunks) + 1,
                title=f"Chunk {len(chunks) + 1}",
                content=text,
            ))
            
            # Start new chunk with overlap
            if overlap_chars > 0:
                # Take last portion of previous chunk as overlap
                overlap_text = text[-overlap_chars:]
                current_chunk = [overlap_text, para]
                current_size = len(overlap_text) + para_size
            else:
                current_chunk = [para]
                current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size
    
    # Save last chunk
    if current_chunk:
        text = '\n\n'.join(current_chunk)
        chunks.append(Chunk(
            number=len(chunks) + 1,
            title=f"Chunk {len(chunks) + 1}",
            content=text,
        ))
    
    # Mark last chunk
    if chunks:
        chunks[-1].is_last = True
    
    return chunks


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximately max_tokens."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    
    # Truncate at word boundary
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    
    return truncated + "\n\n[Content truncated...]"


def create_chunks(
    content: str,
    method: ChunkingMethod,
    fixed_chunk_size: int = 2000,
) -> List[Chunk]:
    """
    Create chunks based on the specified method.
    
    Args:
        content: Full article text
        method: Chunking method (SECTION or FIXED)
        fixed_chunk_size: Size in tokens for FIXED method
    
    Returns:
        List of Chunk objects
    """
    if method == ChunkingMethod.SECTION:
        return chunk_by_sections(content)
    elif method == ChunkingMethod.FIXED:
        # Convert tokens to chars (4 chars per token)
        chunk_size_chars = fixed_chunk_size * 4
        return chunk_by_fixed_size(content, chunk_size_chars)
    else:
        raise ValueError(f"Unknown chunking method: {method}")
