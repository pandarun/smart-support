"""
Unit Tests for Validator

Tests validation logic and accuracy calculations with mocked classifier.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import tempfile
from pathlib import Path

from src.classification.validator import Validator
from src.classification.models import ClassificationResult, ProcessingTimeStats


@pytest.fixture
def mock_classifier():
    """Mock classifier that returns predictable results."""
    classifier = Mock()
    
    def mock_classify(inquiry):
        # Return predictable results based on inquiry
        if "счет" in inquiry:
            return ClassificationResult(
                inquiry=inquiry,
                category="Новые клиенты",
                subcategory="Регистрация и онбординг",
                confidence=0.9,
                processing_time_ms=1000
            )
        elif "вклад" in inquiry:
            return ClassificationResult(
                inquiry=inquiry,
                category="Продукты - Вклады",
                subcategory="Валютные (USD)",
                confidence=0.85,
                processing_time_ms=1200
            )
        else:
            return ClassificationResult(
                inquiry=inquiry,
                category="Техническая поддержка",
                subcategory="Проблемы и решения",
                confidence=0.8,
                processing_time_ms=1100
            )
    
    classifier.classify.side_effect = mock_classify
    return classifier


@pytest.fixture
def validator(mock_classifier):
    """Create validator with mocked classifier."""
    validator = Validator()
    validator.classifier = mock_classifier
    return validator


@pytest.fixture
def sample_dataset_file():
    """Create temporary sample dataset file."""
    data = [
        {
            "inquiry": "Как открыть счет?",
            "expected_category": "Новые клиенты",
            "expected_subcategory": "Регистрация и онбординг"
        },
        {
            "inquiry": "Какая ставка по вкладу?",
            "expected_category": "Продукты - Вклады",
            "expected_subcategory": "Валютные (USD)"
        },
        {
            "inquiry": "Забыл пароль",
            "expected_category": "Техническая поддержка",
            "expected_subcategory": "Проблемы и решения"
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_load_validation_dataset_valid(validator, sample_dataset_file):
    """Test loading valid validation dataset."""
    records = validator.load_validation_dataset(sample_dataset_file)
    
    assert len(records) == 3
    assert records[0].inquiry == "Как открыть счет?"
    assert records[0].expected_category == "Новые клиенты"


@pytest.mark.unit
def test_load_validation_dataset_not_found(validator):
    """Test loading non-existent dataset raises error."""
    with pytest.raises(FileNotFoundError):
        validator.load_validation_dataset("nonexistent.json")


@pytest.mark.unit
def test_accuracy_calculation_all_correct(validator):
    """Test accuracy calculation with 100% correct."""
    # All inquiries should match expected based on mock
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        data = [
            {
                "inquiry": "Как открыть счет?",
                "expected_category": "Новые клиенты",
                "expected_subcategory": "Регистрация и онбординг"
            },
            {
                "inquiry": "Вклад в долларах",
                "expected_category": "Продукты - Вклады",
                "expected_subcategory": "Валютные (USD)"
            }
        ]
        json.dump(data, f)
        temp_path = f.name
    
    try:
        result = validator.run_validation(temp_path)
        
        assert result.total_inquiries == 2
        assert result.correct_classifications == 2
        assert result.accuracy_percentage == 100.0
    finally:
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_accuracy_calculation_partial_correct(validator):
    """Test accuracy calculation with partial correct."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        data = [
            {
                "inquiry": "Как открыть счет?",
                "expected_category": "Новые клиенты",
                "expected_subcategory": "Регистрация и онбординг"
            },
            {
                "inquiry": "Вклад",
                "expected_category": "Wrong Category",  # Will not match
                "expected_subcategory": "Wrong Subcategory"
            }
        ]
        json.dump(data, f)
        temp_path = f.name
    
    try:
        result = validator.run_validation(temp_path)
        
        assert result.total_inquiries == 2
        assert result.correct_classifications == 1
        assert result.accuracy_percentage == 50.0
    finally:
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_per_category_accuracy_breakdown(validator, sample_dataset_file):
    """Test per-category accuracy calculation."""
    result = validator.run_validation(sample_dataset_file)
    
    # Should have accuracy for each category
    assert "Новые клиенты" in result.per_category_accuracy
    assert "Продукты - Вклады" in result.per_category_accuracy
    assert "Техническая поддержка" in result.per_category_accuracy
    
    # Check accuracy structure
    for category, stats in result.per_category_accuracy.items():
        assert stats.total > 0
        assert 0 <= stats.correct <= stats.total
        assert 0.0 <= stats.accuracy <= 100.0


@pytest.mark.unit
def test_processing_time_stats_calculation(validator):
    """Test processing time statistics calculation."""
    times = [1000, 1200, 1500, 1100, 1300]
    
    stats = validator._calculate_time_stats(times)
    
    assert stats.min_ms == 1000
    assert stats.max_ms == 1500
    assert stats.mean_ms == 1220  # (1000 + 1200 + 1500 + 1100 + 1300) / 5
    assert stats.p95_ms >= stats.mean_ms


@pytest.mark.unit
def test_processing_time_stats_empty_list(validator):
    """Test processing time stats with empty list."""
    stats = validator._calculate_time_stats([])
    
    assert stats.min_ms == 0
    assert stats.max_ms == 0
    assert stats.mean_ms == 0
    assert stats.p95_ms == 0


@pytest.mark.unit
def test_processing_time_stats_single_value(validator):
    """Test processing time stats with single value."""
    stats = validator._calculate_time_stats([1000])
    
    assert stats.min_ms == 1000
    assert stats.max_ms == 1000
    assert stats.mean_ms == 1000
    assert stats.p95_ms == 1000


@pytest.mark.unit
def test_validation_result_structure(validator, sample_dataset_file):
    """Test validation result has all required fields."""
    result = validator.run_validation(sample_dataset_file)
    
    assert hasattr(result, 'total_inquiries')
    assert hasattr(result, 'correct_classifications')
    assert hasattr(result, 'accuracy_percentage')
    assert hasattr(result, 'per_category_accuracy')
    assert hasattr(result, 'processing_time_stats')
    assert hasattr(result, 'timestamp')


@pytest.mark.unit
def test_validation_empty_dataset(validator):
    """Test validation with empty dataset."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump([], f)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="No valid records"):
            validator.load_validation_dataset(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_validation_invalid_json(validator):
    """Test validation with invalid JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        f.write("not valid json {")
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Invalid JSON"):
            validator.load_validation_dataset(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)
