"""
Unit tests for validator module.

Tests:
- Accuracy calculation formula (9/10 = 90%)
- Per-query result generation (is_top_1/top_3/top_5 flags)
- Processing time stats calculation (min/max/mean/p95)
- Edge cases (empty dataset, all correct, all incorrect)
- ValidationResult.passes_quality_gate property
- JSON serialization and deserialization
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

from src.retrieval.validator import (
    load_validation_dataset,
    run_validation,
    save_validation_results,
    format_validation_report
)
from src.retrieval.models import (
    ValidationRecord,
    ValidationResult,
    ValidationQueryResult,
    ProcessingTimeStats,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult
)
from src.retrieval.retriever import TemplateRetriever


class TestLoadValidationDataset:
    """Tests for load_validation_dataset function."""

    def test_load_dataset_success(self, tmp_path):
        """Test loading valid validation dataset."""
        # Arrange
        dataset = {
            "version": "1.0",
            "validation_queries": [
                {
                    "id": "test_001",
                    "query": "Test query",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": "tmpl_001"
                }
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f)

        # Act
        records = load_validation_dataset(str(dataset_path))

        # Assert
        assert len(records) == 1
        assert isinstance(records[0], ValidationRecord)
        assert records[0].id == "test_001"
        assert records[0].query == "Test query"
        assert records[0].correct_template_id == "tmpl_001"

    def test_load_dataset_file_not_found(self):
        """Test that nonexistent file raises FileNotFoundError."""
        # Act & Assert
        with pytest.raises(FileNotFoundError, match="not found"):
            load_validation_dataset("/nonexistent/path.json")

    def test_load_dataset_invalid_json(self, tmp_path):
        """Test that invalid JSON raises ValueError."""
        # Arrange
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{invalid json")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_validation_dataset(str(invalid_file))

    def test_load_dataset_missing_validation_queries_key(self, tmp_path):
        """Test that missing validation_queries key raises ValueError."""
        # Arrange
        dataset = {"wrong_key": []}
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        # Act & Assert
        with pytest.raises(ValueError, match="missing 'validation_queries'"):
            load_validation_dataset(str(dataset_path))

    def test_load_dataset_empty_validation_queries(self, tmp_path):
        """Test that empty validation_queries raises ValueError."""
        # Arrange
        dataset = {"validation_queries": []}
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        # Act & Assert
        with pytest.raises(ValueError, match="No valid validation records"):
            load_validation_dataset(str(dataset_path))

    def test_load_dataset_skips_invalid_records(self, tmp_path):
        """Test that invalid records are skipped with warning."""
        # Arrange
        dataset = {
            "validation_queries": [
                {
                    "id": "valid_001",
                    "query": "Valid query",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": "tmpl_001"
                },
                {
                    "id": "invalid_002"
                    # Missing required fields
                }
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f)

        # Act
        records = load_validation_dataset(str(dataset_path))

        # Assert - only valid record loaded
        assert len(records) == 1
        assert records[0].id == "valid_001"


class TestRunValidation:
    """Tests for run_validation function."""

    @pytest.fixture
    def sample_dataset(self, tmp_path):
        """Create sample validation dataset with 10 queries."""
        dataset = {
            "validation_queries": [
                {
                    "id": f"test_{i:03d}",
                    "query": f"Test query {i}",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": f"tmpl_{i:03d}"
                }
                for i in range(1, 11)
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False)
        return str(dataset_path)

    def test_accuracy_calculation_9_out_of_10(self, sample_dataset):
        """Test that 9 correct out of 10 = 90% accuracy."""
        # Arrange - mock retriever that returns correct template in top-3 for 9/10 queries
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True

        # Create mock responses
        def mock_retrieve(request):
            query_num = int(request.query.split()[-1])

            # First 9 queries: correct template at rank 2
            if query_num <= 9:
                results = [
                    RetrievalResult(
                        template_id=f"tmpl_wrong_{query_num}",
                        template_question="Wrong question",
                        template_answer="Wrong answer",
                        similarity_score=0.85,
                        historical_score=0.5,
                        combined_score=0.85,
                        confidence_level="high",
                        rank=1
                    ),
                    RetrievalResult(
                        template_id=f"tmpl_{query_num:03d}",  # CORRECT
                        template_question="Correct question",
                        template_answer="Correct answer",
                        similarity_score=0.80,
                        historical_score=0.5,
                        combined_score=0.80,
                        confidence_level="high",
                        rank=2
                    )
                ]
            else:
                # Query 10: correct template NOT in results
                results = [
                    RetrievalResult(
                        template_id=f"tmpl_wrong_{query_num}",
                        template_question="Wrong question",
                        template_answer="Wrong answer",
                        similarity_score=0.85,
                        historical_score=0.5,
                        combined_score=0.85,
                        confidence_level="high",
                        rank=1
                    )
                ]

            return RetrievalResponse(
                query=request.query,
                category=request.category,
                subcategory=request.subcategory,
                results=results,
                total_candidates=50,
                processing_time_ms=100.0,
                warnings=[]
            )

        mock_retriever.retrieve.side_effect = mock_retrieve

        # Act
        result = run_validation(sample_dataset, mock_retriever, top_k=5)

        # Assert
        assert result.total_queries == 10
        assert result.top_3_correct == 9
        assert result.top_3_accuracy == pytest.approx(90.0)

    def test_accuracy_calculation_all_correct(self, sample_dataset):
        """Test that 10 correct out of 10 = 100% accuracy."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True

        def mock_retrieve(request):
            query_num = int(request.query.split()[-1])
            results = [
                RetrievalResult(
                    template_id=f"tmpl_{query_num:03d}",  # CORRECT at rank 1
                    template_question="Correct question",
                    template_answer="Correct answer",
                    similarity_score=0.95,
                    historical_score=0.5,
                    combined_score=0.95,
                    confidence_level="high",
                    rank=1
                )
            ]
            return RetrievalResponse(
                query=request.query,
                category=request.category,
                subcategory=request.subcategory,
                results=results,
                total_candidates=50,
                processing_time_ms=100.0,
                warnings=[]
            )

        mock_retriever.retrieve.side_effect = mock_retrieve

        # Act
        result = run_validation(sample_dataset, mock_retriever, top_k=5)

        # Assert
        assert result.total_queries == 10
        assert result.top_1_correct == 10
        assert result.top_3_correct == 10
        assert result.top_5_correct == 10
        assert result.top_3_accuracy == pytest.approx(100.0)

    def test_accuracy_calculation_all_incorrect(self, sample_dataset):
        """Test that 0 correct out of 10 = 0% accuracy."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True

        def mock_retrieve(request):
            # Return only incorrect templates
            results = [
                RetrievalResult(
                    template_id="tmpl_wrong",
                    template_question="Wrong question",
                    template_answer="Wrong answer",
                    similarity_score=0.75,
                    historical_score=0.5,
                    combined_score=0.75,
                    confidence_level="medium",
                    rank=1
                )
            ]
            return RetrievalResponse(
                query=request.query,
                category=request.category,
                subcategory=request.subcategory,
                results=results,
                total_candidates=50,
                processing_time_ms=100.0,
                warnings=[]
            )

        mock_retriever.retrieve.side_effect = mock_retrieve

        # Act
        result = run_validation(sample_dataset, mock_retriever, top_k=5)

        # Assert
        assert result.total_queries == 10
        assert result.top_1_correct == 0
        assert result.top_3_correct == 0
        assert result.top_5_correct == 0
        assert result.top_3_accuracy == pytest.approx(0.0)

    def test_per_query_result_flags_top_1(self, tmp_path):
        """Test that is_top_1/top_3/top_5 flags are correct for rank 1."""
        # Arrange
        dataset = {
            "validation_queries": [
                {
                    "id": "test_001",
                    "query": "Test query",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": "tmpl_correct"
                }
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.retrieve.return_value = RetrievalResponse(
            query="Test query",
            category="Test",
            subcategory="Test Sub",
            results=[
                RetrievalResult(
                    template_id="tmpl_correct",  # CORRECT at rank 1
                    template_question="Q",
                    template_answer="A",
                    similarity_score=0.95,
                    historical_score=0.5,
                    combined_score=0.95,
                    confidence_level="high",
                    rank=1
                )
            ],
            total_candidates=50,
            processing_time_ms=100.0,
            warnings=[]
        )

        # Act
        result = run_validation(str(dataset_path), mock_retriever, top_k=5)

        # Assert
        query_result = result.per_query_results[0]
        assert query_result.correct_template_rank == 1
        assert query_result.is_top_1 is True
        assert query_result.is_top_3 is True
        assert query_result.is_top_5 is True

    def test_per_query_result_flags_top_3(self, tmp_path):
        """Test that is_top_1/top_3/top_5 flags are correct for rank 3."""
        # Arrange
        dataset = {
            "validation_queries": [
                {
                    "id": "test_001",
                    "query": "Test query",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": "tmpl_correct"
                }
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.retrieve.return_value = RetrievalResponse(
            query="Test query",
            category="Test",
            subcategory="Test Sub",
            results=[
                RetrievalResult(template_id="tmpl_001", template_question="Q1", template_answer="A1",
                              similarity_score=0.95, historical_score=0.5, combined_score=0.95,
                              confidence_level="high", rank=1),
                RetrievalResult(template_id="tmpl_002", template_question="Q2", template_answer="A2",
                              similarity_score=0.90, historical_score=0.5, combined_score=0.90,
                              confidence_level="high", rank=2),
                RetrievalResult(template_id="tmpl_correct", template_question="Q", template_answer="A",
                              similarity_score=0.85, historical_score=0.5, combined_score=0.85,
                              confidence_level="high", rank=3),  # CORRECT at rank 3
            ],
            total_candidates=50,
            processing_time_ms=100.0,
            warnings=[]
        )

        # Act
        result = run_validation(str(dataset_path), mock_retriever, top_k=5)

        # Assert
        query_result = result.per_query_results[0]
        assert query_result.correct_template_rank == 3
        assert query_result.is_top_1 is False
        assert query_result.is_top_3 is True
        assert query_result.is_top_5 is True

    def test_per_query_result_flags_top_5(self, tmp_path):
        """Test that is_top_1/top_3/top_5 flags are correct for rank 5."""
        # Arrange
        dataset = {
            "validation_queries": [
                {
                    "id": "test_001",
                    "query": "Test query",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": "tmpl_correct"
                }
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.retrieve.return_value = RetrievalResponse(
            query="Test query",
            category="Test",
            subcategory="Test Sub",
            results=[
                RetrievalResult(template_id=f"tmpl_{i:03d}", template_question=f"Q{i}",
                              template_answer=f"A{i}", similarity_score=0.95 - i*0.02,
                              historical_score=0.5, combined_score=0.95 - i*0.02,
                              confidence_level="high", rank=i)
                for i in range(1, 5)
            ] + [
                RetrievalResult(template_id="tmpl_correct", template_question="Q", template_answer="A",
                              similarity_score=0.80, historical_score=0.5, combined_score=0.80,
                              confidence_level="high", rank=5)  # CORRECT at rank 5
            ],
            total_candidates=50,
            processing_time_ms=100.0,
            warnings=[]
        )

        # Act
        result = run_validation(str(dataset_path), mock_retriever, top_k=5)

        # Assert
        query_result = result.per_query_results[0]
        assert query_result.correct_template_rank == 5
        assert query_result.is_top_1 is False
        assert query_result.is_top_3 is False
        assert query_result.is_top_5 is True

    def test_per_query_result_flags_not_found(self, tmp_path):
        """Test that is_top_1/top_3/top_5 flags are False when not found."""
        # Arrange
        dataset = {
            "validation_queries": [
                {
                    "id": "test_001",
                    "query": "Test query",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": "tmpl_correct"
                }
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.retrieve.return_value = RetrievalResponse(
            query="Test query",
            category="Test",
            subcategory="Test Sub",
            results=[
                RetrievalResult(template_id="tmpl_wrong", template_question="Q", template_answer="A",
                              similarity_score=0.75, historical_score=0.5, combined_score=0.75,
                              confidence_level="medium", rank=1)
            ],
            total_candidates=50,
            processing_time_ms=100.0,
            warnings=[]
        )

        # Act
        result = run_validation(str(dataset_path), mock_retriever, top_k=5)

        # Assert
        query_result = result.per_query_results[0]
        assert query_result.correct_template_rank is None
        assert query_result.is_top_1 is False
        assert query_result.is_top_3 is False
        assert query_result.is_top_5 is False

    def test_processing_time_stats_calculation(self, sample_dataset):
        """Test that processing time stats are calculated correctly."""
        # Arrange - return known processing times
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True

        # Known processing times: 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000 ms
        processing_times = [100.0 * (i + 1) for i in range(10)]

        def mock_retrieve(request):
            query_num = int(request.query.split()[-1])
            return RetrievalResponse(
                query=request.query,
                category=request.category,
                subcategory=request.subcategory,
                results=[
                    RetrievalResult(
                        template_id=f"tmpl_{query_num:03d}",
                        template_question="Q",
                        template_answer="A",
                        similarity_score=0.85,
                        historical_score=0.5,
                        combined_score=0.85,
                        confidence_level="high",
                        rank=1
                    )
                ],
                total_candidates=50,
                processing_time_ms=processing_times[query_num - 1],
                warnings=[]
            )

        mock_retriever.retrieve.side_effect = mock_retrieve

        # Act
        result = run_validation(sample_dataset, mock_retriever, top_k=5)

        # Assert
        stats = result.processing_time_stats
        assert stats.min_ms == pytest.approx(100.0)
        assert stats.max_ms == pytest.approx(1000.0)
        assert stats.mean_ms == pytest.approx(550.0)  # (100+200+...+1000) / 10
        assert stats.p95_ms == pytest.approx(950.0)  # 95th percentile
        assert stats.sample_count == 10

    def test_quality_gate_pass_80_percent(self, tmp_path):
        """Test that quality gate passes with ≥80% accuracy."""
        # Arrange - 8 out of 10 correct (80%)
        dataset = {
            "validation_queries": [
                {
                    "id": f"test_{i:03d}",
                    "query": f"Test query {i}",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": f"tmpl_{i:03d}"
                }
                for i in range(1, 11)
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True

        def mock_retrieve(request):
            query_num = int(request.query.split()[-1])
            # First 8 correct, last 2 incorrect
            if query_num <= 8:
                template_id = f"tmpl_{query_num:03d}"  # CORRECT
            else:
                template_id = "tmpl_wrong"  # INCORRECT

            return RetrievalResponse(
                query=request.query,
                category=request.category,
                subcategory=request.subcategory,
                results=[
                    RetrievalResult(
                        template_id=template_id,
                        template_question="Q",
                        template_answer="A",
                        similarity_score=0.85,
                        historical_score=0.5,
                        combined_score=0.85,
                        confidence_level="high",
                        rank=1
                    )
                ],
                total_candidates=50,
                processing_time_ms=100.0,
                warnings=[]
            )

        mock_retriever.retrieve.side_effect = mock_retrieve

        # Act
        result = run_validation(str(dataset_path), mock_retriever, top_k=5)

        # Assert
        assert result.top_3_accuracy == pytest.approx(80.0)
        assert result.passes_quality_gate is True

    def test_quality_gate_fail_below_80_percent(self, tmp_path):
        """Test that quality gate fails with <80% accuracy."""
        # Arrange - 7 out of 10 correct (70%)
        dataset = {
            "validation_queries": [
                {
                    "id": f"test_{i:03d}",
                    "query": f"Test query {i}",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": f"tmpl_{i:03d}"
                }
                for i in range(1, 11)
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True

        def mock_retrieve(request):
            query_num = int(request.query.split()[-1])
            # First 7 correct, last 3 incorrect
            if query_num <= 7:
                template_id = f"tmpl_{query_num:03d}"  # CORRECT
            else:
                template_id = "tmpl_wrong"  # INCORRECT

            return RetrievalResponse(
                query=request.query,
                category=request.category,
                subcategory=request.subcategory,
                results=[
                    RetrievalResult(
                        template_id=template_id,
                        template_question="Q",
                        template_answer="A",
                        similarity_score=0.85,
                        historical_score=0.5,
                        combined_score=0.85,
                        confidence_level="high",
                        rank=1
                    )
                ],
                total_candidates=50,
                processing_time_ms=100.0,
                warnings=[]
            )

        mock_retriever.retrieve.side_effect = mock_retrieve

        # Act
        result = run_validation(str(dataset_path), mock_retriever, top_k=5)

        # Assert
        assert result.top_3_accuracy == pytest.approx(70.0)
        assert result.passes_quality_gate is False

    def test_retriever_not_ready_raises_error(self, sample_dataset):
        """Test that validation raises error if retriever not ready."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = False

        # Act & Assert
        with pytest.raises(ValueError, match="Retriever not ready"):
            run_validation(sample_dataset, mock_retriever, top_k=5)

    def test_similarity_scores_tracking(self, tmp_path):
        """Test that similarity scores are tracked correctly."""
        # Arrange
        dataset = {
            "validation_queries": [
                {
                    "id": f"test_{i:03d}",
                    "query": f"Test query {i}",
                    "category": "Test",
                    "subcategory": "Test Sub",
                    "correct_template_id": f"tmpl_{i:03d}"
                }
                for i in range(1, 6)
            ]
        }
        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f)

        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True

        def mock_retrieve(request):
            query_num = int(request.query.split()[-1])
            # First 3 correct (similarity 0.9), last 2 incorrect (top score 0.6)
            if query_num <= 3:
                return RetrievalResponse(
                    query=request.query,
                    category=request.category,
                    subcategory=request.subcategory,
                    results=[
                        RetrievalResult(
                            template_id=f"tmpl_{query_num:03d}",  # CORRECT
                            template_question="Q",
                            template_answer="A",
                            similarity_score=0.9,
                            historical_score=0.5,
                            combined_score=0.9,
                            confidence_level="high",
                            rank=1
                        )
                    ],
                    total_candidates=50,
                    processing_time_ms=100.0,
                    warnings=[]
                )
            else:
                return RetrievalResponse(
                    query=request.query,
                    category=request.category,
                    subcategory=request.subcategory,
                    results=[
                        RetrievalResult(
                            template_id="tmpl_wrong",  # INCORRECT
                            template_question="Q",
                            template_answer="A",
                            similarity_score=0.6,
                            historical_score=0.5,
                            combined_score=0.6,
                            confidence_level="medium",
                            rank=1
                        )
                    ],
                    total_candidates=50,
                    processing_time_ms=100.0,
                    warnings=[]
                )

        mock_retriever.retrieve.side_effect = mock_retrieve

        # Act
        result = run_validation(str(dataset_path), mock_retriever, top_k=5)

        # Assert
        # Avg similarity for correct: (0.9 + 0.9 + 0.9) / 3 = 0.9
        # Avg similarity for incorrect: (0.6 + 0.6) / 2 = 0.6
        assert result.avg_similarity_correct == pytest.approx(0.9)
        assert result.avg_similarity_incorrect == pytest.approx(0.6)


