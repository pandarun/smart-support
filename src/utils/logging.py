"""
Smart Support System - Structured Logging

Provides JSON-formatted logging for classification, retrieval, and system operations.

Constitution Compliance:
- Principle III: Data-Driven Validation (event logging for analysis)
- FR-008 (Classification): Log classification events with all required fields
- FR-008 (Retrieval): Log retrieval events with all required fields
"""

import os
import sys
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Outputs log records as JSON objects for easy parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present (classification)
        if hasattr(record, "inquiry"):
            log_data["inquiry"] = record.inquiry
        if hasattr(record, "category"):
            log_data["category"] = record.category
        if hasattr(record, "subcategory"):
            log_data["subcategory"] = record.subcategory
        if hasattr(record, "confidence"):
            log_data["confidence"] = record.confidence
        if hasattr(record, "processing_time_ms"):
            log_data["processing_time_ms"] = record.processing_time_ms

        # Add extra fields if present (retrieval)
        if hasattr(record, "query"):
            log_data["query"] = record.query
        if hasattr(record, "total_templates"):
            log_data["total_templates"] = record.total_templates
        if hasattr(record, "embedded_templates"):
            log_data["embedded_templates"] = record.embedded_templates
        if hasattr(record, "failed_templates"):
            log_data["failed_templates"] = record.failed_templates
        if hasattr(record, "precompute_time_seconds"):
            log_data["precompute_time_seconds"] = record.precompute_time_seconds
        if hasattr(record, "total_candidates"):
            log_data["total_candidates"] = record.total_candidates
        if hasattr(record, "top_k"):
            log_data["top_k"] = record.top_k
        if hasattr(record, "top_score"):
            log_data["top_score"] = record.top_score

        # Add extra fields if present (validation)
        if hasattr(record, "total_queries"):
            log_data["total_queries"] = record.total_queries
        if hasattr(record, "top_1_correct"):
            log_data["top_1_correct"] = record.top_1_correct
        if hasattr(record, "top_3_correct"):
            log_data["top_3_correct"] = record.top_3_correct
        if hasattr(record, "top_3_accuracy"):
            log_data["top_3_accuracy"] = record.top_3_accuracy
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(log_level: Optional[str] = None) -> logging.Logger:
    """
    Configure structured logging for the classification module.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
                  Uses LOG_LEVEL env var if not provided
    
    Returns:
        Configured logger instance
    """
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Create logger
    logger = logging.getLogger("classification")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger() -> logging.Logger:
    """
    Get classification logger instance.
    
    Returns:
        Logger configured for classification module
    """
    logger = logging.getLogger("classification")
    
    # Initialize if not already configured
    if not logger.handlers:
        setup_logging()
    
    return logger


def log_classification(
    inquiry: str,
    category: str,
    subcategory: str,
    confidence: float,
    processing_time_ms: int
) -> None:
    """
    Log classification event with all required fields.
    
    Args:
        inquiry: Customer inquiry text (truncated for privacy)
        category: Predicted category
        subcategory: Predicted subcategory
        confidence: Confidence score
        processing_time_ms: Processing time in milliseconds
    """
    logger = get_logger()
    
    # Truncate inquiry for privacy (max 100 chars)
    truncated_inquiry = inquiry[:100] if len(inquiry) > 100 else inquiry
    
    logger.info(
        "Classification completed",
        extra={
            "inquiry": truncated_inquiry,
            "category": category,
            "subcategory": subcategory,
            "confidence": confidence,
            "processing_time_ms": processing_time_ms
        }
    )


def log_error(
    error_message: str,
    error_type: str,
    details: Optional[str] = None
) -> None:
    """
    Log classification error.
    
    Args:
        error_message: Human-readable error message
        error_type: Error category (validation, api_error, timeout, unknown)
        details: Additional error details
    """
    logger = get_logger()
    
    logger.error(
        error_message,
        extra={
            "error_type": error_type,
            "details": details
        }
    )


def log_validation(
    total: int,
    correct: int,
    accuracy: float,
    processing_time_ms: int
) -> None:
    """
    Log validation run results.
    
    Args:
        total: Total test cases
        correct: Correctly classified cases
        accuracy: Accuracy percentage
        processing_time_ms: Total processing time
    """
    logger = get_logger()
    
    logger.info(
        "Validation completed",
        extra={
            "total_inquiries": total,
            "correct_classifications": correct,
            "accuracy_percentage": accuracy,
            "processing_time_ms": processing_time_ms
        }
    )


