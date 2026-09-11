import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer


DATA_DIR = Path(__file__).parent.parent / "data"
CHROMA_DIR = DATA_DIR / "chroma"

MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "rulebook"


# Load the embedding model once when this module is imported.
MODEL = SentenceTransformer(MODEL_NAME)


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(name=COLLECTION_NAME)


def retrieve(question, top_k=8):
    collection = get_collection()

    question_embedding = MODEL.encode(
        [question],
        normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=question_embedding,
        n_results=top_k
    )

    retrieved = []

    for i in range(len(results["documents"][0])):
        retrieved.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "section": results["metadatas"][0][i]["section"],
            "page": results["metadatas"][0][i]["page"],
            "distance": results["distances"][0][i]
        })

    return retrieved


if __name__ == "__main__":
    print("RuleLens Retrieval")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("Question: ").strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        results = retrieve(question)

        print("\nRetrieved evidence:\n")

        for i, result in enumerate(results, start=1):
            print(f"--- Result {i} ---")
            print(f"Source: {result['source']}")
            print(f"Section: {result['section']}")

            if result["page"] != -1:
                print(f"Page: {result['page']}")

            print(f"Distance: {result['distance']:.4f}")
            print(result["text"])
            print()