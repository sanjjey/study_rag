import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from services import load_services

svc = load_services()

st.title("📁 Document Library")

if st.button("🔄 Refresh"):
    st.rerun()

try:
    stats = svc["store"].get_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents", stats["total_documents"])
    c2.metric("Chunks",    stats["total_chunks"])
    c3.metric("Subjects",  len(stats.get("subjects", [])))

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
