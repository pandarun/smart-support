"""
Template ranking utilities for Template Retrieval Module.

Provides efficient cosine similarity computation and ranking algorithms
using numpy vectorized operations.
"""

import logging
from typing import List, Tuple

import numpy as np

from src.retrieval.models import RetrievalResult
from src.retrieval.cache import TemplateMetadata

logger = logging.getLogger(__name__)


def cosine_similarity_batch(
    query_embedding: np.ndarray,
    template_embeddings: np.ndarray
) -> np.ndarray:
    """
    Compute cosine similarity between query and multiple templates (vectorized).

    Uses numpy dot product for efficient batch computation. Assumes embeddings
    are already L2-normalized (as done by EmbeddingCache.add()).

    Performance: <5ms for 50 templates (requirement from constitution)

    Args:
        query_embedding: Shape (1024,) - query embedding vector (normalized or unnormalized)
        template_embeddings: Shape (N, 1024) - N template embedding vectors (normalized)

    Returns:
        similarities: Shape (N,) - cosine similarity scores (0.0 to 1.0)

    Raises:
        ValueError: If embedding shapes are invalid

    Example:
        >>> query = np.random.randn(1024).astype(np.float32)
        >>> templates = np.random.randn(50, 1024).astype(np.float32)
        >>> similarities = cosine_similarity_batch(query, templates)
        >>> similarities.shape
        (50,)
        >>> 0.0 <= similarities[0] <= 1.0
        True
    """
    # Validate shapes
    if query_embedding.ndim != 1 or query_embedding.shape[0] != 1024:
        raise ValueError(
            f"Invalid query embedding shape: {query_embedding.shape}, expected (1024,)"
        )

    if template_embeddings.ndim != 2 or template_embeddings.shape[1] != 1024:
        raise ValueError(
            f"Invalid template embeddings shape: {template_embeddings.shape}, "
            f"expected (N, 1024)"
        )

    # Normalize query embedding (if not already normalized)
    query_norm = np.linalg.norm(query_embedding)
    if query_norm == 0:
        raise ValueError("Query embedding has zero norm (invalid embedding)")

    query_normalized = query_embedding / query_norm

    # Compute cosine similarity using dot product (vectorized)
    # When both vectors are normalized: dot(a, b) = cosine_similarity(a, b)
    similarities = np.dot(template_embeddings, query_normalized)

    # Clip to [0, 1] range (handle numerical precision issues)
    # Cosine similarity can be negative, but we clamp to [0, 1] for relevance ranking
    similarities = np.clip(similarities, 0.0, 1.0)

    return similarities


