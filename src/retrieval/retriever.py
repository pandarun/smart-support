"""
Template Retrieval Module - Core Retrieval Logic.

Orchestrates the retrieval pipeline:
1. Filter templates by category/subcategory (from classification)
2. Embed query using Scibox API
3. Rank templates by cosine similarity
4. Return top-K results with metadata

Performance requirement: <1 second processing time (PR-001)
"""

import logging
import time
from typing import Optional

from src.retrieval.embeddings import EmbeddingsClient
from src.retrieval.cache import EmbeddingCache
from src.retrieval.ranker import rank_templates
from src.retrieval.models import RetrievalRequest, RetrievalResponse
from src.utils.logging import log_template_retrieval_requested, log_template_retrieval_completed

logger = logging.getLogger(__name__)


class TemplateRetriever:
    """
    Main retrieval orchestrator for template recommendation system.

    Combines embeddings API, in-memory cache, and ranking algorithms to
    retrieve and rank relevant FAQ templates based on customer inquiries.

    Performance characteristics:
    - Query embedding: ~100-500ms (Scibox API call)
    - Cosine similarity ranking: <5ms for 50 templates
    - Total: <1000ms (PR-001 requirement)

    Example:
        >>> embeddings_client = EmbeddingsClient()
        >>> cache = asyncio.run(precompute_embeddings("faq.xlsx", embeddings_client))
        >>> retriever = TemplateRetriever(embeddings_client, cache)
        >>>
        >>> request = RetrievalRequest(
        ...     query="Как открыть накопительный счет?",
        ...     category="Счета и вклады",
        ...     subcategory="Открытие счета",
        ...     top_k=5
        ... )
        >>> response = retriever.retrieve(request)
        >>> print(f"Found {len(response.results)} templates in {response.processing_time_ms:.1f}ms")
    """

    def __init__(
        self,
        embeddings_client: EmbeddingsClient,
        cache: EmbeddingCache
    ):
        """
        Initialize template retriever.

        Args:
            embeddings_client: Client for embedding query text
            cache: Cache with precomputed template embeddings

        Raises:
            ValueError: If cache is not ready (no embeddings precomputed)
        """
        if not cache.is_ready:
            raise ValueError(
                "Cache is not ready - embeddings must be precomputed before retrieval. "
                "Call precompute_embeddings() first."
            )

        self.embeddings_client = embeddings_client
        self.cache = cache

        stats = cache.stats
        logger.info(
            f"Initialized TemplateRetriever with {stats['total_templates']} templates "
            f"across {stats['categories']} categories"
        )

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """
        Retrieve top-K relevant templates for a customer inquiry.

        Pipeline:
        1. Log retrieval request
        2. Filter templates by category/subcategory (from classification)
        3. Embed query using Scibox API
        4. Compute cosine similarity for all candidates
        5. Rank by similarity (or weighted score if historical enabled)
        6. Return top-K results with warnings if applicable

        Args:
            request: RetrievalRequest with query, category, subcategory, top_k

        Returns:
            RetrievalResponse with ranked results, processing time, warnings

        Raises:
            EmbeddingsError: If query embedding fails after retries
            ValueError: If request validation fails

        Example:
            >>> request = RetrievalRequest(
            ...     query="Как открыть накопительный счет в мобильном приложении?",
            ...     category="Счета и вклады",
            ...     subcategory="Открытие счета",
            ...     top_k=5
            ... )
            >>> response = retriever.retrieve(request)
            >>> response.results[0].rank
            1
            >>> response.processing_time_ms < 1000
            True
        """
        start_time = time.time()

        # Log retrieval request
        log_template_retrieval_requested(
            query=request.query,
            category=request.category,
            subcategory=request.subcategory,
            top_k=request.top_k
        )

        logger.debug(
            f"Retrieving templates for query: '{request.query[:60]}...' "
            f"(category: {request.category}, subcategory: {request.subcategory}, top_k: {request.top_k})"
        )

        # Step 1: Filter templates by category/subcategory
        candidates = self.cache.get_by_category(
            category=request.category,
            subcategory=request.subcategory
        )

        logger.debug(
            f"Filtered to {len(candidates)} candidates in "
            f"'{request.category}' > '{request.subcategory}'"
        )

        # Handle no templates case
        if not candidates:
            logger.warning(
                f"No templates found in category '{request.category}' > '{request.subcategory}'"
            )

            processing_time_ms = (time.time() - start_time) * 1000

            return RetrievalResponse(
                query=request.query,
                category=request.category,
                subcategory=request.subcategory,
                results=[],
                total_candidates=0,
                processing_time_ms=processing_time_ms,
                warnings=[f"No templates found in category '{request.category}' > '{request.subcategory}'"]
            )

        # Step 2: Embed query
        try:
            query_embedding = self.embeddings_client.embed(request.query)
            logger.debug(f"Embedded query (shape: {query_embedding.shape})")
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise

        # Step 3: Rank templates by cosine similarity
        results = rank_templates(
            query_embedding=query_embedding,
            candidates=candidates,
            top_k=request.top_k,
            use_historical_weighting=request.use_historical_weighting
        )

        logger.debug(
            f"Ranked {len(results)} results (top score: {results[0].similarity_score:.3f})"
            if results else "No results after ranking"
        )

        # Step 4: Generate warnings
        warnings = []

        # Check for low confidence matches
        if results and all(r.combined_score < 0.5 for r in results):
            warning_msg = "Low confidence matches - all scores < 0.5"
            warnings.append(warning_msg)
            logger.warning(warning_msg)

        # Check for very low top score
        if results and results[0].combined_score < 0.3:
            warning_msg = f"Very low top score ({results[0].combined_score:.3f}) - may not be relevant"
            warnings.append(warning_msg)
            logger.warning(warning_msg)

        # Step 5: Calculate processing time and log completion
        processing_time_ms = (time.time() - start_time) * 1000

        # Log performance warning if exceeds requirement
        if processing_time_ms > 1000:
            logger.warning(
                f"Retrieval took {processing_time_ms:.1f}ms, exceeds 1000ms requirement (PR-001)"
            )
            warnings.append(f"Slow retrieval: {processing_time_ms:.0f}ms (target: <1000ms)")

        # Log retrieval completion
        log_template_retrieval_completed(
            query=request.query,
            category=request.category,
            subcategory=request.subcategory,
            total_candidates=len(candidates),
            results_count=len(results),
            top_score=results[0].combined_score if results else 0.0,
            processing_time_ms=processing_time_ms
        )

        logger.info(
            f"Retrieval complete: {len(results)} results in {processing_time_ms:.1f}ms "
            f"(top score: {results[0].similarity_score:.3f})"
            if results else f"Retrieval complete: 0 results in {processing_time_ms:.1f}ms"
        )

        # Step 6: Build response
        return RetrievalResponse(
            query=request.query,
            category=request.category,
            subcategory=request.subcategory,
            results=results,
            total_candidates=len(candidates),
            processing_time_ms=processing_time_ms,
            warnings=warnings
        )

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics

        Example:
            >>> stats = retriever.get_cache_stats()
            >>> stats['total_templates']
            187
        """
        return self.cache.stats

    def is_ready(self) -> bool:
        """
        Check if retriever is ready to handle requests.

        Returns:
            True if cache has precomputed embeddings

        Example:
            >>> retriever.is_ready()
            True
        """
        return self.cache.is_ready
