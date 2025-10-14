"""
Integration test for embedding precomputation.

Tests:
- Full embedding precomputation with real FAQ database (or subset)
- Verifies all templates embedded successfully
- Checks precomputation time (<60 seconds for 200 templates)
- Validates cache statistics (total/embedded/failed counts)
- Tests partial failure handling (some templates fail, others succeed)
"""

import pytest
import time
from unittest.mock import Mock, patch
import numpy as np

from src.retrieval.embeddings import precompute_embeddings, EmbeddingsClient, EmbeddingsError
from src.retrieval.cache import EmbeddingCache


class TestPrecomputationIntegration:
    """Integration tests for embedding precomputation."""

    @pytest.fixture
    def mock_faq_templates_small(self):
        """Small set of FAQ templates for testing (10 templates)."""
        templates = []
        categories = [
            ("Счета и вклады", "Открытие счета", 3),
            ("Кредиты", "Потребительский кредит", 3),
            ("Карты", "Дебетовые карты", 4)
        ]

        template_id = 1
        for category, subcategory, count in categories:
            for i in range(count):
                templates.append({
                    "id": f"tmpl_{template_id:03d}",
                    "category": category,
                    "subcategory": subcategory,
                    "question": f"Вопрос {template_id} про {subcategory}?",
                    "answer": f"Ответ {template_id} по теме {subcategory}. Подробная информация..."
                })
                template_id += 1

        return templates

    @pytest.fixture
    def mock_embeddings_client_success(self):
        """Mock embeddings client that always succeeds."""
        client = Mock(spec=EmbeddingsClient)

        def mock_embed_batch(texts):
            # Return random normalized embeddings
            embeddings = []
            for _ in texts:
                emb = np.random.randn(768).astype(np.float32)
                emb = emb / np.linalg.norm(emb)
                embeddings.append(emb)
            return embeddings

        client.embed_batch = Mock(side_effect=mock_embed_batch)
        return client

    @pytest.mark.asyncio
    @patch('src.retrieval.embeddings.parse_faq')
    async def test_precomputation_success_all_templates(
        self,
        mock_parse_faq,
        mock_faq_templates_small,
        mock_embeddings_client_success
    ):
        """Test successful precomputation of all templates."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates_small

        # Act
        start_time = time.time()
        cache = await precompute_embeddings(
            faq_path="test.xlsx",
            embeddings_client=mock_embeddings_client_success,
            batch_size=5
        )
        elapsed = time.time() - start_time

        # Assert
        assert isinstance(cache, EmbeddingCache)
        assert cache.is_ready

        # All 10 templates should be embedded
        stats = cache.stats
        assert stats["total_templates"] == 10
        assert stats["categories"] == 3
        assert stats["subcategories"] == 3

        # Verify cache has precompute_time set
        assert cache.precompute_time > 0
        assert cache.precompute_time == pytest.approx(elapsed, abs=0.1)

        # Verify embeddings client was called
        # 10 templates / batch_size=5 = 2 batches
        assert mock_embeddings_client_success.embed_batch.call_count == 2

    @pytest.mark.asyncio
    @patch('src.retrieval.embeddings.parse_faq')
    async def test_precomputation_batching_strategy(
        self,
        mock_parse_faq,
        mock_faq_templates_small,
        mock_embeddings_client_success
    ):
        """Test that precomputation correctly batches templates."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates_small

        # Test different batch sizes
        test_cases = [
            (10, 1),  # batch_size=10, expected 1 batch
            (5, 2),   # batch_size=5, expected 2 batches
            (3, 4),   # batch_size=3, expected 4 batches (10/3 = 3.33 -> 4)
            (2, 5),   # batch_size=2, expected 5 batches
        ]

        for batch_size, expected_batches in test_cases:
            # Reset mock
            mock_embeddings_client_success.embed_batch.reset_mock()

            # Act
            cache = await precompute_embeddings(
                faq_path="test.xlsx",
                embeddings_client=mock_embeddings_client_success,
                batch_size=batch_size
            )

            # Assert
            assert mock_embeddings_client_success.embed_batch.call_count == expected_batches, \
                f"batch_size={batch_size} should result in {expected_batches} batches"

    @pytest.mark.asyncio
    @patch('src.retrieval.embeddings.parse_faq')
    async def test_precomputation_partial_failure_continues(
        self,
        mock_parse_faq,
        mock_faq_templates_small
    ):
        """Test that precomputation continues after partial batch failure."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates_small

        # Create client that fails on first batch, succeeds on second
        client = Mock(spec=EmbeddingsClient)
        call_count = 0

        def mock_embed_batch_partial_fail(texts):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise EmbeddingsError("First batch failed")
            # Subsequent batches succeed
            return [np.random.randn(768).astype(np.float32) for _ in texts]

        client.embed_batch = Mock(side_effect=mock_embed_batch_partial_fail)

        # Act
        cache = await precompute_embeddings(
            faq_path="test.xlsx",
            embeddings_client=client,
            batch_size=5  # 10 templates / 5 = 2 batches
        )

        # Assert
        # Should have 5 templates (second batch only)
        assert len(cache) == 5
        assert cache.is_ready  # Still ready despite partial failure

        # Both batches should have been attempted
        assert client.embed_batch.call_count == 2

    @pytest.mark.asyncio
    @patch('src.retrieval.embeddings.parse_faq')
    async def test_precomputation_all_batches_fail_raises_error(
        self,
        mock_parse_faq,
        mock_faq_templates_small
    ):
        """Test that precomputation raises error if all batches fail."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates_small

        client = Mock(spec=EmbeddingsClient)
        client.embed_batch = Mock(side_effect=EmbeddingsError("All batches failed"))

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="All embedding batches failed"):
            await precompute_embeddings(
                faq_path="test.xlsx",
                embeddings_client=client,
                batch_size=5
            )

    @pytest.mark.asyncio
    @patch('src.retrieval.embeddings.parse_faq')
    async def test_precomputation_cache_statistics(
        self,
        mock_parse_faq,
        mock_faq_templates_small,
        mock_embeddings_client_success
    ):
        """Test that cache statistics are correctly computed."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates_small

        # Act
        cache = await precompute_embeddings(
            faq_path="test.xlsx",
            embeddings_client=mock_embeddings_client_success,
            batch_size=5
        )

        # Assert - check statistics
        stats = cache.stats

        # Total templates
        assert stats["total_templates"] == 10

        # Categories: 3 unique categories
        assert stats["categories"] == 3

        # Subcategories: 3 unique subcategories
        assert stats["subcategories"] == 3

        # Precompute time should be set
        assert stats["precompute_time_seconds"] is not None
        assert stats["precompute_time_seconds"] > 0

        # Memory estimate should be reasonable
        # 10 templates × 768 dims × 4 bytes = ~30 KB (very small)
        assert stats["memory_estimate_mb"] < 1.0  # Should be less than 1 MB

    @pytest.mark.asyncio
    @patch('src.retrieval.embeddings.parse_faq')
    async def test_precomputation_embeddings_normalized(
        self,
        mock_parse_faq,
        mock_faq_templates_small,
        mock_embeddings_client_success
    ):
        """Test that precomputed embeddings are normalized in cache."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates_small[:3]  # Just 3 templates

        # Act
        cache = await precompute_embeddings(
            faq_path="test.xlsx",
            embeddings_client=mock_embeddings_client_success,
            batch_size=5
        )

        # Assert - check that all embeddings are normalized
        for template_id, embedding, metadata in cache.get_all():
            norm = np.linalg.norm(embedding)
            assert np.isclose(norm, 1.0, atol=0.01), \
                f"Embedding for {template_id} not normalized: norm={norm}"

    @pytest.mark.asyncio
    @patch('src.retrieval.embeddings.parse_faq')
    async def test_precomputation_performance_fast_with_mocks(
        self,
        mock_parse_faq,
        mock_faq_templates_small,
        mock_embeddings_client_success
    ):
        """Test that precomputation is fast with mocked client."""
        # Arrange
        mock_parse_faq.return_value = mock_faq_templates_small

        # Act
        start_time = time.time()
        cache = await precompute_embeddings(
            faq_path="test.xlsx",
            embeddings_client=mock_embeddings_client_success,
            batch_size=5
        )
        elapsed = time.time() - start_time

        # Assert
        # With mocked client, should be very fast (< 1 second)
        assert elapsed < 1.0, \
            f"Precomputation with mocked client took {elapsed:.2f}s, expected <1s"

    @pytest.mark.asyncio
    @patch('src.retrieval.embeddings.parse_faq')
    async def test_precomputation_empty_faq_raises_error(
        self,
        mock_parse_faq,
        mock_embeddings_client_success
    ):
        """Test that empty FAQ database raises error."""
        # Arrange
        mock_parse_faq.return_value = []  # Empty FAQ

        # Act & Assert
        with pytest.raises(EmbeddingsError, match="FAQ database is empty"):
            await precompute_embeddings(
                faq_path="empty.xlsx",
                embeddings_client=mock_embeddings_client_success,
                batch_size=5
            )

    @pytest.mark.asyncio
    async def test_precomputation_nonexistent_faq_raises_error(
        self,
        mock_embeddings_client_success
    ):
        """Test that nonexistent FAQ file raises FileNotFoundError."""
        # Note: Don't mock parse_faq, let it actually try to load the file

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="FAQ database not found"):
            await precompute_embeddings(
                faq_path="/nonexistent/path/to/faq.xlsx",
                embeddings_client=mock_embeddings_client_success,
                batch_size=5
            )


