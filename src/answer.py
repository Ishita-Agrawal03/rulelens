import re

from src.retrieve import retrieve
from src.classifier import classify


def normalize(text):
    return text.lower().replace("**", "").strip()


def extract_percentage(text):
    matches = re.findall(r"\b\d{1,3}%", text)

    if matches:
        return matches[0]

    return None


def extract_date(text):
    months = (
        "january|february|march|april|may|june|"
        "july|august|september|october|november|december"
    )

    matches = re.findall(
        rf"\b\d{{1,2}}\s+(?:{months})\b",
        text,
        flags=re.IGNORECASE
    )

    if matches:
        return matches[0]

    return None


def extract_time(text):
    matches = re.findall(
        r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b",
        text,
        flags=re.IGNORECASE
    )

    if matches:
        return matches[0]

    return None


def generate_answer(question, state, evidence):
    question_normalized = normalize(question)

    # =========================================================
    # NOT FOUND
    # =========================================================

    if state == "NOT_FOUND":

        return {
            "state": "NOT_FOUND",
            "answer": (
                "The corpus does not contain enough information "
                "to answer this question. I won't infer an answer "
                "from unrelated rules."
            ),
            "sources": []
        }

    # =========================================================
    # CONTRADICTION
    # =========================================================

    if state == "CONTRADICTION":

        sources = []

        for item in evidence:

            source = {
                "source": item["source"],
                "section": item["section"],
                "page": item["page"],
                "passage": item["text"]
            }

            if source not in sources:
                sources.append(source)

        return {
            "state": "CONTRADICTION",
            "answer": (
                "I cannot give one definitive answer because "
                "the corpus contains conflicting rules. "
                "The conflicting passages are shown below."
            ),
            "sources": sources
        }

    # =========================================================
    # ANSWERABLE
    # =========================================================

    answer = None
    primary_evidence = evidence[0] if evidence else None

    if not primary_evidence:

        return {
            "state": "NOT_FOUND",
            "answer": (
                "The corpus does not contain enough information "
                "to answer this question."
            ),
            "sources": []
        }

    combined_text = " ".join(
        item["text"]
        for item in evidence
    )

    # ---------------------------------------------------------
    # ATTENDANCE
    # ---------------------------------------------------------

    if "attendance" in question_normalized:

        percentage = extract_percentage(
            combined_text
        )

        if percentage:

            answer = (
                f"The minimum attendance requirement is "
                f"{percentage} to appear for the relevant "
                f"semester-end examination."
            )

    # ---------------------------------------------------------
    # FEE DEADLINES
    # ---------------------------------------------------------

    if (
        "fee" in question_normalized
        and "deadline" in question_normalized
        and "semester" not in question_normalized
    ):

        date = extract_date(
            combined_text
        )

        if date:

            answer = (
                f"The applicable fee deadline stated in the "
                f"retrieved rule is {date}."
            )

    # ---------------------------------------------------------
    # HOSTEL CURFEW
    # ---------------------------------------------------------

    if (
        "curfew" in question_normalized
        or (
            "hostel" in question_normalized
            and "time" in question_normalized
        )
    ):

        time = extract_time(
            primary_evidence["text"]
        )

        if time:

            answer = (
                f"The standard hostel curfew stated in this "
                f"passage is {time}."
            )

    # ---------------------------------------------------------
    # SEMESTER FEE
    # ---------------------------------------------------------

    if "semester fee" in question_normalized:

        date = extract_date(
            primary_evidence["text"]
        )

        if date:

            answer = (
                f"The retrieved rule states that the semester "
                f"fee is due on {date}."
            )

    # ---------------------------------------------------------
    # GENERIC FALLBACK
    # ---------------------------------------------------------

    if answer is None:

        # Use the first retrieved passage as the grounded
        # evidence. We deliberately do not invent details.
        answer = (
            "The corpus contains a rule relevant to your "
            "question. See the cited passage below."
        )

    sources = [
        {
            "source": item["source"],
            "section": item["section"],
            "page": item["page"],
            "passage": item["text"]
        }
        for item in evidence
    ]

    return {
        "state": "ANSWERABLE",
        "answer": answer,
        "sources": sources
    }


def print_answer(result):

    print()
    print("=" * 70)
    print("RuleLens")
    print("=" * 70)

    print()
    print(f"STATE: {result['state']}")

    print()
    print("ANSWER")
    print(result["answer"])

    if not result["sources"]:
        return

    print()
    print("SOURCES")
    print("-" * 70)

    for i, source in enumerate(
        result["sources"],
        start=1
    ):

        print(f"[{i}] {source['source']}")
        print(f"Section: {source['section']}")

        if source["page"] != -1:
            print(f"Page: {source['page']}")

        print()
        print(source["passage"])
        print("-" * 70)


def answer_question(question):

    results = retrieve(question)

    state, evidence = classify(
        question,
        results
    )

    return generate_answer(
        question,
        state,
        evidence
    )


if __name__ == "__main__":

    print("RuleLens")
    print("Ask a question about the university rules.")
    print("Type 'exit' to quit.\n")

    while True:

        question = input("Question: ").strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        result = answer_question(
            question
        )

        print_answer(
            result
        )