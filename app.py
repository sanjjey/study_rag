import os
import sys
from pathlib import Path

_root = str(Path(__file__).parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(_root, "backend", ".env"))

try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

st.set_page_config(
    page_title="AcademicOS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth gate ─────────────────────────────────────────────────────────────────
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

# ── Sidebar header ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 AcademicOS")
    st.caption("Your AI study companion")
    st.divider()

# ── Pages ─────────────────────────────────────────────────────────────────────
pg = st.navigation(
    [
        st.Page("pages/rag_chat.py",    title="RAG Chat",    icon="💬", default=True),
        st.Page("pages/exploratory.py", title="Exploratory", icon="🧠"),
        st.Page("pages/mock_test.py",   title="Mock Test",   icon="📝"),
        st.Page("pages/upload.py",      title="Upload",      icon="📤"),
        st.Page("pages/documents.py",   title="Documents",   icon="📁"),
    ],
    position="sidebar",
)

if _APP_PASSWORD:
    with st.sidebar:
        st.divider()
        if st.button("🚪 Logout"):
            st.session_state.auth_ok = False
            st.rerun()

pg.run()
