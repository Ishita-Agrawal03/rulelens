from src.retrieve import retrieve


def classify(question, results):
    """
    Classify a question into:
    ANSWERABLE, NOT_FOUND, or CONTRADICTION.
    """

    if not results:
        return "NOT_FOUND", []

    # A small retrieval distance means the result is semantically relevant.
    relevant = [r for r in results if r["distance"] < 1.0]

    if not relevant:
        return "NOT_FOUND", []

    # Look for potentially conflicting numeric/time values.
    evidence_by_topic = {}

    for result in relevant:
        text = result["text"].lower()

        if "attendance" in text:
            topic = "attendance"
        elif "semester fee" in text:
            topic = "semester_fee"
        elif "curfew" in text or "hostel entry" in text:
            topic = "curfew"
        else:
            continue

        evidence_by_topic.setdefault(topic, []).append(result)

    # Detect explicit conflicting values.
    for topic, evidence in evidence_by_topic.items():

        if topic == "attendance":
            has_75 = any("75%" in r["text"] for r in evidence)
            has_65 = any("65%" in r["text"] for r in evidence)

            if has_75 and has_65:
                return "CONTRADICTION", evidence

        elif topic == "semester_fee":
            has_15 = any("15 august" in r["text"].lower() for r in evidence)
            has_20 = any("20 august" in r["text"].lower() for r in evidence)

            if has_15 and has_20:
                return "CONTRADICTION", evidence

        elif topic == "curfew":
            has_10 = any("10:00 pm" in r["text"].lower() for r in evidence)
            has_11 = any("11:00 pm" in r["text"].lower() for r in evidence)

            if has_10 and has_11:
                return "CONTRADICTION", evidence

    return "ANSWERABLE", relevant


def print_result(state, evidence):
    print(f"\nSTATE: {state}\n")

    if state == "NOT_FOUND":
        print("The corpus does not contain enough information to answer this question.")
        return

    print("Evidence:\n")

    for i, result in enumerate(evidence, start=1):
        print(f"--- Evidence {i} ---")
        print(f"Source: {result['source']}")
        print(f"Section: {result['section']}")

        if result["page"] != -1:
            print(f"Page: {result['page']}")

        print(result["text"])
        print()


if __name__ == "__main__":
    print("RuleLens Classifier")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("Question: ").strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        results = retrieve(question)
        state, evidence = classify(question, results)

        print_result(state, evidence)