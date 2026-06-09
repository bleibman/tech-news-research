"""Hand-test semantic retrieval — Phase 3.

Usage (from pipeline/):
    python -m test_retrieval "what are the latest AI developments?"

Embeds the query with the BGE instruction prefix, calls the match_chunks RPC,
and prints the top results with similarity scores and source info.
"""

from __future__ import annotations

import sys

from src.db import search_chunks
from src.embed import embed_query


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m test_retrieval <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"Query: {query}\n")

    print("Embedding query...", flush=True)
    qvec = embed_query(query)

    print("Searching chunks...\n", flush=True)
    results = search_chunks(qvec, top_k=10)

    if not results:
        print("No results found. Have you run the embedding pass yet?")
        return

    for i, row in enumerate(results, 1):
        sim = row.get("similarity", 0)
        text_preview = (row.get("chunk_text") or "")[:200]
        print(f"--- Result {i} (similarity: {sim:.4f}) ---")
        print(f"  article_id: {row.get('article_id')}")
        print(f"  chunk_index: {row.get('chunk_index')}")
        print(f"  {text_preview}...")
        print()


if __name__ == "__main__":
    main()
