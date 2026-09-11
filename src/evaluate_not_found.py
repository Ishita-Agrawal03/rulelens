import json
from pathlib import Path

from .classifier import classify


PROJECT_ROOT = Path(__file__).parent.parent
QUESTIONS_FILE = PROJECT_ROOT / "evaluation" / "not_found_questions.json"


def run_evaluation():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print("=" * 70)
    print("RuleLens - NOT_FOUND Evaluation")
    print("=" * 70)
    print()

    passed = 0
    total = len(questions)

    for i, item in enumerate(questions, start=1):
        question = item["question"]

        expected = "NOT_FOUND"

        result = classify(question)
        actual = result["state"]

        if actual == expected:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(f"[{status}] {i:02d}")
        print(f"Question : {question}")
        print(f"Expected : {expected}")
        print(f"Actual   : {actual}")
        print(f"Confidence: {result['confidence']:.2f}")

        if result.get("reason"):
            print(f"Reason   : {result['reason']}")

        print("-" * 70)

    accuracy = (passed / total * 100) if total else 0

    print()
    print("=" * 70)
    print("NOT_FOUND Evaluation Summary")
    print("=" * 70)
    print(f"Passed   : {passed}/{total}")
    print(f"Accuracy : {accuracy:.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    run_evaluation()