from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Any
from loguru import logger

class ChunkProcessor:
    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )

    def process(self, documents: List[Dict[str, Any]], global_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        for doc in documents:
            text = doc["text"]
            if not text.strip():
                continue
            
            # Combine doc-specific metadata with global metadata
            base_metadata = {**global_metadata, **doc.get("metadata", {})}
            
            # Split text into chunks
            text_chunks = self.splitter.split_text(text)
            
            for i, chunk_text in enumerate(text_chunks):
                chunk_metadata = base_metadata.copy()
                chunk_metadata["chunk_index"] = i
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })
        
        logger.info(f"Generated {len(chunks)} chunks from {len(documents)} document parts.")
        return chunks
