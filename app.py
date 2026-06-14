import os
import re
import sys
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ── Path & env ────────────────────────────────────────────────────────────────
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

load_dotenv(os.path.join(_root, "backend", ".env"))

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="AcademicOS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Backend imports ───────────────────────────────────────────────────────────
from backend.ingestion.pipeline import IngestionPipeline
from backend.retrieval.engine import RetrievalEngine
from backend.api.llm_manager import LLMManager
from backend.database.vector_store import VectorStore
from backend.logs.config import setup_logging

setup_logging()

SUBJECTS = [
    "General", "Mathematics", "Physics", "Chemistry",
    "Biology", "Computer Science", "History",
    "Literature", "Economics", "Other",
]

# ── Cached singletons (loaded once per process, reused across reruns) ─────────
@st.cache_resource(show_spinner="Loading AI models… (first run only, ~30s)")
def load_services():
    return {
        "pipeline": IngestionPipeline(),
        "retrieval": RetrievalEngine(),
        "llm": LLMManager(),
        "store": VectorStore(),
    }

# ── Optional single-password gate ─────────────────────────────────────────────
_APP_PASSWORD = os.getenv("APP_PASSWORD", "")

def check_auth() -> bool:
    if not _APP_PASSWORD:
        return True
    if st.session_state.get("auth_ok"):
        return True

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<h1 style='text-align:center'>🎓 AcademicOS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:grey'>Enter the app password</p>", unsafe_allow_html=True)
        pw = st.text_input("Password", type="password", label_visibility="collapsed")
        if st.button("Sign in", use_container_width=True, type="primary"):
            if pw == _APP_PASSWORD:
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Incorrect password")
    return False

if not check_auth():
    st.stop()

svc = load_services()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 AcademicOS")
    st.caption("Your AI study companion")
    st.divider()
    page = st.radio(
        "Navigate",
        ["💬 RAG Chat", "🧠 Exploratory", "📝 Mock Test", "📤 Upload", "📁 Documents"],
        label_visibility="collapsed",
    )
    st.divider()
    if _APP_PASSWORD and st.button("🚪 Logout"):
        st.session_state.auth_ok = False
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 💬 RAG CHAT
# ═══════════════════════════════════════════════════════════════════════════════
if page == "💬 RAG Chat":
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


# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 EXPLORATORY
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🧠 Exploratory":
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


# ═══════════════════════════════════════════════════════════════════════════════
# 📝 MOCK TEST
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📝 Mock Test":
    st.title("📝 Mock Test")

    with st.form("test_config"):
        c1, c2, c3, c4 = st.columns(4)
        t_subject  = c1.selectbox("Subject",        SUBJECTS)
        t_diff     = c2.selectbox("Difficulty",     ["Easy", "Medium", "Hard", "Mixed"])
        t_types    = c3.selectbox("Question Types", ["Short Answer, MCQ", "MCQ", "Short Answer", "True/False", "Essay"])
        t_num      = c4.slider("Questions", 1, 15, 5)
        generate   = st.form_submit_button("🎯 Generate Test", type="primary", use_container_width=True)

    if generate:
        with st.spinner("Generating test from your documents…"):
            filters = {"subject": t_subject} if t_subject != "General" else None
            ctx = svc["retrieval"].retrieve(
                query=f"Key concepts in {t_subject}",
                filters=filters,
                top_k=20,
                rerank_k=10,
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
                    subj = st.session_state.get("mock_subject", "General")
                    filters = {"subject": subj} if subj != "General" else None
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


# ═══════════════════════════════════════════════════════════════════════════════
# 📤 UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📤 Upload":
    st.title("📤 Upload Documents")
    st.caption("Supports PDF, PPTX, DOCX, TXT — up to 20 MB each")

    c1, c2 = st.columns(2)
    u_subject = c1.selectbox("Subject", SUBJECTS, key="upload_subject")
    u_chapter = c2.text_input("Chapter / Topic (optional)", placeholder="e.g. Chapter 3: Thermodynamics")

    files = st.file_uploader(
        "Drop files here or click to browse",
        type=["pdf", "pptx", "docx", "txt"],
        accept_multiple_files=True,
    )

    if files and st.button("⬆️ Upload & Index", type="primary", use_container_width=True):
        for f in files:
            with st.status(f"Processing **{f.name}**…", expanded=True) as status:
                try:
                    suffix = Path(f.name).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(f.read())
                        tmp_path = tmp.name

                    meta = {
                        "subject": u_subject,
                        "chapter": u_chapter or "",
                        "user_id": "default",
                        "original_filename": f.name,
                    }
                    result = svc["pipeline"].run(tmp_path, meta)
                    os.unlink(tmp_path)

                    if result["success"]:
                        status.update(
                            label=f"✅ **{f.name}** — {result['chunks']} chunks indexed",
                            state="complete",
                        )
                    else:
                        status.update(label=f"❌ **{f.name}** — ingestion failed", state="error")

                except Exception as e:
                    status.update(label=f"❌ **{f.name}** — {e}", state="error")


# ═══════════════════════════════════════════════════════════════════════════════
# 📁 DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📁 Documents":
    st.title("📁 Document Library")

    if st.button("🔄 Refresh"):
        st.rerun()

    try:
        stats = svc["store"].get_stats()
        c1, c2, c3 = st.columns(3)
        c1.metric("Documents",   stats["total_documents"])
        c2.metric("Chunks",      stats["total_chunks"])
        c3.metric("Subjects",    len(stats.get("subjects", [])))

        docs = svc["store"].list_documents()

        if not docs:
            st.info("No documents yet. Go to **📤 Upload** to add study materials.")
        else:
            st.divider()
            hdr = st.columns([4, 2, 1, 1])
            hdr[0].markdown("**File**")
            hdr[1].markdown("**Subject**")
            hdr[2].markdown("**Chunks**")
            st.divider()

            for doc in docs:
                row = st.columns([4, 2, 1, 1])
                row[0].write(doc.get("original_filename") or doc["book_name"])
                row[1].caption(doc.get("subject") or "—")
                row[2].caption(str(doc["chunk_count"]))
                if row[3].button("🗑", key=f"del_{doc['book_name']}", help="Delete"):
                    with st.spinner("Deleting…"):
                        svc["store"].delete_by_metadata({"book_name": doc["book_name"]})
                    st.success(f"Deleted **{doc.get('original_filename') or doc['book_name']}**")
                    st.rerun()

    except Exception as e:
        st.error(f"Could not load documents: {e}")
