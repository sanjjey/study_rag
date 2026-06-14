from backend.database.vector_store import VectorStore
from sentence_transformers import CrossEncoder
import os
from typing import List, Dict, Any
from loguru import logger

class RetrievalEngine:
    def __init__(self):
        self.vector_store = VectorStore()
        reranker_model = os.getenv("RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.reranker = CrossEncoder(reranker_model)

    def retrieve(self, query: str, top_k: int = 10, rerank_k: int = 5, filters: Dict = None) -> List[Dict[str, Any]]:
        # 1. Vector Search (Initial Retrieval)
        results = self.vector_store.search(query, n_results=top_k, where=filters)
        
        if not results or not results['documents'][0]:
            return []

        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        # 2. Reranking
        pairs = [[query, doc] for doc in documents]
        scores = self.reranker.predict(pairs)
        
        # Combine and sort
        combined = []
        for i in range(len(documents)):
            combined.append({
                "text": documents[i],
                "metadata": metadatas[i],
                "rerank_score": float(scores[i])
            })
        
        combined.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Return top reranked results
        return combined[:rerank_k]