class TestSaveValidationResults:
    """Tests for save_validation_results function."""

    def test_save_results_creates_file(self, tmp_path):
        """Test that save_validation_results creates JSON file."""
        # Arrange
        validation_result = ValidationResult(
            total_queries=10,
            top_1_correct=8,
            top_3_correct=9,
            top_5_correct=10,
            per_query_results=[],
            avg_similarity_correct=0.85,
            avg_similarity_incorrect=0.60,
            processing_time_stats=ProcessingTimeStats(
                min_ms=50.0,
                max_ms=150.0,
                mean_ms=100.0,
                p95_ms=145.0,
                sample_count=10
            )
        )
        output_path = tmp_path / "results.json"

        # Act
        save_validation_results(validation_result, str(output_path))

        # Assert
        assert output_path.exists()

        # Verify JSON is valid
        with open(output_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)

        assert saved_data["total_queries"] == 10
        assert saved_data["top_3_correct"] == 9
        assert saved_data["top_3_accuracy"] == 90.0

    def test_save_results_creates_parent_directories(self, tmp_path):
        """Test that save_validation_results creates parent directories."""
        # Arrange
        validation_result = ValidationResult(
            total_queries=5,
            top_1_correct=5,
            top_3_correct=5,
            top_5_correct=5,
            per_query_results=[],
            avg_similarity_correct=0.95,
            avg_similarity_incorrect=0.0,
            processing_time_stats=ProcessingTimeStats(
                min_ms=50.0, max_ms=150.0, mean_ms=100.0, p95_ms=145.0, sample_count=5
            )
        )
        output_path = tmp_path / "nested" / "dir" / "results.json"

        # Act
        save_validation_results(validation_result, str(output_path))

        # Assert
        assert output_path.exists()
        assert output_path.parent.exists()


