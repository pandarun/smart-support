"""
Pydantic data models for Template Retrieval Module.

This module defines all data structures for embeddings-based template retrieval,
including request/response models, validation records, and embedding utilities.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
import re

import numpy as np
from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict


# ============================================================================
# Core Entities
# ============================================================================


class Template(BaseModel):
    """
    Represents a single FAQ template with precomputed embedding.

    State transitions:
    Created (no embedding) → Embedding Pending → Embedded (ready for retrieval)
                                    ↓
                            Embedding Failed (logged, excluded from retrieval)
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(..., min_length=1, description="Template identifier (e.g., 'tmpl_savings_001')")
    category: str = Field(..., min_length=1, description="Top-level category (e.g., 'Счета и вклады')")
    subcategory: str = Field(..., min_length=1, description="Second-level classification (e.g., 'Открытие счета')")
    question: str = Field(..., min_length=10, description="Template question text in Russian")
    answer: str = Field(..., min_length=20, description="Template answer text in Russian")
    embedding: Optional[np.ndarray] = Field(None, description="Precomputed bge-m3 embedding vector (768 dims)")
    success_rate: float = Field(default=0.5, ge=0.0, le=1.0, description="Historical operator selection rate")
    usage_count: int = Field(default=0, ge=0, description="Number of times template selected by operators")
    created_at: datetime = Field(default_factory=datetime.now, description="Template creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last template modification timestamp")

    @computed_field
    @property
    def embedding_text(self) -> str:
        """Combined text used for embedding: question + answer."""
        return f"{self.question} {self.answer}"

    @field_validator('question', 'answer')
    @classmethod
    def validate_cyrillic(cls, v: str) -> str:
        """Ensure text contains at least one Cyrillic character (Russian language validation)."""
        if not re.search(r'[а-яА-ЯёЁ]', v):
            raise ValueError("Text must contain at least one Cyrillic character")
        return v

    @field_validator('embedding')
    @classmethod
    def validate_embedding_shape(cls, v: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Ensure embedding is 768-dimensional (bge-m3 dimension)."""
        if v is not None:
            if v.shape != (768,):
                raise ValueError(f"Embedding must be 768-dimensional, got {v.shape}")
        return v


class TemplateMetadata(BaseModel):
    """
    Metadata for a template stored in cache (without embedding vector).
    Used for filtering and display purposes.
    """
    template_id: str = Field(..., description="Template identifier")
    category: str = Field(..., description="Top-level category")
    subcategory: str = Field(..., description="Second-level classification")
    question: str = Field(..., description="Template question text")
    answer: str = Field(..., description="Template answer text")
    success_rate: float = Field(default=0.5, ge=0.0, le=1.0, description="Historical success rate")
    usage_count: int = Field(default=0, ge=0, description="Usage count")


class RetrievalResult(BaseModel):
    """
    Represents a single retrieved template with relevance scores.
    Denormalized for UI layer (avoids lookups).
    """
    template_id: str = Field(..., description="Reference to Template.id")
    template_question: str = Field(..., description="Template question text (denormalized for UI)")
    template_answer: str = Field(..., description="Template answer text (denormalized for UI)")
    category: str = Field(..., description="Template category (denormalized)")
    subcategory: str = Field(..., description="Template subcategory (denormalized)")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity between query and template")
    combined_score: float = Field(..., ge=0.0, le=1.0, description="Final ranking score (similarity or weighted)")
    rank: int = Field(..., ge=1, description="Position in ranked results (1 = best match)")

    @computed_field
    @property
    def confidence_level(self) -> str:
        """Auto-computed confidence based on combined_score."""
        if self.combined_score >= 0.7:
            return "high"
        elif self.combined_score >= 0.5:
            return "medium"
        else:
            return "low"


class RetrievalRequest(BaseModel):
    """
    Input model for template retrieval endpoint/function.
    Can be constructed from Classification Module output.
    """
    query: str = Field(..., min_length=5, max_length=5000, description="Customer inquiry text in Russian")
    category: str = Field(..., min_length=1, description="Classified category from Classification Module")
    subcategory: str = Field(..., min_length=1, description="Classified subcategory from Classification Module")
    classification_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Classification confidence score")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of templates to return")
    use_historical_weighting: bool = Field(default=False, description="Enable weighted scoring with historical rates")

    @field_validator('query')
    @classmethod
    def validate_cyrillic(cls, v: str) -> str:
        """Ensure query contains at least one Cyrillic character."""
        if not re.search(r'[а-яА-ЯёЁ]', v):
            raise ValueError("Query must contain at least one Cyrillic character")
        return v

    @classmethod
    def from_classification(
        cls,
        query: str,
        classification: Any,  # ClassificationResult from Classification Module
        top_k: int = 5
    ) -> "RetrievalRequest":
        """
        Alternative constructor from Classification Module output.

        Args:
            query: Customer inquiry text
            classification: ClassificationResult object with category, subcategory, confidence
            top_k: Number of templates to return

        Returns:
            RetrievalRequest instance
        """
        return cls(
            query=query,
            category=classification.category,
            subcategory=classification.subcategory,
            classification_confidence=classification.confidence,
            top_k=top_k
        )


class RetrievalResponse(BaseModel):
    """
    Output model for template retrieval endpoint/function.
    Includes ranked results and metadata.
    """
    query: str = Field(..., description="Original customer inquiry (echoed back)")
    category: str = Field(..., description="Category used for filtering (echoed back)")
    subcategory: str = Field(..., description="Subcategory used for filtering (echoed back)")
    results: List[RetrievalResult] = Field(..., max_length=10, description="Ranked template results")
    total_candidates: int = Field(..., ge=0, description="Number of templates in category before ranking")
    processing_time_ms: float = Field(..., ge=0.0, description="Time to embed query + rank templates (ms)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When retrieval completed")
    warnings: List[str] = Field(default_factory=list, description="Warnings (e.g., low confidence, no templates)")

    @field_validator('results')
    @classmethod
    def validate_ranking(cls, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Ensure results are sorted by rank ascending (1, 2, 3, ...)."""
        for i, result in enumerate(results):
            expected_rank = i + 1
            if result.rank != expected_rank:
                raise ValueError(f"Result at index {i} has incorrect rank {result.rank}, expected {expected_rank}")
        return results


# ============================================================================
# Value Objects
# ============================================================================


class EmbeddingVector(BaseModel):
    """
    Wrapper for numpy embedding arrays with utility methods.
    Provides L2 normalization and cosine similarity computation.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    vector: np.ndarray = Field(..., description="bge-m3 embedding vector (768 dims, float32)")
    is_normalized: bool = Field(default=False, description="Whether vector is L2-normalized")

    @field_validator('vector')
    @classmethod
    def validate_shape(cls, v: np.ndarray) -> np.ndarray:
        """Ensure vector is 768-dimensional."""
        if v.shape != (768,):
            raise ValueError(f"Vector must be 768-dimensional, got {v.shape}")
        return v

    def normalize(self) -> "EmbeddingVector":
        """Return L2-normalized copy of this vector."""
        if self.is_normalized:
            return self
        norm = np.linalg.norm(self.vector)
        if norm == 0:
            # Avoid division by zero
            return EmbeddingVector(vector=self.vector, is_normalized=True)
        return EmbeddingVector(vector=self.vector / norm, is_normalized=True)

    def cosine_similarity(self, other: "EmbeddingVector") -> float:
        """
        Compute cosine similarity with another embedding.
        Normalizes both vectors if not already normalized.

        Args:
            other: Another EmbeddingVector

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        v1 = self.normalize() if not self.is_normalized else self
        v2 = other.normalize() if not other.is_normalized else other
        return float(np.dot(v1.vector, v2.vector))


class ProcessingTimeStats(BaseModel):
    """
    Statistical summary of processing times.
    Used for performance monitoring and validation.
    """
    min_ms: float = Field(..., ge=0.0, description="Minimum processing time (milliseconds)")
    max_ms: float = Field(..., ge=0.0, description="Maximum processing time (milliseconds)")
    mean_ms: float = Field(..., ge=0.0, description="Average processing time (milliseconds)")
    p95_ms: float = Field(..., ge=0.0, description="95th percentile processing time (milliseconds)")
    sample_count: int = Field(..., gt=0, description="Number of samples measured")

    @property
    def meets_performance_requirement(self) -> bool:
        """Check if p95 meets <1000ms requirement (PR-001)."""
        return self.p95_ms < 1000.0


# ============================================================================
# Validation Models
# ============================================================================


class ValidationRecord(BaseModel):
    """
    Ground truth pairing for retrieval quality validation.
    Each record represents a test case with known correct answer.
    """
    id: str = Field(..., min_length=1, description="Validation record identifier (e.g., 'val_001')")
    query: str = Field(..., min_length=10, description="Customer inquiry text to test")
    category: str = Field(..., min_length=1, description="Known correct category")
    subcategory: str = Field(..., min_length=1, description="Known correct subcategory")
    correct_template_id: str = Field(..., min_length=1, description="Ground truth template ID")
    notes: Optional[str] = Field(None, description="Human-readable explanation of correctness")


class ValidationQueryResult(BaseModel):
    """
    Detailed results for a single validation query.
    Tracks ranking of correct template and similarity scores.
    """
    query_id: str = Field(..., description="Reference to ValidationRecord.id")
    query_text: str = Field(..., description="Customer inquiry tested")
    correct_template_id: str = Field(..., description="Ground truth template ID")
    retrieved_templates: List[str] = Field(..., description="Template IDs retrieved (in rank order)")
    correct_template_rank: Optional[int] = Field(None, description="Rank of correct template (None if not retrieved)")
    similarity_scores: Dict[str, float] = Field(..., description="Template ID -> similarity score mapping")

    @computed_field
    @property
    def is_top_1(self) -> bool:
        """True if correct template ranked #1."""
        return self.correct_template_rank == 1

    @computed_field
    @property
    def is_top_3(self) -> bool:
        """True if correct template in top-3."""
        return self.correct_template_rank is not None and self.correct_template_rank <= 3

    @computed_field
    @property
    def is_top_5(self) -> bool:
        """True if correct template in top-5."""
        return self.correct_template_rank is not None and self.correct_template_rank <= 5


class ValidationResult(BaseModel):
    """
    Aggregate results from retrieval validation run.
    Includes quality gate check (≥80% top-3 accuracy).
    """
    total_queries: int = Field(..., gt=0, description="Number of validation queries tested")
    top_1_correct: int = Field(..., ge=0, description="Queries where correct template ranked #1")
    top_3_correct: int = Field(..., ge=0, description="Queries where correct template in top-3")
    top_5_correct: int = Field(..., ge=0, description="Queries where correct template in top-5")
    per_query_results: List[ValidationQueryResult] = Field(..., description="Detailed results for each query")
    avg_similarity_correct: float = Field(..., description="Average similarity score for correct templates")
    avg_similarity_incorrect: float = Field(..., description="Average similarity for top-ranked incorrect templates")
    processing_time_stats: ProcessingTimeStats = Field(..., description="Min/max/mean/p95 processing times")
    timestamp: datetime = Field(default_factory=datetime.now, description="When validation run completed")

    @computed_field
    @property
    def top_3_accuracy(self) -> float:
        """Percentage: top_3_correct / total_queries * 100."""
        return (self.top_3_correct / self.total_queries) * 100.0

    @computed_field
    @property
    def passes_quality_gate(self) -> bool:
        """Check if validation meets ≥80% top-3 accuracy requirement."""
        return self.top_3_accuracy >= 80.0
