import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from services import load_services, get_subjects

svc = load_services()

st.title("📤 Upload Documents")
st.caption("Supports PDF, PPTX, DOCX, TXT — up to 200 MB each")

# ── Subject selection ─────────────────────────────────────────────────────────
existing_subjects = get_subjects()

c1, c2 = st.columns(2)
with c1:
    if existing_subjects:
        options = existing_subjects + ["＋ Create new subject…"]
        choice = st.selectbox("Subject / Stream", options, key="upload_subject_select")
        if choice == "＋ Create new subject…":
            u_subject = st.text_input(
                "New subject name",
                placeholder="e.g. Organic Chemistry, DSA, World History",
                key="upload_subject_new",
            )
        else:
            u_subject = choice
    else:
        st.caption("No subjects yet — type one below to create your first.")
        u_subject = st.text_input(
            "Subject / Stream",
            placeholder="e.g. Physics, Economics, CS101",
            key="upload_subject_new",
        )

with c2:
    u_chapter = st.text_input(
        "Chapter / Topic (optional)",
        placeholder="e.g. Chapter 3: Thermodynamics",
    )

files = st.file_uploader(
    "Drop files here or click to browse",
    type=["pdf", "pptx", "docx", "txt"],
    accept_multiple_files=True,
)

if files and st.button("⬆️ Upload & Index", type="primary", use_container_width=True):
    if not u_subject or not u_subject.strip():
        st.error("Please enter or select a subject before uploading.")
    else:
        for f in files:
            with st.status(f"Processing **{f.name}**…", expanded=True) as status:
                try:
                    suffix = Path(f.name).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(f.read())
                        tmp_path = tmp.name

                    meta = {
                        "subject": u_subject.strip(),
                        "chapter": u_chapter.strip() if u_chapter else "",
                        "user_id": "default",
                        "original_filename": f.name,
                    }
                    result = svc["pipeline"].run(tmp_path, meta)
                    os.unlink(tmp_path)

                    if result["success"]:
                        status.update(
                            label=f"✅ **{f.name}** — {result['chunks']} chunks indexed under **{u_subject}**",
                            state="complete",
                        )
                    else:
                        status.update(label=f"❌ **{f.name}** — ingestion failed", state="error")

                except Exception as e:
                    status.update(label=f"❌ **{f.name}** — {e}", state="error")