@pytest.mark.skipif(
    not pytest.config.getoption("--run-online", default=False),
    reason="Online tests require --run-online flag and SCIBOX_API_KEY"
)
class TestPrecomputationIntegrationOnline:
    """
    Integration tests with real Scibox API (online testing).

    Run with: pytest --run-online tests/integration/retrieval/

    Requires:
    - SCIBOX_API_KEY environment variable
    - FAQ_PATH pointing to real FAQ database
    - Internet connection to Scibox API
    """

    @pytest.mark.asyncio
    async def test_precomputation_with_real_api(self, embeddings_client_real):
        """
        Test precomputation with real Scibox API.

        This test will make real API calls and may take 30-60 seconds.
        """
        import os

        # Arrange
        faq_path = os.getenv("FAQ_PATH")
        if not faq_path or not os.path.exists(faq_path):
            pytest.skip("FAQ_PATH not set or file not found")

        # Act
        start_time = time.time()
        cache = await precompute_embeddings(
            faq_path=faq_path,
            embeddings_client=embeddings_client_real,
            batch_size=20
        )
        elapsed = time.time() - start_time

        # Assert
        stats = cache.stats
        assert stats["total_templates"] > 0, "Should have embedded at least one template"
        assert cache.is_ready

        # Performance check: <60s for 200 templates (extrapolate)
        expected_max_time = (stats["total_templates"] / 200) * 60
        assert elapsed < expected_max_time, \
            f"Precomputation took {elapsed:.1f}s for {stats['total_templates']} templates, " \
            f"expected <{expected_max_time:.1f}s"

        # Log performance for monitoring
        templates_per_second = stats["total_templates"] / elapsed
        print(f"\n✓ Real API precomputation: {stats['total_templates']} templates in {elapsed:.1f}s ({templates_per_second:.1f} templates/s)")
