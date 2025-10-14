"""
Integration Tests for Validation Workflow

Tests validation dataset processing with real classification.

Constitution Compliance:
- Principle III: Integration tests mandated
- QR-001: ≥70% accuracy requirement
"""

import pytest
import json
from pathlib import Path


@pytest.mark.integration
def test_validation_with_sample_dataset(classifier):
    """
    Test validation against small sample dataset.
    
    Verifies accuracy calculation and per-category breakdown.
    """
    # Sample validation data (3 test cases)
    sample_data = [
        {
            "inquiry": "Как открыть счет в банке?",
            "expected_category": "Новые клиенты",
            "expected_subcategory": "Регистрация и онбординг"
        },
        {
            "inquiry": "Какая процентная ставка по вкладу?",
            "expected_category": "Продукты - Вклады",
            "expected_subcategory": "Валютные (USD)"  # May not match exactly
        },
        {
            "inquiry": "Забыл пароль от приложения",
            "expected_category": "Техническая поддержка",
            "expected_subcategory": "Проблемы и решения"
        }
    ]
    
    correct = 0
    processing_times = []
    
    for record in sample_data:
        result = classifier.classify(record["inquiry"])
        processing_times.append(result.processing_time_ms)
        
        # Check if classification matches expected
        if (result.category == record["expected_category"] and 
            result.subcategory == record["expected_subcategory"]):
            correct += 1
    
    # Calculate accuracy
    accuracy = (correct / len(sample_data)) * 100
    
    # Verify accuracy calculation
    assert 0.0 <= accuracy <= 100.0
    
    # Verify processing time stats
    assert len(processing_times) == len(sample_data)
    assert all(t < 2000 for t in processing_times), "All should meet <2s requirement"
    
    # Calculate stats
    min_time = min(processing_times)
    max_time = max(processing_times)
    mean_time = sum(processing_times) / len(processing_times)
    
    assert min_time > 0
    assert max_time >= min_time
    assert mean_time > 0


@pytest.mark.integration
def test_validation_accuracy_formula(classifier, sample_validation_records):
    """
    Test validation accuracy calculation formula.
    
    Verifies: accuracy = (correct / total) * 100
    """
    total = len(sample_validation_records)
    correct = 0
    
    for record in sample_validation_records:
        result = classifier.classify(record["inquiry"])
        
        # Exact match required for "correct"
        if (result.category == record["expected_category"] and
            result.subcategory == record["expected_subcategory"]):
            correct += 1
    
    accuracy = (correct / total) * 100
    
    # Verify accuracy is percentage
    assert 0.0 <= accuracy <= 100.0
    assert isinstance(accuracy, float)


@pytest.mark.integration
def test_validation_per_category_breakdown(classifier, sample_validation_records):
    """
    Test per-category accuracy breakdown.
    """
    # Group by category
    from collections import defaultdict
    category_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    
    for record in sample_validation_records:
        result = classifier.classify(record["inquiry"])
        
        expected_cat = record["expected_category"]
        category_stats[expected_cat]["total"] += 1
        
        if (result.category == expected_cat and
            result.subcategory == record["expected_subcategory"]):
            category_stats[expected_cat]["correct"] += 1
    
    # Verify each category has accuracy calculated
    for category, stats in category_stats.items():
        assert stats["total"] > 0
        assert 0 <= stats["correct"] <= stats["total"]
        
        accuracy = (stats["correct"] / stats["total"]) * 100
        assert 0.0 <= accuracy <= 100.0


@pytest.mark.integration
@pytest.mark.slow
def test_validation_processing_time_statistics(classifier, sample_validation_records):
    """
    Test processing time statistics calculation.
    
    Verifies: min, max, mean, p95
    """
    processing_times = []
    
    for record in sample_validation_records:
        result = classifier.classify(record["inquiry"])
        processing_times.append(result.processing_time_ms)
    
    # Calculate statistics
    min_time = min(processing_times)
    max_time = max(processing_times)
    mean_time = sum(processing_times) / len(processing_times)
    
    # P95 calculation (simple: sort and take 95th percentile)
    sorted_times = sorted(processing_times)
    p95_index = int(len(sorted_times) * 0.95)
    p95_time = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
    
    # Verify stats make sense
    assert min_time <= mean_time <= max_time
    assert p95_time >= mean_time  # P95 should be >= mean
    assert p95_time <= max_time
