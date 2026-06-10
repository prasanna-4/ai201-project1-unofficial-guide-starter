# The Unofficial Guide — Project 1

A Retrieval-Augmented Generation (RAG) system that makes student-generated knowledge about
Computer Science professors searchable and answerable, with grounded, cited responses.

## Quick start

```bash
python -m venv .venv
source .venv/Scripts/activate          # Windows (Git Bash);  .venv\Scripts\activate on cmd
pip install -r requirements.txt
cp .env.example .env                   # then paste your free Groq key from console.groq.com
python build_index.py                  # ingest -> chunk -> embed -> store in ChromaDB
python app.py                          # launch the web UI at http://localhost:7860
# or, headless:
python query.py "Is the final in Professor Marsh's class curved?"
python evaluate.py                     # run the 5 eval questions + an out-of-scope question
```

**Pipeline:** `documents/*.txt` → `ingest.py` (clean + chunk) → `build_index.py`
(all-MiniLM-L6-v2 embeddings → ChromaDB) → `query.py` (top-5 retrieval → Groq grounded
generation) → `app.py` (Gradio UI). Full architecture diagram is in
[planning.md](planning.md#architecture).

---

## Domain

**Student reviews of Computer Science professors at Brookfield University** — the core CS
sequence (CS 101 Intro, CS 201 Data Structures, CS 310 Algorithms, CS 330 Databases, CS 340
Operating Systems, CS 420 Machine Learning).

The official course catalog lists prerequisites, credit hours, and a sanitized topic list. It
tells you nothing about what actually determines whether you pass and learn: whether a
professor's exams come from the slides or the textbook, how heavy the real weekly workload is,
whether the curve will save you, and which order to take courses in. That knowledge only lives
in student-to-student channels — Rate My Professors, department subreddits, Discord servers,
course forums — where it is scattered, anonymous, and contradictory, which makes it hard to
search and hard to trust without reading dozens of posts. This system consolidates that
collective knowledge into grounded, cited answers.

> **Note on the corpus:** Brookfield University and these professors are fictional. The
> documents are representative samples authored in the exact structural style of the real
> sources they imitate (RMP review blocks, Reddit threads with nested comments, a Discord FAQ,
> course-forum threads, and a long-form guide), so chunking, retrieval, and evaluation behave
> as they would on scraped real-world data — without publishing opinions about real,
> identifiable people. Swapping in real scraped `.txt` files requires no code changes.

---

## Document Sources

11 documents across five source *types*, chosen so coverage spans different formats and
perspectives (short opinionated reviews, crowd-ranked threads, Q&A, and long-form guidance).

| #  | Source | Type | URL or file path |
|----|--------|------|-----------------|
| 1  | Rate My Professors — Prof. Marsh (CS 201 Data Structures) | Reviews | `documents/rmp_marsh_datastructures.txt` |
| 2  | Rate My Professors — Prof. Okafor (CS 101 Intro) | Reviews | `documents/rmp_okafor_intro.txt` |
| 3  | Rate My Professors — Prof. Patel (CS 310 Algorithms) | Reviews | `documents/rmp_patel_algorithms.txt` |
| 4  | Rate My Professors — Prof. Lin (CS 340 Operating Systems) | Reviews | `documents/rmp_lin_operatingsystems.txt` |
| 5  | Rate My Professors — Prof. Becker (CS 330 Databases) | Reviews | `documents/rmp_becker_databases.txt` |
| 6  | Rate My Professors — Prof. Reyes (CS 420 Machine Learning) | Reviews | `documents/rmp_reyes_machinelearning.txt` |
| 7  | r/BrookfieldU — "Which CS profs to take/avoid" | Forum thread | `documents/reddit_which_cs_profs.txt` |
| 8  | r/BrookfieldU — "Easiest CS electives for GPA" | Forum thread | `documents/reddit_easiest_cs_electives.txt` |
| 9  | Brookfield CS Discord — #pinned-faq export | Q&A / FAQ | `documents/discord_cs_major_faq.txt` |
| 10 | CS course forum — "CS 201 (Marsh) exam prep" | Forum thread | `documents/forum_cs201_exam_tips.txt` |
| 11 | Unofficial CS Major Survival Guide | Long-form guide | `documents/cs_major_survival_guide.txt` |

**Ingestion pipeline** ([ingest.py](ingest.py)): `load_documents()` reads every `.txt` from
`documents/`; `clean_text()` unescapes HTML entities (`&amp;`, `&#39;`), strips any HTML tags,
normalizes smart punctuation (em-dashes/curly quotes) to ASCII, and collapses excess whitespace;
the cleaned text is then passed to chunking. The corpus is plain text, so cleaning is light by
design — but the HTML/entity handling is in place so real scraped pages can be dropped in
without code changes.

---

## Chunking Strategy

**Chunk size:** ~500 characters target, hard cap 800.
**Overlap:** 100 characters (only applied when an oversized unit must be split).
**Final chunk count:** **53 chunks** across 11 documents (avg 333 chars, range 208–687).

**Why these choices fit the documents.** The corpus is mixed-granularity. The RMP / Reddit /
forum sources are made of short, self-contained units — a single review or comment is one
complete opinion (2–6 sentences). The survival guide and FAQ are long-form. A naive fixed
500-char split would slice a 3-sentence review in half (losing the "midterms curved, final NOT
curved" contrast that spans two sentences) and would merge unrelated reviews from *different*
reviewers into one diluted chunk.

So the strategy is **structure-aware splitting, then size-bounded packing** (`chunk_text()` in
[ingest.py](ingest.py)):

1. Split each document on its natural record boundary — the `---` separators between reviews /
   comments, and blank-line paragraph breaks in long-form docs.
2. Pack consecutive small units up to the ~500-char target, so a chunk holds one (or a few)
   complete, related thoughts.
3. If a single unit exceeds the 800-char cap (long guide paragraphs), fall back to a
   sentence-aware split with 100-char overlap so a fact spanning a boundary stays recoverable.

This keeps chunks "one complete thought" sized: big enough that a review is self-contained,
small enough that a specific query (e.g., "is the final curved?") matches the precise chunk
instead of a diluted wall of text. 53 chunks sits in the healthy range (>50, well under 2,000).

> **Divergence from first plan:** my first pass used a flat 500-char split with no structure
> awareness; the chunk-inspection step showed it cutting reviews mid-sentence, so I switched to
> record-boundary splitting + packing. `planning.md` was updated to match.

### Sample chunks (5, each labeled with its source)

**1 — `rmp_marsh_datastructures.txt :: chunk_1`** (382 chars)
```
Review 1  (CS 201, Fall)  Quality 5 / 5  Difficulty 4 / 5
Professor Marsh is tough but completely fair. Every exam question comes straight from
the lecture slides, NOT the textbook, so if you go to class and actually take notes you
will be fine. The weekly problem sets are no joke though - budget 8 to 10 hours each.
Attendance matters way more than the readings. Would take again.
```

**2 — `forum_cs201_exam_tips.txt :: chunk_3`** (327 chars)
```
REPLY 4:
One trap: people assume the final is curved like the midterms. It is NOT. Plan your end-of-
semester effort accordingly - you can't bank on a final curve to save your grade.

REPLY 5:
Practice implementing a hash table and a balanced BST from scratch on paper, timed. That's the
kind of thing that shows up. Good luck!
```

**3 — `rmp_okafor_intro.txt :: chunk_1`** (313 chars)
```
Review 1  (CS 101, Fall)  Quality 5 / 5  Difficulty 2 / 5
If you have NEVER written a line of code in your life, take Okafor. He explains everything
from absolute zero and never makes you feel stupid for asking. Perfect for complete beginners.
The pace is gentle and he holds extra office hours before every exam.
```

**4 — `discord_cs_major_faq.txt :: chunk_3`** (438 chars)
```
Q: I need an easy class to balance my schedule. Suggestions?
A: Becker's CS 330 Databases. Open-note exams, light homework, basically a guaranteed good
grade. Just know you won't go deep on database internals.

Q: What do I need before Reyes's Machine Learning (CS 420)?
A: Linear algebra, full stop. The official prereq is CS 310, but the math is what trips people
up. There is no curve in her class, so no safety net - earn every point.
```

**5 — `reddit_which_cs_profs.txt :: chunk_1`** (687 chars — the largest packed chunk)
```
TOP COMMENT  (u/seniorcsmajor, 142 upvotes)
For the core:
- CS 201 Data Structures: Marsh is the standard pick. Hard but you learn the most. Exams are
  all from her slides, attendance is basically mandatory. There's also a spring section taught
  by Professor Nguyen - supposedly more project-based, but I haven't taken it so I can't say.
- CS 310 Algorithms: Patel is hit or miss. Genius, terrible lecturer, exams way harder than HW.
  You'll be teaching yourself from CLRS. Only take it once you're good at proofs.
- CS 340 OS: Lin. It's the hardest class in the major, 15+ hours/week of C projects, but
  everyone says it's the most worth it. Don't pair it with another heavy course.
```
Each is readable and self-contained — you could answer a question from any one alone.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim embeddings, cosine
similarity in ChromaDB). It runs locally with no API key and no rate limits, is fast on CPU,
and is well-matched to the short, opinion-style text that dominates this corpus.

**Production tradeoff reflection.** If cost weren't a constraint and this served real students,
I'd weigh:
- **Accuracy on domain text** — a larger model (`bge-large`) or an API model (OpenAI
  `text-embedding-3-large`, Voyage) would better disambiguate near-duplicate professor reviews
  and handle paraphrase/slang ("drops your lowest quiz").
- **Context length** — MiniLM truncates at 256 tokens; fine for reviews, but it silently clips
  a long guide paragraph, so a longer-context embedder preserves more signal per chunk.
- **Multilingual support** — if students post in multiple languages, a multilingual model
  (`bge-m3`, `paraphrase-multilingual-MiniLM`) matters.
- **Latency & operations** — local MiniLM has zero network latency, no per-query cost, and no
  privacy question; an API model adds cost, rate limits, and the issue of sending student
  opinions to a third party.

For this project the local model wins on simplicity. For production I'd likely move to a
stronger *local* model (`bge-base`/`bge-large`) to keep data in-house while improving
disambiguation.

---

## Retrieval Test Results

Top-k = 5, cosine distance (lower = more similar). Retrieval is testable without the LLM via
`python query.py` (no API key needed). Distances on the top results are in the 0.37–0.50 range.

**Query A — "Are Professor Marsh's exams from the slides or the textbook?"**
```
0.396 | rmp_marsh_datastructures.txt :: chunk_1 | "...Every exam question comes straight from the lecture slides, NOT the textbook..."
0.450 | rmp_marsh_datastructures.txt :: chunk_3 | "...If you skip lecture you will fail. Exams are basically did you attend..."
0.457 | forum_cs201_exam_tips.txt     :: chunk_1 | "...her exams are 100% from the lecture slides, not the textbook..."
0.473 | cs_major_survival_guide.txt   :: chunk_2 | "...Marsh's exams come entirely from her lecture slides..."
0.481 | rmp_okafor_intro.txt          :: chunk_2 | (Okafor review — weakest of the 5, off-professor)
```
**Why these are relevant:** the top 4 chunks all directly state that Marsh's exams come from the
lecture slides rather than the textbook, and they come from three *different* sources (an RMP
review, the course forum, and the survival guide), which corroborates the fact rather than
echoing a single post. The 5th (Okafor) is a weaker, off-professor match at the highest
distance — expected noise at k=5.

**Query B — "What should I take before Reyes's machine learning class?"**
```
0.374 | discord_cs_major_faq.txt          :: chunk_3 | "...What do I need before Reyes's ML? Linear algebra, full stop..."
0.416 | rmp_reyes_machinelearning.txt      :: chunk_1 | "...Do NOT take Reyes until you have finished linear algebra..."
0.488 | reddit_easiest_cs_electives.txt    :: chunk_3 | "...Avoid Lin or Reyes if you're trying to coast..."
0.495 | reddit_which_cs_profs.txt          :: chunk_2 | "...Machine Learning with Reyes... DO YOUR LINEAR ALGEBRA FIRST..."
0.509 | cs_major_survival_guide.txt        :: chunk_4 | "...only attempt it after you've completed linear algebra and statistics..."
```
**Why these are relevant:** four of the five chunks explicitly name *linear algebra* as the real
prerequisite for Reyes's ML course, drawn from the Discord FAQ, an RMP review, a Reddit thread,
and the survival guide. The convergence of independent sources on the same answer is exactly
what good retrieval should surface.

**Query C — "Which professor is best for someone who has never programmed?"**
```
0.464 | discord_cs_major_faq.txt     :: chunk_0 | "...I've never programmed before. What's my first class? CS 101 with Okafor..."
0.495 | rmp_okafor_intro.txt         :: chunk_0 | (Okafor RMP header — 96% would take again, difficulty 2.1)
0.522 | rmp_reyes_machinelearning.txt :: chunk_0 | (Reyes header — weaker match)
0.529 | reddit_which_cs_profs.txt    :: chunk_0 | (thread intro)
0.533 | rmp_patel_algorithms.txt     :: chunk_0 | (Patel header — weaker match)
```
The top two chunks correctly point to Okafor / CS 101 for absolute beginners.

---

## Grounded Generation

**System prompt grounding instruction** (verbatim from `SYSTEM_PROMPT` in [query.py](query.py)):

> *Answer ONLY using the numbered context passages provided in the user message. Do NOT use any
> outside or prior knowledge about these professors, courses, or universities. If the context
> does not clearly contain the answer, you MUST reply with exactly this sentence and nothing
> else: "I don't have enough information in the collected documents to answer that." Do not
> guess, infer beyond the text, or fill gaps with general assumptions...*

**Structural choices that enforce grounding (not just the prompt):**
- **Numbered, source-tagged context.** Retrieved chunks are formatted as `[Passage N | source:
  filename]` blocks, so the model sees exactly what it is allowed to use and where each claim
  comes from.
- **`temperature=0.0`** for deterministic, conservative answers.
- **Programmatic source attribution.** Sources are computed in code from the retrieval metadata
  (`Retrieved.source`), *not* trusted to the LLM. The `ask()` function appends the deduplicated
  source filenames after generation, so attribution can't be hallucinated.
- **Refusal detection.** If the model returns the mandated refusal sentence, `ask()` attaches
  *no* sources — because nothing was actually used — keeping the UI honest.

**How source attribution is surfaced:** every answer in the Gradio UI shows a separate
"Retrieved from (sources)" box listing the document filenames the chunks came from; the CLI and
evaluation harness print a `SOURCES:` line.

---

## Query Interface

A **Gradio web UI** ([app.py](app.py), `python app.py` → http://localhost:7860).

- **Input field:** "Your question" (multi-line textbox; submit with the button or Enter). Five
  example questions are provided as clickable chips.
- **Output fields:** (1) "Answer" — the grounded response; (2) "Retrieved from (sources)" — the
  list of source documents the answer drew from, or a note that nothing was found.

**Sample interaction transcript:**

```
Your question:  Is the final exam in Professor Marsh's class curved?

Answer:
According to Passage 2, the final exam in Professor Marsh's class is NOT curved. This is
also confirmed by Passage 3 and Passage 4, which both state that the final is not curved,
unlike the midterms.

Retrieved from (sources):
• rmp_marsh_datastructures.txt
• discord_cs_major_faq.txt
• forum_cs201_exam_tips.txt
• rmp_okafor_intro.txt
```

---

## Evaluation Report

Run with `python evaluate.py`. The 5 planned questions plus one out-of-scope question.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Are Prof. Marsh's exams based on the textbook or lecture slides? | Lecture slides, not textbook; attendance effectively mandatory | "Exams come straight from the lecture slides, not the textbook," citing 4 corroborating passages | Relevant (4/5 on-topic) | Accurate |
| 2 | Which CS professor is best for someone who has never programmed? | Prof. Okafor (CS 101) — most patient/beginner-friendly | "Take David Okafor for CS 101… gentle and beginner-friendly," notes 4.8/5 rating | Relevant | Accurate |
| 3 | Is the final exam in Prof. Marsh's class curved? | No — midterms curved, final NOT curved | "The final exam is NOT curved… unlike the midterms," citing 3 passages | Relevant | Accurate |
| 4 | What should I take before Prof. Reyes's ML class? | Linear algebra (and statistics); no curve | "You should have finished linear algebra first… official prereq is CS 310 but linear algebra is the key" | Relevant | Accurate |
| 5 | How does Prof. Nguyen's section of Data Structures compare to Marsh's? | Not enough info — Nguyen appears in one passing sentence | "I don't have enough information in the collected documents to answer that." (refusal) | Off-target (zero Nguyen content retrieved) | Accurate refusal — but the user's question goes unanswered (see Failure Case) |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

Summary: 4/5 answered accurately with grounded citations; Q5 correctly refused rather than
fabricating a comparison. The out-of-scope control question ("best dorms for first-years") also
correctly returned the refusal with no sources — confirming grounding holds outside the domain.

### Example responses (with source attribution)

**Example 1 — grounded answer with attribution** (Q4)
```
Q: What should I take before Professor Reyes's Machine Learning class?

A: To take Professor Reyes's Machine Learning class (CS 420), you should have finished
   linear algebra first. This is stated in Passage 1, Passage 2, and Passage 4, which all
   agree on the importance of linear algebra as a prerequisite for success in the class.
   The official prerequisite is CS 310, but the passages emphasize that linear algebra is
   the key to not getting lost in the class, especially in the first two weeks.

SOURCES: discord_cs_major_faq.txt, rmp_reyes_machinelearning.txt, reddit_which_cs_profs.txt,
         reddit_easiest_cs_electives.txt
```

**Example 2 — grounded answer with attribution** (Q3)
```
Q: Is the final exam in Professor Marsh's class curved?

A: According to Passage 2, the final exam in Professor Marsh's class is NOT curved. This is
   also confirmed by Passage 3 and Passage 4, which both state that the final is not curved,
   unlike the midterms.

SOURCES: rmp_marsh_datastructures.txt, discord_cs_major_faq.txt, forum_cs201_exam_tips.txt,
         rmp_okafor_intro.txt
```

**Example 3 — out-of-scope query, correct refusal (no sources attached)**
```
Q: What are the best dorms for first-year students at Brookfield?

A: I don't have enough information in the collected documents to answer that.

SOURCES: (none)
```
The dorm question is in-universe (Brookfield) but outside the corpus's domain (CS professors);
the system declines instead of fabricating a plausible answer from general knowledge.

---

## Failure Case Analysis

I'll document two honest failures: one a genuine pipeline flaw (over-attribution), one a
coverage limitation (Q5).

### Failure 1 — Over-attribution: a source is cited that the answer never used

**Where it failed:** Q1 — "Are Professor Marsh's exams based on the textbook or the lecture
slides?"

**What the system returned:** the *answer* was correct and explicitly grounded in Passages
1, 2, 3, and 5. But the **SOURCES line listed `rmp_okafor_intro.txt`** — which was Passage 4,
a retrieved-but-unused chunk (an Okafor review at distance 0.536). The LLM never referenced it;
it appeared in the attribution anyway. (Q2 and Q4 show the same pattern.)

**Root cause (tied to a specific pipeline stage):** the **attribution stage** in `ask()`
([query.py](query.py)). Sources are computed as the deduplicated filenames of *all top-k
retrieved chunks*, on the assumption that every retrieved chunk informs the answer. At k=5 that
assumption breaks: the 4th–5th chunks are often weak, off-professor matches (distance > 0.5)
that the LLM correctly ignores, but they still get listed as sources. So the citation overstates
what the answer actually drew from.

**What I would change to fix it:** parse the `Passage N` references the model produces and map
only the *cited* passages back to their source files; or, more robustly, drop chunks above a
distance threshold (e.g. 0.5) from the attribution set so weak retrievals can't be cited. The
cleanest version combines both — attribute only chunks that are both retrieved-strong *and*
referenced in the generated text.

### Failure 2 — Coverage gap: the system can't answer a reasonable comparison (Q5)

**Question:** "How does Professor Nguyen's section of Data Structures compare to Marsh's?"

**What the system returned:** the refusal — *"I don't have enough information in the collected
documents to answer that."* This is the *correct* behavior, but from the user's perspective a
legitimate question went unanswered.

**Root cause (tied to a specific pipeline stage):** a **coverage gap that surfaces at
retrieval**. Professor Nguyen appears in exactly one sentence in the entire corpus
(`reddit_which_cs_profs.txt :: chunk_1`: *"a spring section taught by Professor Nguyen —
supposedly more project-based, but I haven't taken it so I can't say"*). That single mention was
not even strong enough to enter the top-5 — retrieval returned only Marsh-heavy chunks (closest
distance 0.545, all noticeably weaker than the 0.37–0.45 seen on well-covered questions). A
comparison needs balanced evidence on *both* sides; the vector store has substantive content for
only one, and semantic search cannot surface information that was never collected.

**What I would change to fix it:** (1) **collect more documents** about Nguyen's section — the
real fix, since this is a data gap, not an algorithm bug; (2) add an **entity-coverage check**
so a query naming "Nguyen" requires at least one retrieved chunk that actually mentions Nguyen
before the LLM attempts a comparison — turning a silent refusal into a precise "I have notes on
Marsh but nothing substantive on Nguyen" response.

---

## Spec Reflection

**One way the spec helped me during implementation.** Writing the Chunking Strategy section of
`planning.md` *before* coding forced me to look at the actual document structure first, and that
is the reason I caught the mid-sentence-splitting problem early. Because I had already written
down that reviews are "self-contained 2–6 sentence units separated by `---`," the chunk-
inspection step had a concrete expectation to check against — when the flat splitter produced
fragments, I immediately knew it violated the spec and what to change, instead of shipping bad
chunks and discovering it as mysterious retrieval failures two milestones later.

**One way my implementation diverged from the spec, and why.** My planning.md initially implied
a straightforward fixed-size character split. In practice I had to make the chunker
*structure-aware* (split on record boundaries, then pack to a size target, with a sentence-aware
fallback only for oversized units). The divergence happened because the corpus is
mixed-granularity — tiny reviews next to long guide paragraphs — and a single fixed size can't
serve both without either fragmenting reviews or diluting them. I updated the Chunking Strategy
section of planning.md to record the change and the reason.

---

## AI Usage

**Instance 1 — Structure-aware chunker**
- *What I gave the AI:* my planning.md Documents table and Chunking Strategy section,
  specifically the description of the `---`/blank-line record structure of each source type and
  the ~500/100/800 character parameters, with the goal "one complete thought per chunk."
- *What it produced:* a `chunk_text()` that did a flat fixed-character split with overlap.
- *What I changed or overrode:* that version cut reviews mid-sentence (caught in the chunk
  inspection step). I redirected it to split on record boundaries first, then *pack* small units
  up to a size target, and only sentence-split units exceeding the hard cap. I also added the
  punctuation-normalization step in `clean_text()` after seeing em-dashes render as `�` in the
  Windows console. planning.md was updated to match.

**Instance 2 — Grounded generation prompt and attribution**
- *What I gave the AI:* my grounding requirement (answer only from retrieved context; emit an
  exact refusal sentence otherwise; cite sources) and the Gradio skeleton.
- *What it produced:* a working `ask()` that passed chunks to the LLM and asked it to cite
  sources in its prose.
- *What I changed or overrode:* letting the LLM cite sources in prose meant attribution could be
  hallucinated or omitted. I changed it so **sources are computed in code from retrieval
  metadata** and appended programmatically, added `temperature=0.0`, formatted context as
  numbered `[Passage N | source: ...]` blocks, and added refusal-detection so a refusal attaches
  no sources. This makes attribution a guarantee of the pipeline rather than a request to the
  model.
```
