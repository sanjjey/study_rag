import os
from typing import Any, Dict

from backend.parsers.manager import ParserManager
from backend.chunking.processor import ChunkProcessor
from backend.database.vector_store import VectorStore
from loguru import logger


class IngestionPipeline:
    def __init__(self):
        self.parser = ParserManager()
        self.chunker = ChunkProcessor()
        self.vector_store = VectorStore()

    def run(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Ingestion started: {file_path}")

        documents = self.parser.parse(file_path)
        if not documents:
            logger.error(f"Parsing returned no content for: {file_path}")
            return {"success": False, "chunks": 0, "book_name": ""}

        book_name = os.path.basename(file_path)
        metadata["book_name"] = book_name

        chunks = self.chunker.process(documents, metadata)
        if not chunks:
            logger.warning(f"Chunking produced no chunks for: {file_path}")
            return {"success": False, "chunks": 0, "book_name": book_name}

        count = self.vector_store.add_chunks(chunks)
        logger.info(f"Ingestion complete: {file_path} → {count} chunks stored")

        return {"success": True, "chunks": count, "book_name": book_name}