def log_batch(
    batch_size: int,
    total_processing_time_ms: int,
    successful: int,
    failed: int
) -> None:
    """
    Log batch classification results.

    Args:
        batch_size: Number of inquiries in batch
        total_processing_time_ms: Total processing time
        successful: Number of successful classifications
        failed: Number of failed classifications
    """
    logger = get_logger()

    logger.info(
        "Batch classification completed",
        extra={
            "batch_size": batch_size,
            "successful": successful,
            "failed": failed,
            "total_processing_time_ms": total_processing_time_ms,
            "avg_time_per_inquiry_ms": total_processing_time_ms // batch_size if batch_size > 0 else 0
        }
    )


# ============================================================================
# Retrieval Module Logging Functions
# ============================================================================


def log_embedding_precomputation_started(
    total_templates: int,
    batch_size: int
) -> None:
    """
    Log start of embedding precomputation.

    Args:
        total_templates: Number of templates to embed
        batch_size: Number of templates per API batch
    """
    logger = get_logger()

    logger.info(
        "Embedding precomputation started",
        extra={
            "total_templates": total_templates,
            "batch_size": batch_size
        }
    )


def log_embedding_precomputation_completed(
    total_templates: int,
    embedded_templates: int,
    failed_templates: int,
    precompute_time_seconds: float
) -> None:
    """
    Log completion of embedding precomputation.

    Args:
        total_templates: Total number of templates
        embedded_templates: Number of successfully embedded templates
        failed_templates: Number of failed templates
        precompute_time_seconds: Total precomputation time in seconds
    """
    logger = get_logger()

    logger.info(
        "Embedding precomputation completed",
        extra={
            "total_templates": total_templates,
            "embedded_templates": embedded_templates,
            "failed_templates": failed_templates,
            "precompute_time_seconds": precompute_time_seconds,
            "templates_per_second": embedded_templates / precompute_time_seconds if precompute_time_seconds > 0 else 0
        }
    )


def log_template_retrieval_requested(
    query: str,
    category: str,
    subcategory: str,
    top_k: int
) -> None:
    """
    Log template retrieval request.

    Args:
        query: Customer inquiry text (truncated for privacy)
        category: Classified category
        subcategory: Classified subcategory
        top_k: Number of templates requested
    """
    logger = get_logger()

    # Truncate query for privacy (max 100 chars)
    truncated_query = query[:100] if len(query) > 100 else query

    logger.info(
        "Template retrieval requested",
        extra={
            "query": truncated_query,
            "category": category,
            "subcategory": subcategory,
            "top_k": top_k
        }
    )


def log_template_retrieval_completed(
    query: str,
    category: str,
    subcategory: str,
    total_candidates: int,
    results_count: int,
    top_score: float,
    processing_time_ms: float
) -> None:
    """
    Log template retrieval completion.

    Args:
        query: Customer inquiry text (truncated for privacy)
        category: Classified category
        subcategory: Classified subcategory
        total_candidates: Number of templates in category before ranking
        results_count: Number of results returned
        top_score: Similarity score of top result
        processing_time_ms: Processing time in milliseconds
    """
    logger = get_logger()

    # Truncate query for privacy (max 100 chars)
    truncated_query = query[:100] if len(query) > 100 else query

    logger.info(
        "Template retrieval completed",
        extra={
            "query": truncated_query,
            "category": category,
            "subcategory": subcategory,
            "total_candidates": total_candidates,
            "results_count": results_count,
            "top_score": top_score,
            "processing_time_ms": processing_time_ms
        }
    )


def log_retrieval_validation_started(
    total_queries: int,
    dataset_path: str
) -> None:
    """
    Log start of retrieval validation run.

    Args:
        total_queries: Number of validation queries
        dataset_path: Path to validation dataset
    """
    logger = get_logger()

    logger.info(
        "Retrieval validation started",
        extra={
            "total_queries": total_queries,
            "dataset_path": dataset_path
        }
    )


def log_retrieval_validation_completed(
    total_queries: int,
    top_1_correct: int,
    top_3_correct: int,
    top_3_accuracy: float,
    processing_time_ms: float
) -> None:
    """
    Log completion of retrieval validation run.

    Args:
        total_queries: Total validation queries tested
        top_1_correct: Queries where correct template ranked #1
        top_3_correct: Queries where correct template in top-3
        top_3_accuracy: Top-3 accuracy percentage
        processing_time_ms: Total processing time in milliseconds
    """
    logger = get_logger()

    logger.info(
        "Retrieval validation completed",
        extra={
            "total_queries": total_queries,
            "top_1_correct": top_1_correct,
            "top_3_correct": top_3_correct,
            "top_3_accuracy": top_3_accuracy,
            "processing_time_ms": processing_time_ms
        }
    )
