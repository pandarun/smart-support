"""
Template Retrieval Module - Initialization and Public API.

Provides initialization function for system startup:
- initialize_retrieval(): Precompute embeddings and return ready retriever

Public exports:
- TemplateRetriever: Main retrieval orchestrator
- RetrievalRequest/RetrievalResponse: Request/response models
- initialize_retrieval(): System initialization function
"""

import os
import logging
from typing import Optional

from src.retrieval.embeddings import EmbeddingsClient, precompute_embeddings
from src.retrieval.cache import EmbeddingCache
from src.retrieval.retriever import TemplateRetriever
from src.retrieval.models import RetrievalRequest, RetrievalResponse

logger = logging.getLogger(__name__)


from src.retrieval.integration import classify_and_retrieve, format_integrated_result, IntegratedResult

__all__ = [
    "initialize_retrieval",
    "TemplateRetriever",
    "RetrievalRequest",
    "RetrievalResponse",
    "EmbeddingsClient",
    "EmbeddingCache",
    "classify_and_retrieve",
    "format_integrated_result",
    "IntegratedResult",
]


async def initialize_retrieval(
    faq_path: Optional[str] = None,
    api_key: Optional[str] = None,
    embedding_model: str = "bge-m3",
    batch_size: int = 20
) -> TemplateRetriever:
    """
    Initialize Template Retrieval Module with embedding precomputation.

    This is the main entry point for system startup. It will:
    1. Initialize Scibox embeddings API client
    2. Load FAQ templates from database
    3. Precompute embeddings for all templates (may take 30-60s)
    4. Return ready-to-use TemplateRetriever instance

    Performance expectation: <60 seconds for 200 templates (PR-002)

    Args:
        faq_path: Path to FAQ Excel database
                  Defaults to FAQ_PATH environment variable
        api_key: Scibox API key
                 Defaults to SCIBOX_API_KEY environment variable
        embedding_model: Embedding model name (default: bge-m3)
        batch_size: Number of templates per API batch (default: 20)

    Returns:
        TemplateRetriever instance ready to handle retrieval requests

    Raises:
        ValueError: If API key or FAQ path not provided/found
        FileNotFoundError: If FAQ database file not found
        EmbeddingsError: If precomputation fails (all batches fail)

    Example:
        >>> import asyncio
        >>> retriever = asyncio.run(initialize_retrieval())
        >>> retriever.is_ready()
        True
        >>>
        >>> # Use retriever
        >>> request = RetrievalRequest(
        ...     query="0: >B:@KBL AG5B?",
        ...     category="!G5B0 8 2:;04K",
        ...     subcategory="B:@KB85 AG5B0"
        ... )
        >>> response = retriever.retrieve(request)
        >>> len(response.results)
        5
    """
    logger.info("Initializing Template Retrieval Module...")

    # Get FAQ path from environment if not provided
    if faq_path is None:
        faq_path = os.getenv("FAQ_PATH")
        if not faq_path:
            raise ValueError(
                "FAQ path not provided and FAQ_PATH environment variable not set. "
                "Set FAQ_PATH or pass faq_path parameter."
            )

    logger.info(f"FAQ database path: {faq_path}")

    # Verify FAQ file exists
    if not os.path.exists(faq_path):
        raise FileNotFoundError(f"FAQ database not found: {faq_path}")

    # Get embedding model from environment if not specified
    if embedding_model == "bge-m3":
        embedding_model = os.getenv("EMBEDDING_MODEL", "bge-m3")

    logger.info(f"Embedding model: {embedding_model}")

    # Initialize embeddings client
    try:
        embeddings_client = EmbeddingsClient(
            api_key=api_key,
            model=embedding_model
        )
        logger.info(" Embeddings client initialized")
    except ValueError as e:
        logger.error(f"Failed to initialize embeddings client: {e}")
        raise

    # Precompute embeddings
    logger.info(f"Starting embedding precomputation (batch_size={batch_size})...")
    logger.info("� This may take 30-60 seconds for ~200 templates")

    try:
        cache = await precompute_embeddings(
            faq_path=faq_path,
            embeddings_client=embeddings_client,
            batch_size=batch_size
        )
        logger.info(" Embedding precomputation complete")
    except Exception as e:
        logger.error(f"Failed to precompute embeddings: {e}")
        raise

    # Log cache statistics
    stats = cache.stats
    logger.info(
        f"Cache ready: {stats['total_templates']} templates, "
        f"{stats['categories']} categories, "
        f"{stats['memory_estimate_mb']:.2f} MB memory"
    )

    # Initialize retriever
    try:
        retriever = TemplateRetriever(
            embeddings_client=embeddings_client,
            cache=cache
        )
        logger.info(" Template retriever initialized and ready")
    except ValueError as e:
        logger.error(f"Failed to initialize retriever: {e}")
        raise

    # Final readiness check
    if not retriever.is_ready():
        raise RuntimeError("Retriever initialization failed - not ready")

    logger.info(
        f"=� Template Retrieval Module ready! "
        f"({stats['total_templates']} templates in {cache.precompute_time:.1f}s)"
    )

    return retriever


def get_initialization_status(retriever: Optional[TemplateRetriever]) -> dict:
    """
    Get current initialization status of retrieval module.

    Used for health/readiness checks in production systems.

    Args:
        retriever: TemplateRetriever instance (None if not initialized)

    Returns:
        Dictionary with status information:
        - ready: bool - Whether system is ready
        - total_templates: int - Number of templates (0 if not ready)
        - categories: int - Number of categories
        - precompute_time_seconds: float - Time taken to precompute

    Example:
        >>> status = get_initialization_status(retriever)
        >>> status['ready']
        True
        >>> status['total_templates']
        187
    """
    if retriever is None or not retriever.is_ready():
        return {
            "ready": False,
            "status": "not_initialized",
            "total_templates": 0,
            "categories": 0,
            "precompute_time_seconds": None,
            "message": "Retrieval module not initialized"
        }

    stats = retriever.get_cache_stats()

    return {
        "ready": True,
        "status": "ready",
        "total_templates": stats["total_templates"],
        "categories": stats["categories"],
        "subcategories": stats["subcategories"],
        "precompute_time_seconds": stats["precompute_time_seconds"],
        "memory_estimate_mb": stats["memory_estimate_mb"],
        "message": "Retrieval module ready to handle requests"
    }
