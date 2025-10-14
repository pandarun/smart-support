"""
Classification Module - Structured Logging

Provides JSON-formatted logging for classification events and system operations.

Constitution Compliance:
- Principle III: Data-Driven Validation (event logging for analysis)
- FR-008: Log classification events with all required fields
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
        
        # Add extra fields if present
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
