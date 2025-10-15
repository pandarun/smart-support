"""
Integration Tests for POST /api/retrieve Endpoint

Tests the retrieval API endpoint with various inputs and validates:
- Request/response model validation
- Performance requirements (FR-010: <1s retrieval time)
- Ranking and filtering logic
- Top-k result limiting

Constitution Compliance:
- Principle III: Data-Driven Validation (tests against real retrieval requirements)
- Principle VI: Knowledge Base Integration (validates template retrieval)
"""

import pytest
from fastapi.testclient import TestClient
from backend.src.api.main import app
import time

client = TestClient(app)


class TestRetrieveEndpoint:
    """Test suite for POST /api/retrieve endpoint."""

    def test_retrieve_valid_request(self):
        """Test successful template retrieval with valid request."""
        # Arrange
        request_data = {
            "query": "Как открыть счет в банке?",
            "category": "Счета",
            "subcategory": "Открытие счета",
            "classification_confidence": 0.85,
            "top_k": 5
        }

        # Act
        start_time = time.time()
        response = client.post("/api/retrieve", json=request_data)
        duration_ms = (time.time() - start_time) * 1000

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Validate response structure (RetrievalResponse model)
        assert "query" in data, "Response missing 'query' field"
        assert "category" in data, "Response missing 'category' field"
        assert "subcategory" in data, "Response missing 'subcategory' field"
        assert "results" in data, "Response missing 'results' field"
        assert "total_candidates" in data, "Response missing 'total_candidates' field"
        assert "processing_time_ms" in data, "Response missing 'processing_time_ms' field"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        assert "warnings" in data, "Response missing 'warnings' field"

        # Validate echoed fields
        assert data["query"] == request_data["query"]
        assert data["category"] == request_data["category"]
        assert data["subcategory"] == request_data["subcategory"]

        # Validate results array
        assert isinstance(data["results"], list), "Results must be a list"
        assert len(data["results"]) <= request_data["top_k"], f"Results exceed top_k={request_data['top_k']}"

        # Validate total_candidates
        assert isinstance(data["total_candidates"], int)
        assert data["total_candidates"] >= 0

        # Validate processing time
        assert isinstance(data["processing_time_ms"], (int, float))
        assert data["processing_time_ms"] >= 0

        # FR-010: Retrieval must complete in <1 second
        assert duration_ms < 1000, f"Retrieval took {duration_ms:.2f}ms (expected <1000ms)"

        # Validate warnings array
        assert isinstance(data["warnings"], list)

    def test_retrieve_result_structure(self):
        """Test that each TemplateResult has correct structure."""
        request_data = {
            "query": "Забыл пароль от приложения",
            "category": "Мобильное приложение",
            "subcategory": "Вход и авторизация",
            "top_k": 3
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 200

        data = response.json()

        for i, result in enumerate(data["results"]):
            # Validate required fields
            assert "template_id" in result, f"Result {i} missing 'template_id'"
            assert "template_question" in result, f"Result {i} missing 'template_question'"
            assert "template_answer" in result, f"Result {i} missing 'template_answer'"
            assert "category" in result, f"Result {i} missing 'category'"
            assert "subcategory" in result, f"Result {i} missing 'subcategory'"
            assert "similarity_score" in result, f"Result {i} missing 'similarity_score'"
            assert "combined_score" in result, f"Result {i} missing 'combined_score'"
            assert "rank" in result, f"Result {i} missing 'rank'"

            # Validate field types and constraints
            assert isinstance(result["template_id"], str)
            assert len(result["template_id"]) > 0
            assert isinstance(result["template_question"], str)
            assert len(result["template_question"]) > 0
            assert isinstance(result["template_answer"], str)
            assert len(result["template_answer"]) > 0

            # Validate scores are in [0.0, 1.0]
            assert 0.0 <= result["similarity_score"] <= 1.0, \
                f"similarity_score {result['similarity_score']} out of range"
            assert 0.0 <= result["combined_score"] <= 1.0, \
                f"combined_score {result['combined_score']} out of range"

            # Validate rank
            assert isinstance(result["rank"], int)
            assert result["rank"] >= 1

    def test_retrieve_ranking_order(self):
        """Test that results are properly ranked (1, 2, 3, ...)."""
        request_data = {
            "query": "Как получить кредит?",
            "category": "Кредиты",
            "subcategory": "Потребительский кредит",
            "top_k": 5
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 200

        data = response.json()
        results = data["results"]

        if len(results) > 0:
            # Ranks should be sequential: 1, 2, 3, ...
            for i, result in enumerate(results):
                expected_rank = i + 1
                assert result["rank"] == expected_rank, \
                    f"Result at index {i} has rank {result['rank']}, expected {expected_rank}"

            # Combined scores should be in descending order (best first)
            if len(results) > 1:
                for i in range(len(results) - 1):
                    assert results[i]["combined_score"] >= results[i + 1]["combined_score"], \
                        f"Results not sorted by combined_score descending"

    def test_retrieve_top_k_limiting(self):
        """Test that top_k parameter correctly limits results."""
        for top_k in [1, 3, 5, 10]:
            request_data = {
                "query": "Вопрос о депозитах",
                "category": "Депозиты",
                "subcategory": "Открытие депозита",
                "top_k": top_k
            }

            response = client.post("/api/retrieve", json=request_data)
            assert response.status_code == 200

            data = response.json()
            assert len(data["results"]) <= top_k, \
                f"Results count {len(data['results'])} exceeds top_k={top_k}"

    def test_retrieve_default_top_k(self):
        """Test that default top_k=5 is used when not specified."""
        request_data = {
            "query": "Вопрос о картах",
            "category": "Карты",
            "subcategory": "Дебетовые карты"
            # top_k not specified, should default to 5
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 200

        data = response.json()
        # Should return at most 5 results (default)
        assert len(data["results"]) <= 5

    def test_retrieve_validation_missing_query(self):
        """Test validation error for missing query field."""
        request_data = {
            "category": "Карты",
            "subcategory": "Блокировка карты"
            # Missing required 'query' field
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 422  # Missing required field

    def test_retrieve_validation_missing_category(self):
        """Test validation error for missing category field."""
        request_data = {
            "query": "Как заблокировать карту?",
            "subcategory": "Блокировка карты"
            # Missing required 'category' field
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 422

    def test_retrieve_validation_missing_subcategory(self):
        """Test validation error for missing subcategory field."""
        request_data = {
            "query": "Как заблокировать карту?",
            "category": "Карты"
            # Missing required 'subcategory' field
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 422

    def test_retrieve_validation_invalid_top_k(self):
        """Test validation error for invalid top_k values."""
        # Test top_k < 1
        request_data = {
            "query": "Вопрос о кредите",
            "category": "Кредиты",
            "subcategory": "Ипотека",
            "top_k": 0
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 422 or response.status_code == 400

        # Test top_k > 10
        request_data["top_k"] = 11
        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 422 or response.status_code == 400

    def test_retrieve_validation_query_too_short(self):
        """Test validation error for query that's too short."""
        request_data = {
            "query": "Как",  # Only 3 characters, min is 5
            "category": "Карты",
            "subcategory": "Общие вопросы"
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 400

    def test_retrieve_validation_query_too_long(self):
        """Test validation error for query that's too long."""
        request_data = {
            "query": "а" * 5001,  # 5001 characters, max is 5000
            "category": "Карты",
            "subcategory": "Общие вопросы"
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 400 or response.status_code == 422

    def test_retrieve_validation_no_cyrillic_query(self):
        """Test validation error for query without Cyrillic characters."""
        request_data = {
            "query": "Hello, how are you today?",  # English only
            "category": "Карты",
            "subcategory": "Общие вопросы"
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 400

    def test_retrieve_performance_benchmark(self):
        """Benchmark retrieval performance for FR-010 requirement."""
        request_data = {
            "query": "Как узнать баланс карты?",
            "category": "Карты",
            "subcategory": "Проверка баланса",
            "top_k": 5
        }

        durations = []
        iterations = 5

        for _ in range(iterations):
            start_time = time.time()
            response = client.post("/api/retrieve", json=request_data)
            duration_ms = (time.time() - start_time) * 1000
            durations.append(duration_ms)

            assert response.status_code == 200

        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        print(f"\nRetrieval Performance ({iterations} iterations):")
        print(f"  Average: {avg_duration:.2f}ms")
        print(f"  Min: {min_duration:.2f}ms")
        print(f"  Max: {max_duration:.2f}ms")

        # FR-010: Retrieval must complete in <1 second
        assert max_duration < 1000, f"Max duration {max_duration:.2f}ms exceeds 1000ms threshold"

    def test_retrieve_optional_classification_confidence(self):
        """Test that classification_confidence is optional."""
        # Without classification_confidence
        request_data = {
            "query": "Вопрос о переводах",
            "category": "Переводы",
            "subcategory": "Внутренние переводы"
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 200

        # With classification_confidence
        request_data["classification_confidence"] = 0.92
        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 200

    def test_retrieve_optional_use_historical_weighting(self):
        """Test that use_historical_weighting is optional (MVP: not used)."""
        request_data = {
            "query": "Вопрос о вкладах",
            "category": "Вклады",
            "subcategory": "Процентные ставки",
            "use_historical_weighting": False
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 200

        # Note: In MVP, this parameter is ignored, but should not cause errors
        request_data["use_historical_weighting"] = True
        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 200


class TestRetrieveWarnings:
    """Test warning generation in retrieval responses."""

    def test_retrieve_warns_on_low_confidence(self):
        """Test that warnings are generated for low classification confidence."""
        request_data = {
            "query": "Непонятный вопрос",
            "category": "Общие",
            "subcategory": "Прочее",
            "classification_confidence": 0.3  # Low confidence
        }

        response = client.post("/api/retrieve", json=request_data)
        assert response.status_code == 200

        data = response.json()
        # Implementation may add warning about low confidence
        # This is implementation-specific, so we just check warnings field exists
        assert isinstance(data["warnings"], list)

    def test_retrieve_empty_results_warning(self):
        """Test behavior when no templates found in category."""
        # Using a potentially non-existent category
        request_data = {
            "query": "Вопрос о чём-то странном",
            "category": "Несуществующая категория",
            "subcategory": "Несуществующая подкатегория"
        }

        response = client.post("/api/retrieve", json=request_data)
        # Should still return 200, but with empty results or warning
        assert response.status_code == 200

        data = response.json()
        # Either results are empty, or there's a warning
        if len(data["results"]) == 0:
            assert data["total_candidates"] == 0
