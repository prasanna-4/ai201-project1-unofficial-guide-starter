# Project 1 Planning: The Unofficial Guide

> Written before the pipeline code. Updated during implementation where my approach changed
> (see notes in the Chunking Strategy and Retrieval sections).

---

## Domain

**Student reviews of Computer Science professors at Brookfield University** (the core CS
course sequence: CS 101 Intro, CS 201 Data Structures, CS 310 Algorithms, CS 330 Databases,
CS 340 Operating Systems, CS 420 Machine Learning).

This knowledge is valuable because the official course catalog only lists prerequisites,
credit hours, and a sanitized topic list. It tells you *nothing* about what actually determines
whether you pass and learn: whether a professor's exams come from the slides or the textbook,
how heavy the real weekly workload is, whether the curve will save you, which order to take
courses in, and which professor to pick when a course has multiple sections. That information
only lives in student-to-student channels — Rate My Professors, department subreddits, Discord
servers, and course forums — and it is scattered, anonymous, and contradictory, which makes it
hard to search and hard to trust without reading dozens of posts. This system makes that
collective student knowledge searchable and answerable with citations.

> Note on the corpus: Brookfield University and these professors are fictional. The documents
> are representative samples I authored in the exact structural style of the real sources they
> imitate (RMP review blocks with rating headers, Reddit threads with nested comments, a Discord
> FAQ, course-forum threads, and an unofficial long-form guide), so that chunking, retrieval,
> and evaluation behave the way they would on scraped real-world data without publishing
> opinions about real, identifiable people.

---

## Documents

11 documents across five source *types* so coverage spans different formats and perspectives
(short opinionated reviews, crowd-ranked threads, Q&A, and long-form guidance).

