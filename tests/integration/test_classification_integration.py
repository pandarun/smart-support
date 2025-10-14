"""
Integration Tests for Classification Workflow

Tests end-to-end classification with real Scibox API and FAQ data.

Constitution Compliance:
- Principle III: Integration tests with testcontainers (mandated)
- PR-001: <2 seconds response time requirement
- QR-001: ≥70% accuracy requirement (tested in validation)
"""

import pytest


@pytest.mark.integration
def test_single_inquiry_classification(classifier):
    """
    Test single inquiry classification end-to-end.
    
    Verifies:
    - Classification completes successfully
    - Returns valid category and subcategory
    - Confidence is in valid range [0.0, 1.0]
    - Processing time is <2000ms (performance requirement)
    """
    inquiry = "Как открыть счет в банке?"
    
    result = classifier.classify(inquiry)
    
    # Verify result structure
    assert result.inquiry == inquiry
    assert result.category, "Category should not be empty"
    assert result.subcategory, "Subcategory should not be empty"
    
    # Verify confidence range
    assert 0.0 <= result.confidence <= 1.0, "Confidence must be between 0.0 and 1.0"
    
    # Verify performance requirement (PR-001)
    assert result.processing_time_ms < 2000, \
        f"Processing time {result.processing_time_ms}ms exceeds 2000ms requirement"
    
    # Verify timestamp
    assert result.timestamp, "Timestamp should be set"
    
    # Verify category is valid (exists in FAQ)
    assert classifier.faq_parser.is_valid_category(result.category), \
        f"Category '{result.category}' not found in FAQ"
    
    # Verify subcategory is valid for category
    assert classifier.faq_parser.is_valid_subcategory(result.category, result.subcategory), \
        f"Subcategory '{result.subcategory}' not valid for category '{result.category}'"


@pytest.mark.integration
def test_classification_response_format(classifier):
    """
    Test that classification response matches expected format.
    
    Verifies JSON response from LLM is properly parsed.
    """
    inquiry = "Какая процентная ставка по вкладу?"
    
    result = classifier.classify(inquiry)
    
    # Verify all required fields are present
    assert hasattr(result, 'inquiry')
    assert hasattr(result, 'category')
    assert hasattr(result, 'subcategory')
    assert hasattr(result, 'confidence')
    assert hasattr(result, 'processing_time_ms')
    assert hasattr(result, 'timestamp')


@pytest.mark.integration
def test_classification_with_technical_support_inquiry(classifier):
    """
    Test classification of technical support inquiry.
    
    Verifies classifier can handle different inquiry types.
    """
    inquiry = "Забыл пароль от мобильного приложения"
    
    result = classifier.classify(inquiry)
    
    # Should classify to technical support or similar
    assert result.category in classifier.faq_parser.get_categories()
    assert result.confidence > 0.0
    assert result.processing_time_ms < 2000


@pytest.mark.integration
def test_classification_performance_multiple_calls(classifier, sample_inquiries):
    """
    Test that multiple classifications maintain performance.
    
    Verifies caching and performance optimization work correctly.
    """
    results = []
    
    for inquiry in sample_inquiries[:3]:  # Test with 3 inquiries
        result = classifier.classify(inquiry)
        results.append(result)
        
        # Each call should meet performance requirement
        assert result.processing_time_ms < 2000, \
            f"Call exceeded 2000ms: {result.processing_time_ms}ms"
    
    # Verify all succeeded
    assert len(results) == 3
    
    # Verify mean processing time
    mean_time = sum(r.processing_time_ms for r in results) / len(results)
    assert mean_time < 1800, f"Mean processing time {mean_time}ms exceeds target 1800ms"


@pytest.mark.integration
def test_invalid_inquiry_handling(classifier):
    """
    Test that invalid inquiries are properly rejected.
    """
    from src.classification.classifier import ClassificationError
    
    # Test empty inquiry
    with pytest.raises(ClassificationError, match="at least 5 characters"):
        classifier.classify("")
    
    # Test non-Cyrillic inquiry
    with pytest.raises(ClassificationError, match="Cyrillic"):
        classifier.classify("How to open an account?")
    
    # Test too short inquiry
    with pytest.raises(ClassificationError, match="at least 5 characters"):
        classifier.classify("Hi")


@pytest.mark.integration
@pytest.mark.slow
def test_classification_deterministic(classifier):
    """
    Test that classification is deterministic (QR-002).
    
    Same inquiry should produce same result when called multiple times.
    """
    inquiry = "Как открыть счет?"
    
    # Classify same inquiry twice
    result1 = classifier.classify(inquiry)
    result2 = classifier.classify(inquiry)
    
    # Results should be identical (deterministic with temperature=0)
    assert result1.category == result2.category, "Categories should match"
    assert result1.subcategory == result2.subcategory, "Subcategories should match"
    # Confidence may vary slightly due to floating point, but should be close
    assert abs(result1.confidence - result2.confidence) < 0.01, \
        "Confidence should be nearly identical"
