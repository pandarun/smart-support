"""
Integration tests for Template Retrieval Module.

Tests the complete retrieval workflow with real dependencies:
- Single template retrieval with embeddings client
- Processing time validation (<1000ms requirement)
- Response format validation (RetrievalResponse schema)
- Result ranking order verification
"""

import pytest
import time
import numpy as np

from src.retrieval.models import RetrievalRequest, RetrievalResponse
from src.retrieval.retriever import TemplateRetriever


class TestRetrievalIntegration:
    """Integration tests for template retrieval workflow."""

    def test_single_retrieval_with_mock_client(self, retriever_with_mock_client):
        """
        Test single template retrieval with mocked embeddings client.

        Verifies:
        - Retrieval completes successfully
        - Response format is correct (RetrievalResponse)
        - Results are ranked by similarity
        - Processing time is measured
        """
        # Arrange
        retriever = retriever_with_mock_client
        request = RetrievalRequest(
            query="Как открыть накопительный счет в мобильном приложении?",
            category="Счета и вклады",
            subcategory="Открытие счета",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert - Response structure
        assert isinstance(response, RetrievalResponse)
        assert response.query == request.query
        assert response.category == request.category
        assert response.subcategory == request.subcategory
        assert isinstance(response.results, list)
        assert response.total_candidates >= 0
        assert response.processing_time_ms > 0
        assert isinstance(response.warnings, list)

        # Assert - Results present (should have 2 templates in "Открытие счета")
        assert len(response.results) > 0, "Should retrieve at least one template"
        assert len(response.results) <= request.top_k, f"Should return at most {request.top_k} results"

        # Assert - Results are ranked correctly
        for i, result in enumerate(response.results):
            assert result.rank == i + 1, f"Result {i} has incorrect rank"
            assert 0.0 <= result.similarity_score <= 1.0, "Similarity score out of range"
            assert 0.0 <= result.combined_score <= 1.0, "Combined score out of range"
            assert result.confidence_level in ["high", "medium", "low"]

        # Assert - Results are sorted by similarity descending
        if len(response.results) > 1:
            for i in range(len(response.results) - 1):
                assert response.results[i].similarity_score >= response.results[i + 1].similarity_score, \
                    "Results not sorted by similarity"

    def test_retrieval_processing_time(self, retriever_with_mock_client):
        """
        Test that retrieval meets <1000ms performance requirement (PR-001).

        Note: With mocked client, this should be very fast (<50ms).
        Real API calls would be 100-500ms.
        """
        # Arrange
        retriever = retriever_with_mock_client
        request = RetrievalRequest(
            query="Какой процент по вкладу для пенсионеров?",
            category="Счета и вклады",
            subcategory="Процентные ставки",
            top_k=5
        )

        # Act
        start_time = time.time()
        response = retriever.retrieve(request)
        elapsed_ms = (time.time() - start_time) * 1000

        # Assert
        assert response.processing_time_ms < 1000, \
            f"Retrieval took {response.processing_time_ms:.1f}ms, exceeds 1000ms requirement"

        # Verify processing_time_ms is accurate (within 50ms of measured time)
        assert abs(response.processing_time_ms - elapsed_ms) < 50, \
            "Reported processing time differs significantly from measured time"

    def test_retrieval_with_no_templates_in_category(self, retriever_with_mock_client):
        """
        Test retrieval when no templates exist in the specified category.

        Should return empty results with appropriate warning.
        """
        # Arrange
        retriever = retriever_with_mock_client
        request = RetrievalRequest(
            query="Какие-то услуги?",
            category="Несуществующая категория",
            subcategory="Несуществующая подкатегория",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        assert len(response.results) == 0, "Should return no results for non-existent category"
        assert response.total_candidates == 0, "Should have 0 candidates"
        assert len(response.warnings) > 0, "Should have warnings for empty category"
        assert any("No templates found" in w for w in response.warnings), \
            "Warning should mention no templates found"

    def test_retrieval_result_denormalization(self, retriever_with_mock_client):
        """
        Test that results contain denormalized template data for UI.

        Verifies:
        - template_question is populated
        - template_answer is populated
        - category and subcategory are echoed back
        """
        # Arrange
        retriever = retriever_with_mock_client
        request = RetrievalRequest(
            query="Как заказать дебетовую карту?",
            category="Карты",
            subcategory="Дебетовые карты",
            top_k=3
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        assert len(response.results) > 0, "Should have results"

        for result in response.results:
            # Denormalized fields should be populated
            assert result.template_id, "template_id should be present"
            assert result.template_question, "template_question should be present"
            assert result.template_answer, "template_answer should be present"
            assert result.category == request.category, "category should match request"
            assert result.subcategory == request.subcategory, "subcategory should match request"

            # Verify question and answer contain Cyrillic characters (Russian text)
            assert any(ord('а') <= ord(c) <= ord('я') or ord('А') <= ord(c) <= ord('Я')
                      for c in result.template_question), \
                "Question should contain Cyrillic characters"
            assert any(ord('а') <= ord(c) <= ord('я') or ord('А') <= ord(c) <= ord('Я')
                      for c in result.template_answer), \
                "Answer should contain Cyrillic characters"

    def test_retrieval_top_k_parameter(self, retriever_with_mock_client):
        """
        Test that top_k parameter correctly limits number of results.
        """
        # Arrange
        retriever = retriever_with_mock_client

        # Test different top_k values
        for top_k in [1, 3, 5, 10]:
            request = RetrievalRequest(
                query="Карты вопрос",
                category="Карты",
                subcategory="Дебетовые карты",
                top_k=top_k
            )

            # Act
            response = retriever.retrieve(request)

            # Assert
            # Results should be <= top_k and <= total_candidates
            expected_results = min(top_k, response.total_candidates)
            assert len(response.results) == expected_results, \
                f"Should return {expected_results} results for top_k={top_k}"

    def test_retrieval_with_multiple_categories(self, retriever_with_mock_client):
        """
        Test retrieval across different categories to verify filtering works.
        """
        # Arrange
        retriever = retriever_with_mock_client

        test_cases = [
            ("Счета и вклады", "Открытие счета", 2),  # 2 templates
            ("Счета и вклады", "Процентные ставки", 1),  # 1 template
            ("Кредиты", "Потребительский кредит", 2),  # 2 templates
            ("Кредиты", "Ипотека", 1),  # 1 template
            ("Карты", "Дебетовые карты", 2),  # 2 templates
            ("Карты", "Кредитные карты", 1),  # 1 template
            ("Карты", "Блокировка карты", 1),  # 1 template
        ]

        for category, subcategory, expected_candidates in test_cases:
            request = RetrievalRequest(
                query=f"Вопрос про {subcategory}",
                category=category,
                subcategory=subcategory,
                top_k=5
            )

            # Act
            response = retriever.retrieve(request)

            # Assert
            assert response.total_candidates == expected_candidates, \
                f"Expected {expected_candidates} candidates in {category} > {subcategory}, " \
                f"got {response.total_candidates}"
            assert len(response.results) <= expected_candidates, \
                f"Results count should not exceed candidates"

    def test_retrieval_confidence_levels(self, retriever_with_mock_client):
        """
        Test that confidence levels are computed correctly based on scores.

        Confidence levels:
        - high: score >= 0.7
        - medium: 0.5 <= score < 0.7
        - low: score < 0.5
        """
        # Arrange
        retriever = retriever_with_mock_client
        request = RetrievalRequest(
            query="Тестовый запрос",
            category="Карты",
            subcategory="Дебетовые карты",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        for result in response.results:
            # Verify confidence level matches score
            if result.combined_score >= 0.7:
                assert result.confidence_level == "high", \
                    f"Score {result.combined_score:.3f} should have 'high' confidence"
            elif result.combined_score >= 0.5:
                assert result.confidence_level == "medium", \
                    f"Score {result.combined_score:.3f} should have 'medium' confidence"
            else:
                assert result.confidence_level == "low", \
                    f"Score {result.combined_score:.3f} should have 'low' confidence"

    def test_retrieval_warnings_for_low_scores(self, retriever_with_mock_client, monkeypatch):
        """
        Test that warnings are generated when all results have low scores (<0.5).

        Uses monkeypatch to force low similarity scores.
        """
        # Arrange
        retriever = retriever_with_mock_client

        # Monkeypatch embeddings client to return embeddings that will have low similarity
        # (since we're using random embeddings, we can force this by making query very different)
        def mock_embed_low_similarity(text):
            # Return embedding with all small values (will have low similarity with normalized random vectors)
            return np.full(768, 0.01, dtype=np.float32)

        monkeypatch.setattr(retriever.embeddings_client, "embed", mock_embed_low_similarity)

        request = RetrievalRequest(
            query="Совершенно несвязанный запрос",
            category="Карты",
            subcategory="Дебетовые карты",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        # Should have warning about low confidence if all scores < 0.5
        if response.results and all(r.combined_score < 0.5 for r in response.results):
            assert len(response.warnings) > 0, "Should have warnings for low confidence matches"
            assert any("Low confidence" in w for w in response.warnings), \
                "Warning should mention low confidence"

    def test_cache_stats_accessible(self, retriever_with_mock_client):
        """
        Test that cache statistics are accessible through retriever.
        """
        # Arrange
        retriever = retriever_with_mock_client

        # Act
        stats = retriever.get_cache_stats()

        # Assert
        assert "total_templates" in stats
        assert "categories" in stats
        assert "subcategories" in stats
        assert "precompute_time_seconds" in stats
        assert "memory_estimate_mb" in stats

        assert stats["total_templates"] == 10  # From sample_templates fixture
        assert stats["categories"] == 3  # Счета и вклады, Кредиты, Карты
        assert stats["subcategories"] == 7  # 7 unique subcategories

    def test_retriever_readiness_check(self, retriever_with_mock_client):
        """
        Test that retriever reports readiness correctly.
        """
        # Arrange
        retriever = retriever_with_mock_client

        # Act & Assert
        assert retriever.is_ready(), "Retriever with populated cache should be ready"


@pytest.mark.skipif(
    not pytest.config.getoption("--run-online", default=False),
    reason="Online tests require --run-online flag and SCIBOX_API_KEY"
)
class TestRetrievalIntegrationOnline:
    """
    Integration tests with real Scibox API (online testing).

    Run with: pytest --run-online tests/integration/retrieval/

    Requires:
    - SCIBOX_API_KEY environment variable
    - FAQ_PATH pointing to real FAQ database
    - Internet connection to Scibox API
    """

    @pytest.mark.asyncio
    async def test_retrieval_with_real_embeddings(self, retriever_with_real_client):
        """
        Test retrieval with real Scibox embeddings API.

        This test will:
        - Precompute embeddings for real FAQ templates
        - Embed a real query
        - Verify semantic similarity works correctly
        """
        # Arrange
        retriever = await retriever_with_real_client
        request = RetrievalRequest(
            query="Как открыть накопительный счет в мобильном приложении?",
            category="Счета и вклады",
            subcategory="Открытие счета",
            top_k=5
        )

        # Act
        response = retriever.retrieve(request)

        # Assert
        assert len(response.results) > 0, "Should retrieve templates from real FAQ"
        assert response.processing_time_ms < 2000, \
            f"Real API retrieval took {response.processing_time_ms:.1f}ms (allowing 2s for network)"

        # With real embeddings, top result should have reasonable similarity
        if response.results:
            assert response.results[0].similarity_score > 0.3, \
                "Top result should have reasonable semantic similarity (>0.3)"

    @pytest.mark.asyncio
    async def test_precomputation_performance(self, embeddings_client_real):
        """
        Test that embedding precomputation meets <60s requirement for 200 templates.

        Note: This test may take up to 60 seconds to run.
        """
        from src.retrieval.embeddings import precompute_embeddings
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

        # Performance requirement: <60s for 200 templates (extrapolate from actual count)
        expected_max_time = (stats["total_templates"] / 200) * 60
        assert elapsed < expected_max_time, \
            f"Precomputation took {elapsed:.1f}s for {stats['total_templates']} templates, " \
            f"expected <{expected_max_time:.1f}s"


def pytest_configure(config):
    """Add custom pytest configuration for online tests."""
    config.addinivalue_line(
        "markers", "online: mark test as requiring internet connection and real API"
    )