def rank_templates(
    query_embedding: np.ndarray,
    candidates: List[Tuple[str, np.ndarray, TemplateMetadata]],
    top_k: int = 5,
    use_historical_weighting: bool = False
) -> List[RetrievalResult]:
    """
    Rank templates by cosine similarity (with optional historical weighting).

    Scoring methods:
    - Pure similarity (default): score = similarity
    - Historical weighting (if enabled): score = 0.7 * similarity + 0.3 * historical_success_rate

    Args:
        query_embedding: Query embedding vector (1024 dims)
        candidates: List of (template_id, embedding, metadata) tuples from cache
        top_k: Number of results to return (default: 5, max: 10)
        use_historical_weighting: Enable weighted scoring with historical success rates

    Returns:
        Top-K ranked templates as RetrievalResult objects (sorted by rank)

    Raises:
        ValueError: If top_k < 1 or query_embedding has invalid shape

    Example:
        >>> query_emb = np.random.randn(1024).astype(np.float32)
        >>> candidates = [
        ...     ("tmpl_001", np.random.randn(1024).astype(np.float32), metadata1),
        ...     ("tmpl_002", np.random.randn(1024).astype(np.float32), metadata2),
        ... ]
        >>> results = rank_templates(query_emb, candidates, top_k=5)
        >>> len(results)
        2
        >>> results[0].rank
        1
        >>> results[0].similarity_score >= results[1].similarity_score
        True
    """
    if top_k < 1:
        raise ValueError(f"top_k must be >= 1, got {top_k}")

    if query_embedding.shape != (1024,):
        raise ValueError(
            f"Invalid query embedding shape: {query_embedding.shape}, expected (1024,)"
        )

    # Handle empty candidates
    if not candidates:
        logger.debug("rank_templates: No candidates to rank")
        return []

    # Extract components from candidates
    template_ids = [c[0] for c in candidates]
    template_embeddings_list = [c[1] for c in candidates]
    template_metadata = [c[2] for c in candidates]

    # Stack embeddings into numpy array for vectorized operations
    template_embeddings = np.array(template_embeddings_list)

    # Compute cosine similarities (vectorized)
    similarities = cosine_similarity_batch(query_embedding, template_embeddings)

    # Compute combined scores
    if use_historical_weighting:
        # Weighted scoring: 70% similarity + 30% historical success rate
        historical_rates = np.array([m.success_rate for m in template_metadata])
        combined_scores = 0.7 * similarities + 0.3 * historical_rates
        logger.debug(f"Using historical weighting (mean historical rate: {historical_rates.mean():.3f})")
    else:
        # Pure similarity scoring
        combined_scores = similarities

    # Sort by combined score descending and take top-K
    ranked_indices = np.argsort(combined_scores)[::-1][:top_k]

    # Build RetrievalResult objects
    results = []
    for rank, idx in enumerate(ranked_indices, start=1):
        metadata = template_metadata[idx]
        similarity = float(similarities[idx])
        combined_score = float(combined_scores[idx])

        result = RetrievalResult(
            template_id=template_ids[idx],
            template_question=metadata.question,
            template_answer=metadata.answer,
            category=metadata.category,
            subcategory=metadata.subcategory,
            similarity_score=similarity,
            combined_score=combined_score,
            rank=rank
        )
        results.append(result)

    logger.debug(
        f"rank_templates: Ranked {len(candidates)} candidates, "
        f"returning top-{len(results)} (similarity range: "
        f"{results[0].similarity_score:.3f}-{results[-1].similarity_score:.3f})"
    )

    return results


def calculate_similarity_statistics(
    similarities: np.ndarray
) -> dict:
    """
    Calculate statistical summary of similarity scores.

    Used for validation reporting and quality analysis.

    Args:
        similarities: Array of cosine similarity scores

    Returns:
        Dictionary with min, max, mean, median, std, p25, p75, p95

    Example:
        >>> similarities = np.array([0.85, 0.72, 0.68, 0.55, 0.42])
        >>> stats = calculate_similarity_statistics(similarities)
        >>> stats['mean']
        0.644
        >>> stats['p95']
        0.823
    """
    if len(similarities) == 0:
        return {
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "p25": 0.0,
            "p75": 0.0,
            "p95": 0.0
        }

    return {
        "min": float(np.min(similarities)),
        "max": float(np.max(similarities)),
        "mean": float(np.mean(similarities)),
        "median": float(np.median(similarities)),
        "std": float(np.std(similarities)),
        "p25": float(np.percentile(similarities, 25)),
        "p75": float(np.percentile(similarities, 75)),
        "p95": float(np.percentile(similarities, 95))
    }


def filter_low_confidence_results(
    results: List[RetrievalResult],
    min_score: float = 0.5
) -> Tuple[List[RetrievalResult], List[RetrievalResult]]:
    """
    Split results into high-confidence and low-confidence groups.

    Used for generating warnings and UI display logic.

    Args:
        results: Ranked retrieval results
        min_score: Minimum combined_score threshold (default: 0.5)

    Returns:
        Tuple of (high_confidence_results, low_confidence_results)

    Example:
        >>> results = [
        ...     RetrievalResult(..., combined_score=0.75, ...),
        ...     RetrievalResult(..., combined_score=0.45, ...)
        ... ]
        >>> high, low = filter_low_confidence_results(results, min_score=0.5)
        >>> len(high)
        1
        >>> len(low)
        1
    """
    high_confidence = [r for r in results if r.combined_score >= min_score]
    low_confidence = [r for r in results if r.combined_score < min_score]

    return high_confidence, low_confidence
