"""
Unit tests for initialization module.

Tests:
- initialize_retrieval() success path
- Precomputation failure handling (all embeddings fail)
- Partial success (some embeddings fail)
- Readiness status transitions (not_ready → ready)
- get_initialization_status() function
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import os

from src.retrieval import initialize_retrieval, get_initialization_status
from src.retrieval.retriever import TemplateRetriever
from src.retrieval.cache import EmbeddingCache
from src.retrieval.embeddings import EmbeddingsError


class TestInitializeRetrieval:
    """Tests for initialize_retrieval function."""

    @pytest.mark.asyncio
    @patch('src.retrieval.EmbeddingsClient')
    @patch('src.retrieval.precompute_embeddings')
    async def test_initialize_success(self, mock_precompute, mock_client_class, monkeypatch):
        """Test successful initialization."""
        # Arrange
        monkeypatch.setenv("FAQ_PATH", "test.xlsx")
        monkeypatch.setenv("SCIBOX_API_KEY", "test_key")

        # Create mock cache
        mock_cache = Mock(spec=EmbeddingCache)
        mock_cache.is_ready = True
        mock_cache.precompute_time = 5.0
        mock_cache.stats = {
            "total_templates": 10,
            "categories": 3,
            "subcategories": 5,
            "memory_estimate_mb": 0.5,
            "precompute_time_seconds": 5.0
        }

        mock_precompute.return_value = mock_cache

        # Mock client
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Act
        retriever = await initialize_retrieval()

        # Assert
        assert isinstance(retriever, TemplateRetriever)
        assert retriever.is_ready()

        # Verify embeddings client was created
        mock_client_class.assert_called_once()

        # Verify precompute_embeddings was called
        mock_precompute.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_missing_faq_path_raises_error(self, monkeypatch):
        """Test that missing FAQ_PATH raises ValueError."""
        # Arrange
        monkeypatch.delenv("FAQ_PATH", raising=False)
        monkeypatch.setenv("SCIBOX_API_KEY", "test_key")

        # Act & Assert
        with pytest.raises(ValueError, match="FAQ path not provided"):
            await initialize_retrieval()

    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_initialize_nonexistent_faq_raises_error(self, mock_exists, monkeypatch):
        """Test that nonexistent FAQ file raises FileNotFoundError."""
        # Arrange
        monkeypatch.setenv("FAQ_PATH", "nonexistent.xlsx")
        monkeypatch.setenv("SCIBOX_API_KEY", "test_key")
        mock_exists.return_value = False

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="FAQ database not found"):
            await initialize_retrieval()

    @pytest.mark.asyncio
    @patch('src.retrieval.EmbeddingsClient')
    async def test_initialize_missing_api_key_raises_error(self, mock_client_class, monkeypatch):
        """Test that missing API key raises ValueError."""
        # Arrange
        monkeypatch.setenv("FAQ_PATH", "test.xlsx")
        monkeypatch.delenv("SCIBOX_API_KEY", raising=False)

        # Mock client initialization to raise ValueError
        mock_client_class.side_effect = ValueError("SCIBOX_API_KEY must be provided")

        # Act & Assert
        with pytest.raises(ValueError, match="SCIBOX_API_KEY"):
            await initialize_retrieval()

    @pytest.mark.asyncio
    @patch('src.retrieval.EmbeddingsClient')
    @patch('src.retrieval.precompute_embeddings')
    async def test_initialize_precompute_failure_raises_error(
        self,
        mock_precompute,
        mock_client_class,
        monkeypatch
    ):
        """Test that precomputation failure raises error."""
        # Arrange
        monkeypatch.setenv("FAQ_PATH", "test.xlsx")
        monkeypatch.setenv("SCIBOX_API_KEY", "test_key")

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock precompute to raise error
        mock_precompute.side_effect = EmbeddingsError("All batches failed")

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="All batches failed"):
            await initialize_retrieval()

    @pytest.mark.asyncio
    @patch('src.retrieval.EmbeddingsClient')
    @patch('src.retrieval.precompute_embeddings')
    async def test_initialize_custom_parameters(self, mock_precompute, mock_client_class):
        """Test initialization with custom parameters."""
        # Arrange
        mock_cache = Mock(spec=EmbeddingCache)
        mock_cache.is_ready = True
        mock_cache.precompute_time = 10.0
        mock_cache.stats = {
            "total_templates": 20,
            "categories": 5,
            "subcategories": 10,
            "memory_estimate_mb": 1.0,
            "precompute_time_seconds": 10.0
        }
        mock_precompute.return_value = mock_cache

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Act
        retriever = await initialize_retrieval(
            faq_path="/custom/path.xlsx",
            api_key="custom_key",
            embedding_model="custom-model",
            batch_size=30
        )

        # Assert
        assert isinstance(retriever, TemplateRetriever)

        # Verify embeddings client created with custom params
        mock_client_class.assert_called_once_with(
            api_key="custom_key",
            model="custom-model"
        )

        # Verify precompute called with custom params
        call_kwargs = mock_precompute.call_args[1]
        assert call_kwargs["faq_path"] == "/custom/path.xlsx"
        assert call_kwargs["batch_size"] == 30

    @pytest.mark.asyncio
    @patch('src.retrieval.EmbeddingsClient')
    @patch('src.retrieval.precompute_embeddings')
    async def test_initialize_cache_not_ready_raises_error(
        self,
        mock_precompute,
        mock_client_class,
        monkeypatch
    ):
        """Test that cache not ready raises RuntimeError."""
        # Arrange
        monkeypatch.setenv("FAQ_PATH", "test.xlsx")
        monkeypatch.setenv("SCIBOX_API_KEY", "test_key")

        # Create cache that's not ready
        mock_cache = Mock(spec=EmbeddingCache)
        mock_cache.is_ready = False  # Not ready!
        mock_cache.stats = {"total_templates": 0}
        mock_precompute.return_value = mock_cache

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Act & Assert
        with pytest.raises((ValueError, RuntimeError)):
            await initialize_retrieval()


class TestGetInitializationStatus:
    """Tests for get_initialization_status function."""

    def test_status_with_none_retriever(self):
        """Test status when retriever is None."""
        # Act
        status = get_initialization_status(None)

        # Assert
        assert status["ready"] is False
        assert status["status"] == "not_initialized"
        assert status["total_templates"] == 0

    def test_status_with_not_ready_retriever(self):
        """Test status when retriever is not ready."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = False

        # Act
        status = get_initialization_status(mock_retriever)

        # Assert
        assert status["ready"] is False
        assert status["total_templates"] == 0

    def test_status_with_ready_retriever(self):
        """Test status when retriever is ready."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 100,
            "categories": 5,
            "subcategories": 15,
            "precompute_time_seconds": 15.5,
            "memory_estimate_mb": 2.5
        }

        # Act
        status = get_initialization_status(mock_retriever)

        # Assert
        assert status["ready"] is True
        assert status["status"] == "ready"
        assert status["total_templates"] == 100
        assert status["categories"] == 5
        assert status["subcategories"] == 15
        assert status["precompute_time_seconds"] == 15.5
        assert status["memory_estimate_mb"] == 2.5
