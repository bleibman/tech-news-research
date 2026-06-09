"""Token-aware text chunking for embedding — Phase 3.

Splits article body text into chunks that fit within the BGE model's 512-token
context window (with a configurable ceiling, default 480). Splitting strategy:

1. Paragraph boundaries (double newlines)
2. Sentence boundaries (period/question/exclamation followed by space)
3. Word boundaries (last resort)

Adjacent chunks overlap by ~60 tokens to preserve cross-boundary context.
Articles shorter than CHUNK_MIN_TOKENS become a single chunk with no splitting.
"""

from __future__ import annotations

import re

from .config import CHUNK_MAX_TOKENS, CHUNK_OVERLAP_TOKENS, CHUNK_MIN_TOKENS

# Sentence-ending punctuation followed by whitespace.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, tokenizer) -> list[tuple[int, str]]:
    """Split *text* into (chunk_index, chunk_text) tuples.

    *tokenizer* must support ``tokenizer.encode(text)`` returning a list of
    token IDs (any HuggingFace tokenizer works).
    """
    text = text.strip()
    if not text:
        return []

    token_ids = tokenizer.encode(text, add_special_tokens=False)
    if len(token_ids) <= CHUNK_MIN_TOKENS:
        return [(0, text)]

    # --- split into paragraphs, then sentences ---
    paragraphs = re.split(r"\n{2,}", text)
    # Flatten paragraphs into sentences, keeping paragraph breaks as context.
    segments: list[str] = []
    for para in paragraphs:
        sentences = _SENTENCE_RE.split(para.strip())
        segments.extend(s.strip() for s in sentences if s.strip())

    # --- greedy merge: accumulate segments until we hit the token ceiling ---
    chunks: list[tuple[int, str]] = []
    current_segments: list[str] = []
    current_tokens = 0
    idx = 0  # position in segments list

    while idx < len(segments):
        seg = segments[idx]
        seg_tokens = len(tokenizer.encode(seg, add_special_tokens=False))

        # If a single segment exceeds the max, split it by words.
        if seg_tokens > CHUNK_MAX_TOKENS:
            # Flush anything accumulated so far.
            if current_segments:
                chunks.append((len(chunks), " ".join(current_segments)))
                current_segments = []
                current_tokens = 0

            word_chunks = _split_long_segment(seg, tokenizer)
            for wc in word_chunks:
                chunks.append((len(chunks), wc))
            idx += 1
            continue

        # Would adding this segment exceed the ceiling?
        if current_tokens + seg_tokens > CHUNK_MAX_TOKENS and current_segments:
            chunks.append((len(chunks), " ".join(current_segments)))
            # Overlap: rewind to include trailing segments that fit within
            # the overlap budget.
            overlap_segs, overlap_tokens = _build_overlap(
                current_segments, tokenizer
            )
            # If overlap + this segment still exceeds the ceiling, drop
            # overlap entirely so we don't loop forever on the same segment.
            if overlap_tokens + seg_tokens > CHUNK_MAX_TOKENS:
                current_segments = []
                current_tokens = 0
            else:
                current_segments = overlap_segs
                current_tokens = overlap_tokens
        else:
            current_segments.append(seg)
            current_tokens += seg_tokens
            idx += 1

    # Flush remainder.
    if current_segments:
        chunks.append((len(chunks), " ".join(current_segments)))

    return chunks


def _build_overlap(
    prev_segments: list[str], tokenizer
) -> tuple[list[str], int]:
    """Return trailing segments from *prev_segments* that fit within the
    overlap budget, to seed the next chunk for continuity."""
    overlap_segs: list[str] = []
    overlap_tokens = 0
    for seg in reversed(prev_segments):
        seg_tok = len(tokenizer.encode(seg, add_special_tokens=False))
        if overlap_tokens + seg_tok > CHUNK_OVERLAP_TOKENS:
            break
        overlap_segs.insert(0, seg)
        overlap_tokens += seg_tok
    return overlap_segs, overlap_tokens


def _split_long_segment(segment: str, tokenizer) -> list[str]:
    """Split a single oversized segment by word boundaries."""
    words = segment.split()
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for word in words:
        word_tokens = len(tokenizer.encode(word, add_special_tokens=False))
        if current_tokens + word_tokens > CHUNK_MAX_TOKENS and current:
            chunks.append(" ".join(current))
            # Keep overlap words.
            current, current_tokens = _word_overlap(current, tokenizer)
        current.append(word)
        current_tokens += word_tokens

    if current:
        chunks.append(" ".join(current))
    return chunks


def _word_overlap(
    words: list[str], tokenizer
) -> tuple[list[str], int]:
    """Return trailing words from *words* that fit within the overlap budget."""
    overlap: list[str] = []
    overlap_tokens = 0
    for w in reversed(words):
        w_tok = len(tokenizer.encode(w, add_special_tokens=False))
        if overlap_tokens + w_tok > CHUNK_OVERLAP_TOKENS:
            break
        overlap.insert(0, w)
        overlap_tokens += w_tok
    return overlap, overlap_tokens
