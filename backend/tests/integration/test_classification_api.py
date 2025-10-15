"""
Integration Tests for POST /api/classify Endpoint

Tests the classification API endpoint with various inputs and validates:
- Request/response model validation
- Performance requirements (FR-005: <2s response time)
- Error handling for invalid inputs
- Cyrillic text validation

Constitution Compliance:
- Principle III: Data-Driven Validation (tests against real classification requirements)
- Principle II: User-Centric Design (validates user-friendly error messages)
"""

import pytest
from fastapi.testclient import TestClient
from backend.src.api.main import app
import time

client = TestClient(app)


class TestClassifyEndpoint:
    """Test suite for POST /api/classify endpoint."""

    def test_classify_valid_russian_inquiry(self):
        """Test successful classification of valid Russian inquiry."""
        # Arrange
        request_data = {
            "inquiry": "Как открыть счет в банке?"  # "How to open a bank account?"
        }

        # Act
        start_time = time.time()
        response = client.post("/api/classify", json=request_data)
        duration_ms = (time.time() - start_time) * 1000

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Validate response structure (ClassificationResult model)
        assert "inquiry" in data, "Response missing 'inquiry' field"
        assert "category" in data, "Response missing 'category' field"
        assert "subcategory" in data, "Response missing 'subcategory' field"
        assert "confidence" in data, "Response missing 'confidence' field"
        assert "processing_time_ms" in data, "Response missing 'processing_time_ms' field"
        assert "timestamp" in data, "Response missing 'timestamp' field"

        # Validate field types and constraints
        assert data["inquiry"] == request_data["inquiry"], "Inquiry not echoed back correctly"
        assert isinstance(data["category"], str), "Category must be string"
        assert len(data["category"]) > 0, "Category must not be empty"
        assert isinstance(data["subcategory"], str), "Subcategory must be string"
        assert len(data["subcategory"]) > 0, "Subcategory must not be empty"
        assert isinstance(data["confidence"], (int, float)), "Confidence must be numeric"
        assert 0.0 <= data["confidence"] <= 1.0, "Confidence must be in range [0.0, 1.0]"
        assert isinstance(data["processing_time_ms"], int), "Processing time must be integer"
        assert data["processing_time_ms"] > 0, "Processing time must be positive"

        # Validate performance (FR-005: must respond in <2s)
        assert duration_ms < 2000, f"Classification took {duration_ms:.2f}ms (expected <2000ms)"

        # Validate timestamp format (ISO 8601 UTC)
        assert data["timestamp"].endswith("Z"), "Timestamp must be in UTC (end with Z)"

    def test_classify_multiple_valid_inquiries(self):
        """Test classification with various valid Russian inquiries."""
        test_cases = [
            "Забыл пароль от мобильного приложения",  # Forgot mobile app password
            "Как получить кредит на покупку квартиры?",  # How to get mortgage credit?
            "Почему не работает интернет-банкинг?",  # Why isn't internet banking working?
            "Хочу открыть депозит",  # Want to open deposit
            "Где найти реквизиты моей карты?",  # Where to find my card details?
        ]

        for inquiry in test_cases:
            request_data = {"inquiry": inquiry}
            response = client.post("/api/classify", json=request_data)

            assert response.status_code == 200, f"Failed for inquiry: {inquiry}"
            data = response.json()
            assert data["inquiry"] == inquiry
            assert len(data["category"]) > 0
            assert len(data["subcategory"]) > 0
            assert 0.0 <= data["confidence"] <= 1.0

    def test_classify_validation_too_short(self):
        """Test validation error for inquiry that's too short."""
        request_data = {"inquiry": "Hi"}  # Only 2 characters, min is 5

        response = client.post("/api/classify", json=request_data)

        # Should return 400 Bad Request with ErrorResponse
        assert response.status_code == 400
        data = response.json()

        assert "error" in data, "Error response missing 'error' field"
        assert "error_type" in data, "Error response missing 'error_type' field"
        assert data["error_type"] == "validation"

        # Error message should be user-friendly (no technical jargon)
        assert "5 characters" in data["error"] or "at least 5" in data["error"]

    def test_classify_validation_too_long(self):
        """Test validation error for inquiry that's too long."""
        request_data = {"inquiry": "а" * 5001}  # 5001 Cyrillic characters, max is 5000

        response = client.post("/api/classify", json=request_data)

        assert response.status_code == 400
        data = response.json()

        assert data["error_type"] == "validation"
        assert "5000" in data["error"] or "exceed" in data["error"].lower()

    def test_classify_validation_no_cyrillic(self):
        """Test validation error for inquiry without Cyrillic characters."""
        request_data = {"inquiry": "Hello, how are you today?"}  # English only

        response = client.post("/api/classify", json=request_data)

        assert response.status_code == 400
        data = response.json()

        assert data["error_type"] == "validation"
        # Error should mention Russian/Cyrillic requirement
        error_lower = data["error"].lower()
        assert "russian" in error_lower or "cyrillic" in error_lower

    def test_classify_validation_missing_inquiry(self):
        """Test validation error for missing inquiry field."""
        request_data = {}  # Missing required 'inquiry' field

        response = client.post("/api/classify", json=request_data)

        assert response.status_code == 422  # FastAPI returns 422 for missing required fields

    def test_classify_validation_whitespace_only(self):
        """Test validation error for whitespace-only inquiry."""
        request_data = {"inquiry": "     "}  # Only whitespace

        response = client.post("/api/classify", json=request_data)

        # After trimming, this is < 5 characters
        assert response.status_code == 400

    def test_classify_mixed_text_with_cyrillic(self):
        """Test that inquiry with mixed text but containing Cyrillic is accepted."""
        request_data = {
            "inquiry": "Вопрос about credit cards and loans"  # Mixed Russian + English
        }

        response = client.post("/api/classify", json=request_data)

        # Should succeed because it contains at least one Cyrillic character
        assert response.status_code == 200
        data = response.json()
        assert data["inquiry"] == request_data["inquiry"]

    def test_classify_performance_benchmark(self):
        """Benchmark classification performance for FR-005 requirement."""
        request_data = {
            "inquiry": "Как узнать баланс моей карты через мобильное приложение?"
        }

        durations = []
        iterations = 5

        for _ in range(iterations):
            start_time = time.time()
            response = client.post("/api/classify", json=request_data)
            duration_ms = (time.time() - start_time) * 1000
            durations.append(duration_ms)

            assert response.status_code == 200

        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        print(f"\nClassification Performance ({iterations} iterations):")
        print(f"  Average: {avg_duration:.2f}ms")
        print(f"  Min: {min_duration:.2f}ms")
        print(f"  Max: {max_duration:.2f}ms")

        # FR-005: Classification must complete in <2 seconds
        assert max_duration < 2000, f"Max duration {max_duration:.2f}ms exceeds 2000ms threshold"

    def test_classify_concurrent_requests(self):
        """Test that multiple concurrent requests are handled correctly."""
        import concurrent.futures

        inquiries = [
            "Как открыть счет?",
            "Забыл пароль",
            "Хочу взять кредит",
            "Проблемы с картой",
            "Где мои реквизиты?",
        ]

        def make_request(inquiry):
            response = client.post("/api/classify", json={"inquiry": inquiry})
            return response.status_code, response.json() if response.status_code == 200 else None

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, inq) for inq in inquiries]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        assert all(status == 200 for status, _ in results), "Some concurrent requests failed"
        assert all(data is not None for _, data in results), "Some responses missing data"


class TestClassifyEdgeCases:
    """Test edge cases and special characters."""

    def test_classify_special_characters(self):
        """Test inquiry with special characters."""
        request_data = {
            "inquiry": "Как открыть счёт? Нужна помощь!!!"  # Contains ё and punctuation
        }

        response = client.post("/api/classify", json=request_data)
        assert response.status_code == 200

    def test_classify_numbers_and_cyrillic(self):
        """Test inquiry with numbers and Cyrillic text."""
        request_data = {
            "inquiry": "Карта 5555-1234-5678-9012 заблокирована"  # Card number + Russian
        }

        response = client.post("/api/classify", json=request_data)
        assert response.status_code == 200

    def test_classify_newlines_and_tabs(self):
        """Test inquiry with newlines and tabs."""
        request_data = {
            "inquiry": "Вопрос:\n\nКак\tоткрыть\tсчет?\n"
        }

        response = client.post("/api/classify", json=request_data)
        assert response.status_code == 200
        # Inquiry should be preserved as-is
        assert response.json()["inquiry"] == request_data["inquiry"]
