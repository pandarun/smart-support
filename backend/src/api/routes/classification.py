"""
Classification Endpoint for Smart Support Operator API

Provides customer inquiry classification into categories and subcategories.

Constitution Compliance:
- Principle I: Modular Architecture (wraps classification module)
- Principle IV: API-First Integration (REST endpoint for classification)
"""

from fastapi import APIRouter, status, HTTPException
from backend.src.api.models import (
    ClassificationRequest,
    ClassificationResult,
    ErrorResponse
)
import logging
from src.classification.classifier import classify, ClassificationError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/classify",
    response_model=ClassificationResult,
    status_code=status.HTTP_200_OK,
    summary="Classify customer inquiry",
    description="Analyze inquiry text and determine product category and subcategory",
    responses={
        200: {
            "description": "Successful classification",
            "model": ClassificationResult
        },
        400: {
            "description": "Validation error (invalid input)",
            "model": ErrorResponse
        },
        503: {
            "description": "Classification service unavailable",
            "model": ErrorResponse
        },
        504: {
            "description": "Classification timeout (>2s)",
            "model": ErrorResponse
        }
    }
)
async def classify_inquiry(request: ClassificationRequest) -> ClassificationResult:
    """
    Classify customer inquiry into category and subcategory.

    This endpoint wraps the existing classification module and provides
    a REST API interface for the operator web interface.

    **Performance**: Must complete in < 2 seconds (FR-005)

    **Input Requirements**:
    - Inquiry must be 5-5000 characters
    - Must contain at least one Cyrillic character (Russian text)

    **Output**:
    - Category: Top-level product category
    - Subcategory: Second-level classification
    - Confidence: Classification confidence score (0.0-1.0)
    - Processing time: Time taken in milliseconds

    Args:
        request: ClassificationRequest with inquiry text

    Returns:
        ClassificationResult with category, subcategory, and confidence

    Raises:
        HTTPException: If classification service unavailable or fails
    """
    try:
        logger.info(f"Classifying inquiry: {request.inquiry[:50]}...")

        # Call existing classification module
        result = classify(request.inquiry)

        logger.info(
            f"Classification successful: category={result.category}, "
            f"subcategory={result.subcategory}, confidence={result.confidence:.2f}, "
            f"time={result.processing_time_ms}ms"
        )

        return result

    except ClassificationError as e:
        # Classification module error (validation, API errors, etc.)
        logger.error(f"Classification error: {str(e)}")

        # Determine appropriate HTTP status code
        error_message = str(e)

        if "API" in error_message or "service" in error_message.lower():
            # Service unavailable
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Classification service is temporarily unavailable. Please try again.",
                    "error_type": "api_error",
                    "details": str(e),
                    "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
                }
            )
        elif "timeout" in error_message.lower():
            # Timeout
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "error": "Classification took too long to complete. Please try again.",
                    "error_type": "timeout",
                    "details": str(e),
                    "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
                }
            )
        else:
            # Generic error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": str(e),
                    "error_type": "validation",
                    "details": str(e),
                    "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
                }
            )

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error during classification: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "An unexpected error occurred. Please try again or contact support.",
                "error_type": "unknown",
                "details": str(e)
            }
        )
