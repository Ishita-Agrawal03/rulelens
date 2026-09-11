from pathlib import Path
from pypdf import PdfReader


CORPUS_DIR = Path(__file__).parent.parent / "corpus"

REQUIRED_FILES = {
    "academic_regulations.md",
    "medical_policy.md",
    "hostel_handbook.md",
    "scholarship_policy.md",
    "fees_policy.md",
    "student_code_of_conduct.md",
    "university_regulations.pdf",
}


def count_words(text):
    return len(text.split())


def validate_corpus():
    errors = []
    total_words = 0

    # --------------------------------------------------
    # 1. Check required files
    # --------------------------------------------------

    actual_files = {
        file.name
        for file in CORPUS_DIR.iterdir()
        if file.is_file()
    }

    missing_files = REQUIRED_FILES - actual_files

    if missing_files:
        for file in sorted(missing_files):
            errors.append(f"Missing required file: {file}")

    # --------------------------------------------------
    # 2. Check unexpected evaluation files
    # --------------------------------------------------

    forbidden_files = {
        "contradictions.md",
        "rule_inventory.md",
        "test_questions.json",
    }

    for file in CORPUS_DIR.iterdir():

        if file.name in forbidden_files:
            errors.append(
                f"Evaluation file found inside corpus: {file.name}"
            )

    # --------------------------------------------------
    # 3. Validate Markdown files
    # --------------------------------------------------

    for filename in REQUIRED_FILES:

        if not filename.endswith(".md"):
            continue

        file_path = CORPUS_DIR / filename

        if not file_path.exists():
            continue

        text = file_path.read_text(encoding="utf-8")

        if not text.strip():
            errors.append(f"Empty Markdown file: {filename}")

        total_words += count_words(text)

    # --------------------------------------------------
    # 4. Validate PDF
    # --------------------------------------------------

    pdf_path = CORPUS_DIR / "university_regulations.pdf"

    if pdf_path.exists():

        reader = PdfReader(pdf_path)

        if len(reader.pages) == 0:
            errors.append("PDF contains no pages.")

        for page in reader.pages:

            text = page.extract_text()

            if text:
                total_words += count_words(text)

    # --------------------------------------------------
    # 5. Check corpus size
    # --------------------------------------------------

    minimum_words = 6000

    if total_words < minimum_words:

        errors.append(
            f"Corpus has only {total_words} words. "
            f"Minimum required is {minimum_words}."
        )

    return errors, total_words


if __name__ == "__main__":

    errors, total_words = validate_corpus()

    print(f"Corpus word count: {total_words}")
    print()

    if errors:

        print("❌ Corpus validation FAILED\n")

        for error in errors:
            print(f"- {error}")

    else:

        print("✅ Corpus validation PASSED")
        print()
        print("All required files are present.")
        print("No evaluation files are inside corpus.")
        print("Corpus meets the 6,000-word minimum.")