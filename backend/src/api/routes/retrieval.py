"""
Retrieval Endpoint for Smart Support Operator API

Provides template response retrieval based on classified inquiry.

Constitution Compliance:
- Principle I: Modular Architecture (wraps retrieval module)
- Principle IV: API-First Integration (REST endpoint for retrieval)
"""

from fastapi import APIRouter, status, HTTPException
from backend.src.api.models import (
    RetrievalRequest,
    RetrievalResponse,
    ErrorResponse
)
import logging
from typing import Optional

# Import will happen after retriever is initialized in main.py
from src.retrieval.retriever import TemplateRetriever

logger = logging.getLogger(__name__)

router = APIRouter()

# Global retriever instance (will be set in main.py lifespan)
_retriever: Optional[TemplateRetriever] = None


def set_retriever(retriever: TemplateRetriever):
    """
    Set global retriever instance (called from main.py lifespan).

    Args:
        retriever: Initialized TemplateRetriever instance
    """
    global _retriever
    _retriever = retriever
    logger.info("Retriever instance registered with API")


def get_retriever() -> TemplateRetriever:
    """
    Get global retriever instance.

    Returns:
        TemplateRetriever instance

    Raises:
        HTTPException: If retriever not initialized
    """
    if _retriever is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Retrieval service is not initialized. System is starting up.",
                "error_type": "api_error",
                "details": "Retriever not initialized"
            }
        )
    return _retriever


@router.post(
    "/retrieve",
    response_model=RetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve template responses",
    description="Find and rank relevant template responses for classified inquiry",
    responses={
        200: {
            "description": "Successful retrieval",
            "model": RetrievalResponse
        },
        400: {
            "description": "Validation error (invalid input)",
            "model": ErrorResponse
        },
        503: {
            "description": "Retrieval service unavailable",
            "model": ErrorResponse
        },
        504: {
            "description": "Retrieval timeout (>1s)",
            "model": ErrorResponse
        }
    }
)
async def retrieve_templates(request: RetrievalRequest) -> RetrievalResponse:
    """
    Retrieve and rank template responses for inquiry.

    This endpoint wraps the existing retrieval module and provides
    a REST API interface for the operator web interface.

    **Performance**: Must complete in < 1 second (FR-010)

    **Input Requirements**:
    - Query must be 5-5000 characters with Russian text
    - Category and subcategory from classification
    - top_k: 1-10 templates (default: 5)

    **Output**:
    - Ranked template results (sorted by relevance)
    - Each template includes question, answer, scores
    - Processing time and warnings

    Args:
        request: RetrievalRequest with query, category, subcategory

    Returns:
        RetrievalResponse with ranked template results

    Raises:
        HTTPException: If retrieval service unavailable or fails
    """
    try:
        # Get retriever instance
        retriever = get_retriever()

        logger.info(
            f"Retrieving templates: query={request.query[:50]}..., "
            f"category={request.category}, subcategory={request.subcategory}, "
            f"top_k={request.top_k}"
        )

        # Convert API model to retrieval model
        from src.retrieval.models import RetrievalRequest as SrcRetrievalRequest

        src_request = SrcRetrievalRequest(
            query=request.query,
            category=request.category,
            subcategory=request.subcategory,
            classification_confidence=request.classification_confidence or 0.0,
            top_k=request.top_k or 5,
            use_historical_weighting=request.use_historical_weighting or False
        )

        # Call retrieval module
        src_response = retriever.retrieve(src_request)

        logger.info(
            f"Retrieval successful: found {len(src_response.results)} templates, "
            f"time={src_response.processing_time_ms:.1f}ms"
        )

        # Convert retrieval model to API model
        from backend.src.api.models import TemplateResult

        api_results = [
            TemplateResult(
                template_id=r.template_id,
                template_question=r.template_question,
                template_answer=r.template_answer,
                category=r.category,
                subcategory=r.subcategory,
                similarity_score=r.similarity_score,
                combined_score=r.combined_score,
                rank=r.rank
            )
            for r in src_response.results
        ]

        return RetrievalResponse(
            query=src_response.query,
            category=src_response.category,
            subcategory=src_response.subcategory,
            results=api_results,
            total_candidates=src_response.total_candidates,
            processing_time_ms=src_response.processing_time_ms,
            warnings=src_response.warnings
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 503 from get_retriever)
        raise

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error during retrieval: {str(e)}", exc_info=True)

        # Determine error type
        error_message = str(e).lower()

        if "timeout" in error_message:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "error": "Retrieval took too long to complete. Please try again.",
                    "error_type": "timeout",
                    "details": str(e)
                }
            )
        elif "embeddings" in error_message or "api" in error_message:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Retrieval service is temporarily unavailable. Please try again.",
                    "error_type": "api_error",
                    "details": str(e)
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "An unexpected error occurred. Please try again or contact support.",
                    "error_type": "unknown",
                    "details": str(e)
                }
            )
