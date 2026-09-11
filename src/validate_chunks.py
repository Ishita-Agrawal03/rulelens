from src.ingestion import load_corpus
from src.chunking import create_chunks


def validate_chunks(chunks):
    """
    Validate the quality and integrity of generated chunks.
    """

    errors = []

    # 1. Check for duplicate IDs
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]

    if len(chunk_ids) != len(set(chunk_ids)):
        errors.append("Duplicate chunk IDs found.")

    # 2. Check for empty text
    for chunk in chunks:
        if not chunk["text"].strip():
            errors.append(
                f"Empty text in {chunk['chunk_id']}"
            )

    # 3. Check source metadata
    for chunk in chunks:
        if not chunk["source"]:
            errors.append(
                f"Missing source in {chunk['chunk_id']}"
            )

    # 4. Check section metadata for Markdown
    for chunk in chunks:
        if chunk["source"].endswith(".md"):
            if not chunk["section"]:
                errors.append(
                    f"Missing section in {chunk['chunk_id']}"
                )

    # 5. Check page metadata for PDF
    for chunk in chunks:
        if chunk["source"].endswith(".pdf"):
            if chunk["page"] is None:
                errors.append(
                    f"Missing page number in {chunk['chunk_id']}"
                )

    return errors


if __name__ == "__main__":

    documents = load_corpus()
    chunks = create_chunks(documents)

    errors = validate_chunks(chunks)

    print(f"Documents: {len(documents)}")
    print(f"Chunks:    {len(chunks)}")
    print()

    if errors:
        print("❌ Validation FAILED\n")

        for error in errors:
            print(f"- {error}")

    else:
        print("✅ Validation PASSED")
        print("All chunks have valid IDs and metadata.")