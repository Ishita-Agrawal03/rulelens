import streamlit as st

from src.answer import answer_question


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="RuleLens",
    page_icon="📘",
    layout="centered"
)


# =========================================================
# HEADER
# =========================================================

st.title("📘 RuleLens")

st.subheader(
    "Ask your university rulebook"
)

st.write(
    "Get answers grounded in the regulation corpus, "
    "with exact sources and explicit handling of "
    "unknown or conflicting rules."
)


# =========================================================
# QUESTION INPUT
# =========================================================

question = st.text_input(
    "Ask a question",
    placeholder="e.g. When is the semester fee due?"
)


ask = st.button(
    "Ask RuleLens",
    type="primary"
)


# =========================================================
# PROCESS QUESTION
# =========================================================

if ask and question.strip():

    with st.spinner("Searching the rulebook..."):

        result = answer_question(
            question.strip()
        )

    state = result["state"]


    # =====================================================
    # ANSWERABLE
    # =====================================================

    if state == "ANSWERABLE":

        st.success(
            "ANSWERABLE"
        )

        st.markdown(
            "### Answer"
        )

        st.write(
            result["answer"]
        )

        st.markdown(
            "### Sources"
        )

        for index, source in enumerate(
            result["sources"],
            start=1
        ):

            with st.expander(
                f"Source {index}: {source['source']}"
            ):

                st.write(
                    f"**Section:** {source['section']}"
                )

                if source["page"] != -1:

                    st.write(
                        f"**Page:** {source['page']}"
                    )

                st.markdown(
                    "**Passage:**"
                )

                st.info(
                    source["passage"]
                )


    # =====================================================
    # CONTRADICTION
    # =====================================================

    elif state == "CONTRADICTION":

        st.warning(
            "CONTRADICTION"
        )

        st.markdown(
            "### Answer"
        )

        st.write(
            result["answer"]
        )

        st.markdown(
            "### Conflicting Sources"
        )

        for index, source in enumerate(
            result["sources"],
            start=1
        ):

            with st.expander(
                f"Conflicting Rule {index}: "
                f"{source['source']}"
            ):

                st.write(
                    f"**Section:** {source['section']}"
                )

                if source["page"] != -1:

                    st.write(
                        f"**Page:** {source['page']}"
                    )

                st.markdown(
                    "**Exact passage:**"
                )

                st.info(
                    source["passage"]
                )


    # =====================================================
    # NOT FOUND
    # =====================================================

    elif state == "NOT_FOUND":

        st.error(
            "NOT FOUND"
        )

        st.markdown(
            "### Answer"
        )

        st.write(
            result["answer"]
        )


# =========================================================
# EMPTY QUESTION
# =========================================================

elif ask:

    st.warning(
        "Please enter a question."
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "RuleLens answers only from the provided regulation corpus. "
    "It does not rely on model memory for policy decisions."
)