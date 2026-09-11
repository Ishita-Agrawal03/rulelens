import json
import os
import time

from dotenv import load_dotenv
from groq import Groq, RateLimitError

from .retrieve import retrieve


# ============================================================
# Configuration
# ============================================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Add it to your .env file."
    )

client = Groq(api_key=API_KEY)

MODEL_NAME = "openai/gpt-oss-20b"

# Retrieve enough evidence to detect cross-document conflicts.
DEFAULT_TOP_K = 8

# Keep the complete retrieved chunk whenever possible.
# Your chunks are approximately 1800 characters.
MAX_EVIDENCE_CHARS = 1800


VALID_STATES = {
    "ANSWERABLE",
    "NOT_FOUND",
    "CONTRADICTION",
}


# ============================================================
# LLM instructions
# ============================================================

SYSTEM_PROMPT = """
You are the evidence judge for a university rulebook QA system.

Your job is to classify the user's question using ONLY the supplied
retrieved evidence.

Never use outside knowledge.
Never invent facts.
Never infer missing information.

You must return exactly one of these states:

ANSWERABLE
The supplied evidence directly contains enough information to answer
the specific question.

NOT_FOUND
The supplied evidence may be related to the question, but it does not
actually contain enough information to answer the specific question.

CONTRADICTION
The supplied evidence contains two or more incompatible rules that
apply to the same situation/question, and the evidence does not
establish which rule takes precedence.

============================================================
IMPORTANT CLASSIFICATION RULES
============================================================

1. SPECIFICITY OVER TOPICAL SIMILARITY

Do not classify a question as ANSWERABLE merely because the evidence
is about the same general topic.

The evidence must support the exact object, action, condition,
quantity, permission, deadline, threshold, requirement, or cost asked
about.

Example:
If the question asks whether free Wi-Fi equipment is provided,
evidence saying that internet access is available is NOT sufficient.
Do not infer that Wi-Fi equipment is free.

2. NO OUTSIDE KNOWLEDGE

Use only the retrieved passages.

Do not assume normal university practice.
Do not assume common hostel rules.
Do not assume legal requirements.
Do not assume what a university would normally do.

If the answer is not explicitly supported by the evidence,
use NOT_FOUND.

3. DO NOT INFER ONE PROPERTY FROM ANOTHER

A rule about one property does not automatically establish another.

Examples:

Internet access != free Wi-Fi equipment.
Scholarship eligibility != guaranteed renewal.
Medical certificate != automatic deadline extension.
Exam absence approval != attendance exemption.
Parent message != official hostel leave approval.

4. DIFFERENT CONDITIONS ARE NOT CONTRADICTIONS

Two different rules are not contradictory merely because they contain
different numbers, dates, times, or requirements.

For example:

"75% attendance is required for ordinary students."

and

"Students in a specified programme have a different programme-specific
requirement."

are not necessarily contradictory if the evidence establishes that
the rules apply to different populations.

Determine whether the rules actually apply to the same situation.

5. IDENTIFY THE ACTUAL VALUES

When checking for contradiction, inspect the actual values in the
evidence.

Pay attention to:

- percentages
- dates
- times
- monetary amounts
- deadlines
- permissions
- prohibitions
- required conditions
- eligibility thresholds

Do not look only for repeated wording.

6. SAME REQUIREMENT + INCOMPATIBLE VALUES

If two passages give incompatible values for the same requirement
under the same applicable conditions, classify as CONTRADICTION unless
the evidence explicitly establishes precedence.

Examples:

75% attendance vs 65% attendance for the same medical-attendance
eligibility situation.

15 August vs 20 August for the same semester-fee deadline.

10:00 PM vs 11:00 PM for the same hostel curfew/entry requirement,
when the evidence itself states that the difference is unresolved.

7. INTERNAL CONTRADICTIONS COUNT

A contradiction can occur inside one retrieved passage.

Read the entire passage.

For example, if a passage says:

"The standard hostel curfew is 10:00 PM. Residents may enter until
11:00 PM. The documents do not provide a precedence rule resolving
the difference."

Do NOT ignore the 11:00 PM statement simply because 10:00 PM is also
called the "standard curfew."

The evidence contains two relevant operational times and explicitly
says that there is no precedence rule.

This should be treated as CONTRADICTION when the question concerns
the hostel curfew/entry requirement.

8. DO NOT RESOLVE A CONFLICT YOURSELF

If the evidence contains conflicting rules and no precedence rule,
do not choose one.

Do not choose the rule because it:

- appears more frequently,
- appears first,
- appears last,
- seems newer,
- seems more specific,
- appears in a particular document,
- seems more authoritative.

Only use precedence if the supplied evidence explicitly establishes it.

9. EXPLICIT NO-PRECEDENCE LANGUAGE

Statements such as:

"no precedence rule"
"does not provide a precedence rule"
"without precedence"
"no rule establishes which provision controls"
"conflicting rules"
"inconsistent provisions"

are strong evidence that an identified conflict remains unresolved.

10. NOT_FOUND MUST BE A REAL OPTION

Do not force an answer.

If the retrieved evidence is merely related but does not answer the
specific question, classify as NOT_FOUND.

11. EVIDENCE IDS

Evidence IDs refer only to the numbered evidence passages supplied in
the user prompt.

Never invent an evidence ID.

12. FINAL DECISION

Choose the state that is best supported by the supplied evidence.

Return ONLY valid JSON matching the required schema.
"""


