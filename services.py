import json
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


# ── Cached services ───────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading AI models… (first run only, ~30s)")
def load_services():
    # Lazy imports — only load heavy backend when services are first requested
    from backend.ingestion.pipeline import IngestionPipeline
    from backend.retrieval.engine import RetrievalEngine
    from backend.api.llm_manager import LLMManager

    pipeline = IngestionPipeline()
    retrieval = RetrievalEngine()
    return {
        "pipeline": pipeline,
        "retrieval": retrieval,
        "llm": LLMManager(),
        "store": pipeline.vector_store,
    }


# ── Subject helpers ───────────────────────────────────────────────────────────
def get_subjects() -> list:
    try:
        stats = load_services()["store"].get_stats()
        return sorted(s for s in stats.get("subjects", []) if s)
    except Exception:
        return []


# ── Chat persistence ──────────────────────────────────────────────────────────
_CHAT_DIR = Path.home() / ".academicos"
_CHAT_DIR.mkdir(exist_ok=True)


def _chat_path(name: str) -> Path:
    return _CHAT_DIR / f"{name}.json"


def load_chat(name: str) -> list:
    p = _chat_path(name)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_chat(name: str, messages: list):
    try:
        _chat_path(name).write_text(
            json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def delete_chat(name: str):
    p = _chat_path(name)
    if p.exists():
        p.unlink()
