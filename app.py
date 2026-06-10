"""
Milestone 5 — Query interface (Gradio web UI).

Run:  python app.py     then open http://localhost:7860

Type a question about Brookfield CS professors; the app retrieves the most relevant chunks,
generates a grounded answer with Groq, and shows which source documents the answer drew from.
"""

from __future__ import annotations

import gradio as gr

from query import ask


def handle_query(question: str):
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", ""
    try:
        result = ask(question)
    except RuntimeError as exc:  # e.g. missing API key or unbuilt index
        return f"⚠️ {exc}", ""

    answer = result["answer"]
    if result["sources"]:
        sources = "\n".join(f"• {s}" for s in result["sources"])
    else:
        sources = "(no sources — the answer was not found in the documents)"
    return answer, sources


EXAMPLES = [
    "Are Professor Marsh's exams based on the textbook or the lecture slides?",
    "Which CS professor is best for someone who has never programmed before?",
    "Is the final exam in Professor Marsh's class curved?",
    "What should I take before Professor Reyes's Machine Learning class?",
    "Which class is the easiest A for boosting my GPA?",
]

with gr.Blocks(title="The Unofficial Guide — Brookfield CS") as demo:
    gr.Markdown(
        "# The Unofficial Guide — Brookfield CS Professors\n"
        "Ask what students actually say about CS professors and courses. "
        "Answers are grounded in collected student reviews, threads, and guides — "
        "with sources cited. If the documents don't cover it, the system says so."
    )
    with gr.Row():
        inp = gr.Textbox(
            label="Your question",
            placeholder="e.g. Is the final exam in Professor Marsh's class curved?",
            lines=2,
            scale=4,
        )
        btn = gr.Button("Ask", variant="primary", scale=1)
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from (sources)", lines=4)

    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()