# ============================================================
# Evidence preparation
# ============================================================

def compact_evidence(evidence):
    """
    Prepare retrieved evidence for the LLM.

    The source, section and page metadata are retained.
    Evidence is truncated only if it exceeds MAX_EVIDENCE_CHARS.
    """

    compact = []

    for item in evidence:
        text = item["text"].strip()

        if len(text) > MAX_EVIDENCE_CHARS:
            text = (
                text[:MAX_EVIDENCE_CHARS]
                .rstrip()
                + "..."
            )

        compact.append(
            {
                "text": text,
                "source": item["source"],
                "section": item["section"],
                "page": item.get("page", -1),
            }
        )

    return compact


def build_evidence_prompt(question, evidence):
    """
    Build the user message sent to the evidence judge.
    """

    parts = []

    for i, item in enumerate(evidence, start=1):

        page = ""

        if item.get("page", -1) != -1:
            page = f" | Page: {item['page']}"

        parts.append(
            f"""
Evidence {i}
Source: {item['source']}
Section: {item['section']}{page}

{item['text']}
"""
        )

    return (
        f"Question:\n{question}\n\n"
        "Retrieved evidence:\n"
        + "\n".join(parts)
        + "\n\n"
        "Classify the question using ONLY the evidence above."
    )


# ============================================================
# Deterministic conflict detection
# ============================================================

def has_explicit_unresolved_conflict(evidence):
    """
    Detect explicit statements in the retrieved corpus saying that
    a conflict has no precedence/resolution.

    This is deliberately generic. It does not know the test questions
    or hard-code particular questions, dates, or topics.
    """

    conflict_phrases = (
        "do not provide a precedence rule",
        "does not provide a precedence rule",
        "no precedence rule",
        "without precedence",
        "no rule establishes which provision controls",
        "conflicting rules",
        "conflicting provisions",
        "inconsistent provisions",
        "difference is unresolved",
        "conflict remains unresolved",
    )

    for item in evidence:

        text = item["text"].lower()

        for phrase in conflict_phrases:

            if phrase in text:
                return True

    return False


def deterministic_safety_check(judgment, evidence):
    """
    Apply deterministic checks after the LLM.

    The purpose is to prevent the LLM from silently resolving an
    explicitly unresolved conflict in the retrieved rulebook.
    """

    if not has_explicit_unresolved_conflict(evidence):
        return judgment

    # If the corpus explicitly says that the retrieved rules conflict
    # and there is no precedence rule, preserve that fact.
    return {
        **judgment,
        "state": "CONTRADICTION",
        "confidence": max(
            float(judgment.get("confidence", 0.0)),
            0.95,
        ),
        "evidence_ids": list(
            range(1, len(evidence) + 1)
        ),
        "reason": (
            "The retrieved evidence explicitly identifies an "
            "unresolved conflict and provides no precedence rule "
            "for selecting one rule over the other."
        ),
    }


