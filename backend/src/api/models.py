"""
Pydantic Request/Response Models for Operator Web Interface API

Mirrors the existing classification and retrieval module models for type-safe
API contracts. These models are used for FastAPI request validation and
response serialization.

Constitution Compliance:
- Principle I: Modular Architecture (mirrors existing models without modification)
- Principle IV: API-First Integration (enables OpenAPI auto-generation)
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re


# ============================================================================
# Classification Models (mirror src/classification/models.py)
# ============================================================================

class ClassificationRequest(BaseModel):
    """
    Request model for POST /api/classify endpoint.

    Validates customer inquiry text for classification.
    """
    inquiry: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Customer inquiry text in Russian"
    )

    @field_validator('inquiry')
    @classmethod
    def validate_cyrillic(cls, v: str) -> str:
        """Ensure inquiry contains at least one Cyrillic character (Russian)."""
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Inquiry text must be at least 5 characters")
        if not re.search(r'[а-яА-ЯёЁ]', v):
            raise ValueError("Inquiry must contain at least one Cyrillic character")
        return v


class ClassificationResult(BaseModel):
    """
    Response model for POST /api/classify endpoint.

    Contains classification results with category, subcategory, and confidence.
    """
    inquiry: str = Field(..., description="Original inquiry text (echoed back)")
    category: str = Field(..., description="Top-level product category")
    subcategory: str = Field(..., description="Second-level classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence (0.0-1.0)")
    processing_time_ms: int = Field(..., gt=0, description="Processing time in milliseconds")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="When classification was performed (ISO 8601 UTC)"
    )


# ============================================================================
# Retrieval Models (mirror src/retrieval/models.py)
# ============================================================================

class RetrievalRequest(BaseModel):
    """
    Request model for POST /api/retrieve endpoint.

    Constructed from ClassificationResult on frontend.
    """
    query: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Customer inquiry text (must match classified inquiry)"
    )
    category: str = Field(..., min_length=1, description="Category from classification")
    subcategory: str = Field(..., min_length=1, description="Subcategory from classification")
    classification_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score from classification (optional)"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of templates to return"
    )
    use_historical_weighting: bool = Field(
        default=False,
        description="Enable weighted scoring (not used in MVP)"
    )

    @field_validator('query')
    @classmethod
    def validate_cyrillic(cls, v: str) -> str:
        """Ensure query contains at least one Cyrillic character."""
        if not re.search(r'[а-яА-ЯёЁ]', v):
            raise ValueError("Query must contain at least one Cyrillic character")
        return v


class TemplateResult(BaseModel):
    """
    Single retrieved template with ranking metadata.

    Denormalized for UI display (includes question, answer, scores).
    """
    template_id: str = Field(..., description="Unique template identifier")
    template_question: str = Field(..., description="FAQ question text")
    template_answer: str = Field(..., description="FAQ answer text (for copy-to-clipboard)")
    category: str = Field(..., description="Template category")
    subcategory: str = Field(..., description="Template subcategory")
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cosine similarity (0.0-1.0)"
    )
    combined_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Final ranking score"
    )
    rank: int = Field(..., ge=1, description="Position in result list (1=best)")


class RetrievalResponse(BaseModel):
    """
    Response model for POST /api/retrieve endpoint.

    Contains ranked template results with metadata and warnings.
    """
    query: str = Field(..., description="Original inquiry (echoed back)")
    category: str = Field(..., description="Category used for filtering")
    subcategory: str = Field(..., description="Subcategory used for filtering")
    results: List[TemplateResult] = Field(
        ...,
        max_length=10,
        description="Ranked template results"
    )
    total_candidates: int = Field(
        ...,
        ge=0,
        description="Number of templates in category before ranking"
    )
    processing_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Time to embed query + rank (ms)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="When retrieval completed (ISO 8601 UTC)"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings (e.g., low confidence, no templates)"
    )

    @field_validator('results')
    @classmethod
    def validate_ranking(cls, results: List[TemplateResult]) -> List[TemplateResult]:
        """Ensure results are sorted by rank ascending (1, 2, 3, ...)."""
        for i, result in enumerate(results):
            expected_rank = i + 1
            if result.rank != expected_rank:
                raise ValueError(
                    f"Result at index {i} has incorrect rank {result.rank}, expected {expected_rank}"
                )
        return results


# ============================================================================
# Error Response Model
# ============================================================================

class ErrorResponse(BaseModel):
    """
    Standardized error response format for all API failures.

    Used for validation errors (400), service errors (503), timeouts (504).
    """
    error: str = Field(
        ...,
        description="User-friendly, actionable error message (no technical jargon)"
    )
    error_type: str = Field(
        ...,
        pattern="^(validation|api_error|timeout|unknown)$",
        description="Error category for frontend handling"
    )
    details: Optional[str] = Field(
        None,
        description="Technical details for logging (not shown to user)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="When error occurred (ISO 8601 UTC)"
    )


# ============================================================================
# Health Check Model
# ============================================================================

class HealthResponse(BaseModel):
    """
    Health check response for GET /api/health endpoint.

    Used by frontend to detect service availability.
    """
    status: str = Field(..., description="Overall health status (healthy/unhealthy)")
    classification_available: bool = Field(
        ...,
        description="Whether classification service can handle requests"
    )
    retrieval_available: bool = Field(
        ...,
        description="Whether retrieval service can handle requests"
    )
    embeddings_count: int = Field(
        ...,
        description="Number of FAQ templates in embeddings database"
    )
