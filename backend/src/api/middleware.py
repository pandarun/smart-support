"""
Middleware for Smart Support Operator API

Provides request/response logging, performance monitoring, and error handling utilities.

Constitution Compliance:
- Principle II: User-Centric Design (user-friendly error messages)
- Principle IV: API-First Integration (request/response tracking)
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all incoming requests and outgoing responses with performance metrics.

    Tracks:
    - HTTP method and path
    - Response status code
    - Processing time in milliseconds
    - Client IP address
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log metrics."""
        start_time = time.time()

        # Log incoming request
        logger.info(
            f"Incoming request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        # Process request
        try:
            response = await call_next(request)
            processing_time_ms = (time.time() - start_time) * 1000

            # Log response with timing
            logger.info(
                f"Completed: {request.method} {request.url.path} "
                f"status={response.status_code} time={processing_time_ms:.2f}ms"
            )

            # Add custom header with processing time
            response.headers["X-Processing-Time-Ms"] = f"{processing_time_ms:.2f}"

            return response

        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"time={processing_time_ms:.2f}ms error={str(e)}",
                exc_info=True
            )
            raise


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Monitors API performance and logs slow requests.

    Logs warnings for requests exceeding thresholds:
    - Classification: 2000ms (FR-005: must respond in <2s)
    - Retrieval: 1000ms (FR-010: must retrieve in <1s)
    - Other endpoints: 500ms
    """

    THRESHOLDS = {
        "/api/classify": 2000,    # Classification threshold
        "/api/retrieve": 1000,    # Retrieval threshold
        "default": 500            # Default for other endpoints
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request performance."""
        start_time = time.time()
        response = await call_next(request)
        processing_time_ms = (time.time() - start_time) * 1000

        # Get threshold for this endpoint
        threshold = self.THRESHOLDS.get(
            request.url.path,
            self.THRESHOLDS["default"]
        )

        # Log warning if threshold exceeded
        if processing_time_ms > threshold:
            logger.warning(
                f"SLOW REQUEST: {request.method} {request.url.path} "
                f"took {processing_time_ms:.2f}ms (threshold: {threshold}ms)"
            )

        return response


def format_validation_error(error_detail: list) -> str:
    """
    Format Pydantic validation errors into user-friendly messages.

    Args:
        error_detail: List of error dictionaries from Pydantic ValidationError

    Returns:
        User-friendly error message (no technical jargon)
    """
    if not error_detail:
        return "Validation failed"

    # Get first error
    first_error = error_detail[0]
    field = first_error.get('loc', ['unknown'])[-1]
    msg = first_error.get('msg', 'Validation failed')
    error_type = first_error.get('type', '')

    # Map to user-friendly messages based on field and error type
    user_messages = {
        'inquiry': {
            'string_too_short': "Inquiry must be at least 5 characters",
            'string_too_long': "Inquiry must not exceed 5000 characters",
            'value_error': "Please enter inquiry in Russian (at least 5 characters)",
        },
        'query': {
            'string_too_short': "Query must be at least 5 characters",
            'string_too_long': "Query must not exceed 5000 characters",
            'value_error': "Query must contain Russian text",
        },
        'category': {
            'string_too_short': "Category is required",
        },
        'subcategory': {
            'string_too_short': "Subcategory is required",
        },
        'top_k': {
            'greater_than_equal': "Number of results must be at least 1",
            'less_than_equal': "Number of results must not exceed 10",
        }
    }

    # Check if we have a specific user-friendly message
    if field in user_messages and error_type in user_messages[field]:
        return user_messages[field][error_type]

    # Check for Cyrillic validation errors
    if 'cyrillic' in msg.lower() or 'Cyrillic' in msg:
        return "Please enter text in Russian (Cyrillic characters required)"

    # Default fallback
    return f"Invalid {field}: {msg}"


def get_error_type(exception: Exception) -> str:
    """
    Classify exception into error_type for ErrorResponse model.

    Args:
        exception: The exception that occurred

    Returns:
        Error type string: validation|api_error|timeout|unknown
    """
    exception_name = exception.__class__.__name__

    if exception_name in ['ValidationError', 'RequestValidationError']:
        return 'validation'
    elif exception_name in ['TimeoutError', 'asyncio.TimeoutError']:
        return 'timeout'
    elif exception_name in ['HTTPException', 'APIError']:
        return 'api_error'
    else:
        return 'unknown'