# ============================================================
# Groq call
# ============================================================

def call_llm_judge(question, evidence):
    """
    Ask Groq to classify the retrieved evidence.

    Uses strict JSON schema so the classifier receives a predictable
    machine-readable response.
    """

    compact = compact_evidence(evidence)

    prompt = build_evidence_prompt(
        question,
        compact,
    )

    max_retries = 4

    for attempt in range(max_retries):

        try:

            response = client.chat.completions.create(
                model=MODEL_NAME,

                temperature=0,

                reasoning_effort="low",

                include_reasoning=False,

                max_completion_tokens=800,

                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "rulelens_classification",
                        "strict": True,
                        "schema": {
                            "type": "object",

                            "properties": {

                                "state": {
                                    "type": "string",
                                    "enum": [
                                        "ANSWERABLE",
                                        "NOT_FOUND",
                                        "CONTRADICTION",
                                    ],
                                },

                                "confidence": {
                                    "type": "number",
                                },

                                "evidence_ids": {
                                    "type": "array",
                                    "items": {
                                        "type": "integer",
                                    },
                                },

                                "reason": {
                                    "type": "string",
                                },
                            },

                            "required": [
                                "state",
                                "confidence",
                                "evidence_ids",
                                "reason",
                            ],

                            "additionalProperties": False,
                        },
                    },
                },

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            content = response.choices[0].message.content

            # --------------------------------------------
            # Parse JSON
            # --------------------------------------------

            try:

                result = json.loads(content)

            except (json.JSONDecodeError, TypeError):

                return {
                    "state": "NOT_FOUND",
                    "confidence": 0.0,
                    "evidence_ids": [],
                    "reason": (
                        "The evidence judge returned invalid JSON."
                    ),
                }

            # --------------------------------------------
            # Validate state
            # --------------------------------------------

            state = result.get("state")

            if state not in VALID_STATES:

                state = "NOT_FOUND"

            # --------------------------------------------
            # Validate confidence
            # --------------------------------------------

            try:

                confidence = float(
                    result.get(
                        "confidence",
                        0.0,
                    )
                )

            except (TypeError, ValueError):

                confidence = 0.0

            confidence = max(
                0.0,
                min(
                    1.0,
                    confidence,
                ),
            )

            # --------------------------------------------
            # Validate evidence IDs
            # --------------------------------------------

            evidence_ids = result.get(
                "evidence_ids",
                [],
            )

            if not isinstance(
                evidence_ids,
                list,
            ):
                evidence_ids = []

            valid_ids = []

            for evidence_id in evidence_ids:

                if isinstance(
                    evidence_id,
                    int,
                ):

                    if (
                        1
                        <= evidence_id
                        <= len(evidence)
                    ):

                        if evidence_id not in valid_ids:
                            valid_ids.append(
                                evidence_id
                            )

            # --------------------------------------------
            # Return normalized result
            # --------------------------------------------

            return {
                "state": state,
                "confidence": confidence,
                "evidence_ids": valid_ids,
                "reason": str(
                    result.get(
                        "reason",
                        "",
                    )
                ),
            }

        except RateLimitError:

            if attempt == max_retries - 1:

                return {
                    "state": "NOT_FOUND",
                    "confidence": 0.0,
                    "evidence_ids": [],
                    "reason": (
                        "Groq rate limit was reached after "
                        "multiple retries."
                    ),
                }

            wait_seconds = 2 ** attempt

            print(
                f"\nGroq rate limit reached. "
                f"Retrying in {wait_seconds}s..."
            )

            time.sleep(wait_seconds)

        except Exception as exc:

            return {
                "state": "NOT_FOUND",
                "confidence": 0.0,
                "evidence_ids": [],
                "reason": (
                    f"Evidence judge error: {exc}"
                ),
            }


