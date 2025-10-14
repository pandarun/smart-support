"""
Integration test for validation workflow.

Tests:
- Full validation run against sample dataset
- Verifies accuracy calculation formula (correct / total * 100)
- Checks per-query results format
- Validates processing time stats calculation (min/max/mean/p95)
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock
import numpy as np

from src.retrieval.validator import run_validation, load_validation_dataset, save_validation_results
from src.retrieval.models import ValidationResult


class TestValidationIntegration:
    """Integration tests for validation workflow."""

    @pytest.fixture
    def sample_validation_dataset(self, tmp_path):
        """Create sample validation dataset file."""
        dataset = {
            "version": "1.0",
            "description": "Test dataset",
            "validation_queries": [
                {
                    "id": "val_test_001",
                    "query": "Как открыть счет?",
                    "category": "Счета и вклады",
                    "subcategory": "Открытие счета",
                    "correct_template_id": "tmpl_001",
                    "notes": "Test case 1"
                },
                {
                    "id": "val_test_002",
                    "query": "Какой процент?",
                    "category": "Счета и вклады",
                    "subcategory": "Процентные ставки",
                    "correct_template_id": "tmpl_003",
                    "notes": "Test case 2"
                },
                {
                    "id": "val_test_003",
                    "query": "Как получить кредит?",
                    "category": "Кредиты",
                    "subcategory": "Потребительский кредит",
                    "correct_template_id": "tmpl_004",
                    "notes": "Test case 3"
                },
                {
                    "id": "val_test_004",
                    "query": "Как заказать карту?",
                    "category": "Карты",
                    "subcategory": "Дебетовые карты",
                    "correct_template_id": "tmpl_007",
                    "notes": "Test case 4"
                },
                {
                    "id": "val_test_005",
                    "query": "Как заблокировать карту?",
                    "category": "Карты",
                    "subcategory": "Блокировка карты",
                    "correct_template_id": "tmpl_010",
                    "notes": "Test case 5"
                },
            ]
        }

        dataset_path = tmp_path / "test_validation.json"
        with open(dataset_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        return str(dataset_path)

    def test_load_validation_dataset_success(self, sample_validation_dataset):
        """Test loading validation dataset from JSON file."""
        # Act
        records = load_validation_dataset(sample_validation_dataset)

        # Assert
        assert len(records) == 5
        assert all(hasattr(r, 'query') for r in records)
        assert all(hasattr(r, 'correct_template_id') for r in records)

    def test_load_validation_dataset_nonexistent_file(self):
        """Test that nonexistent file raises FileNotFoundError."""
        # Act & Assert
        with pytest.raises(FileNotFoundError, match="not found"):
            load_validation_dataset("/nonexistent/path.json")

    def test_load_validation_dataset_invalid_json(self, tmp_path):
        """Test that invalid JSON raises ValueError."""
        # Arrange
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{invalid json")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_validation_dataset(str(invalid_file))

    def test_load_validation_dataset_missing_key(self, tmp_path):
        """Test that missing validation_queries key raises ValueError."""
        # Arrange
        dataset_file = tmp_path / "missing_key.json"
        with open(dataset_file, 'w') as f:
            json.dump({"wrong_key": []}, f)

        # Act & Assert
        with pytest.raises(ValueError, match="missing 'validation_queries'"):
            load_validation_dataset(str(dataset_file))

    def test_run_validation_with_mock_retriever(
        self,
        sample_validation_dataset,
        retriever_with_mock_client
    ):
        """Test full validation run with mocked retriever."""
        # Arrange
        retriever = retriever_with_mock_client

        # Act
        result = run_validation(
            dataset_path=sample_validation_dataset,
            retriever=retriever,
            top_k=5
        )

        # Assert
        assert isinstance(result, ValidationResult)
        assert result.total_queries == 5
        assert 0 <= result.top_1_correct <= 5
        assert 0 <= result.top_3_correct <= 5
        assert 0 <= result.top_5_correct <= 5
        assert len(result.per_query_results) == 5

        # Check accuracy calculation
        expected_accuracy = (result.top_3_correct / result.total_queries) * 100
        assert result.top_3_accuracy == pytest.approx(expected_accuracy)

    def test_run_validation_accuracy_calculation(
        self,
        sample_validation_dataset,
        populated_cache,
        embeddings_client_mock
    ):
        """Test that accuracy is calculated correctly."""
        # Arrange
        from src.retrieval.retriever import TemplateRetriever

        # Modify cache to have predictable template IDs matching dataset
        # (In real test, would use actual templates)
        retriever = TemplateRetriever(embeddings_client_mock, populated_cache)

        # Act
        result = run_validation(
            dataset_path=sample_validation_dataset,
            retriever=retriever,
            top_k=5
        )

        # Assert - verify accuracy formula
        assert result.top_3_accuracy == (result.top_3_correct / result.total_queries) * 100

        # Verify counts are logical
        assert result.top_1_correct <= result.top_3_correct <= result.top_5_correct
        assert result.top_5_correct <= result.total_queries

    def test_run_validation_per_query_results_format(
        self,
        sample_validation_dataset,
        retriever_with_mock_client
    ):
        """Test that per-query results have correct format."""
        # Arrange
        retriever = retriever_with_mock_client

        # Act
        result = run_validation(
            dataset_path=sample_validation_dataset,
            retriever=retriever,
            top_k=5
        )

        # Assert
        for query_result in result.per_query_results:
            # Check required fields
            assert hasattr(query_result, 'query_id')
            assert hasattr(query_result, 'query_text')
            assert hasattr(query_result, 'correct_template_id')
            assert hasattr(query_result, 'retrieved_templates')
            assert hasattr(query_result, 'correct_template_rank')
            assert hasattr(query_result, 'similarity_scores')

            # Check computed properties
            assert hasattr(query_result, 'is_top_1')
            assert hasattr(query_result, 'is_top_3')
            assert hasattr(query_result, 'is_top_5')

            # Verify logical consistency
            if query_result.is_top_1:
                assert query_result.correct_template_rank == 1
                assert query_result.is_top_3
                assert query_result.is_top_5

            if query_result.is_top_3:
                assert query_result.correct_template_rank is not None
                assert query_result.correct_template_rank <= 3
                assert query_result.is_top_5

    def test_run_validation_processing_time_stats(
        self,
        sample_validation_dataset,
        retriever_with_mock_client
    ):
        """Test that processing time stats are calculated correctly."""
        # Arrange
        retriever = retriever_with_mock_client

        # Act
        result = run_validation(
            dataset_path=sample_validation_dataset,
            retriever=retriever,
            top_k=5
        )

        # Assert
        stats = result.processing_time_stats

        assert stats.min_ms >= 0
        assert stats.max_ms >= stats.min_ms
        assert stats.mean_ms >= stats.min_ms
        assert stats.mean_ms <= stats.max_ms
        assert stats.p95_ms >= stats.mean_ms
        assert stats.sample_count == result.total_queries

    def test_run_validation_quality_gate_check(
        self,
        sample_validation_dataset,
        retriever_with_mock_client
    ):
        """Test that quality gate check works correctly."""
        # Arrange
        retriever = retriever_with_mock_client

        # Act
        result = run_validation(
            dataset_path=sample_validation_dataset,
            retriever=retriever,
            top_k=5
        )

        # Assert
        if result.top_3_accuracy >= 80.0:
            assert result.passes_quality_gate is True
        else:
            assert result.passes_quality_gate is False

    def test_run_validation_similarity_scores_tracking(
        self,
        sample_validation_dataset,
        retriever_with_mock_client
    ):
        """Test that similarity scores are tracked for analysis."""
        # Arrange
        retriever = retriever_with_mock_client

        # Act
        result = run_validation(
            dataset_path=sample_validation_dataset,
            retriever=retriever,
            top_k=5
        )

        # Assert
        assert isinstance(result.avg_similarity_correct, float)
        assert isinstance(result.avg_similarity_incorrect, float)
        assert 0.0 <= result.avg_similarity_correct <= 1.0
        assert 0.0 <= result.avg_similarity_incorrect <= 1.0

    def test_run_validation_retriever_not_ready_raises_error(
        self,
        sample_validation_dataset
    ):
        """Test that validation raises error if retriever not ready."""
        # Arrange
        from src.retrieval.retriever import TemplateRetriever

        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = False

        # Act & Assert
        with pytest.raises(ValueError, match="Retriever not ready"):
            run_validation(
                dataset_path=sample_validation_dataset,
                retriever=mock_retriever,
                top_k=5
            )

    def test_save_validation_results(self, tmp_path, retriever_with_mock_client, sample_validation_dataset):
        """Test saving validation results to JSON file."""
        # Arrange
        retriever = retriever_with_mock_client
        result = run_validation(
            dataset_path=sample_validation_dataset,
            retriever=retriever,
            top_k=5
        )

        output_path = tmp_path / "results.json"

        # Act
        save_validation_results(result, str(output_path))

        # Assert
        assert output_path.exists()

        # Verify JSON is valid
        with open(output_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)

        assert "total_queries" in saved_data
        assert "top_3_accuracy" in saved_data
        assert "per_query_results" in saved_data

    def test_validation_empty_dataset_raises_error(self, tmp_path, retriever_with_mock_client):
        """Test that empty dataset raises error."""
        # Arrange
        dataset = {"validation_queries": []}
        dataset_path = tmp_path / "empty.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        # Act & Assert
        with pytest.raises(ValueError, match="No valid validation records"):
            load_validation_dataset(str(dataset_path))
