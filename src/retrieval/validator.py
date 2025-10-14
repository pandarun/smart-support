"""
Validation module for Template Retrieval Module.

Validates retrieval quality against ground truth dataset:
- Loads validation queries with correct template IDs
- Runs retrieval for each query
- Calculates top-1, top-3, top-5 accuracy
- Generates detailed per-query results
- Computes processing time statistics
- Checks quality gate (≥80% top-3 accuracy)
"""

import json
import logging
from pathlib import Path
from typing import List
import numpy as np

from src.retrieval.retriever import TemplateRetriever
from src.retrieval.models import (
    RetrievalRequest,
    ValidationRecord,
    ValidationResult,
    ValidationQueryResult,
    ProcessingTimeStats
)
from src.utils.logging import log_retrieval_validation_started, log_retrieval_validation_completed

logger = logging.getLogger(__name__)


def load_validation_dataset(dataset_path: str) -> List[ValidationRecord]:
    """
    Load validation dataset from JSON file.

    Args:
        dataset_path: Path to validation dataset JSON

    Returns:
        List of ValidationRecord objects

    Raises:
        FileNotFoundError: If dataset file not found
        ValueError: If dataset format is invalid

    Example:
        >>> records = load_validation_dataset("data/validation/retrieval_validation_dataset.json")
        >>> len(records)
        15
    """
    dataset_file = Path(dataset_path)

    if not dataset_file.exists():
        raise FileNotFoundError(f"Validation dataset not found: {dataset_path}")

    try:
        with open(dataset_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in validation dataset: {e}")

    if "validation_queries" not in data:
        raise ValueError("Dataset missing 'validation_queries' key")

    # Parse validation records
    records = []
    for query_data in data["validation_queries"]:
        try:
            record = ValidationRecord(**query_data)
            records.append(record)
        except Exception as e:
            logger.warning(f"Skipping invalid validation record: {e}")
            continue

    if not records:
        raise ValueError("No valid validation records found in dataset")

    logger.info(f"Loaded {len(records)} validation queries from {dataset_path}")

    return records


def run_validation(
    dataset_path: str,
    retriever: TemplateRetriever,
    top_k: int = 5
) -> ValidationResult:
    """
    Run retrieval validation against test dataset.

    For each validation query:
    1. Call retriever.retrieve() with query and classification
    2. Check if correct_template_id appears in top-K results
    3. Record rank of correct template (or None if not found)
    4. Track similarity scores and processing times

    Quality gate: ≥80% top-3 accuracy (constitution requirement)

    Args:
        dataset_path: Path to validation dataset JSON
        retriever: TemplateRetriever instance (must be ready)
        top_k: Number of templates to retrieve per query (default: 5)

    Returns:
        ValidationResult with aggregate statistics and per-query results

    Raises:
        FileNotFoundError: If dataset not found
        ValueError: If retriever not ready

    Example:
        >>> result = run_validation("data/validation/retrieval_validation_dataset.json", retriever)
        >>> result.top_3_accuracy
        86.7
        >>> result.passes_quality_gate
        True
    """
    # Verify retriever is ready
    if not retriever.is_ready():
        raise ValueError("Retriever not ready - embeddings must be precomputed first")

    # Load validation dataset
    validation_records = load_validation_dataset(dataset_path)

    # Log validation start
    log_retrieval_validation_started(
        total_queries=len(validation_records),
        dataset_path=dataset_path
    )

    logger.info(f"Starting validation with {len(validation_records)} queries...")

    # Run retrieval for each query
    per_query_results = []
    processing_times = []

    for i, record in enumerate(validation_records, start=1):
        logger.debug(f"Validating query {i}/{len(validation_records)}: {record.id}")

        # Create retrieval request
        request = RetrievalRequest(
            query=record.query,
            category=record.category,
            subcategory=record.subcategory,
            top_k=top_k
        )

        # Retrieve templates
        try:
            response = retriever.retrieve(request)
            processing_times.append(response.processing_time_ms)
        except Exception as e:
            logger.error(f"Retrieval failed for query {record.id}: {e}")
            # Record as failure (correct template not found)
            per_query_results.append(ValidationQueryResult(
                query_id=record.id,
                query_text=record.query,
                correct_template_id=record.correct_template_id,
                retrieved_templates=[],
                correct_template_rank=None,
                similarity_scores={}
            ))
            continue

        # Extract retrieved template IDs
        retrieved_ids = [r.template_id for r in response.results]

        # Find rank of correct template (if present)
        correct_rank = None
        if record.correct_template_id in retrieved_ids:
            correct_rank = retrieved_ids.index(record.correct_template_id) + 1

        # Build similarity scores mapping
        similarity_scores = {r.template_id: r.similarity_score for r in response.results}

        # Create per-query result
        query_result = ValidationQueryResult(
            query_id=record.id,
            query_text=record.query,
            correct_template_id=record.correct_template_id,
            retrieved_templates=retrieved_ids,
            correct_template_rank=correct_rank,
            similarity_scores=similarity_scores
        )

        per_query_results.append(query_result)

        # Log progress
        status = "✓" if query_result.is_top_3 else "✗"
        logger.debug(
            f"  {status} Query {record.id}: "
            f"correct template {'in top-3' if query_result.is_top_3 else 'NOT in top-3'} "
            f"(rank: {correct_rank or 'not found'})"
        )

    # Calculate aggregate statistics
    top_1_correct = sum(1 for r in per_query_results if r.is_top_1)
    top_3_correct = sum(1 for r in per_query_results if r.is_top_3)
    top_5_correct = sum(1 for r in per_query_results if r.is_top_5)

    # Calculate average similarity scores
    correct_scores = []
    incorrect_scores = []

    for query_result in per_query_results:
        if query_result.correct_template_rank is not None:
            # Correct template was retrieved
            correct_score = query_result.similarity_scores.get(
                query_result.correct_template_id, 0.0
            )
            correct_scores.append(correct_score)
        else:
            # Correct template not retrieved - get top score from incorrect templates
            if query_result.similarity_scores:
                top_incorrect = max(query_result.similarity_scores.values())
                incorrect_scores.append(top_incorrect)

    avg_similarity_correct = float(np.mean(correct_scores)) if correct_scores else 0.0
    avg_similarity_incorrect = float(np.mean(incorrect_scores)) if incorrect_scores else 0.0

    # Calculate processing time statistics
    processing_time_stats = ProcessingTimeStats(
        min_ms=float(np.min(processing_times)) if processing_times else 0.0,
        max_ms=float(np.max(processing_times)) if processing_times else 0.0,
        mean_ms=float(np.mean(processing_times)) if processing_times else 0.0,
        p95_ms=float(np.percentile(processing_times, 95)) if processing_times else 0.0,
        sample_count=len(processing_times)
    )

    # Create validation result
    validation_result = ValidationResult(
        total_queries=len(validation_records),
        top_1_correct=top_1_correct,
        top_3_correct=top_3_correct,
        top_5_correct=top_5_correct,
        per_query_results=per_query_results,
        avg_similarity_correct=avg_similarity_correct,
        avg_similarity_incorrect=avg_similarity_incorrect,
        processing_time_stats=processing_time_stats
    )

    # Log validation completion
    log_retrieval_validation_completed(
        total_queries=validation_result.total_queries,
        top_1_correct=validation_result.top_1_correct,
        top_3_correct=validation_result.top_3_correct,
        top_3_accuracy=validation_result.top_3_accuracy,
        processing_time_ms=processing_time_stats.mean_ms * len(validation_records)
    )

    # Log summary
    logger.info(f"\n{'='*60}")
    logger.info("Validation Complete:")
    logger.info(f"  Total queries: {validation_result.total_queries}")
    logger.info(f"  Top-1 correct: {validation_result.top_1_correct} ({validation_result.top_1_correct/validation_result.total_queries*100:.1f}%)")
    logger.info(f"  Top-3 correct: {validation_result.top_3_correct} ({validation_result.top_3_accuracy:.1f}%)")
    logger.info(f"  Top-5 correct: {validation_result.top_5_correct} ({validation_result.top_5_correct/validation_result.total_queries*100:.1f}%)")
    logger.info(f"  Quality gate: {'✅ PASS' if validation_result.passes_quality_gate else '❌ FAIL'} (≥80% top-3 accuracy)")
    logger.info(f"  Avg similarity (correct): {validation_result.avg_similarity_correct:.3f}")
    logger.info(f"  Avg similarity (incorrect): {validation_result.avg_similarity_incorrect:.3f}")
    logger.info(f"  Processing time (mean): {processing_time_stats.mean_ms:.1f}ms")
    logger.info(f"  Processing time (p95): {processing_time_stats.p95_ms:.1f}ms")
    logger.info(f"{'='*60}\n")

    return validation_result


def save_validation_results(
    validation_result: ValidationResult,
    output_path: str = "data/results/retrieval_validation_results.json"
) -> None:
    """
    Save validation results to JSON file.

    Args:
        validation_result: ValidationResult object
        output_path: Path to save results JSON

    Example:
        >>> save_validation_results(result, "data/results/validation_2025-10-14.json")
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict (Pydantic model_dump)
    results_dict = validation_result.model_dump(mode='json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_dict, f, indent=2, ensure_ascii=False)

    logger.info(f"Validation results saved to {output_path}")


def format_validation_report(validation_result: ValidationResult) -> str:
    """
    Format human-readable validation report.

    Args:
        validation_result: ValidationResult object

    Returns:
        Formatted report string

    Example:
        >>> report = format_validation_report(result)
        >>> print(report)
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("RETRIEVAL VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Overall statistics
    lines.append("Overall Statistics:")
    lines.append(f"  Total queries: {validation_result.total_queries}")
    lines.append(f"  Top-1 correct: {validation_result.top_1_correct} ({validation_result.top_1_correct/validation_result.total_queries*100:.1f}%)")
    lines.append(f"  Top-3 correct: {validation_result.top_3_correct} ({validation_result.top_3_accuracy:.1f}%)")
    lines.append(f"  Top-5 correct: {validation_result.top_5_correct} ({validation_result.top_5_correct/validation_result.total_queries*100:.1f}%)")
    lines.append("")

    # Quality gate
    if validation_result.passes_quality_gate:
        lines.append("✅ PASS: Top-3 accuracy ≥80% (quality gate)")
    else:
        lines.append("❌ FAIL: Top-3 accuracy <80% (quality gate)")
    lines.append("")

    # Similarity scores
    lines.append("Similarity Scores:")
    lines.append(f"  Avg (correct templates): {validation_result.avg_similarity_correct:.3f}")
    lines.append(f"  Avg (top incorrect): {validation_result.avg_similarity_incorrect:.3f}")
    lines.append(f"  Separation: {validation_result.avg_similarity_correct - validation_result.avg_similarity_incorrect:.3f}")
    lines.append("")

    # Processing time
    stats = validation_result.processing_time_stats
    lines.append("Processing Time:")
    lines.append(f"  Mean: {stats.mean_ms:.1f}ms")
    lines.append(f"  Min: {stats.min_ms:.1f}ms")
    lines.append(f"  Max: {stats.max_ms:.1f}ms")
    lines.append(f"  P95: {stats.p95_ms:.1f}ms")
    lines.append(f"  Performance: {'✅ P95 <1000ms' if stats.meets_performance_requirement else '❌ P95 ≥1000ms'}")
    lines.append("")

    # Per-query breakdown
    lines.append("Per-Query Results:")
    lines.append(f"{'Query ID':<12} {'Result':<8} {'Rank':<6} {'Top Score':<10} {'Status'}")
    lines.append("-" * 80)

    for query_result in validation_result.per_query_results:
        query_id = query_result.query_id
        rank = str(query_result.correct_template_rank) if query_result.correct_template_rank else "N/A"
        top_score = f"{max(query_result.similarity_scores.values()):.3f}" if query_result.similarity_scores else "N/A"

        if query_result.is_top_1:
            result = "Top-1"
            status = "✅ Excellent"
        elif query_result.is_top_3:
            result = "Top-3"
            status = "✅ Good"
        elif query_result.is_top_5:
            result = "Top-5"
            status = "⚠️  Fair"
        else:
            result = "Miss"
            status = "❌ Failed"

        lines.append(f"{query_id:<12} {result:<8} {rank:<6} {top_score:<10} {status}")

    lines.append("=" * 80)

    return "\n".join(lines)