class TestFormatValidationReport:
    """Tests for format_validation_report function."""

    def test_format_report_includes_statistics(self):
        """Test that formatted report includes all key statistics."""
        # Arrange
        validation_result = ValidationResult(
            total_queries=10,
            top_1_correct=8,
            top_3_correct=9,
            top_5_correct=10,
            per_query_results=[
                ValidationQueryResult(
                    query_id="test_001",
                    query_text="Test query",
                    correct_template_id="tmpl_001",
                    retrieved_templates=["tmpl_001"],
                    correct_template_rank=1,
                    similarity_scores={"tmpl_001": 0.95}
                )
            ],
            avg_similarity_correct=0.85,
            avg_similarity_incorrect=0.60,
            processing_time_stats=ProcessingTimeStats(
                min_ms=50.0,
                max_ms=150.0,
                mean_ms=100.0,
                p95_ms=145.0,
                sample_count=10
            )
        )

        # Act
        report = format_validation_report(validation_result)

        # Assert
        assert "RETRIEVAL VALIDATION REPORT" in report
        assert "Total queries: 10" in report
        assert "Top-1 correct: 8" in report
        assert "Top-3 correct: 9" in report
        assert "90.0%" in report  # Top-3 accuracy
        assert "Mean: 100.0ms" in report
        assert "P95: 145.0ms" in report

    def test_format_report_shows_quality_gate_pass(self):
        """Test that report shows quality gate pass for ≥80% accuracy."""
        # Arrange
        validation_result = ValidationResult(
            total_queries=10,
            top_1_correct=8,
            top_3_correct=9,
            top_5_correct=10,
            per_query_results=[],
            avg_similarity_correct=0.85,
            avg_similarity_incorrect=0.60,
            processing_time_stats=ProcessingTimeStats(
                min_ms=50.0, max_ms=150.0, mean_ms=100.0, p95_ms=145.0, sample_count=10
            )
        )

        # Act
        report = format_validation_report(validation_result)

        # Assert
        assert "✅ PASS" in report or "PASS" in report
        assert "quality gate" in report.lower()

    def test_format_report_shows_quality_gate_fail(self):
        """Test that report shows quality gate fail for <80% accuracy."""
        # Arrange
        validation_result = ValidationResult(
            total_queries=10,
            top_1_correct=5,
            top_3_correct=7,
            top_5_correct=8,
            per_query_results=[],
            avg_similarity_correct=0.75,
            avg_similarity_incorrect=0.65,
            processing_time_stats=ProcessingTimeStats(
                min_ms=50.0, max_ms=150.0, mean_ms=100.0, p95_ms=145.0, sample_count=10
            )
        )

        # Act
        report = format_validation_report(validation_result)

        # Assert
        assert "❌ FAIL" in report or "FAIL" in report
        assert "quality gate" in report.lower()

    def test_format_report_is_multiline(self):
        """Test that report is formatted with multiple lines."""
        # Arrange
        validation_result = ValidationResult(
            total_queries=5,
            top_1_correct=5,
            top_3_correct=5,
            top_5_correct=5,
            per_query_results=[],
            avg_similarity_correct=0.95,
            avg_similarity_incorrect=0.0,
            processing_time_stats=ProcessingTimeStats(
                min_ms=50.0, max_ms=150.0, mean_ms=100.0, p95_ms=145.0, sample_count=5
            )
        )

        # Act
        report = format_validation_report(validation_result)

        # Assert
        lines = report.split("\n")
        assert len(lines) > 10, "Report should have multiple lines"
        assert any("=" in line for line in lines), "Report should have separator lines"
