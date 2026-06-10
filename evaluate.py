"""
Milestone 6 — Evaluation harness.

Runs the 5 evaluation questions from planning.md (plus one out-of-scope question to test the
refusal behavior) through the full RAG pipeline and prints a report: the question, the answer,
the cited sources, and the retrieved chunks with distances. Copy the output into README.md.

Run:  python evaluate.py
"""

from __future__ import annotations

from query import ask

EVAL_QUESTIONS = [
    "Are Professor Marsh's exams based on the textbook or the lecture slides?",
    "Which CS professor is best for someone who has never programmed before?",
    "Is the final exam in Professor Marsh's class curved?",
    "What should I take before Professor Reyes's Machine Learning class?",
    "How does Professor Nguyen's section of Data Structures compare to Marsh's?",
]

OUT_OF_SCOPE = "What are the best dorms for first-year students at Brookfield?"


def run_one(n: str, question: str) -> None:
    result = ask(question)
    print("=" * 88)
    print(f"[{n}] {question}\n")
    print(f"ANSWER:\n{result['answer']}\n")
    print("SOURCES: " + (", ".join(result["sources"]) if result["sources"] else "(none)"))
    print("\nRETRIEVED CHUNKS (distance | source :: chunk):")
    for c in result["chunks"]:
        preview = c.text.replace("\n", " ")[:95]
        print(f"  {c.distance:.3f} | {c.source} :: chunk_{c.chunk_index} | {preview}...")
    print()


if __name__ == "__main__":
    for i, q in enumerate(EVAL_QUESTIONS, 1):
        run_one(str(i), q)
    run_one("OUT-OF-SCOPE", OUT_OF_SCOPE)
