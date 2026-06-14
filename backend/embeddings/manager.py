import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

_embeddings = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-base-en-v1.5")
        _embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


class EmbeddingManager:
    def get_embeddings(self):
        return _get_embeddings()
