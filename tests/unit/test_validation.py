"""
Unit Tests for Validation Helpers

Tests input validation and sanitization functions.
"""

import pytest
from src.utils.validation import (
    contains_cyrillic,
    validate_inquiry_text,
    sanitize_inquiry,
    validate_batch_size,
    validate_confidence,
    validate_category_match
)


@pytest.mark.unit
def test_contains_cyrillic_with_russian_text():
    """Test Cyrillic detection with Russian text."""
    assert contains_cyrillic("Как открыть счет?") is True
    assert contains_cyrillic("Привет мир") is True
    assert contains_cyrillic("МОСКВА") is True


@pytest.mark.unit
def test_contains_cyrillic_with_english_text():
    """Test Cyrillic detection with English text."""
    assert contains_cyrillic("How to open account?") is False
    assert contains_cyrillic("Hello world") is False


@pytest.mark.unit
def test_contains_cyrillic_with_mixed_text():
    """Test Cyrillic detection with mixed text."""
    assert contains_cyrillic("How открыть account?") is True
    assert contains_cyrillic("123 рублей") is True


@pytest.mark.unit
def test_contains_cyrillic_with_empty_text():
    """Test Cyrillic detection with empty text."""
    assert contains_cyrillic("") is False
    assert contains_cyrillic("   ") is False


@pytest.mark.unit
def test_validate_inquiry_text_valid():
    """Test validation of valid inquiry text."""
    is_valid, error = validate_inquiry_text("Как открыть счет?")
    
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_inquiry_text_too_short():
    """Test validation rejects too short text."""
    is_valid, error = validate_inquiry_text("Hi")
    
    assert is_valid is False
    assert "at least 5 characters" in error


@pytest.mark.unit
def test_validate_inquiry_text_too_long():
    """Test validation rejects too long text."""
    long_text = "а" * 5001
    is_valid, error = validate_inquiry_text(long_text)
    
    assert is_valid is False
    assert "must not exceed" in error


@pytest.mark.unit
def test_validate_inquiry_text_no_cyrillic():
    """Test validation rejects text without Cyrillic."""
    is_valid, error = validate_inquiry_text("How to open account?")
    
    assert is_valid is False
    assert "Cyrillic" in error


@pytest.mark.unit
def test_validate_inquiry_text_empty():
    """Test validation rejects empty text."""
    is_valid, error = validate_inquiry_text("")
    
    assert is_valid is False
    assert "required" in error.lower()


@pytest.mark.unit
def test_validate_inquiry_text_whitespace_only():
    """Test validation rejects whitespace-only text."""
    is_valid, error = validate_inquiry_text("     ")
    
    assert is_valid is False
    assert "at least 5 characters" in error


@pytest.mark.unit
def test_sanitize_inquiry_removes_extra_whitespace():
    """Test sanitization removes extra whitespace."""
    sanitized = sanitize_inquiry("  Как   открыть  счет?  ")
    
    assert sanitized == "Как открыть счет?"


@pytest.mark.unit
def test_sanitize_inquiry_normalizes_spaces():
    """Test sanitization normalizes multiple spaces."""
    sanitized = sanitize_inquiry("Как    открыть     счет?")
    
    assert sanitized == "Как открыть счет?"


@pytest.mark.unit
def test_sanitize_inquiry_preserves_content():
    """Test sanitization preserves actual content."""
    original = "Как открыть счет в ВТБ?"
    sanitized = sanitize_inquiry(original)
    
    assert sanitized == original


@pytest.mark.unit
def test_validate_batch_size_valid():
    """Test batch size validation with valid size."""
    is_valid, error = validate_batch_size(10)
    
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_batch_size_zero():
    """Test batch size validation rejects zero."""
    is_valid, error = validate_batch_size(0)
    
    assert is_valid is False
    assert "at least one" in error


@pytest.mark.unit
def test_validate_batch_size_negative():
    """Test batch size validation rejects negative."""
    is_valid, error = validate_batch_size(-5)
    
    assert is_valid is False
    assert "at least one" in error


@pytest.mark.unit
def test_validate_batch_size_too_large():
    """Test batch size validation rejects too large."""
    is_valid, error = validate_batch_size(101)
    
    assert is_valid is False
    assert "must not exceed" in error


@pytest.mark.unit
def test_validate_confidence_valid():
    """Test confidence validation with valid values."""
    assert validate_confidence(0.0)[0] is True
    assert validate_confidence(0.5)[0] is True
    assert validate_confidence(1.0)[0] is True


@pytest.mark.unit
def test_validate_confidence_out_of_range():
    """Test confidence validation rejects out of range."""
    is_valid, error = validate_confidence(1.5)
    assert is_valid is False
    assert "between 0.0 and 1.0" in error
    
    is_valid, error = validate_confidence(-0.1)
    assert is_valid is False


@pytest.mark.unit
def test_validate_confidence_non_numeric():
    """Test confidence validation rejects non-numeric."""
    is_valid, error = validate_confidence("high")
    
    assert is_valid is False
    assert "must be a number" in error


@pytest.mark.unit
def test_validate_category_match_valid():
    """Test category/subcategory validation with valid match."""
    valid_categories = {
        "Новые клиенты": ["Регистрация и онбординг", "Первые шаги"]
    }
    
    is_valid, error = validate_category_match(
        "Новые клиенты",
        "Регистрация и онбординг",
        valid_categories
    )
    
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_category_match_invalid_category():
    """Test category/subcategory validation with invalid category."""
    valid_categories = {
        "Новые клиенты": ["Регистрация и онбординг"]
    }
    
    is_valid, error = validate_category_match(
        "InvalidCategory",
        "Регистрация и онбординг",
        valid_categories
    )
    
    assert is_valid is False
    assert "Invalid category" in error


@pytest.mark.unit
def test_validate_category_match_invalid_subcategory():
    """Test category/subcategory validation with invalid subcategory."""
    valid_categories = {
        "Новые клиенты": ["Регистрация и онбординг"]
    }
    
    is_valid, error = validate_category_match(
        "Новые клиенты",
        "InvalidSubcategory",
        valid_categories
    )
    
    assert is_valid is False
    assert "Invalid subcategory" in error
