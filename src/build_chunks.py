import json
from pathlib import Path

from src.ingestion import load_corpus
from src.chunking import create_chunks


OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "chunks.json"


def build_chunks():
    """
    Load the corpus, create searchable chunks,
    and save them as JSON.
    """

    documents = load_corpus()
    chunks = create_chunks(documents)

    OUTPUT_DIR.mkdir(exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            chunks,
            file,
            ensure_ascii=False,
            indent=2
        )

    return chunks


if __name__ == "__main__":

    chunks = build_chunks()

    print(f"Created {len(chunks)} chunks.")
    print(f"Saved to: {OUTPUT_FILE}")