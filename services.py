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

from backend.ingestion.pipeline import IngestionPipeline
from backend.retrieval.engine import RetrievalEngine
from backend.api.llm_manager import LLMManager


@st.cache_resource(show_spinner="Loading AI models… (first run only, ~30s)")
def load_services():
    pipeline = IngestionPipeline()
    retrieval = RetrievalEngine()
    return {
        "pipeline": pipeline,
        "retrieval": retrieval,
        "llm": LLMManager(),
        "store": pipeline.vector_store,
    }


SUBJECTS = [
    "General", "Mathematics", "Physics", "Chemistry",
    "Biology", "Computer Science", "History",
    "Literature", "Economics", "Other",
]