| #  | Source | Description | Location |
|----|--------|-------------|----------|
| 1  | Rate My Professors | Reviews of Prof. Marsh (CS 201 Data Structures) | `documents/rmp_marsh_datastructures.txt` |
| 2  | Rate My Professors | Reviews of Prof. Okafor (CS 101 Intro) | `documents/rmp_okafor_intro.txt` |
| 3  | Rate My Professors | Reviews of Prof. Patel (CS 310 Algorithms) | `documents/rmp_patel_algorithms.txt` |
| 4  | Rate My Professors | Reviews of Prof. Lin (CS 340 Operating Systems) | `documents/rmp_lin_operatingsystems.txt` |
| 5  | Rate My Professors | Reviews of Prof. Becker (CS 330 Databases) | `documents/rmp_becker_databases.txt` |
| 6  | Rate My Professors | Reviews of Prof. Reyes (CS 420 Machine Learning) | `documents/rmp_reyes_machinelearning.txt` |
| 7  | Reddit (r/BrookfieldU) | Thread: which CS profs to take/avoid | `documents/reddit_which_cs_profs.txt` |
| 8  | Reddit (r/BrookfieldU) | Thread: easiest CS electives for GPA | `documents/reddit_easiest_cs_electives.txt` |
| 9  | Discord (#pinned-faq) | CS majors Discord FAQ export | `documents/discord_cs_major_faq.txt` |
| 10 | Course forum | CS 201 exam-prep advice thread | `documents/forum_cs201_exam_tips.txt` |
| 11 | Unofficial guide | Long-form CS major survival/sequencing guide | `documents/cs_major_survival_guide.txt` |

The mix is deliberate: the same fact (e.g., "Marsh's final is not curved") shows up in a short
review, a Discord answer, and a long guide, so I can see whether retrieval surfaces the best
phrasing. One topic — a second CS 201 section taught by Prof. Nguyen — appears in only a single
sentence, which I use as a deliberate sparse-coverage test (see Evaluation Plan Q5).

---

## Chunking Strategy

**Chunk size:** ~500 characters target, with a hard cap of 800.

**Overlap:** 100 characters.

**Reasoning:** The corpus is mixed-granularity. The RMP/Reddit/forum sources are made of short,
self-contained units — a single review or a single comment is one complete opinion, usually
2–6 sentences. The survival guide and FAQ are long-form. A naive fixed-character split would
slice a 3-sentence review in half (losing the "midterms curved, final NOT curved" contrast that
spans two sentences) and would merge unrelated reviews from different reviewers into one diluted
chunk.

So the strategy is **structure-aware splitting, then size-bounded packing:**
1. Split each document on its natural record boundary — the `---` separators between reviews and
   comments, and blank-line paragraph breaks in the long-form docs.
2. Pack consecutive small units together up to the ~500-char target so a single chunk holds one
   or a few complete, related thoughts (a whole short review, or a coherent paragraph).
3. If a single unit exceeds the 800-char cap (long guide paragraphs), fall back to a
   sentence-aware character split with 100-char overlap so a fact spanning a boundary is still
   recoverable from at least one chunk.

This keeps chunks "one complete thought" sized — large enough that a review is self-contained,
small enough that a specific query (e.g., "is the final curved?") matches the precise chunk
instead of a diluted wall of text.

> Updated during implementation: my first pass used a flat 500-char split with no structure
> awareness and it cut reviews mid-sentence (confirmed by the chunk-inspection step). I switched
> to record-boundary splitting + packing, which fixed it. Numbers above reflect the final code.

**Final chunk count:** recorded after running ingestion — see README (≈70 chunks across 11 docs).

---

## Retrieval Approach

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers`. It runs locally (no API key,
no rate limits), is fast on CPU, and its 384-dim embeddings are well-suited to the short,
opinion-style text that dominates this corpus.

**Top-k:** 5. Enough to pull the same fact from more than one source (which raises confidence and
gives the LLM corroboration), but not so many that loosely related professor reviews dilute the
context and pull the answer off-target. Tunable in `query.py`.

**Production tradeoff reflection:** If cost weren't a constraint and this served real students,
I'd weigh: (a) **accuracy on domain text** — a larger model like `bge-large` or an API model
(OpenAI `text-embedding-3-large`, Voyage) would better disambiguate near-duplicate professor
reviews and handle paraphrase/slang ("the prof drops your lowest quiz"); (b) **context length** —
MiniLM truncates at 256 tokens, fine for reviews but it silently clips a long guide paragraph,
so a longer-context embedder would preserve more signal per chunk; (c) **multilingual support** —
if the student body posts in multiple languages, a multilingual model (`bge-m3`,
`paraphrase-multilingual-MiniLM`) matters; (d) **latency & ops** — local MiniLM has zero network
latency and no vendor dependency, while an API model adds per-query cost, rate limits, and a
privacy question (sending student opinions to a third party). For this project the local model
wins on simplicity; for production I'd likely move to a stronger local model (`bge-base/large`)
to keep data in-house while improving disambiguation.

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | Are Professor Marsh's exams based on the textbook or the lecture slides? | The lecture slides, not the textbook; attendance is effectively mandatory. |
| 2 | Which CS professor is best for someone who has never programmed before? | Prof. Okafor (CS 101) — most patient/beginner-friendly, gentle pace. |
| 3 | Is the final exam in Professor Marsh's class curved? | No. Her midterms are curved but the final is NOT curved. |
| 4 | What should I take before Professor Reyes's Machine Learning class? | Linear algebra (and ideally statistics) — the math is the real prereq; no curve. |
| 5 | How does Professor Nguyen's section of Data Structures compare to Marsh's? | Intentionally hard: Nguyen is mentioned once ("supposedly more project-based, haven't taken it"). The honest answer is that there isn't enough info to compare — a good test of whether the system over-claims. |

Q1–Q4 have specific, checkable answers. Q5 is the designed failure/edge case (sparse coverage).

---

## Anticipated Challenges

1. **Contradiction and corroboration across sources.** The same professor is described in a
   terse RMP review, a Reddit comment, and a long guide. Retrieval might return five chunks that
   all say roughly the same thing (wasting the top-k budget) or, worse, return reviews for the
   *wrong* professor that share vocabulary ("exams," "curve," "office hours"). Mitigation:
   structure-aware chunks that keep the professor's name attached to the opinion, plus source
   metadata so I can see which document each chunk came from.

2. **Sparse-coverage / over-claiming.** Some entities (Prof. Nguyen's CS 201 section) appear in
   a single sentence. The risk is that retrieval returns Marsh-heavy chunks and the LLM
   confidently fabricates a Nguyen-vs-Marsh comparison from general knowledge. Mitigation: a
   strict grounding prompt that forces an "I don't have enough information" response when the
   retrieved context doesn't actually contain the answer. This is exactly what Q5 tests.

3. (Bonus risk) **Facts split across a chunk boundary.** "Midterms are curved" and "the final is
   NOT curved" can land in different sentences; if a boundary splits them, retrieval might surface
   only half. Mitigation: 100-char overlap + packing related sentences into one chunk.

---

## Architecture

```
                   THE UNOFFICIAL GUIDE — RAG PIPELINE

  [1] Document Ingestion          documents/*.txt
        |                         load raw text from disk, strip source
        |                         boilerplate / headers / HTML entities
        v                         (Python, ingest.py)
  [2] Chunking                    structure-aware split on review/comment
        |                         boundaries, pack to ~500 chars, 100 overlap
        |                         (Python, ingest.py: chunk_text)
        v
  [3] Embedding + Vector Store    embed each chunk -> 384-dim vector
        |                         store vectors + {source, chunk_index} metadata
        |                         (sentence-transformers all-MiniLM-L6-v2  ->  ChromaDB)
        v                         (build_index.py)
  [4] Retrieval                   embed user query, semantic top-k=5 search
        |                         return chunks + sources + distance scores
        |                         (ChromaDB query, query.py: retrieve)
        v
  [5] Generation                  stuff retrieved chunks into a strict grounding
        |                         prompt; LLM answers ONLY from context + cites
        v                         sources  (Groq llama-3.3-70b-versatile, query.py: ask)
   Answer + Source attribution    surfaced through a Gradio web UI (app.py)
```

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:** Give Claude the Documents table and Chunking Strategy
section above (the `---`/blank-line record structure of each source type, the ~500/100/800
parameters, and the "one complete thought per chunk" goal) and ask it to implement
`ingest.py` with `load_documents()`, `clean_text()`, and `chunk_text()`. Verify by printing
5 random chunks and the total count, checking each is self-contained and carries correct source
metadata. Override anything that does a naive flat split.

**Milestone 4 — Embedding and retrieval:** Give Claude the Retrieval Approach section + the
architecture diagram and ask it to implement `build_index.py` (embed chunks with
all-MiniLM-L6-v2, persist to ChromaDB with `source` + `chunk_index` metadata) and a `retrieve()`
function returning top-5 chunks with distances. Verify by running 3 eval queries and inspecting
distances (expect < 0.5 on good matches). Ask it to explain any ChromaDB API I don't recognize.

**Milestone 5 — Generation and interface:** Give Claude the grounding requirement (answer only
from retrieved context; say "I don't have enough information" otherwise; cite sources) and the
Gradio skeleton, and ask it to implement `ask()` in `query.py` (Groq `llama-3.3-70b-versatile`)
and `app.py`. Verify grounding by asking an out-of-corpus question and confirming the refusal;
verify attribution is appended programmatically from retrieval metadata, not invented by the LLM.
