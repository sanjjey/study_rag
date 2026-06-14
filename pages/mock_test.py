import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from services import load_services, get_subjects

svc = load_services()

st.title("📝 Mock Test")

subjects = get_subjects()
if not subjects:
    st.info("No documents uploaded yet. Go to **📤 Upload** to add study materials first.")
    st.stop()

with st.form("test_config"):
    c1, c2, c3, c4 = st.columns(4)
    t_subject = c1.selectbox("Subject",        ["All"] + subjects)
    t_diff    = c2.selectbox("Difficulty",     ["Easy", "Medium", "Hard", "Mixed"])
    t_types   = c3.selectbox("Question Types", ["Short Answer, MCQ", "MCQ", "Short Answer", "True/False", "Essay"])
    t_num     = c4.slider("Questions", 1, 15, 5)
    generate  = st.form_submit_button("🎯 Generate Test", type="primary", use_container_width=True)

if generate:
    with st.spinner("Generating test from your documents…"):
        filters = {"subject": t_subject} if t_subject != "All" else None
        ctx = svc["retrieval"].retrieve(
            query=f"Key concepts in {t_subject}", filters=filters, top_k=20, rerank_k=10
        )
        if not ctx:
            st.error(f"No documents found for **{t_subject}**. Upload relevant materials first.")
        else:
            test_content = svc["llm"].generate_mock_test(
                context=ctx,
                subject=t_subject,
                difficulty=t_diff,
                question_types=t_types,
                num_questions=t_num,
            )
            st.session_state.mock_test    = test_content
            st.session_state.mock_subject = t_subject
            st.session_state.eval_result  = None

if st.session_state.get("mock_test"):
    st.divider()
    st.subheader("📋 Practice Questions")
    st.markdown(st.session_state.mock_test)

    st.divider()
    st.subheader("✍️ Your Answers")
    student_ans = st.text_area(
        "Reference questions by number (Q1, Q2…)",
        height=220,
        key="student_answer",
        placeholder="Q1: ...\nQ2: ...",
    )

    if st.button("📊 Submit for Grading", type="primary"):
        if not student_ans.strip():
            st.warning("Write your answers before submitting.")
        else:
            with st.spinner("Grading…"):
                subj = st.session_state.get("mock_subject", "All")
                filters = {"subject": subj} if subj != "All" else None
                ctx = svc["retrieval"].retrieve(
                    query=f"concepts in {subj}", filters=filters, top_k=10, rerank_k=5
                )
                result = svc["llm"].evaluate_answer(
                    query=f"Mock test on {subj}",
                    student_answer=student_ans,
                    context=ctx,
                )
                st.session_state.eval_result = result

if st.session_state.get("eval_result"):
    st.divider()
    st.subheader("📊 Evaluation Report")
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", st.session_state.eval_result)
    if m:
        score = float(m.group(1))
        colour = "green" if score >= 7 else "orange" if score >= 5 else "red"
        st.markdown(
            f"<h2 style='color:{colour}'>Score: {score} / 10</h2>",
            unsafe_allow_html=True,
        )
    st.markdown(st.session_state.eval_result)
    if st.button("🔁 New Test"):
        st.session_state.mock_test   = None
        st.session_state.eval_result = None
        st.rerun()
