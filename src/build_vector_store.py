import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


DATA_FILE = Path(__file__).parent.parent / "data" / "chunks.json"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma"

MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "rulebook"


def load_chunks():
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_vector_store(chunks):

    print(f"Loading embedding model: {MODEL_NAME}")

    model = SentenceTransformer(MODEL_NAME)

    print("Creating Chroma database...")

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "RuleLens university regulations"
        }
    )

    texts = [chunk["text"] for chunk in chunks]

    print(f"Generating embeddings for {len(texts)} chunks...")

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    ).tolist()

    ids = [
        chunk["chunk_id"]
        for chunk in chunks
    ]

    metadatas = []

    for chunk in chunks:

        metadata = {
            "source": chunk["source"],
            "section": chunk["section"] or "",
            "page": chunk["page"] or -1
        }

        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return collection


if __name__ == "__main__":

    chunks = load_chunks()

    collection = build_vector_store(chunks)

    print()
    print(f"Collection: {collection.name}")
    print(f"Documents indexed: {collection.count()}")
    print()
    print("✅ Chroma vector store built successfully.")