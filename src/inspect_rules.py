from src.ingestion import load_corpus
from src.chunking import create_chunks


def search_chunks(chunks, keywords):
    """
    Find chunks containing all specified keywords.
    """

    results = []

    for chunk in chunks:

        text = chunk["text"].lower()

        if all(keyword.lower() in text for keyword in keywords):
            results.append(chunk)

    return results


if __name__ == "__main__":

    documents = load_corpus()
    chunks = create_chunks(documents)

    searches = {
        "Medical attendance": ["medical", "65%"],
        "Semester fee": ["semester", "15 august"],
        "Hostel curfew": ["curfew", "10:00"],
    }

    for name, keywords in searches.items():

        print("\n" + "=" * 70)
        print(name)
        print("=" * 70)

        results = search_chunks(chunks, keywords)

        for chunk in results:

            print(f"\nChunk ID: {chunk['chunk_id']}")
            print(f"Source:  {chunk['source']}")
            print(f"Section: {chunk['section']}")
            print(f"Page:    {chunk['page']}")
            print(f"\n{chunk['text'][:1000]}")