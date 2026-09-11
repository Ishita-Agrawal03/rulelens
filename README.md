# RuleLens

RuleLens is a retrieval-augmented question-answering system for university academic regulations.

Instead of relying on model memory, RuleLens retrieves relevant passages from a regulation corpus and returns one of three states:

- `ANSWERABLE` — the corpus contains a clear rule that answers the question.
- `NOT_FOUND` — the corpus does not contain enough information to answer the question.
- `CONTRADICTION` — the corpus contains incompatible rules that apply to the same situation.

Every answer is designed to include the source document, section, and relevant passage so that the student can verify it.

## Project Structure

```text
rulelens/
├── corpus/                 # Regulation documents used by the system
├── data/
│   └── chunks.json         # Generated section-aware chunks
├── evaluation/             # Evaluation questions and ground truth
├── src/
│   ├── ingestion.py        # Load Markdown and PDF regulations
│   ├── chunking.py         # Create section-aware chunks
│   ├── validate_corpus.py  # Validate corpus requirements
│   ├── validate_chunks.py  # Validate generated chunks
│   ├── build_chunks.py     # Build chunks.json
│   └── build_vector_store.py
├── requirements.txt
└── README.md