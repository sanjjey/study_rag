import os
import tempfile
from pathlib import Path

import streamlit as st
from services import load_services, SUBJECTS

svc = load_services()

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
