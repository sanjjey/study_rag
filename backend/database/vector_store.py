import os
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)
from loguru import logger

from backend.embeddings.manager import EmbeddingManager

_VECTOR_DIM = 768  # BAAI/bge-base-en-v1.5


class VectorStore:
    def __init__(self, collection_name: str = "academic_resources"):
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if not url or not api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY environment variables must be set")

        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name
        self.embedding_manager = EmbeddingManager()
        self._ensure_collection()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _ensure_collection(self):
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection '{self.collection_name}'")

    def _sanitize(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: v for k, v in metadata.items()
            if v is not None and isinstance(v, (str, int, float, bool))
        } | {
            k: str(v) for k, v in metadata.items()
            if v is not None and not isinstance(v, (str, int, float, bool))
        }

    def _build_filter(self, where: Dict) -> Filter:
        return Filter(
            must=[FieldCondition(key=k, match=MatchValue(value=v)) for k, v in where.items()]
        )

    def _scroll_all(self, query_filter: Optional[Filter]) -> list:
        points, offset = [], None
        while True:
            batch, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points.extend(batch)
            if next_offset is None:
                break
            offset = next_offset
        return points

    # ── Add chunks ────────────────────────────────────────────────────────────
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        try:
            documents = [c["text"] if isinstance(c, dict) else c.page_content for c in chunks]
            metadatas = [
                self._sanitize(c["metadata"] if isinstance(c, dict) else c.metadata)
                for c in chunks
            ]
            embeddings = self.embedding_manager.get_embeddings().embed_documents(documents)

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embeddings[i],
                        payload={**metadatas[i], "_text": documents[i]},
                    )
                    for i in range(len(documents))
                ],
            )
            logger.info(f"Added {len(chunks)} chunks to '{self.collection_name}'")
            return len(chunks)
        except Exception as e:
            logger.exception(f"Vector store insertion failed: {e}")
            raise

    # ── Search (returns ChromaDB-compatible dict for RetrievalEngine) ─────────
    def search(self, query: str, n_results: int = 5, where: Optional[Dict] = None) -> Dict:
        try:
            query_embedding = self.embedding_manager.get_embeddings().embed_query(query)
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=n_results,
                query_filter=self._build_filter(where) if where else None,
                with_payload=True,
            )
            documents, metadatas = [], []
            for hit in response.points:
                payload = dict(hit.payload)
                documents.append(payload.pop("_text", ""))
                metadatas.append(payload)

            return {"documents": [documents], "metadatas": [metadatas]}
        except Exception as e:
            logger.exception(f"Vector search failed: {e}")
            raise

    # ── List documents ────────────────────────────────────────────────────────
    def list_documents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            query_filter = self._build_filter({"user_id": user_id}) if user_id else None
            points = self._scroll_all(query_filter)

            seen: Dict[str, Dict] = {}
            for point in points:
                p = point.payload or {}
                key = p.get("book_name", p.get("original_filename", "unknown"))
                if key not in seen:
                    seen[key] = {
                        "book_name": key,
                        "original_filename": p.get("original_filename", key),
                        "subject": p.get("subject", ""),
                        "chapter": p.get("chapter", ""),
                        "chunk_count": 0,
                    }
                seen[key]["chunk_count"] += 1

            return list(seen.values())
        except Exception as e:
            logger.exception(f"list_documents failed: {e}")
            raise

    # ── Stats ─────────────────────────────────────────────────────────────────
    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            query_filter = self._build_filter({"user_id": user_id}) if user_id else None
            total_chunks = self.client.count(
                collection_name=self.collection_name,
                count_filter=query_filter,
                exact=True,
            ).count

            points = self._scroll_all(query_filter)
            unique_docs: set = set()
            subjects: set = set()
            for point in points:
                p = point.payload or {}
                if p.get("book_name"):
                    unique_docs.add(p["book_name"])
                if p.get("subject"):
                    subjects.add(p["subject"])

            return {
                "total_chunks": total_chunks,
                "total_documents": len(unique_docs),
                "subjects": sorted(subjects),
            }
        except Exception as e:
            logger.exception(f"get_stats failed: {e}")
            raise

    # ── Delete by metadata ────────────────────────────────────────────────────
    def delete_by_metadata(self, filter_criteria: Dict) -> int:
        if not filter_criteria:
            raise ValueError("Delete filter criteria cannot be empty")
        try:
            query_filter = self._build_filter(filter_criteria)
            count = self.client.count(
                collection_name=self.collection_name,
                count_filter=query_filter,
                exact=True,
            ).count
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(filter=query_filter),
            )
            logger.info(f"Deleted {count} chunks matching {filter_criteria}")
            return count
        except Exception as e:
            logger.exception(f"Vector deletion failed: {e}")
            raise
