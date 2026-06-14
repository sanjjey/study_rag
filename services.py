import json
import os
import sys
import uuid
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


# ── Multi-session chat storage ────────────────────────────────────────────────
_CHAT_DIR = Path.home() / ".academicos"
_CHAT_DIR.mkdir(exist_ok=True)


def _sessions_path(kind: str) -> Path:
    return _CHAT_DIR / f"{kind}_sessions.json"


def load_sessions(kind: str) -> dict:
    """
    Returns:
        {
          "active_id": "<uuid>",
          "chats": {
              "<uuid>": {"title": "...", "messages": [...]}
          }
        }
    """
    p = _sessions_path(kind)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _fresh_sessions()


def save_sessions(kind: str, data: dict):
    try:
        _sessions_path(kind).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _fresh_sessions() -> dict:
    chat_id = str(uuid.uuid4())
    return {
        "active_id": chat_id,
        "chats": {chat_id: {"title": "New Chat", "messages": []}},
    }


def new_session(data: dict) -> str:
    """Add a new empty chat, set it active, return new id."""
    chat_id = str(uuid.uuid4())
    data["chats"][chat_id] = {"title": "New Chat", "messages": []}
    data["active_id"] = chat_id
    return chat_id


def delete_session(data: dict, chat_id: str):
    """Delete a chat. If it was active, switch to the most recent remaining one."""
    data["chats"].pop(chat_id, None)
    if not data["chats"]:
        new_id = str(uuid.uuid4())
        data["chats"][new_id] = {"title": "New Chat", "messages": []}
        data["active_id"] = new_id
    elif data["active_id"] == chat_id:
        data["active_id"] = list(data["chats"].keys())[-1]
