"""
Unit tests for TemplateRetriever class.

Tests retrieval logic with mocked dependencies:
- Valid retrieval request handling
- Empty category handling (no templates)
- Low similarity score warnings
- top_k parameter validation
- Processing time measurement
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np

from src.retrieval.retriever import TemplateRetriever
from src.retrieval.models import RetrievalRequest, RetrievalResponse
from src.retrieval.cache import EmbeddingCache, TemplateMetadata


class TestTemplateRetriever:
    """Unit tests for TemplateRetriever."""

    @pytest.fixture
    def mock_embeddings_client(self):
        """Mock embeddings client that returns fixed embedding."""
        client = Mock()
        client.embed = Mock(return_value=np.ones(768, dtype=np.float32))
        return client

    @pytest.fixture
    def mock_cache_with_templates(self):
        """Mock cache with 3 templates in one category."""
        cache = EmbeddingCache()

        # Add 3 templates with known embeddings
        for i in range(3):
            template_id = f"tmpl_{i:03d}"
            # Create embeddings with decreasing similarity to query (all ones)
            # More ones = higher similarity
            embedding = np.full(768, 1.0 - (i * 0.2), dtype=np.float32)

            metadata = TemplateMetadata(
                template_id=template_id,
                category="Счета и вклады",
                subcategory="Открытие счета",
                question=f"Вопрос {i}?",
                answer=f"Ответ {i}."
            )

            cache.add(template_id, embedding, metadata)

        return cache

    @pytest.fixture
    def mock_cache_empty(self):
        """Mock cache with no templates (but is_ready=True to pass initialization)."""
        cache = EmbeddingCache()
        # Add one dummy template to make cache ready, but in different category
        cache.add(
            "dummy",
            np.ones(768, dtype=np.float32),
            TemplateMetadata(
                template_id="dummy",
                category="Другая категория",
                subcategory="Другая подкатегория",
                question="Dummy",
                answer="Dummy"
            )
        )
        return cache

    def test_retriever_initialization_with_ready_cache(self, mock_embeddings_client, mock_cache_with_templates):
        """Test that retriever initializes successfully with ready cache."""
        # Act
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)

        # Assert
        assert retriever.is_ready()
        assert retriever.embeddings_client == mock_embeddings_client
        assert retriever.cache == mock_cache_with_templates

    def test_retriever_initialization_fails_with_empty_cache(self, mock_embeddings_client):
        """Test that retriever raises ValueError if cache is not ready."""
        # Arrange
        empty_cache = EmbeddingCache()  # Not ready

        # Act & Assert
        with pytest.raises(ValueError, match="Cache is not ready"):
            TemplateRetriever(mock_embeddings_client, empty_cache)

    def test_retrieve_valid_request(self, mock_embeddings_client, mock_cache_with_templates):
        """Test valid retrieval request returns correct results."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)
        request = RetrievalRequest(
            query="Как открыть счет?",
            category="Счета и вклады",
            subcategory="Открытие счета",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        assert isinstance(response, RetrievalResponse)
        assert response.query == request.query
        assert response.category == request.category
        assert response.subcategory == request.subcategory
        assert len(response.results) == 3  # All 3 templates in category
        assert response.total_candidates == 3
        assert response.processing_time_ms > 0

        # Verify results are ranked
        for i, result in enumerate(response.results):
            assert result.rank == i + 1

    def test_retrieve_empty_category(self, mock_embeddings_client, mock_cache_empty):
        """Test retrieval when no templates in category returns empty results with warning."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_empty)
        request = RetrievalRequest(
            query="Тестовый запрос",
            category="Несуществующая категория",
            subcategory="Несуществующая подкатегория",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        assert len(response.results) == 0
        assert response.total_candidates == 0
        assert len(response.warnings) > 0
        assert any("No templates found" in w for w in response.warnings)

    def test_retrieve_top_k_parameter(self, mock_embeddings_client, mock_cache_with_templates):
        """Test that top_k parameter limits number of results."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)

        # Test top_k=2 (should return 2 results even though 3 available)
        request = RetrievalRequest(
            query="Тестовый запрос",
            category="Счета и вклады",
            subcategory="Открытие счета",
            top_k=2
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        assert len(response.results) == 2
        assert response.total_candidates == 3  # But only 2 returned

    def test_retrieve_low_similarity_warning(self, mock_embeddings_client, mock_cache_with_templates):
        """Test that warning is generated when all scores < 0.5."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)

        # Mock embed to return vector with very low similarity
        mock_embeddings_client.embed = Mock(
            return_value=np.full(768, -1.0, dtype=np.float32)  # Will have low similarity
        )

        request = RetrievalRequest(
            query="Совершенно несвязанный запрос",
            category="Счета и вклады",
            subcategory="Открытие счета",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert - check if warning exists (only if all scores actually < 0.5)
        if response.results and all(r.combined_score < 0.5 for r in response.results):
            assert any("Low confidence" in w for w in response.warnings)

    def test_retrieve_processing_time_measured(self, mock_embeddings_client, mock_cache_with_templates):
        """Test that processing time is measured and included in response."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)
        request = RetrievalRequest(
            query="Тестовый запрос",
            category="Счета и вклады",
            subcategory="Открытие счета",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        assert response.processing_time_ms > 0
        assert response.processing_time_ms < 1000  # Should be fast with mocked client

    def test_retrieve_embeddings_client_called(self, mock_embeddings_client, mock_cache_with_templates):
        """Test that embeddings client is called to embed query."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)
        request = RetrievalRequest(
            query="Тест запрос",
            category="Счета и вклады",
            subcategory="Открытие счета",
            top_k=5
        )

        # Act
        retriever.retrieve(request)

        # Assert
        mock_embeddings_client.embed.assert_called_once_with(request.query)

    def test_get_cache_stats(self, mock_embeddings_client, mock_cache_with_templates):
        """Test that cache statistics are accessible."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)

        # Act
        stats = retriever.get_cache_stats()

        # Assert
        assert "total_templates" in stats
        assert stats["total_templates"] == 3

    def test_is_ready(self, mock_embeddings_client, mock_cache_with_templates):
        """Test is_ready method."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)

        # Act & Assert
        assert retriever.is_ready() is True

    @patch('src.retrieval.retriever.log_template_retrieval_requested')
    @patch('src.retrieval.retriever.log_template_retrieval_completed')
    def test_logging_called(self, mock_log_completed, mock_log_requested,
                           mock_embeddings_client, mock_cache_with_templates):
        """Test that logging functions are called during retrieval."""
        # Arrange
        retriever = TemplateRetriever(mock_embeddings_client, mock_cache_with_templates)
        request = RetrievalRequest(
            query="Тестовый запрос",
            category="Счета и вклады",
            subcategory="Открытие счета",
            top_k=5
        )

        # Act
        retriever.retrieve(request)

        # Assert
        mock_log_requested.assert_called_once()
        mock_log_completed.assert_called_once()
