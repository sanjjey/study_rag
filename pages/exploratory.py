import streamlit as st
from services import load_services

svc = load_services()

st.title("🧠 Exploratory Mode")
st.caption("Draws on broad AI knowledge — not limited to your documents")
st.info("Answers here are **not** verified against your uploaded files.", icon="ℹ️")

if st.button("🗑 Clear chat"):
    st.session_state.exp_msgs = []
    st.rerun()

if "exp_msgs" not in st.session_state:
    st.session_state.exp_msgs = []

for m in st.session_state.exp_msgs:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Explore any academic topic…"):
    st.session_state.exp_msgs.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer = svc["llm"].generate_hallucination_answer(prompt)
        st.markdown(answer)

    st.session_state.exp_msgs.append({"role": "assistant", "content": answer})
