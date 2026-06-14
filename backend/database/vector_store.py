import chromadb
import os
import uuid
from typing import Any, Dict, List, Optional
from backend.embeddings.manager import EmbeddingManager
from loguru import logger


class VectorStore:
    def __init__(self, collection_name: str = "academic_resources"):
        db_path = os.getenv("CHROMA_DB_PATH", "../vector_db")
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection_name = collection_name
        self.embedding_manager = EmbeddingManager()

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=None,
        )

    # ── Metadata sanitisation ─────────────────────────────────────────────────
    def _sanitize(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                out[key] = value
            else:
                out[key] = str(value)
        return out

    # ── Add chunks ────────────────────────────────────────────────────────────
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        try:
            ids = [str(uuid.uuid4()) for _ in chunks]
            documents = [c["text"] if isinstance(c, dict) else c.page_content for c in chunks]
            metadatas = [
                self._sanitize(c["metadata"] if isinstance(c, dict) else c.metadata)
                for c in chunks
            ]
            embeddings = self.embedding_manager.get_embeddings().embed_documents(documents)

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(chunks)} chunks to '{self.collection_name}'")
            return len(chunks)
        except Exception as e:
            logger.exception(f"Vector store insertion failed: {e}")
            raise

    # ── Search ────────────────────────────────────────────────────────────────
    def search(self, query: str, n_results: int = 5, where: Optional[Dict] = None) -> Dict:
        try:
            query_embedding = self.embedding_manager.get_embeddings().embed_query(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where if where else None,
            )
            return results
        except Exception as e:
            logger.exception(f"Vector search failed: {e}")
            raise

    # ── List documents ────────────────────────────────────────────────────────
    def list_documents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            where = {"user_id": user_id} if user_id else None
            results = self.collection.get(where=where, include=["metadatas"])
            metadatas = results.get("metadatas") or []

            seen: Dict[str, Dict] = {}
            for meta in metadatas:
                if not meta:
                    continue
                key = meta.get("book_name", meta.get("original_filename", "unknown"))
                if key not in seen:
                    seen[key] = {
                        "book_name": key,
                        "original_filename": meta.get("original_filename", key),
                        "subject": meta.get("subject", ""),
                        "chapter": meta.get("chapter", ""),
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
            where = {"user_id": user_id} if user_id else None
            results = self.collection.get(where=where, include=["metadatas"])
            metadatas = results.get("metadatas") or []

            total_chunks = len(metadatas)
            unique_docs: set = set()
            subjects: set = set()
            for meta in metadatas:
                if not meta:
                    continue
                bk = meta.get("book_name")
                if bk:
                    unique_docs.add(bk)
                sub = meta.get("subject")
                if sub:
                    subjects.add(sub)

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
            # Fetch IDs matching criteria first
            results = self.collection.get(where=filter_criteria, include=[])
            ids = results.get("ids") or []
            if ids:
                self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} chunks matching {filter_criteria}")
            return len(ids)
        except Exception as e:
            logger.exception(f"Vector deletion failed: {e}")
            raise
