from src.ingestion import load_corpus


MAX_CHARS = 1800
OVERLAP = 200


def split_long_text(text):
    """
    Split very long sections into overlapping chunks.
    """

    if len(text) <= MAX_CHARS:
        return [text]

    chunks = []

    start = 0

    while start < len(text):

        end = start + MAX_CHARS

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - OVERLAP

    return chunks


def create_chunks(documents):
    """
    Convert parsed documents into searchable chunks.
    Each chunk receives a unique ID.
    """

    chunks = []

    # Track chunk number separately for each source file
    source_counters = {}

    for document in documents:

        source = document["source"]

        # Initialize counter for this source
        if source not in source_counters:
            source_counters[source] = 0

        text_parts = split_long_text(document["text"])

        for text in text_parts:

            source_counters[source] += 1

            source_name = source.replace(".", "_")

            chunk_id = (
                f"{source_name}_"
                f"{source_counters[source]:03d}"
            )

            chunks.append({
                "chunk_id": chunk_id,
                "text": text,
                "source": source,
                "section": document["section"],
                "page": document["page"]
            })

    return chunks


if __name__ == "__main__":

    documents = load_corpus()

    chunks = create_chunks(documents)

    print(f"Parsed documents: {len(documents)}")
    print(f"Searchable chunks: {len(chunks)}")

    print("\nSample chunks:")

    for chunk in chunks[:5]:

        print("=" * 60)

        print(f"Chunk ID: {chunk['chunk_id']}")
        print(f"Source:  {chunk['source']}")
        print(f"Section: {chunk['section']}")
        print(f"Page:    {chunk['page']}")

        print(f"\n{chunk['text'][:500]}")