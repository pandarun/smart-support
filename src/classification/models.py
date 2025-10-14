"""
Classification Module - Pydantic Data Models

This module defines all data structures used in the classification system.
Implements validation, serialization, and type safety for classification requests and results.

Constitution Compliance:
- Principle I: Modular Architecture (type-safe interfaces between components)
- Principle III: Data-Driven Validation (input validation, testability)
"""

from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, field_validator
import re


class ClassificationRequest(BaseModel):
    """
    Single inquiry classification request.
    
    Attributes:
        text: Customer inquiry text in Russian (Cyrillic required)
    
    Raises:
        ValueError: If text is invalid (too short, no Cyrillic, etc.)
    """
    text: str = Field(..., min_length=5, max_length=5000, description="Customer inquiry text")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate inquiry contains Cyrillic and is not empty."""
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Inquiry text must be at least 5 characters")
        if len(v) > 5000:
            raise ValueError("Inquiry text must not exceed 5000 characters")
        if not re.search(r'[а-яА-ЯёЁ]', v):
            raise ValueError("Inquiry must contain at least one Cyrillic character")
        return v


class ClassificationResult(BaseModel):
    """
    Classification result for a single inquiry.
    
    Attributes:
        inquiry: Original inquiry text
        category: Predicted top-level category
        subcategory: Predicted subcategory
        confidence: Confidence score (0.0 to 1.0)
        processing_time_ms: Processing time in milliseconds
        timestamp: When classification was performed (ISO 8601)
    """
    inquiry: str
    category: str
    subcategory: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    processing_time_ms: int = Field(..., gt=0)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class BatchClassificationRequest(BaseModel):
    """
    Batch classification request for multiple inquiries.
    
    Attributes:
        inquiries: List of inquiry texts to classify (1-100 items)
    """
    inquiries: List[str] = Field(..., min_length=1, max_length=100)


class BatchClassificationResult(BaseModel):
    """
    Batch classification results.
    
    Attributes:
        results: Classification results in same order as input
        total_processing_time_ms: Total time to process all inquiries
    """
    results: List[ClassificationResult]
    total_processing_time_ms: int


class ValidationRecord(BaseModel):
    """
    Single validation test case with ground truth.
    
    Attributes:
        inquiry: Test inquiry text
        expected_category: Ground truth category
        expected_subcategory: Ground truth subcategory
        note: Optional description of test case
    """
    inquiry: str
    expected_category: str
    expected_subcategory: str
    note: Optional[str] = None


class CategoryAccuracy(BaseModel):
    """
    Accuracy statistics for a specific category.
    
    Attributes:
        total: Total inquiries in this category
        correct: Correctly classified inquiries
        accuracy: Category-specific accuracy percentage
    """
    total: int
    correct: int
    accuracy: float


class ProcessingTimeStats(BaseModel):
    """
    Processing time statistics.
    
    Attributes:
        min_ms: Minimum processing time
        max_ms: Maximum processing time
        mean_ms: Mean processing time
        p95_ms: 95th percentile processing time
    """
    min_ms: int
    max_ms: int
    mean_ms: int
    p95_ms: int


class ValidationResult(BaseModel):
    """
    Validation dataset results.
    
    Attributes:
        total_inquiries: Total test cases processed
        correct_classifications: Number of correct predictions
        accuracy_percentage: Overall accuracy percentage
        per_category_accuracy: Accuracy breakdown by category
        processing_time_stats: Processing time statistics
        timestamp: When validation was performed
    """
    total_inquiries: int
    correct_classifications: int
    accuracy_percentage: float = Field(..., ge=0.0, le=100.0)
    per_category_accuracy: Dict[str, CategoryAccuracy]
    processing_time_stats: ProcessingTimeStats
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ClassificationError(BaseModel):
    """
    Classification error information.
    
    Attributes:
        error: Human-readable error message
        error_type: Error category (validation, api_error, timeout, unknown)
        details: Additional error details (optional)
    """
    error: str
    error_type: str = Field(..., pattern="^(validation|api_error|timeout|unknown)$")
    details: Optional[str] = None
