"""
Integration Tests for Batch Classification

Tests batch processing with parallel execution and result ordering.

Constitution Compliance:
- Principle III: Integration tests mandated
- User Story 3: Batch processing efficiency
"""

import pytest
import asyncio


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_classification_basic(classifier, sample_inquiries):
    """
    Test basic batch classification with multiple inquiries.
    
    Verifies all inquiries are classified successfully.
    """
    # Use first 5 sample inquiries
    inquiries = sample_inquiries[:5]
    
    results = await classifier.classify_batch(inquiries)
    
    # All inquiries should be classified
    assert len(results) == len(inquiries)
    
    # Each result should have valid structure
    for result in results:
        assert result.category
        assert result.subcategory
        assert 0.0 <= result.confidence <= 1.0
        assert result.processing_time_ms >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_classification_parallel_performance(classifier, sample_inquiries):
    """
    Test that batch processing uses parallel execution.
    
    Verifies total time < sum of individual times (parallel speedup).
    """
    inquiries = sample_inquiries[:3]
    
    # Measure batch processing time
    import time
    start_time = time.time()
    results = await classifier.classify_batch(inquiries)
    batch_time_ms = (time.time() - start_time) * 1000
    
    # Sum individual processing times
    individual_times_sum = sum(r.processing_time_ms for r in results)
    
    # Batch should be faster than sequential (allowing for overhead)
    # Parallel processing should take ~max(individual_times) not sum
    assert batch_time_ms < individual_times_sum, \
        f"Batch time {batch_time_ms}ms should be less than sum {individual_times_sum}ms"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_classification_result_ordering(classifier):
    """
    Test that results maintain input order.
    
    Verifies results are returned in same order as input inquiries.
    """
    inquiries = [
        "Первый запрос: как открыть счет?",
        "Второй запрос: какая ставка по вкладу?",
        "Третий запрос: забыл пароль"
    ]
    
    results = await classifier.classify_batch(inquiries)
    
    # Verify order by checking inquiry text
    assert len(results) == len(inquiries)
    for i, (inquiry, result) in enumerate(zip(inquiries, results)):
        assert result.inquiry == inquiry, f"Result {i} order mismatch"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_classification_empty_batch(classifier):
    """
    Test that empty batch is rejected.
    """
    from src.classification.classifier import ClassificationError
    
    with pytest.raises(ClassificationError, match="at least one"):
        await classifier.classify_batch([])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_classification_oversized_batch(classifier):
    """
    Test that oversized batch (>100) is rejected.
    """
    from src.classification.classifier import ClassificationError
    
    # Create batch with 101 inquiries
    inquiries = ["Тестовый запрос"] * 101
    
    with pytest.raises(ClassificationError, match="must not exceed 100"):
        await classifier.classify_batch(inquiries)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_classification_mixed_validity(classifier):
    """
    Test batch with mix of valid and invalid inquiries.
    
    Verifies partial failures are handled gracefully.
    """
    inquiries = [
        "Как открыть счет?",  # Valid
        "",  # Invalid - too short
        "Какая ставка по вкладу?",  # Valid
        "Hi",  # Invalid - no Cyrillic, too short
        "Забыл пароль"  # Valid
    ]
    
    results = await classifier.classify_batch(inquiries)
    
    # Should return results for all (with placeholder for failed)
    assert len(results) == len(inquiries)
    
    # Valid inquiries should have proper classifications
    assert results[0].category != "Unknown"
    assert results[2].category != "Unknown"
    assert results[4].category != "Unknown"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_batch_classification_large_batch(classifier, sample_inquiries):
    """
    Test batch processing with 10 inquiries.
    
    Verifies scalability and performance with larger batches.
    """
    # Create batch of 10 inquiries
    inquiries = sample_inquiries[:5] * 2  # Duplicate to get 10
    
    results = await classifier.classify_batch(inquiries)
    
    # All should succeed
    assert len(results) == len(inquiries)
    
    # Total time should be reasonable (<20 seconds for 10 inquiries)
    total_time_ms = sum(r.processing_time_ms for r in results)
    assert total_time_ms < 20000, \
        f"Batch of 10 took {total_time_ms}ms, exceeds 20s limit"