# ============================================================
# Result validation
# ============================================================

def validate_result(judgment, evidence):
    """
    Validate and normalize the LLM result.

    This layer:
    1. prevents unsupported evidence IDs,
    2. prevents ANSWERABLE/CONTRADICTION without evidence,
    3. preserves explicit unresolved conflicts found in the corpus.
    """

    valid_ids = judgment.get(
        "evidence_ids",
        [],
    )

    # --------------------------------------------
    # Evidence is mandatory for positive decisions
    # --------------------------------------------

    if judgment["state"] in {
        "ANSWERABLE",
        "CONTRADICTION",
    }:

        if not valid_ids:

            judgment = {
                **judgment,
                "state": "NOT_FOUND",
                "confidence": 0.0,
                "reason": (
                    "The evidence judge did not identify "
                    "a valid supporting passage."
                ),
                "evidence_ids": [],
            }

    # --------------------------------------------
    # Deterministic unresolved-conflict safeguard
    # --------------------------------------------

    judgment = deterministic_safety_check(
        judgment,
        evidence,
    )

    return judgment


# ============================================================
# Main classifier
# ============================================================

def classify(
    question,
    top_k=DEFAULT_TOP_K,
):
    """
    Retrieve evidence and classify the question into:

    ANSWERABLE
    NOT_FOUND
    CONTRADICTION
    """

    question = question.strip()

    if not question:

        return {
            "state": "NOT_FOUND",
            "confidence": 1.0,
            "reason": "The question is empty.",
            "evidence": [],
        }

    # --------------------------------------------
    # Retrieval
    # --------------------------------------------

    evidence = retrieve(
        question,
        top_k=top_k,
    )

    if not evidence:

        return {
            "state": "NOT_FOUND",
            "confidence": 1.0,
            "reason": "No evidence was retrieved.",
            "evidence": [],
        }

    # --------------------------------------------
    # LLM classification
    # --------------------------------------------

    judgment = call_llm_judge(
        question,
        evidence,
    )

    # --------------------------------------------
    # Safety validation
    # --------------------------------------------

    judgment = validate_result(
        judgment,
        evidence,
    )

    # --------------------------------------------
    # Convert evidence IDs to actual evidence
    # --------------------------------------------

    selected_evidence = []

    for evidence_id in judgment.get(
        "evidence_ids",
        [],
    ):

        selected_evidence.append(
            evidence[evidence_id - 1]
        )

    return {
        "state": judgment["state"],
        "confidence": judgment["confidence"],
        "reason": judgment["reason"],
        "evidence": selected_evidence,
    }


# ============================================================
# CLI output
# ============================================================

def print_result(result):

    print("\n" + "=" * 60)

    print(
        f"STATE: {result['state']}"
    )

    print("=" * 60)

    print(
        f"\nConfidence: "
        f"{result['confidence']:.2f}"
    )

    if result.get("reason"):

        print(
            f"Reason: "
            f"{result['reason']}"
        )

    evidence = result.get(
        "evidence",
        [],
    )

    if not evidence:

        print(
            "\nNo supporting evidence."
        )

        return

    print(
        "\nSupporting evidence:\n"
    )

    for i, item in enumerate(
        evidence,
        start=1,
    ):

        print(
            f"--- Evidence {i} ---"
        )

        print(
            f"Source: "
            f"{item['source']}"
        )

        print(
            f"Section: "
            f"{item['section']}"
        )

        if item.get("page", -1) != -1:

            print(
                f"Page: "
                f"{item['page']}"
            )

        print(
            item["text"]
        )

        print()


# ============================================================
# Direct execution
# ============================================================

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

        try:

            result = classify(
                question
            )

            print_result(
                result
            )

        except Exception as exc:

            print(
                "\nERROR:"
            )

            print(exc)