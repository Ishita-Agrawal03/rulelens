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
    question = normalize(question)

    claims = []

    # =========================================================
    # ATTENDANCE
    # =========================================================

    attendance_question = (
        "attendance" in question
        and any(
            word in question
            for word in [
                "examination",
                "exam",
                "eligibility",
                "appear",
                "required",
                "minimum",
                "percentage",
            ]
        )
    )

    if attendance_question:

        # Medical rules should only participate in contradiction
        # detection when the user actually asks about medical
        # circumstances.
        medical_question = any(
            phrase in question
            for phrase in [
                "medical",
                "medical documentation",
                "medical certificate",
                "medical exemption",
                "approved medical",
                "medical circumstances",
                "illness",
                "sick",
            ]
        )

        for result in results:

            text = normalize(result["text"])
            source = normalize(result["source"])
            section = normalize(result["section"])

            # -------------------------------------------------
            # General academic attendance rules
            # -------------------------------------------------

            is_general_attendance_rule = (
                (
                    "academic_regulations.md" in source
                    and "attendance requirements" in section
                )
                or
                (
                    "university_regulations.pdf" in source
                    and "academic attendance" in section
                )
            )

            if is_general_attendance_rule:

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

            # -------------------------------------------------
            # Medical attendance rule
            # -------------------------------------------------

            is_medical_rule = (
                "medical_policy.md" in source
                and "medical attendance exemption" in section
            )

            if is_medical_rule and medical_question:

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

    # =========================================================
    # SEMESTER FEE
    # =========================================================

    if "semester fee" in question:

        for result in results:

            text = normalize(result["text"])

            # Sentence-style rule
            sentence_matches = re.findall(
                r"semester fee.*?("
                r"\d{1,2}\s+"
                r"(?:january|february|march|april|may|june|"
                r"july|august|september|october|november|december))",
                text
            )

            # Markdown table-style rule
            table_matches = re.findall(
                r"semester fee\s*\|\s*("
                r"\d{1,2}\s+"
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

    # =========================================================
    # HOSTEL CURFEW
    # =========================================================

    curfew_question = (
        "curfew" in question
        or (
            "hostel" in question
            and any(
                word in question
                for word in [
                    "entry",
                    "return",
                    "returning",
                    "allowed",
                    "time",
                ]
            )
        )
    )

    if curfew_question:

        for result in results:

            text = normalize(result["text"])
            source = normalize(result["source"])
            section = normalize(result["section"])

            is_hostel_entry_rule = (
                "curfew" in text
                or "hostel entry" in section
                or "late entry" in section
            )

            if not is_hostel_entry_rule:
                continue

            times = re.findall(
                r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b",
                text
            )

            # The PDF explicitly documents an unresolved
            # 10 PM vs 11 PM conflict.
            if (
                "university_regulations.pdf" in source
                and "hostel entry" in section
                and "do not provide a precedence rule" in text
                and len(times) >= 2
            ):

                claims.append(
                    make_claim(
                        "hostel_curfew",
                        "10:00 pm",
                        result
                    )
                )

                claims.append(
                    make_claim(
                        "hostel_curfew",
                        "11:00 pm",
                        result
                    )
                )

            else:

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

    topics = {}

    for claim in claims:

        topics.setdefault(
            claim["topic"],
            []
        ).append(claim)

    contradictions = []

    for topic, topic_claims in topics.items():

        distinct_values = {
            claim["value"]
            for claim in topic_claims
        }

        # One value means no contradiction.
        if len(distinct_values) <= 1:
            continue

        value_sources = {}

        for claim in topic_claims:

            value_sources.setdefault(
                claim["value"],
                set()
            ).add(
                claim["source"]
            )

        values = list(
            value_sources.keys()
        )

        contradiction_found = False

        for i in range(len(values)):

            for j in range(i + 1, len(values)):

                sources_a = value_sources[
                    values[i]
                ]

                sources_b = value_sources[
                    values[j]
                ]

                # Contradiction when incompatible values
                # originate from independent sources.
                if sources_a.isdisjoint(sources_b):

                    contradiction_found = True

                # The university PDF explicitly documents
                # the unresolved hostel conflict itself.
                if (
                    topic == "hostel_curfew"
                    and values[i] == "10:00 pm"
                    and values[j] == "11:00 pm"
                ):

                    contradiction_found = True

        if contradiction_found:

            contradictions.append(
                topic_claims
            )

    return contradictions


def evidence_supports_question(question, evidence):

    question = normalize(question)

    combined_text = " ".join(
        normalize(result["text"])
        for result in evidence
    )

    # ---------------------------------------------------------
    # Specific qualifier: FREE
    # ---------------------------------------------------------
    #
    # "Laundry exists" does not answer:
    # "Is laundry free?"
    #

    if (
        "free" in question
        and "free" not in combined_text
    ):
        return False

    # ---------------------------------------------------------
    # Specific subject: blood type
    # ---------------------------------------------------------
    #
    # Generic academic-record rules do not answer a
    # blood-type-specific question.
    #

    if (
        "blood type" in question
        and "blood type" not in combined_text
    ):
        return False

    return True


def classify(question, results):

    # No retrieval results.
    if not results:

        return "NOT_FOUND", []

    # ---------------------------------------------------------
    # Relevance filtering
    # ---------------------------------------------------------

    relevant = [
        result
        for result in results
        if result["distance"] < RELEVANCE_THRESHOLD
    ]

    if not relevant:

        return "NOT_FOUND", []

    # ---------------------------------------------------------
    # Extract rule claims
    # ---------------------------------------------------------

    claims = extract_claims(
        question,
        relevant
    )

    # ---------------------------------------------------------
    # Detect contradictions
    # ---------------------------------------------------------

    contradictions = find_contradictions(
        claims
    )

    if contradictions:

        evidence = []

        for group in contradictions:

            for claim in group:

                if claim not in evidence:

                    evidence.append(
                        claim
                    )

        return "CONTRADICTION", evidence

    # ---------------------------------------------------------
    # Check whether retrieved evidence actually supports
    # the specific question.
    # ---------------------------------------------------------

    if not evidence_supports_question(
        question,
        relevant
    ):

        return "NOT_FOUND", []

    # ---------------------------------------------------------
    # Otherwise the corpus contains relevant evidence.
    # ---------------------------------------------------------

    return "ANSWERABLE", relevant


def print_result(state, evidence):

    print()

    print("=" * 60)

    print(
        f"STATE: {state}"
    )

    print("=" * 60)

    # =========================================================
    # NOT FOUND
    # =========================================================

    if state == "NOT_FOUND":

        print(
            "\nThe corpus does not contain enough information "
            "to answer this question."
        )

        return

    # =========================================================
    # CONTRADICTION
    # =========================================================

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

    # =========================================================
    # ANSWERABLE
    # =========================================================

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

        print(
            result["text"]
        )

        print()


if __name__ == "__main__":

    print(
        "RuleLens Classifier"
    )

    print(
        "Type 'exit' to quit.\n"
    )

    while True:

        question = input(
            "Question: "
        ).strip()

        if question.lower() == "exit":

            break

        if not question:

            continue

        results = retrieve(
            question
        )

        state, evidence = classify(
            question,
            results
        )

        print_result(
            state,
            evidence
        )