import re

from src.retrieve import retrieve


RELEVANCE_THRESHOLD = 1.0


def normalize(text):
    return text.lower().replace("**", "").strip()


def make_claim(topic, value, result):
    return {
        "topic": topic,
        "value": value.lower(),
        "source": result["source"],
        "section": result["section"],
        "page": result["page"],
        "text": result["text"],
    }


def extract_claims(question, results):
    """
    Extract claims relevant to the user's question.
    """

    question = normalize(question)
    claims = []

    for result in results:

        text = normalize(result["text"])
        source = normalize(result["source"])
        section = normalize(result["section"])

        # =====================================================
        # ATTENDANCE
        # =====================================================

        if "attendance" in question:

            # General attendance requirement.
            #
            # We specifically look for the academic regulation
            # or a passage clearly stating the general requirement.
            if (
                "academic_regulations.md" in source
                and "attendance requirements" in section
            ):
                percentages = re.findall(
                    r"\b\d{1,3}%",
                    text
                )

                for value in percentages:
                    claims.append(
                        make_claim(
                            "exam_attendance_requirement",
                            value,
                            result
                        )
                    )

            # Medical attendance exemption.
            #
            # This is a separate policy and therefore a separate
            # source of the attendance requirement.
            if (
                "medical_policy.md" in source
                and "medical attendance exemption" in section
            ):
                percentages = re.findall(
                    r"\b\d{1,3}%",
                    text
                )

                for value in percentages:
                    claims.append(
                        make_claim(
                            "exam_attendance_requirement",
                            value,
                            result
                        )
                    )

            # University PDF also states the ordinary 75% rule.
            if (
                "university_regulations.pdf" in source
                and "academic attendance" in section
            ):
                percentages = re.findall(
                    r"\b\d{1,3}%",
                    text
                )

                for value in percentages:
                    claims.append(
                        make_claim(
                            "exam_attendance_requirement",
                            value,
                            result
                        )
                    )

        # =====================================================
        # SEMESTER FEE
        # =====================================================

        if "semester fee" in question:

            # Sentence:
            # "semester fee deadline is 20 August"
            sentence_matches = re.findall(
                r"semester fee.*?"
                r"(\d{1,2}\s+"
                r"(?:january|february|march|april|may|june|"
                r"july|august|september|october|november|december))",
                text
            )

            # Table:
            # "| Semester Fee | 15 August |"
            table_matches = re.findall(
                r"semester fee\s*\|\s*"
                r"(\d{1,2}\s+"
                r"(?:january|february|march|april|may|june|"
                r"july|august|september|october|november|december))",
                text
            )

            for value in sentence_matches + table_matches:
                claims.append(
                    make_claim(
                        "semester_fee_deadline",
                        value,
                        result
                    )
                )

        # =====================================================
        # HOSTEL CURFEW
        # =====================================================

        if "curfew" in question:

            if (
                "curfew" in text
                or "hostel entry" in text
            ):

                times = re.findall(
                    r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b",
                    text
                )

                for value in times:
                    claims.append(
                        make_claim(
                            "hostel_curfew",
                            value,
                            result
                        )
                    )

    return claims


def find_contradictions(claims):
    """
    Find different values for the same rule/topic
    when those values come from different documents.
    """

    topics = {}

    for claim in claims:
        topics.setdefault(
            claim["topic"],
            []
        ).append(claim)

    contradictions = []

    for topic, topic_claims in topics.items():

        # Get distinct values.
        distinct_values = {
            claim["value"]
            for claim in topic_claims
        }

        # One value = no contradiction.
        if len(distinct_values) <= 1:
            continue

        # Make sure competing values come from
        # different source documents.
        value_sources = {}

        for claim in topic_claims:

            value_sources.setdefault(
                claim["value"],
                set()
            ).add(
                claim["source"]
            )

        # We have at least two different values.
        # Now check that they are supported by
        # different documents.
        values = list(value_sources.keys())

        contradiction_found = False

        for i in range(len(values)):

            for j in range(i + 1, len(values)):

                sources_a = value_sources[values[i]]
                sources_b = value_sources[values[j]]

                if sources_a.isdisjoint(sources_b):
                    contradiction_found = True

        if contradiction_found:
            contradictions.append(topic_claims)

    return contradictions


def classify(question, results):

    if not results:
        return "NOT_FOUND", []

    relevant = [
        result
        for result in results
        if result["distance"] < RELEVANCE_THRESHOLD
    ]

    if not relevant:
        return "NOT_FOUND", []

    claims = extract_claims(
        question,
        relevant
    )

    contradictions = find_contradictions(
        claims
    )

    if contradictions:

        evidence = []

        for group in contradictions:

            for claim in group:

                if claim not in evidence:
                    evidence.append(claim)

        return "CONTRADICTION", evidence

    return "ANSWERABLE", relevant


def print_result(state, evidence):

    print()
    print("=" * 60)
    print(f"STATE: {state}")
    print("=" * 60)

    # -----------------------------------------------------
    # NOT FOUND
    # -----------------------------------------------------

    if state == "NOT_FOUND":

        print(
            "\nThe corpus does not contain enough information "
            "to answer this question."
        )

        return

    # -----------------------------------------------------
    # CONTRADICTION
    # -----------------------------------------------------

    if state == "CONTRADICTION":

        print(
            "\nConflicting rules were found:\n"
        )

        for i, result in enumerate(
            evidence,
            start=1
        ):

            print(
                f"--- Conflicting Evidence {i} ---"
            )

            print(
                f"Source: {result['source']}"
            )

            print(
                f"Section: {result['section']}"
            )

            if result["page"] != -1:
                print(
                    f"Page: {result['page']}"
                )

            print(
                f"Claimed value: {result['value']}"
            )

            print(
                f"Passage:\n{result['text']}"
            )

            print()

        return

    # -----------------------------------------------------
    # ANSWERABLE
    # -----------------------------------------------------

    print(
        "\nRelevant evidence:\n"
    )

    for i, result in enumerate(
        evidence,
        start=1
    ):

        print(
            f"--- Evidence {i} ---"
        )

        print(
            f"Source: {result['source']}"
        )

        print(
            f"Section: {result['section']}"
        )

        if result["page"] != -1:
            print(
                f"Page: {result['page']}"
            )

        print(result["text"])
        print()


if __name__ == "__main__":

    print("RuleLens Classifier")
    print("Type 'exit' to quit.\n")

    while True:

        question = input(
            "Question: "
        ).strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        results = retrieve(question)

        state, evidence = classify(
            question,
            results
        )

        print_result(
            state,
            evidence
        )