"""
Milestone 4 (part 2) + Milestone 5 — Retrieval and grounded generation.

  retrieve(question, k)  -> top-k chunks from ChromaDB with source + cosine distance
  ask(question, k)       -> grounded answer from Groq's LLM, using ONLY the retrieved chunks,
                            with source attribution appended programmatically from metadata.

Grounding is enforced two ways (see README):
  1. A strict system prompt that forbids outside knowledge and mandates the exact refusal
     string when the context is insufficient.
  2. Source attribution is built from retrieval metadata in code, not trusted to the LLM.

Run directly to test retrieval + generation from the command line:
    python query.py "Are Professor Marsh's exams from the slides or the textbook?"
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

from build_index import get_collection, get_model

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
TOP_K = 5
# distance above this = weak match; used only to inform the LLM, not to hard-filter
WEAK_MATCH_DISTANCE = 0.6

REFUSAL = "I don't have enough information in the collected documents to answer that."

SYSTEM_PROMPT = """You are The Unofficial Guide, a question-answering assistant for student \
reviews of Computer Science professors at Brookfield University.

STRICT GROUNDING RULES:
- Answer ONLY using the numbered context passages provided in the user message.
- Do NOT use any outside or prior knowledge about these professors, courses, or universities.
- If the context does not clearly contain the answer, you MUST reply with exactly this sentence \
and nothing else: "{refusal}"
- Do not guess, infer beyond the text, or fill gaps with general assumptions. If the context \
only mentions something in passing without enough detail to answer, treat it as insufficient \
and refuse.
- When you do answer, base every claim on the passages and keep it concise (2-5 sentences). \
You may note when sources agree or disagree.
- Do not invent source names; the system appends sources separately.""".format(refusal=REFUSAL)


@dataclass
class Retrieved:
    text: str
    source: str
    chunk_index: int
    distance: float


def retrieve(question: str, k: int = TOP_K) -> list[Retrieved]:
    """Embed the question and return the top-k most similar chunks from ChromaDB."""
    model = get_model()
    collection = get_collection()
    query_embedding = model.encode([question], normalize_embeddings=True)[0].tolist()

    res = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    out: list[Retrieved] = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        out.append(
            Retrieved(
                text=doc,
                source=str(meta["source"]),
                chunk_index=int(meta["chunk_index"]),
                distance=float(dist),
            )
        )
    return out


def _format_context(chunks: list[Retrieved]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[Passage {i} | source: {c.source}]\n{c.text}")
    return "\n\n".join(blocks)


def _get_groq_client():
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com"
        )
    return Groq(api_key=api_key)


def ask(question: str, k: int = TOP_K) -> dict:
    """Full RAG: retrieve -> grounded generation. Returns answer, sources, and the chunks used."""
    chunks = retrieve(question, k=k)

    client = _get_groq_client()
    user_msg = (
        f"Context passages:\n\n{_format_context(chunks)}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the passages above, following the grounding rules."
    )
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,  # deterministic, factual answers
    )
    answer = completion.choices[0].message.content.strip()

    # Source attribution is computed from retrieval metadata, not trusted to the LLM.
    # If the model refused, we don't attach sources (nothing was actually used).
    if answer.strip().rstrip(".") == REFUSAL.rstrip("."):
        sources: list[str] = []
    else:
        seen: list[str] = []
        for c in chunks:
            if c.source not in seen:
                seen.append(c.source)
        sources = seen

    return {"answer": answer, "sources": sources, "chunks": chunks}


def _print_result(question: str, result: dict) -> None:
    print(f"\nQ: {question}\n")
    print(f"A: {result['answer']}\n")
    if result["sources"]:
        print("Sources:")
        for s in result["sources"]:
            print(f"  - {s}")
    print("\nRetrieved chunks (distance | source):")
    for c in result["chunks"]:
        preview = c.text.replace("\n", " ")[:90]
        print(f"  {c.distance:.3f} | {c.source} :: chunk_{c.chunk_index} | {preview}...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        _print_result(q, ask(q))
    else:
        # No question given: just demo retrieval (no API key required) for 3 queries.
        demo_qs = [
            "Are Professor Marsh's exams from the slides or the textbook?",
            "Which professor is best for someone who has never programmed?",
            "What should I take before Reyes's machine learning class?",
        ]
        for q in demo_qs:
            print(f"\nQ: {q}")
            for c in retrieve(q):
                preview = c.text.replace("\n", " ")[:80]
                print(f"  {c.distance:.3f} | {c.source} :: chunk_{c.chunk_index} | {preview}...")
