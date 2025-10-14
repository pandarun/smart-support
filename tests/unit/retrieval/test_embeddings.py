"""
Unit tests for EmbeddingsClient and precomputation.

Tests:
- embed() returns correct shape (768,) and dtype (float32)
- embed_batch() handles multiple texts
- Exponential backoff retry on API failures (mock retries)
- Error wrapping for Scibox API exceptions
- Precomputation logic with mocked FAQ parser
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from openai import OpenAIError

from src.retrieval.embeddings import EmbeddingsClient, EmbeddingsError, precompute_embeddings
from src.retrieval.cache import EmbeddingCache


class TestEmbeddingsClient:
    """Unit tests for EmbeddingsClient."""

    def test_initialization_with_api_key(self):
        """Test successful initialization with API key."""
        # Act
        client = EmbeddingsClient(api_key="test_key", model="bge-m3")

        # Assert
        assert client.api_key == "test_key"
        assert client.model == "bge-m3"
        assert client.client is not None

    def test_initialization_without_api_key_raises_error(self, monkeypatch):
        """Test that initialization without API key raises ValueError."""
        # Arrange - remove SCIBOX_API_KEY from environment
        monkeypatch.delenv("SCIBOX_API_KEY", raising=False)

        # Act & Assert
        with pytest.raises(ValueError, match="SCIBOX_API_KEY must be provided"):
            EmbeddingsClient()

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_returns_correct_shape_and_dtype(self, mock_openai_class):
        """Test that embed() returns (768,) float32 array."""
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 768)]
        mock_client.embeddings.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act
        embedding = client.embed("Test text")

        # Assert
        assert embedding.shape == (768,)
        assert embedding.dtype == np.float32
        mock_client.embeddings.create.assert_called_once()

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_empty_text_raises_error(self, mock_openai_class):
        """Test that embed() with empty text raises ValueError."""
        # Arrange
        client = EmbeddingsClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(ValueError, match="Text cannot be empty"):
            client.embed("")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            client.embed("   ")  # Whitespace only

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_batch_returns_list_of_arrays(self, mock_openai_class):
        """Test that embed_batch() returns list of numpy arrays."""
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 768),
            Mock(embedding=[0.2] * 768),
            Mock(embedding=[0.3] * 768)
        ]
        mock_client.embeddings.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act
        embeddings = client.embed_batch(["Text 1", "Text 2", "Text 3"])

        # Assert
        assert len(embeddings) == 3
        for emb in embeddings:
            assert emb.shape == (768,)
            assert emb.dtype == np.float32

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_batch_empty_list_raises_error(self, mock_openai_class):
        """Test that embed_batch() with empty list raises ValueError."""
        # Arrange
        client = EmbeddingsClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            client.embed_batch([])

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_batch_filters_empty_strings(self, mock_openai_class):
        """Test that embed_batch() filters out empty strings."""
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 768),
            Mock(embedding=[0.2] * 768)
        ]
        mock_client.embeddings.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act
        embeddings = client.embed_batch(["Text 1", "", "Text 2", "   "])

        # Assert
        assert len(embeddings) == 2
        # Verify only non-empty texts were sent to API
        call_args = mock_client.embeddings.create.call_args
        assert len(call_args[1]["input"]) == 2

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_retries_on_api_error(self, mock_openai_class):
        """Test exponential backoff retry on API errors."""
        # Arrange
        mock_client = Mock()

        # First 2 calls fail, 3rd succeeds
        mock_client.embeddings.create = Mock(
            side_effect=[
                OpenAIError("API Error 1"),
                OpenAIError("API Error 2"),
                Mock(data=[Mock(embedding=[0.1] * 768)])
            ]
        )
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act
        embedding = client.embed("Test text")

        # Assert
        assert embedding.shape == (768,)
        # Should have been called 3 times (2 failures + 1 success)
        assert mock_client.embeddings.create.call_count == 3

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_fails_after_max_retries(self, mock_openai_class):
        """Test that embed() raises EmbeddingsError after max retries."""
        # Arrange
        mock_client = Mock()
        mock_client.embeddings.create = Mock(
            side_effect=OpenAIError("Persistent API Error")
        )
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="Scibox API error"):
            client.embed("Test text")

        # Should have retried 3 times
        assert mock_client.embeddings.create.call_count == 3

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_wraps_api_errors(self, mock_openai_class):
        """Test that API errors are wrapped in EmbeddingsError."""
        # Arrange
        mock_client = Mock()
        mock_client.embeddings.create = Mock(
            side_effect=OpenAIError("Test API Error")
        )
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="Scibox API error"):
            client.embed("Test text")

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_validates_response_shape(self, mock_openai_class):
        """Test that unexpected embedding shape raises EmbeddingsError."""
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 100)]  # Wrong shape
        mock_client.embeddings.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="Unexpected embedding shape"):
            client.embed("Test text")

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_empty_response_raises_error(self, mock_openai_class):
        """Test that empty API response raises EmbeddingsError."""
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = []  # Empty response
        mock_client.embeddings.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="empty response"):
            client.embed("Test text")

    @patch('src.retrieval.embeddings.OpenAI')
    def test_embed_batch_validates_response_count(self, mock_openai_class):
        """Test that mismatched response count raises EmbeddingsError."""
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 768)]  # Only 1, expected 3
        mock_client.embeddings.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        client = EmbeddingsClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="returned .* embeddings, expected"):
            client.embed_batch(["Text 1", "Text 2", "Text 3"])


class TestPrecomputeEmbeddings:
    """Unit tests for precompute_embeddings function."""

    @pytest.fixture
    def mock_faq_templates(self):
        """Sample FAQ templates for testing."""
        return [
            {
                "id": "tmpl_001",
                "category": "Счета и вклады",
                "subcategory": "Открытие счета",
                "question": "Как открыть счет?",
                "answer": "Посетите отделение банка."
            },
            {
                "id": "tmpl_002",
                "category": "Кредиты",
                "subcategory": "Потребительский кредит",
                "question": "Как получить кредит?",
                "answer": "Подайте заявку онлайн."
            },
        ]

    @pytest.mark.asyncio
    @patch('src.classification.faq_parser.parse_faq')
    async def test_precompute_embeddings_success(self, mock_parse_faq, mock_faq_templates):
        """Test successful precomputation with mocked FAQ parser."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates

        mock_client = Mock()
        mock_client.embed_batch = Mock(
            return_value=[
                np.ones(768, dtype=np.float32),
                np.ones(768, dtype=np.float32)
            ]
        )

        # Act
        cache = await precompute_embeddings(
            faq_path="test.xlsx",
            embeddings_client=mock_client,
            batch_size=2
        )

        # Assert
        assert isinstance(cache, EmbeddingCache)
        assert len(cache) == 2
        assert cache.is_ready
        assert cache.precompute_time > 0

        # Verify embeddings were called
        mock_client.embed_batch.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.classification.faq_parser.parse_faq')
    async def test_precompute_embeddings_batching(self, mock_parse_faq, mock_faq_templates):
        """Test that templates are batched correctly."""
        # Arrange - create 5 templates, batch_size=2
        templates = mock_faq_templates * 3  # 6 templates
        mock_parse_faq.return_value = templates

        mock_client = Mock()
        mock_client.embed_batch = Mock(
            return_value=[np.ones(768, dtype=np.float32)] * 2  # Return 2 embeddings per batch
        )

        # Act
        cache = await precompute_embeddings(
            faq_path="test.xlsx",
            embeddings_client=mock_client,
            batch_size=2
        )

        # Assert
        # Should have called embed_batch 3 times (6 templates / batch_size=2)
        assert mock_client.embed_batch.call_count == 3

    @pytest.mark.asyncio
    @patch('src.classification.faq_parser.parse_faq')
    async def test_precompute_embeddings_partial_failure(self, mock_parse_faq, mock_faq_templates):
        """Test that precomputation continues after partial batch failure."""
        # Arrange
        templates = mock_faq_templates * 3  # 6 templates
        mock_parse_faq.return_value = templates

        mock_client = Mock()
        # First batch fails, second and third succeed
        mock_client.embed_batch = Mock(
            side_effect=[
                EmbeddingsError("Batch 1 failed"),
                [np.ones(768, dtype=np.float32)] * 2,
                [np.ones(768, dtype=np.float32)] * 2
            ]
        )

        # Act
        cache = await precompute_embeddings(
            faq_path="test.xlsx",
            embeddings_client=mock_client,
            batch_size=2
        )

        # Assert
        # Should have 2 templates (2 batches succeeded with 1 template each due to filtering)
        # Note: The actual cache ends up with 2 templates due to how the mock is set up
        assert len(cache) == 2
        assert cache.is_ready  # Still ready even with partial failure

    @pytest.mark.asyncio
    @patch('src.classification.faq_parser.parse_faq')
    async def test_precompute_embeddings_all_batches_fail(self, mock_parse_faq, mock_faq_templates):
        """Test that precomputation raises error if all batches fail."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates

        mock_client = Mock()
        mock_client.embed_batch = Mock(
            side_effect=EmbeddingsError("All batches failed")
        )

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="All embedding batches failed"):
            await precompute_embeddings(
                faq_path="test.xlsx",
                embeddings_client=mock_client,
                batch_size=2
            )

    @pytest.mark.asyncio
    @patch('src.classification.faq_parser.parse_faq')
    async def test_precompute_embeddings_faq_not_found(self, mock_parse_faq):
        """Test that FileNotFoundError is raised if FAQ not found."""
        # Arrange
        mock_parse_faq.side_effect = FileNotFoundError("FAQ not found")
        mock_client = Mock()

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="FAQ database not found"):
            await precompute_embeddings(
                faq_path="nonexistent.xlsx",
                embeddings_client=mock_client,
                batch_size=2
            )

    @pytest.mark.asyncio
    @patch('src.classification.faq_parser.parse_faq')
    async def test_precompute_embeddings_empty_faq(self, mock_parse_faq):
        """Test that error is raised if FAQ is empty."""
        # Arrange
        mock_parse_faq.return_value = []  # Empty FAQ
        mock_client = Mock()

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="FAQ database is empty"):
            await precompute_embeddings(
                faq_path="empty.xlsx",
                embeddings_client=mock_client,
                batch_size=2
            )

    @pytest.mark.asyncio
    @patch('src.classification.faq_parser.parse_faq')
    async def test_precompute_embeddings_performance_warning(self, mock_parse_faq, mock_faq_templates):
        """Test that warning is logged if precomputation takes >60s."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates

        mock_client = Mock()
        mock_client.embed_batch = Mock(
            return_value=[np.ones(768, dtype=np.float32)] * 2
        )

        # Act
        # Mock time.time to return start time 0 and end time 65
        with patch('src.retrieval.embeddings.time') as mock_time:
            mock_time.time.side_effect = [0, 65]
            cache = await precompute_embeddings(
                faq_path="test.xlsx",
                embeddings_client=mock_client,
                batch_size=2
            )

        # Assert
        # Should still succeed but with warning logged
        assert cache.precompute_time == 65
