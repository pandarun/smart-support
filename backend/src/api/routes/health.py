"""
Health Check Endpoint for Smart Support Operator API

Provides service availability status for frontend health monitoring.

Constitution Compliance:
- Principle I: Modular Architecture (checks module availability without tight coupling)
- Principle IV: API-First Integration (standard health endpoint pattern)
"""

from fastapi import APIRouter, status
from backend.src.api.models import HealthResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check API and service availability status",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with service availability status

    Checks:
        - Classification module: Always available (uses Scibox API)
        - Retrieval module: Available if embeddings precomputed
        - Embeddings count: Number of templates in cache
    """
    # Check classification availability (always available via Scibox API)
    classification_available = True

    # Check retrieval availability
    retrieval_available = False
    embeddings_count = 0

    try:
        from backend.src.api.routes.retrieval import get_retriever

        retriever = get_retriever()

        if retriever.is_ready():
            retrieval_available = True
            stats = retriever.get_cache_stats()
            embeddings_count = stats.get('total_templates', 0)

    except Exception as e:
        # Retriever not initialized or not ready
        logger.debug(f"Retrieval module not available: {e}")

    # Determine overall health status
    # System is healthy if both modules are available
    if classification_available and retrieval_available:
        overall_status = "healthy"
    elif classification_available:
        overall_status = "degraded"  # Classification works but retrieval doesn't
    else:
        overall_status = "unhealthy"

    logger.info(
        f"Health check: status={overall_status}, "
        f"classification={classification_available}, "
        f"retrieval={retrieval_available}, "
        f"embeddings={embeddings_count}"
    )

    return HealthResponse(
        status=overall_status,
        classification_available=classification_available,
        retrieval_available=retrieval_available,
        embeddings_count=embeddings_count,
    )
