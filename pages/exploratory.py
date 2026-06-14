import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from services import (
    load_services,
    load_sessions, save_sessions, new_session, delete_session,
)

svc = load_services()

# ── Load / initialise sessions ────────────────────────────────────────────────
if "exp_sessions" not in st.session_state:
    st.session_state.exp_sessions = load_sessions("exploratory")

data = st.session_state.exp_sessions
chats = data["chats"]

# ── Sidebar: conversation list ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("#### 🧠 Conversations")
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_session(data)
        save_sessions("exploratory", data)
        st.rerun()

    st.divider()

    for cid in reversed(list(chats.keys())):
        chat = chats[cid]
        is_active = cid == data["active_id"]
        col1, col2 = st.columns([5, 1])
        if col1.button(
            chat["title"][:38],
            key=f"exp_sw_{cid}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            data["active_id"] = cid
            save_sessions("exploratory", data)
            st.rerun()
        if col2.button("🗑", key=f"exp_del_{cid}", help="Delete"):
            delete_session(data, cid)
            save_sessions("exploratory", data)
            st.rerun()

# ── Active chat ───────────────────────────────────────────────────────────────
current  = chats[data["active_id"]]
messages = current["messages"]

st.title("🧠 Exploratory Mode")
st.caption("Draws on broad AI knowledge — not limited to your documents")
st.info("Answers here are **not** verified against your uploaded files.", icon="ℹ️")

for m in messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Explore any academic topic…"):
    if not messages:
        current["title"] = prompt[:40] + ("…" if len(prompt) > 40 else "")

    messages.append({"role": "user", "content": prompt})
    save_sessions("exploratory", data)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer = svc["llm"].generate_hallucination_answer(prompt)
        st.markdown(answer)

    messages.append({"role": "assistant", "content": answer})
    save_sessions("exploratory", data)
