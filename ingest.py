"""
Milestone 3 — Document ingestion and chunking.

Loads the raw .txt documents from documents/, cleans light boilerplate, and splits each
document into self-contained chunks using a structure-aware strategy (see planning.md):

  1. Split on natural record boundaries: the "---" separators between RMP reviews / Reddit
     comments, and blank-line paragraph breaks in long-form docs.
  2. Pack consecutive small units up to a ~500-char target so a chunk holds one (or a few)
     complete, related thoughts.
  3. If a single unit exceeds the hard cap (800 chars), fall back to a sentence-aware split
     with overlap so a fact spanning a boundary is still recoverable.

Each chunk carries its source filename and position so attribution works downstream.

Run directly to inspect the output:  python ingest.py
"""

from __future__ import annotations

import html
import random
import re
from dataclasses import dataclass
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).parent / "documents"

TARGET_CHARS = 500   # aim to pack units up to roughly this size
MAX_CHARS = 800      # hard cap; oversized units get sentence-split
OVERLAP_CHARS = 100  # overlap when a single oversized unit must be split


@dataclass
class Chunk:
    text: str
    source: str        # filename, e.g. "rmp_marsh_datastructures.txt"
    chunk_index: int    # position of this chunk within its source document

    @property
    def id(self) -> str:
        return f"{self.source}::chunk_{self.chunk_index}"


def load_documents(documents_dir: Path = DOCUMENTS_DIR) -> dict[str, str]:
    """Load every .txt file in the documents directory as {filename: raw_text}."""
    docs: dict[str, str] = {}
    for path in sorted(documents_dir.glob("*.txt")):
        docs[path.name] = path.read_text(encoding="utf-8")
    if not docs:
        raise FileNotFoundError(f"No .txt documents found in {documents_dir}")
    return docs


def clean_text(text: str) -> str:
    """Light cleaning: unescape HTML entities, drop any stray tags, normalize whitespace.

    The corpus is already plain text, but this guards against artifacts (&amp;, &#39;, <div>)
    that show up when sources are copied from rendered web pages.
    """
    text = html.unescape(text)                 # &amp; -> &, &#39; -> '
    text = re.sub(r"<[^>]+>", "", text)        # strip any HTML tags
    # normalize smart punctuation to ASCII so downstream text/console stays clean
    for fancy, plain in {
        "—": "-", "–": "-", "’": "'", "‘": "'",
        "“": '"', "”": '"', "…": "...", " ": " ",
    }.items():
        text = text.replace(fancy, plain)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # collapse 3+ blank lines to a single blank line; trim trailing spaces per line
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_into_units(text: str) -> list[str]:
    """Split a cleaned document into natural record/paragraph units.

    Records are separated by a line of dashes ("---") in the review/thread sources; long-form
    docs fall back to blank-line paragraph boundaries.
    """
    # First split on horizontal-rule separators if present.
    if re.search(r"^\s*-{3,}\s*$", text, flags=re.MULTILINE):
        parts = re.split(r"^\s*-{3,}\s*$", text, flags=re.MULTILINE)
    else:
        parts = [text]

    units: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # within each record, paragraphs are the finer-grained unit
        for para in re.split(r"\n{2,}", part):
            para = para.strip()
            if para:
                units.append(para)
    return units


def _split_oversized(unit: str) -> list[str]:
    """Sentence-aware split with overlap for a single unit larger than MAX_CHARS."""
    sentences = re.split(r"(?<=[.!?])\s+", unit)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > MAX_CHARS:
            chunks.append(current.strip())
            # carry the tail of the previous chunk as overlap
            current = current[-OVERLAP_CHARS:] + " " + sentence
        else:
            current = f"{current} {sentence}".strip()
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_text(text: str) -> list[str]:
    """Turn one cleaned document into a list of chunk strings.

    Packs consecutive small units up to TARGET_CHARS; sentence-splits any oversized unit.
    """
    units = _split_into_units(text)
    chunks: list[str] = []
    current = ""

    for unit in units:
        if len(unit) > MAX_CHARS:
            # flush whatever we were packing, then split the big unit on its own
            if current.strip():
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_oversized(unit))
            continue

        if not current:
            current = unit
        elif len(current) + len(unit) + 2 <= TARGET_CHARS:
            current = f"{current}\n\n{unit}"
        else:
            chunks.append(current.strip())
            current = unit

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) > 0]


def build_chunks(documents_dir: Path = DOCUMENTS_DIR) -> list[Chunk]:
    """Full ingestion: load -> clean -> chunk every document, with source metadata attached."""
    docs = load_documents(documents_dir)
    all_chunks: list[Chunk] = []
    for source, raw in docs.items():
        cleaned = clean_text(raw)
        for i, piece in enumerate(chunk_text(cleaned)):
            all_chunks.append(Chunk(text=piece, source=source, chunk_index=i))
    return all_chunks


if __name__ == "__main__":
    chunks = build_chunks()
    per_doc: dict[str, int] = {}
    for c in chunks:
        per_doc[c.source] = per_doc.get(c.source, 0) + 1

    print(f"Loaded {len(per_doc)} documents -> {len(chunks)} total chunks\n")
    print("Chunks per document:")
    for src in sorted(per_doc):
        print(f"  {per_doc[src]:>3}  {src}")

    lengths = [len(c.text) for c in chunks]
    print(
        f"\nChunk length (chars): min={min(lengths)}  "
        f"avg={sum(lengths)//len(lengths)}  max={max(lengths)}"
    )

    print("\n--- 5 random chunks (inspection) ---")
    for c in random.Random(7).sample(chunks, 5):
        print(f"\n[{c.id}]  ({len(c.text)} chars)")
        print(c.text)
