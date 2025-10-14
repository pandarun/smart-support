"""
Unit tests for ranking utilities.

Tests:
- cosine_similarity_batch() correctness with known embeddings
- rank_templates() sorting (highest similarity first)
- top_k truncation
- weighted scoring formula (0.7*sim + 0.3*hist when enabled)
- statistical calculations
"""

import pytest
import numpy as np

from src.retrieval.ranker import (
    cosine_similarity_batch,
    rank_templates,
    calculate_similarity_statistics,
    filter_low_confidence_results
)
from src.retrieval.cache import TemplateMetadata
from src.retrieval.models import RetrievalResult


class TestCosineSimilarityBatch:
    """Tests for cosine_similarity_batch function."""

    def test_cosine_similarity_identical_vectors(self):
        """Test that identical vectors have similarity = 1.0."""
        # Arrange
        query = np.ones(1024, dtype=np.float32)
        templates = np.ones((5, 1024), dtype=np.float32)

        # Act
        similarities = cosine_similarity_batch(query, templates)

        # Assert
        assert similarities.shape == (5,)
        assert np.allclose(similarities, 1.0, atol=0.01)

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test that orthogonal vectors have similarity ≈ 0.0."""
        # Arrange - create orthogonal vectors
        query = np.zeros(1024, dtype=np.float32)
        query[0] = 1.0  # Vector along first axis

        template = np.zeros(1024, dtype=np.float32)
        template[1] = 1.0  # Vector along second axis (orthogonal)

        templates = np.array([template])

        # Act
        similarities = cosine_similarity_batch(query, templates)

        # Assert
        assert similarities.shape == (1,)
        assert np.abs(similarities[0]) < 0.1  # Should be close to 0

    def test_cosine_similarity_opposite_vectors(self):
        """Test that opposite vectors have similarity = 0.0 (clamped from -1.0)."""
        # Arrange
        query = np.ones(1024, dtype=np.float32)
        template = -np.ones(1024, dtype=np.float32)
        templates = np.array([template])

        # Act
        similarities = cosine_similarity_batch(query, templates)

        # Assert
        # Cosine of opposite vectors is -1, but we clamp to [0, 1]
        assert similarities[0] >= 0.0

    def test_cosine_similarity_shape_validation(self):
        """Test that invalid shapes raise ValueError."""
        # Test invalid query shape
        with pytest.raises(ValueError, match="Invalid query embedding shape"):
            cosine_similarity_batch(np.ones(100), np.ones((5, 1024)))

        # Test invalid template shape
        with pytest.raises(ValueError, match="Invalid template embeddings shape"):
            cosine_similarity_batch(np.ones(1024), np.ones((5, 100)))

    def test_cosine_similarity_zero_norm_query(self):
        """Test that zero-norm query raises ValueError."""
        # Arrange
        query = np.zeros(1024, dtype=np.float32)  # Zero vector
        templates = np.ones((5, 1024), dtype=np.float32)

        # Act & Assert
        with pytest.raises(ValueError, match="zero norm"):
            cosine_similarity_batch(query, templates)

    def test_cosine_similarity_normalized_inputs(self):
        """Test that pre-normalized inputs work correctly."""
        # Arrange - create normalized vectors
        query = np.random.randn(1024).astype(np.float32)
        query = query / np.linalg.norm(query)

        templates = np.random.randn(10, 1024).astype(np.float32)
        templates = templates / np.linalg.norm(templates, axis=1, keepdims=True)

        # Act
        similarities = cosine_similarity_batch(query, templates)

        # Assert
        assert similarities.shape == (10,)
        assert np.all(similarities >= 0.0)
        assert np.all(similarities <= 1.0)

    def test_cosine_similarity_range(self):
        """Test that similarities are in [0, 1] range."""
        # Arrange
        query = np.random.randn(1024).astype(np.float32)
        templates = np.random.randn(50, 1024).astype(np.float32)

        # Act
        similarities = cosine_similarity_batch(query, templates)

        # Assert
        assert np.all(similarities >= 0.0), "Similarities should be >= 0.0"
        assert np.all(similarities <= 1.0), "Similarities should be <= 1.0"


class TestRankTemplates:
    """Tests for rank_templates function."""

    @pytest.fixture
    def sample_candidates(self):
        """Create sample candidates with known embeddings."""
        candidates = []

        for i in range(5):
            template_id = f"tmpl_{i:03d}"
            # Create embeddings with decreasing similarity to query
            # (query will be all ones, so higher values = higher similarity)
            embedding = np.full(1024, 1.0 - (i * 0.15), dtype=np.float32)
            embedding = embedding / np.linalg.norm(embedding)  # Normalize

            metadata = TemplateMetadata(
                template_id=template_id,
                category="Test Category",
                subcategory="Test Subcategory",
                question=f"Question {i}?",
                answer=f"Answer {i}.",
                success_rate=0.5 + (i * 0.05),  # Increasing success rates
                usage_count=i * 10
            )

            candidates.append((template_id, embedding, metadata))

        return candidates

    def test_rank_templates_sorting(self, sample_candidates):
        """Test that templates are sorted by similarity descending."""
        # Arrange
        query_embedding = np.ones(1024, dtype=np.float32)

        # Act
        results = rank_templates(query_embedding, sample_candidates, top_k=5)

        # Assert
        assert len(results) == 5

        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i].similarity_score >= results[i+1].similarity_score, \
                f"Result {i} score {results[i].similarity_score} < result {i+1} score {results[i+1].similarity_score}"

        # Verify ranks are correct
        for i, result in enumerate(results):
            assert result.rank == i + 1

    def test_rank_templates_top_k_truncation(self, sample_candidates):
        """Test that top_k parameter limits results."""
        # Arrange
        query_embedding = np.ones(1024, dtype=np.float32)

        # Test different top_k values
        for top_k in [1, 2, 3]:
            # Act
            results = rank_templates(query_embedding, sample_candidates, top_k=top_k)

            # Assert
            assert len(results) == top_k, f"Should return exactly {top_k} results"

    def test_rank_templates_empty_candidates(self):
        """Test that empty candidates list returns empty results."""
        # Arrange
        query_embedding = np.ones(1024, dtype=np.float32)
        candidates = []

        # Act
        results = rank_templates(query_embedding, candidates, top_k=5)

        # Assert
        assert len(results) == 0

    def test_rank_templates_pure_similarity_scoring(self, sample_candidates):
        """Test pure similarity scoring (default, no historical weighting)."""
        # Arrange
        query_embedding = np.ones(1024, dtype=np.float32)

        # Act
        results = rank_templates(
            query_embedding,
            sample_candidates,
            top_k=5,
            use_historical_weighting=False
        )

        # Assert
        for result in results:
            # Combined score should equal similarity score (no weighting)
            assert result.combined_score == result.similarity_score

    def test_rank_templates_weighted_scoring(self, sample_candidates):
        """Test weighted scoring: 0.7*similarity + 0.3*historical."""
        # Arrange
        query_embedding = np.ones(1024, dtype=np.float32)

        # Act
        results = rank_templates(
            query_embedding,
            sample_candidates,
            top_k=5,
            use_historical_weighting=True
        )

        # Assert
        for result in results:
            # Get metadata to check success_rate
            metadata = next(
                c[2] for c in sample_candidates if c[0] == result.template_id
            )

            # Verify weighted formula
            expected_score = 0.7 * result.similarity_score + 0.3 * metadata.success_rate
            assert np.isclose(result.combined_score, expected_score, atol=0.01), \
                f"Combined score {result.combined_score} != expected {expected_score}"

    def test_rank_templates_result_denormalization(self, sample_candidates):
        """Test that results contain denormalized template data."""
        # Arrange
        query_embedding = np.ones(1024, dtype=np.float32)

        # Act
        results = rank_templates(query_embedding, sample_candidates, top_k=3)

        # Assert
        for result in results:
            assert result.template_id
            assert result.template_question
            assert result.template_answer
            assert result.category == "Test Category"
            assert result.subcategory == "Test Subcategory"

    def test_rank_templates_confidence_levels(self, sample_candidates):
        """Test that confidence levels are computed correctly."""
        # Arrange
        query_embedding = np.ones(1024, dtype=np.float32)

        # Act
        results = rank_templates(query_embedding, sample_candidates, top_k=5)

        # Assert
        for result in results:
            if result.combined_score >= 0.7:
                assert result.confidence_level == "high"
            elif result.combined_score >= 0.5:
                assert result.confidence_level == "medium"
            else:
                assert result.confidence_level == "low"

    def test_rank_templates_invalid_top_k(self, sample_candidates):
        """Test that invalid top_k raises ValueError."""
        # Arrange
        query_embedding = np.ones(1024, dtype=np.float32)

        # Act & Assert
        with pytest.raises(ValueError, match="top_k must be >= 1"):
            rank_templates(query_embedding, sample_candidates, top_k=0)

    def test_rank_templates_invalid_query_shape(self, sample_candidates):
        """Test that invalid query embedding shape raises ValueError."""
        # Arrange
        query_embedding = np.ones(100, dtype=np.float32)  # Wrong shape

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid query embedding shape"):
            rank_templates(query_embedding, sample_candidates, top_k=5)


class TestCalculateSimilarityStatistics:
    """Tests for calculate_similarity_statistics function."""

    def test_statistics_with_known_values(self):
        """Test statistics calculation with known values."""
        # Arrange
        similarities = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1])

        # Act
        stats = calculate_similarity_statistics(similarities)

        # Assert
        assert stats["min"] == 0.1
        assert stats["max"] == 0.9
        assert np.isclose(stats["mean"], 0.5, atol=0.01)
        assert stats["median"] == 0.5
        assert stats["p25"] == 0.3
        assert stats["p75"] == 0.7
        assert np.isclose(stats["p95"], 0.88, atol=0.02)

    def test_statistics_with_empty_array(self):
        """Test that empty array returns zeros."""
        # Arrange
        similarities = np.array([])

        # Act
        stats = calculate_similarity_statistics(similarities)

        # Assert
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
        assert stats["mean"] == 0.0
        assert stats["median"] == 0.0

    def test_statistics_with_single_value(self):
        """Test statistics with single value."""
        # Arrange
        similarities = np.array([0.75])

        # Act
        stats = calculate_similarity_statistics(similarities)

        # Assert
        assert stats["min"] == 0.75
        assert stats["max"] == 0.75
        assert stats["mean"] == 0.75
        assert stats["median"] == 0.75


class TestFilterLowConfidenceResults:
    """Tests for filter_low_confidence_results function."""

    def test_filter_with_mixed_confidence(self):
        """Test filtering results with mixed confidence levels."""
        # Arrange
        results = [
            RetrievalResult(
                template_id="t1",
                template_question="Q1",
                template_answer="A1",
                category="Cat",
                subcategory="Sub",
                similarity_score=0.8,
                combined_score=0.8,
                rank=1
            ),
            RetrievalResult(
                template_id="t2",
                template_question="Q2",
                template_answer="A2",
                category="Cat",
                subcategory="Sub",
                similarity_score=0.4,
                combined_score=0.4,
                rank=2
            ),
        ]

        # Act
        high, low = filter_low_confidence_results(results, min_score=0.5)

        # Assert
        assert len(high) == 1
        assert len(low) == 1
        assert high[0].combined_score >= 0.5
        assert low[0].combined_score < 0.5

    def test_filter_all_high_confidence(self):
        """Test filtering when all results are high confidence."""
        # Arrange
        results = [
            RetrievalResult(
                template_id="t1",
                template_question="Q1",
                template_answer="A1",
                category="Cat",
                subcategory="Sub",
                similarity_score=0.9,
                combined_score=0.9,
                rank=1
            ),
            RetrievalResult(
                template_id="t2",
                template_question="Q2",
                template_answer="A2",
                category="Cat",
                subcategory="Sub",
                similarity_score=0.8,
                combined_score=0.8,
                rank=2
            ),
        ]

        # Act
        high, low = filter_low_confidence_results(results, min_score=0.5)

        # Assert
        assert len(high) == 2
        assert len(low) == 0

    def test_filter_all_low_confidence(self):
        """Test filtering when all results are low confidence."""
        # Arrange
        results = [
            RetrievalResult(
                template_id="t1",
                template_question="Q1",
                template_answer="A1",
                category="Cat",
                subcategory="Sub",
                similarity_score=0.3,
                combined_score=0.3,
                rank=1
            ),
            RetrievalResult(
                template_id="t2",
                template_question="Q2",
                template_answer="A2",
                category="Cat",
                subcategory="Sub",
                similarity_score=0.2,
                combined_score=0.2,
                rank=2
            ),
        ]

        # Act
        high, low = filter_low_confidence_results(results, min_score=0.5)

        # Assert
        assert len(high) == 0
        assert len(low) == 2

    def test_filter_empty_results(self):
        """Test filtering empty results list."""
        # Act
        high, low = filter_low_confidence_results([], min_score=0.5)

        # Assert
        assert len(high) == 0
        assert len(low) == 0
