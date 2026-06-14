import os
import shutil
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.ingestion.pipeline import IngestionPipeline
from backend.retrieval.engine import RetrievalEngine
from backend.api.llm_manager import LLMManager
from backend.database.vector_store import VectorStore
from backend.security.auth import User, get_current_user
from loguru import logger

router = APIRouter()

# ── Lazy service singletons ───────────────────────────────────────────────────
_pipeline: Optional[IngestionPipeline] = None
_retrieval_engine: Optional[RetrievalEngine] = None
_llm_manager: Optional[LLMManager] = None
_vector_store: Optional[VectorStore] = None


def _get_pipeline() -> IngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline


def _get_retrieval_engine() -> RetrievalEngine:
    global _retrieval_engine
    if _retrieval_engine is None:
        _retrieval_engine = RetrievalEngine()
    return _retrieval_engine


def _get_llm_manager() -> LLMManager:
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


# ── Config ────────────────────────────────────────────────────────────────────
_MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_MB", "20")) * 1024 * 1024
_ALLOWED_EXTENSIONS = set(
    os.getenv("ALLOWED_EXTENSIONS", ".pdf,.pptx,.docx,.txt").split(",")
)
_DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "10"))
_DEFAULT_RERANK_K = int(os.getenv("DEFAULT_RERANK_K", "5"))


# ── Request / Response Models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    subject: Optional[str] = None
    filters: Optional[dict] = None
    top_k: int = Field(default=10, ge=1, le=50)
    rerank_k: int = Field(default=5, ge=1, le=20)


class MockTestRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    difficulty: str = "Medium"
    types: str = "Short Answer, MCQ"
    num_questions: int = Field(default=5, ge=1, le=20)


class EvaluateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    student_answer: str = Field(..., min_length=1)


class DeleteDocumentRequest(BaseModel):
    book_name: str


# ── Upload ────────────────────────────────────────────────────────────────────
@router.post("/upload", tags=["documents"])
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form(...),
    chapter: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{ext}' is not allowed. Permitted: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {os.getenv('MAX_FILE_SIZE_MB', '20')} MB limit",
        )

    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
    file_path = os.path.join(temp_dir, safe_name)

    try:
        with open(file_path, "wb") as buf:
            buf.write(content)

        metadata = {
            "subject": subject,
            "chapter": chapter or "",
            "user_id": current_user.user_id,
            "original_filename": file.filename,
        }

        pipeline = _get_pipeline()
        result = pipeline.run(file_path, metadata)

        if not result["success"]:
            raise HTTPException(status_code=500, detail="Document ingestion failed at pipeline stage")

        return {
            "message": f"Successfully uploaded and indexed '{file.filename}'",
            "chunks_created": result["chunks"],
            "book_name": result["book_name"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Upload failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ── List Documents ────────────────────────────────────────────────────────────
@router.get("/documents", tags=["documents"])
async def list_documents(current_user: User = Depends(get_current_user)):
    try:
        vs = _get_vector_store()
        docs = vs.list_documents(user_id=current_user.user_id)
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        logger.exception(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve document list")


# ── Delete Document ───────────────────────────────────────────────────────────
@router.delete("/documents", tags=["documents"])
async def delete_document(
    body: DeleteDocumentRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        vs = _get_vector_store()
        deleted = vs.delete_by_metadata({"book_name": body.book_name, "user_id": current_user.user_id})
        return {"message": f"Deleted '{body.book_name}'", "chunks_removed": deleted}
    except Exception as e:
        logger.exception(f"Delete failed for {body.book_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# ── Collection Stats ──────────────────────────────────────────────────────────
@router.get("/documents/stats", tags=["documents"])
async def get_stats(current_user: User = Depends(get_current_user)):
    try:
        vs = _get_vector_store()
        return vs.get_stats(user_id=current_user.user_id)
    except Exception as e:
        logger.exception(f"Stats fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve stats")


# ── RAG Chat ──────────────────────────────────────────────────────────────────
@router.post("/chat/rag", tags=["chat"])
async def chat_rag(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        retrieval_engine = _get_retrieval_engine()
        llm_manager = _get_llm_manager()

        filters: dict = {"user_id": current_user.user_id}
        if request.subject:
            filters["subject"] = request.subject
        if request.filters:
            filters.update(request.filters)

        context = retrieval_engine.retrieve(
            query=request.query,
            filters=filters,
            top_k=request.top_k,
            rerank_k=request.rerank_k,
        )

        if not context:
            return {
                "answer": (
                    "No relevant content found in your uploaded documents. "
                    "Try uploading more material or switch to Exploratory mode."
                ),
                "context": [],
                "sources": [],
            }

        answer = llm_manager.generate_rag_answer(query=request.query, context=context)
        sources = _extract_sources(context)

        return {"answer": answer, "context": context, "sources": sources}

    except Exception as e:
        logger.exception(f"RAG chat error: {e}")
        raise HTTPException(status_code=500, detail=f"RAG chat failed: {str(e)}")


# ── Exploratory (Hallucination) Chat ─────────────────────────────────────────
@router.post("/chat/hallucinate", tags=["chat"])
async def chat_hallucinate(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        llm_manager = _get_llm_manager()
        answer = llm_manager.generate_hallucination_answer(query=request.query)
        return {"answer": answer}
    except Exception as e:
        logger.exception(f"Exploratory chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Exploratory mode failed: {str(e)}")


# ── Mock Test Generator ───────────────────────────────────────────────────────
@router.post("/mock-test/generate", tags=["mock-test"])
async def generate_test(
    request: MockTestRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        retrieval_engine = _get_retrieval_engine()
        llm_manager = _get_llm_manager()

        filters: dict = {"user_id": current_user.user_id}
        if request.subject.lower() != "general":
            filters["subject"] = request.subject

        context = retrieval_engine.retrieve(
            query=f"Key concepts in {request.subject}",
            filters=filters,
            top_k=20,
            rerank_k=10,
        )

        if not context:
            raise HTTPException(
                status_code=404,
                detail=f"No documents found for subject '{request.subject}'. Upload relevant materials first.",
            )

        test_content = llm_manager.generate_mock_test(
            context=context,
            subject=request.subject,
            difficulty=request.difficulty,
            question_types=request.types,
            num_questions=request.num_questions,
        )

        return {"test": test_content, "subject": request.subject, "difficulty": request.difficulty}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Mock test generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")


# ── Mock Test Evaluator ───────────────────────────────────────────────────────
@router.post("/mock-test/evaluate", tags=["mock-test"])
async def evaluate_test(
    request: EvaluateRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        retrieval_engine = _get_retrieval_engine()
        llm_manager = _get_llm_manager()

        filters = {"user_id": current_user.user_id}
        context = retrieval_engine.retrieve(request.query, filters=filters, top_k=_DEFAULT_TOP_K, rerank_k=_DEFAULT_RERANK_K)

        evaluation = llm_manager.evaluate_answer(
            query=request.query,
            student_answer=request.student_answer,
            context=context,
        )

        return {"evaluation": evaluation}

    except Exception as e:
        logger.exception(f"Evaluation error: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _extract_sources(context: list) -> list:
    seen = set()
    sources = []
    for chunk in context:
        meta = chunk.get("metadata") or {}
        name = meta.get("book_name") or meta.get("original_filename", "Unknown")
        if name not in seen:
            seen.add(name)
            sources.append({
                "name": name,
                "subject": meta.get("subject", ""),
                "chapter": meta.get("chapter", ""),
            })
    return sources
