from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"


if __name__ == "__main__":

    print(f"Loading model: {MODEL_NAME}")

    model = SentenceTransformer(MODEL_NAME)

    text = "Students need 75% attendance to appear for the semester-end examination."

    embedding = model.encode(text)

    print(f"Embedding type: {type(embedding)}")
    print(f"Embedding dimensions: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")

    print("\n✅ Embedding model working.")