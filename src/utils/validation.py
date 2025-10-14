"""
Classification Module - Input Validation

Provides validation helpers for inquiry text and classification inputs.

Constitution Compliance:
- Principle III: Data-Driven Validation (input sanitization, error prevention)
- FR-009: Input validation (non-empty, Cyrillic requirement)
"""

import re
from typing import Optional, Tuple


def contains_cyrillic(text: str) -> bool:
    """
    Check if text contains at least one Cyrillic character.
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains Cyrillic, False otherwise
    """
    return bool(re.search(r'[а-яА-ЯёЁ]', text))


def validate_inquiry_text(
    text: str,
    min_length: int = 5,
    max_length: int = 5000
) -> Tuple[bool, Optional[str]]:
    """
    Validate inquiry text meets all requirements.
    
    Args:
        text: Inquiry text to validate
        min_length: Minimum character length (default: 5)
        max_length: Maximum character length (default: 5000)
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if validation passes, False otherwise
        - error_message: Descriptive error message if validation fails, None if passes
    """
    # Check if text is provided
    if not text:
        return False, "Inquiry text is required"
    
    # Strip whitespace for length checks
    text_stripped = text.strip()
    
    # Check minimum length
    if len(text_stripped) < min_length:
        return False, f"Inquiry text must be at least {min_length} characters"
    
    # Check maximum length
    if len(text_stripped) > max_length:
        return False, f"Inquiry text must not exceed {max_length} characters"
    
    # Check for Cyrillic characters (Russian requirement)
    if not contains_cyrillic(text_stripped):
        return False, "Inquiry must contain at least one Cyrillic character"
    
    # Check if text is only whitespace
    if not text_stripped:
        return False, "Inquiry text cannot be only whitespace"
    
    return True, None


def sanitize_inquiry(text: str) -> str:
    """
    Sanitize inquiry text for processing.
    
    Removes excessive whitespace and normalizes input.
    
    Args:
        text: Raw inquiry text
        
    Returns:
        Sanitized inquiry text
    """
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    
    return text


def validate_batch_size(batch_size: int, max_batch_size: int = 100) -> Tuple[bool, Optional[str]]:
    """
    Validate batch size is within acceptable range.
    
    Args:
        batch_size: Number of inquiries in batch
        max_batch_size: Maximum allowed batch size (default: 100)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if batch_size < 1:
        return False, "Batch must contain at least one inquiry"
    
    if batch_size > max_batch_size:
        return False, f"Batch size must not exceed {max_batch_size} inquiries"
    
    return True, None


def validate_confidence(confidence: float) -> Tuple[bool, Optional[str]]:
    """
    Validate confidence score is in valid range.
    
    Args:
        confidence: Confidence score to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(confidence, (int, float)):
        return False, "Confidence must be a number"
    
    if confidence < 0.0 or confidence > 1.0:
        return False, "Confidence must be between 0.0 and 1.0"
    
    return True, None


def validate_category_match(
    category: str,
    subcategory: str,
    valid_categories: dict[str, list[str]]
) -> Tuple[bool, Optional[str]]:
    """
    Validate category and subcategory match exists in FAQ.
    
    Args:
        category: Category name
        subcategory: Subcategory name
        valid_categories: Dictionary mapping categories to subcategories
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if category not in valid_categories:
        return False, f"Invalid category: {category}"
    
    if subcategory not in valid_categories[category]:
        return False, f"Invalid subcategory '{subcategory}' for category '{category}'"
    
    return True, None
