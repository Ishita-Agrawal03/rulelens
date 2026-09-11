from pathlib import Path
from pypdf import PdfReader


CORPUS_DIR = Path(__file__).parent.parent / "corpus"


def load_markdown(file_path):
    """
    Load a Markdown regulation file and split it by numbered sections.
    Document-level metadata before the first numbered section is ignored.
    """

    text = file_path.read_text(encoding="utf-8")

    sections = []
    current_section = None
    current_text = []

    for line in text.splitlines():

        if line.startswith("## "):

            heading = line[3:].strip()

            # Only treat numbered headings as regulation sections.
            # Example:
            # "1. Purpose and Scope"
            # "4. Attendance Requirements"
            if not heading[0].isdigit():
                continue

            # Save previous section
            if current_section is not None:
                sections.append({
                    "text": "\n".join(current_text).strip(),
                    "source": file_path.name,
                    "section": current_section,
                    "page": None
                })

            current_section = heading
            current_text = []

        else:

            # Ignore document-level metadata before first section
            if current_section is not None:
                current_text.append(line)

    # Save final section
    if current_section is not None:
        sections.append({
            "text": "\n".join(current_text).strip(),
            "source": file_path.name,
            "section": current_section,
            "page": None
        })

    return sections


def load_pdf(file_path):
    """
    Load PDF pages and split numbered sections while
    preserving the original PDF page number.
    """

    reader = PdfReader(file_path)

    sections = []

    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text()

        if not text or not text.strip():
            continue

        current_section = None
        current_text = []

        for line in text.splitlines():

            line = line.strip()

            # Detect numbered sections such as:
            # 1. Academic Attendance
            # 4. Fee Deadlines
            # 5. Hostel Entry
            if (
                len(line) > 2
                and line[0].isdigit()
                and ". " in line
            ):

                # Save previous section
                section_text = "\n".join(current_text).strip()

                if current_section is not None and section_text:
                    sections.append({
                        "text": section_text,
                        "source": file_path.name,
                        "section": current_section,
                        "page": page_number
                    })

                current_section = line
                current_text = []

            else:

                if current_section is not None:
                    current_text.append(line)

        # Save final section
        section_text = "\n".join(current_text).strip()

        if current_section is not None and section_text:
            sections.append({
                "text": section_text,
                "source": file_path.name,
                "section": current_section,
                "page": page_number
            })

    return sections


def load_corpus():
    """
    Load all Markdown and PDF files from the corpus.
    """

    documents = []

    for file_path in CORPUS_DIR.iterdir():

        if file_path.suffix.lower() == ".md":
            documents.extend(load_markdown(file_path))

        elif file_path.suffix.lower() == ".pdf":
            documents.extend(load_pdf(file_path))

    return documents


if __name__ == "__main__":

    documents = load_corpus()

    print(f"\nTotal sections/pages loaded: {len(documents)}\n")

    # Count documents by source
    source_counts = {}

    for document in documents:
        source = document["source"]
        source_counts[source] = source_counts.get(source, 0) + 1

    print("Documents loaded:")

    for source, count in source_counts.items():
        print(f"  {source}: {count}")

    print("\nSample records:")

    for i, document in enumerate(documents[:5], start=1):
        print("=" * 60)
        print(f"Document {i}")
        print(f"Source:   {document['source']}")
        print(f"Section:  {document['section']}")
        print(f"Page:     {document['page']}")
        print(f"Text:     {document['text'][:200]}...")