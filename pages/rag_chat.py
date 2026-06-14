import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from services import (
    load_services, get_subjects,
    load_sessions, save_sessions, new_session, delete_session,
)

svc = load_services()

# ── Load / initialise sessions ────────────────────────────────────────────────
if "rag_sessions" not in st.session_state:
    st.session_state.rag_sessions = load_sessions("rag")

data = st.session_state.rag_sessions
active_id = data["active_id"]
chats = data["chats"]

# ── Sidebar: conversation list ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("#### 💬 Conversations")
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_session(data)
        save_sessions("rag", data)
        st.rerun()

    st.divider()

    for cid in reversed(list(chats.keys())):
        chat = chats[cid]
        is_active = cid == active_id
        col1, col2 = st.columns([5, 1])
        if col1.button(
            chat["title"][:38],
            key=f"rag_sw_{cid}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            data["active_id"] = cid
            save_sessions("rag", data)
            st.rerun()
        if col2.button("🗑", key=f"rag_del_{cid}", help="Delete"):
            delete_session(data, cid)
            save_sessions("rag", data)
            st.rerun()

# ── Active chat ───────────────────────────────────────────────────────────────
current  = chats[data["active_id"]]          # re-read after possible rerun
messages = current["messages"]

st.title("💬 RAG Chat")
st.caption("Answers grounded strictly in your uploaded documents")

subjects = get_subjects()
c1, c2 = st.columns([8, 3])
with c2:
    options = ["All Documents"] + subjects
    subject = st.selectbox("Filter", options, key="rag_subject", label_visibility="collapsed")

# Render history
for m in messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            st.caption("📚 " + "  ·  ".join(m["sources"]))

# New message
if prompt := st.chat_input("Ask anything from your notes…"):
    # Auto-title from first user message
    if not messages:
        current["title"] = prompt[:40] + ("…" if len(prompt) > 40 else "")

    messages.append({"role": "user", "content": prompt})
    save_sessions("rag", data)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching and reasoning…"):
            filters = {"subject": subject} if subject != "All Documents" else None
            ctx = svc["retrieval"].retrieve(query=prompt, filters=filters, top_k=10, rerank_k=5)

            if not ctx:
                answer = (
                    "⚠️ No relevant content found in your documents. "
                    "Upload study materials first, or switch to **🧠 Exploratory** mode."
                )
                sources = []
            else:
                answer = svc["llm"].generate_rag_answer(prompt, ctx)
                seen, sources = set(), []
                for c in ctx:
                    name = c.get("metadata", {}).get("book_name", "Unknown")
                    if name not in seen:
                        seen.add(name)
                        sources.append(name)

        st.markdown(answer)
        if sources:
            st.caption("📚 " + "  ·  ".join(sources))

    messages.append({"role": "assistant", "content": answer, "sources": sources})
    save_sessions("rag", data)
