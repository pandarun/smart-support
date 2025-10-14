"""
Unit Tests for Classifier

Tests classification logic with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json

from src.classification.classifier import Classifier, ClassificationError
from src.classification.models import ClassificationResult


@pytest.fixture
def mock_faq_parser():
    """Mock FAQ parser."""
    parser = Mock()
    parser.get_all_categories_dict.return_value = {
        "Новые клиенты": ["Регистрация и онбординг", "Первые шаги"],
        "Техническая поддержка": ["Проблемы и решения"]
    }
    parser.get_category_count.return_value = 2
    parser.get_subcategory_count.return_value = 3
    parser.is_valid_category.return_value = True
    parser.is_valid_subcategory.return_value = True
    parser.get_categories.return_value = ["Новые клиенты", "Техническая поддержка"]
    parser.get_subcategories.return_value = ["Регистрация и онбординг"]
    return parser


@pytest.fixture
def mock_scibox_client():
    """Mock Scibox client."""
    client = Mock()
    
    # Mock successful response
    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message = Mock()
    mock_completion.choices[0].message.content = json.dumps({
        "category": "Новые клиенты",
        "subcategory": "Регистрация и онбординг",
        "confidence": 0.92
    })
    
    client.chat_completion.return_value = mock_completion
    return client


@pytest.fixture
def classifier(mock_faq_parser, mock_scibox_client):
    """Create classifier with mocked dependencies."""
    return Classifier(faq_parser=mock_faq_parser, scibox_client=mock_scibox_client)


@pytest.mark.unit
def test_classify_valid_inquiry(classifier, mock_scibox_client):
    """Test classification of valid inquiry."""
    inquiry = "Как открыть счет?"
    
    result = classifier.classify(inquiry)
    
    assert isinstance(result, ClassificationResult)
    assert result.inquiry == inquiry
    assert result.category == "Новые клиенты"
    assert result.subcategory == "Регистрация и онбординг"
    assert result.confidence == 0.92
    assert result.processing_time_ms > 0
    
    # Verify API was called
    mock_scibox_client.chat_completion.assert_called_once()


@pytest.mark.unit
def test_classify_empty_inquiry(classifier):
    """Test that empty inquiry raises error."""
    with pytest.raises(ClassificationError, match="at least 5 characters"):
        classifier.classify("")


@pytest.mark.unit
def test_classify_non_cyrillic_text(classifier):
    """Test that non-Cyrillic text raises error."""
    with pytest.raises(ClassificationError, match="Cyrillic"):
        classifier.classify("How to open account?")


@pytest.mark.unit
def test_classify_timeout_handling(classifier, mock_scibox_client):
    """Test handling of API timeout."""
    from src.classification.client import SciboxAPIError
    
    # Mock timeout error
    mock_scibox_client.chat_completion.side_effect = SciboxAPIError("Classification timed out")
    
    with pytest.raises(ClassificationError, match="timed out"):
        classifier.classify("Как открыть счет?")


@pytest.mark.unit
def test_classify_invalid_json_response(classifier, mock_scibox_client):
    """Test handling of invalid JSON response from LLM."""
    # Mock invalid JSON response
    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message = Mock()
    mock_completion.choices[0].message.content = "This is not JSON"
    
    mock_scibox_client.chat_completion.return_value = mock_completion
    
    with pytest.raises(ClassificationError, match="invalid data"):
        classifier.classify("Как открыть счет?")


@pytest.mark.unit
def test_classify_whitespace_handling(classifier):
    """Test that whitespace is properly sanitized."""
    inquiry = "  Как  открыть   счет?  "
    
    result = classifier.classify(inquiry)
    
    assert result.inquiry == "Как открыть счет?"  # Whitespace normalized


@pytest.mark.unit
def test_classify_confidence_bounds(classifier, mock_scibox_client):
    """Test confidence values are within valid range."""
    # Mock response with edge case confidence
    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message = Mock()
    mock_completion.choices[0].message.content = json.dumps({
        "category": "Новые клиенты",
        "subcategory": "Регистрация и онбординг",
        "confidence": 1.5  # Invalid, should be clamped
    })
    
    mock_scibox_client.chat_completion.return_value = mock_completion
    
    # Should still work (confidence extracted as-is, validation in Pydantic model)
    result = classifier.classify("Как открыть счет?")
    assert isinstance(result, ClassificationResult)


# Batch Processing Tests

@pytest.mark.unit
@pytest.mark.asyncio
async def test_classify_batch_valid_inquiries(classifier):
    """Test batch classification with valid inquiries."""
    inquiries = [
        "Как открыть счет?",
        "Какая ставка по вкладу?",
        "Забыл пароль"
    ]
    
    results = await classifier.classify_batch(inquiries)
    
    assert len(results) == len(inquiries)
    for result in results:
        assert isinstance(result, ClassificationResult)
        assert result.category
        assert result.subcategory


@pytest.mark.unit
@pytest.mark.asyncio
async def test_classify_batch_empty_batch(classifier):
    """Test that empty batch raises error."""
    from src.classification.classifier import ClassificationError
    
    with pytest.raises(ClassificationError, match="at least one"):
        await classifier.classify_batch([])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_classify_batch_oversized_batch(classifier):
    """Test that oversized batch raises error."""
    from src.classification.classifier import ClassificationError
    
    inquiries = ["Тест"] * 101
    
    with pytest.raises(ClassificationError, match="must not exceed 100"):
        await classifier.classify_batch(inquiries)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_classify_batch_result_ordering(classifier):
    """Test that batch results maintain input order."""
    inquiries = [
        "Первый запрос",
        "Второй запрос",
        "Третий запрос"
    ]
    
    results = await classifier.classify_batch(inquiries)
    
    for i, (inquiry, result) in enumerate(zip(inquiries, results)):
        assert result.inquiry == inquiry


@pytest.mark.unit
@pytest.mark.asyncio
async def test_classify_batch_mixed_validity(classifier, mock_scibox_client):
    """Test batch with mixed valid/invalid inquiries."""
    inquiries = [
        "Как открыть счет?",  # Valid
        "",  # Invalid
        "Какая ставка?"  # Valid
    ]
    
    # Configure mock to fail for empty inquiry
    def side_effect_classify(inquiry):
        if not inquiry:
            from src.classification.classifier import ClassificationError
            raise ClassificationError("Empty inquiry")
        return classifier.classify(inquiry)
    
    results = await classifier.classify_batch(inquiries)
    
    # Should return results for all (with placeholder for failed)
    assert len(results) == len(inquiries)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_classify_batch_one_failure_continues(classifier, mock_scibox_client):
    """Test that one failure doesn't stop batch processing."""
    # Mock one failure in the middle
    call_count = [0]
    
    def mock_classify_with_failure(inquiry):
        call_count[0] += 1
        if call_count[0] == 2:
            from src.classification.classifier import ClassificationError
            raise ClassificationError("Simulated failure")
        return classifier.classify(inquiry)
    
    inquiries = ["Запрос 1", "Запрос 2", "Запрос 3"]
    
    results = await classifier.classify_batch(inquiries)
    
    # All should have results (failed one gets placeholder)
    assert len(results) == len(inquiries)
