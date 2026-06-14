import os
import sys

# Ensure the repo root (parent of this file's directory) is on sys.path so that
# "from backend.xxx import ..." works whether you run:
#   python backend/main.py          (from d:\BOOK_RAG)
#   python main.py                  (from d:\BOOK_RAG\backend)
#   python -m backend.main          (from d:\BOOK_RAG)
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger

from backend.logs.config import setup_logging
from backend.api.router import router as api_router
from backend.api.auth_router import auth_router

setup_logging()

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AcademicOS API",
    version="2.0.0",
    description="Robust Academic RAG system with document management and JWT auth",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "AcademicOS API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "environment": os.getenv("ENVIRONMENT", "development")}


# ── Dev server entry ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    is_dev = os.getenv("ENVIRONMENT", "development") == "development"
    logger.info(f"Starting AcademicOS API (reload={is_dev})…")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=is_dev)
