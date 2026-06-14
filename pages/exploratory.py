import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from services import load_services, load_chat, save_chat, delete_chat

svc = load_services()

st.title("🧠 Exploratory Mode")
st.caption("Draws on broad AI knowledge — not limited to your documents")
st.info("Answers here are **not** verified against your uploaded files.", icon="ℹ️")

if st.button("🗑 Delete chat history"):
    st.session_state.exp_msgs = []
    delete_chat("exploratory")
    st.rerun()

if "exp_msgs" not in st.session_state:
    st.session_state.exp_msgs = load_chat("exploratory")

for m in st.session_state.exp_msgs:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Explore any academic topic…"):
    st.session_state.exp_msgs.append({"role": "user", "content": prompt})
    save_chat("exploratory", st.session_state.exp_msgs)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer = svc["llm"].generate_hallucination_answer(prompt)
        st.markdown(answer)

    st.session_state.exp_msgs.append({"role": "assistant", "content": answer})
    save_chat("exploratory", st.session_state.exp_msgs)
