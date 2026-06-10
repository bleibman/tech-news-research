"""Interactive test script for LLM synthesis — Phase 4.

Usage (from pipeline/):
    python -m test_synthesis "what are the latest AI developments?"
    python -m test_synthesis --verbose "Apple WWDC announcements"
    python -m test_synthesis --abstain
    python -m test_synthesis --model meta-llama/Llama-3.1-8B-Instruct "query"
"""

from __future__ import annotations

import argparse
import sys

from src.synthesize import ask


ABSTAIN_QUERIES = [
    "What is the best recipe for chocolate chip cookies?",
    "Who won the 1987 World Series?",
    "How do I change a flat tire?",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test LLM synthesis with citation discipline (Phase 4)"
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Question to ask (omit if using --abstain)",
    )
    parser.add_argument(
        "--abstain",
        action="store_true",
        help="Run abstention test with out-of-corpus questions",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show retrieval details (similarity scores, titles)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override the synthesis model (e.g. meta-llama/Llama-3.1-8B-Instruct)",
    )
    args = parser.parse_args()

    if args.abstain:
        print("=" * 60)
        print("ABSTENTION TEST — out-of-corpus questions")
        print("The model should decline to answer these.")
        print("=" * 60)
        for q in ABSTAIN_QUERIES:
            print(f"\n{'─' * 60}")
            print(f"Q: {q}\n")
            answer = ask(q, model=args.model, verbose=args.verbose)
            print(f"\nA: {answer}")
        return

    query = " ".join(args.query)
    if not query:
        parser.print_help()
        sys.exit(1)

    print(f"Q: {query}\n")
    answer = ask(query, model=args.model, verbose=args.verbose)
    print(f"\n{'─' * 60}")
    print(f"A: {answer}")


if __name__ == "__main__":
    main()
