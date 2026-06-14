import os
from typing import Any, Dict, List

from loguru import logger
from sentence_transformers import CrossEncoder

from backend.database.vector_store import VectorStore

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        model_name = os.getenv("RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        _reranker = CrossEncoder(model_name)
    return _reranker


class RetrievalEngine:
    def __init__(self):
        self.vector_store = VectorStore()

    def retrieve(self, query: str, top_k: int = 10, rerank_k: int = 5, filters: Dict = None) -> List[Dict[str, Any]]:
        results = self.vector_store.search(query, n_results=top_k, where=filters)

        if not results or not results["documents"][0]:
            return []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]

        reranker = _get_reranker()
        scores = reranker.predict([[query, doc] for doc in documents])

        combined = sorted(
            [
                {"text": documents[i], "metadata": metadatas[i], "rerank_score": float(scores[i])}
                for i in range(len(documents))
            ],
            key=lambda x: x["rerank_score"],
            reverse=True,
        )

        return combined[:rerank_k]
