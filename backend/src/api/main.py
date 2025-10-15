"""
Smart Support Operator Web Interface - FastAPI Application

This module provides the FastAPI application factory with CORS middleware,
error handlers, and app lifecycle management.

Constitution Compliance:
- Principle I: Modular Architecture (wraps existing modules without modification)
- Principle IV: API-First Integration (OpenAPI auto-generation)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

from backend.src.api.routes import classification, retrieval, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("Smart Support Operator Interface starting up...")

    # Startup: Initialize retrieval module with pre-stored embeddings
    try:
        logger.info("Initializing retrieval module from stored embeddings...")
        import os
        import time
        from backend.src.api.routes import retrieval
        from src.retrieval.embeddings import EmbeddingsClient
        from src.retrieval.cache import EmbeddingCache
        from src.retrieval.retriever import TemplateRetriever
        from src.retrieval.storage.sqlite_backend import SQLiteBackend

        start_time = time.time()

        # Path to pre-stored embeddings database
        # Get project root (4 levels up from this file)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        embeddings_db_path = os.path.join(project_root, "data", "embeddings.db")

        logger.info(f"Loading embeddings from: {embeddings_db_path}")

        # Check if embeddings database exists
        if not os.path.exists(embeddings_db_path):
            raise FileNotFoundError(
                f"Embeddings database not found at: {embeddings_db_path}\n"
                "Please run embedding precomputation first."
            )

        # Initialize SQLite storage backend
        storage = SQLiteBackend(db_path=embeddings_db_path)
        storage.connect()

        # Create cache and load embeddings from storage
        cache = EmbeddingCache(storage_backend=storage)

        if not cache.is_ready:
            raise RuntimeError(
                f"Failed to load embeddings from {embeddings_db_path}. "
                "Database may be empty or corrupted."
            )

        # Initialize embeddings client (needed for query embedding)
        embeddings_client = EmbeddingsClient()

        # Create retriever with loaded cache
        retriever = TemplateRetriever(
            embeddings_client=embeddings_client,
            cache=cache
        )

        # Set global retriever instance for API routes
        retrieval.set_retriever(retriever)

        elapsed = time.time() - start_time
        stats = cache.stats

        logger.info(
            f"✓ Retrieval module initialized in {elapsed:.2f}s "
            f"({stats['total_templates']} templates from storage)"
        )

    except FileNotFoundError as e:
        logger.error(f"Embeddings database not found: {e}")
        logger.warning("API will start but retrieval endpoint will return 503")
        # Don't fail startup - allow API to run without retrieval

    except Exception as e:
        logger.error(f"Failed to initialize retrieval module: {e}", exc_info=True)
        logger.warning("API will start but retrieval endpoint will return 503")
        # Don't fail startup - allow API to run without retrieval

    yield

    # Shutdown: Cleanup
    logger.info("Smart Support Operator Interface shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Smart Support Operator API",
    description="REST API for operator interface to classify inquiries and retrieve template responses",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative port
        "http://localhost:8080",  # Docker deployment
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with user-friendly messages."""
    logger.warning(f"Validation error: {exc}")

    # Extract first error for user message
    first_error = exc.errors()[0] if exc.errors() else {}
    field = first_error.get('loc', ['unknown'])[-1]
    msg = first_error.get('msg', 'Validation failed')

    # Map to user-friendly message
    if 'cyrillic' in msg.lower() or field == 'text':
        error_message = "Please enter inquiry in Russian (at least 5 characters)"
    elif 'min_length' in msg.lower():
        error_message = "Inquiry must be at least 5 characters"
    elif 'max_length' in msg.lower():
        error_message = "Inquiry must not exceed 5000 characters"
    else:
        error_message = f"Invalid input: {msg}"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": error_message,
            "error_type": "validation",
            "timestamp": "2025-10-15T00:00:00Z",  # TODO: Use actual timestamp
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors with generic user message."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An unexpected error occurred. Please try again or contact support.",
            "error_type": "unknown",
            "details": str(exc),  # For logging, not shown to user
            "timestamp": "2025-10-15T00:00:00Z",  # TODO: Use actual timestamp
        }
    )


# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(classification.router, prefix="/api", tags=["classification"])
app.include_router(retrieval.router, prefix="/api", tags=["retrieval"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "Smart Support Operator API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
