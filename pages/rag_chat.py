import streamlit as st
from services import load_services, SUBJECTS

svc = load_services()

st.title("💬 RAG Chat")
st.caption("Answers grounded strictly in your uploaded documents")

c1, c2, c3 = st.columns([6, 2, 1])
with c2:
    subject = st.selectbox("Subject", SUBJECTS, key="rag_subject", label_visibility="collapsed")
with c3:
    if st.button("🗑 Clear"):
        st.session_state.rag_msgs = []
        st.rerun()

if "rag_msgs" not in st.session_state:
    st.session_state.rag_msgs = []

for m in st.session_state.rag_msgs:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            st.caption("📚 " + "  ·  ".join(m["sources"]))

if prompt := st.chat_input("Ask anything from your notes…"):
    st.session_state.rag_msgs.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching and reasoning…"):
            filters = {"subject": subject} if subject != "General" else None
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

    st.session_state.rag_msgs.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
