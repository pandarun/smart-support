"""
Integration Helper - Combines Classification + Retrieval.

Provides convenience functions for end-to-end inquiry processing:
- classify_and_retrieve(): Single function call for full pipeline
- Automatic error handling and result formatting
- Simplified API for operator interfaces

Example:
    >>> result = await classify_and_retrieve("Как открыть накопительный счет?")
    >>> print(f"Category: {result.classification.category}")
    >>> print(f"Top template: {result.retrieval.results[0].template_question}")
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from src.classification.classifier import classify
from src.retrieval.retriever import TemplateRetriever
from src.retrieval.models import RetrievalRequest, RetrievalResponse
from src.classification.models import ClassificationResult

logger = logging.getLogger(__name__)


class IntegratedResult(BaseModel):
    """
    Result of classify_and_retrieve() operation.

    Contains both classification and retrieval results in single object.

    Attributes:
        inquiry: Original customer inquiry text
        classification: Classification result (category, subcategory, confidence)
        retrieval: Retrieval result (ranked templates with scores)
        total_processing_time_ms: Total time for classification + retrieval
        success: Whether operation completed successfully
        error: Error message if operation failed
    """
    inquiry: str
    classification: Optional[ClassificationResult] = None
    retrieval: Optional[RetrievalResponse] = None
    total_processing_time_ms: float = Field(default=0.0)
    success: bool = Field(default=True)
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


async def classify_and_retrieve(
    inquiry: str,
    retriever: TemplateRetriever,
    top_k: int = 5,
    use_historical_weighting: bool = False,
    classification_confidence_threshold: float = 0.0
) -> IntegratedResult:
    """
    Perform classification + retrieval in single call.

    This is the main integration function that combines both modules:
    1. Classify inquiry → get category/subcategory
    2. Retrieve templates using classification results
    3. Return combined result

    Performance: <3 seconds total (<2s classification + <1s retrieval)

    Args:
        inquiry: Customer inquiry text (Russian/Cyrillic)
        retriever: TemplateRetriever instance (must be initialized)
        top_k: Number of templates to retrieve (default: 5)
        use_historical_weighting: Enable historical success rate weighting (default: False)
        classification_confidence_threshold: Minimum confidence to proceed with retrieval (default: 0.0)

    Returns:
        IntegratedResult with classification + retrieval results

    Raises:
        ValueError: If inquiry is invalid or retriever not ready

    Example:
        >>> import asyncio
        >>> from src.retrieval import initialize_retrieval
        >>>
        >>> # Initialize system
        >>> retriever = asyncio.run(initialize_retrieval())
        >>>
        >>> # Process inquiry end-to-end
        >>> result = asyncio.run(classify_and_retrieve(
        ...     "Как открыть накопительный счет в мобильном приложении?",
        ...     retriever
        ... ))
        >>>
        >>> # Check results
        >>> if result.success:
        ...     print(f"Category: {result.classification.category}")
        ...     print(f"Confidence: {result.classification.confidence:.2f}")
        ...     print(f"Top template: {result.retrieval.results[0].template_question}")
        ...     print(f"Total time: {result.total_processing_time_ms:.0f}ms")
        ... else:
        ...     print(f"Error: {result.error}")
        Category: Счета и вклады
        Confidence: 0.89
        Top template: Как открыть накопительный счет через мобильное приложение?
        Total time: 2143ms
    """
    import time

    start_time = time.time()

    logger.info(f"Starting integrated classification + retrieval for inquiry: '{inquiry[:60]}...'")

    # Verify retriever is ready
    if not retriever.is_ready():
        error_msg = "Retriever not ready - embeddings must be precomputed first"
        logger.error(error_msg)
        return IntegratedResult(
            inquiry=inquiry,
            success=False,
            error=error_msg
        )

    # Step 1: Classification
    try:
        logger.debug("Step 1/2: Classifying inquiry...")
        classification_result = classify(inquiry)

        logger.info(
            f"Classification complete: category='{classification_result.category}', "
            f"subcategory='{classification_result.subcategory}', "
            f"confidence={classification_result.confidence:.3f}"
        )

    except Exception as e:
        error_msg = f"Classification failed: {e}"
        logger.error(error_msg, exc_info=True)

        return IntegratedResult(
            inquiry=inquiry,
            success=False,
            error=error_msg,
            total_processing_time_ms=(time.time() - start_time) * 1000
        )

    # Check classification confidence threshold
    if classification_result.confidence < classification_confidence_threshold:
        logger.warning(
            f"Classification confidence {classification_result.confidence:.3f} below "
            f"threshold {classification_confidence_threshold:.3f}, skipping retrieval"
        )

        return IntegratedResult(
            inquiry=inquiry,
            classification=classification_result,
            success=True,
            total_processing_time_ms=(time.time() - start_time) * 1000
        )

    # Step 2: Retrieval
    try:
        logger.debug("Step 2/2: Retrieving templates...")

        retrieval_request = RetrievalRequest(
            query=inquiry,
            category=classification_result.category,
            subcategory=classification_result.subcategory,
            classification_confidence=classification_result.confidence,
            top_k=top_k,
            use_historical_weighting=use_historical_weighting
        )

        retrieval_result = retriever.retrieve(retrieval_request)

        logger.info(
            f"Retrieval complete: found {len(retrieval_result.results)} templates "
            f"in {retrieval_result.processing_time_ms:.1f}ms"
        )

    except Exception as e:
        error_msg = f"Retrieval failed: {e}"
        logger.error(error_msg, exc_info=True)

        # Return classification result even if retrieval failed
        return IntegratedResult(
            inquiry=inquiry,
            classification=classification_result,
            success=False,
            error=error_msg,
            total_processing_time_ms=(time.time() - start_time) * 1000
        )

    # Success - return combined result
    total_time_ms = (time.time() - start_time) * 1000

    logger.info(
        f"Integrated operation complete: "
        f"total_time={total_time_ms:.0f}ms, "
        f"classification={classification_result.processing_time_ms:.0f}ms, "
        f"retrieval={retrieval_result.processing_time_ms:.0f}ms"
    )

    return IntegratedResult(
        inquiry=inquiry,
        classification=classification_result,
        retrieval=retrieval_result,
        total_processing_time_ms=total_time_ms,
        success=True
    )


def format_integrated_result(result: IntegratedResult) -> str:
    """
    Format IntegratedResult for console display.

    Args:
        result: IntegratedResult from classify_and_retrieve()

    Returns:
        Formatted string with classification + retrieval results

    Example:
        >>> result = asyncio.run(classify_and_retrieve("Как открыть счет?", retriever))
        >>> print(format_integrated_result(result))
        ================================================================================
        SMART SUPPORT - INTEGRATED RESULT
        ================================================================================
        ...
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("SMART SUPPORT - INTEGRATED RESULT")
    lines.append("=" * 80)
    lines.append("")

    # Inquiry
    lines.append(f"Inquiry: {result.inquiry}")
    lines.append("")

    # Check success
    if not result.success:
        lines.append(f"❌ ERROR: {result.error}")
        lines.append("=" * 80)
        return "\n".join(lines)

    # Classification results
    if result.classification:
        lines.append("📊 CLASSIFICATION RESULT")
        lines.append("-" * 80)
        lines.append(f"Category: {result.classification.category}")
        lines.append(f"Subcategory: {result.classification.subcategory}")
        lines.append(f"Confidence: {result.classification.confidence:.2f}")
        lines.append(f"Processing time: {result.classification.processing_time_ms:.0f}ms")
        lines.append("")

    # Retrieval results
    if result.retrieval:
        lines.append("📋 RETRIEVAL RESULTS")
        lines.append("-" * 80)
        lines.append(f"Total candidates: {result.retrieval.total_candidates}")
        lines.append(f"Processing time: {result.retrieval.processing_time_ms:.0f}ms")

        # Warnings
        if result.retrieval.warnings:
            lines.append("")
            lines.append("⚠️  Warnings:")
            for warning in result.retrieval.warnings:
                lines.append(f"   - {warning}")

        # Templates
        if result.retrieval.results:
            lines.append("")
            lines.append(f"Top {len(result.retrieval.results)} Templates:")
            lines.append("")

            for template_result in result.retrieval.results:
                # Confidence emoji
                confidence_emoji = {
                    "high": "🟢",
                    "medium": "🟡",
                    "low": "🔴"
                }.get(template_result.confidence_level, "⚪")

                lines.append(
                    f"#{template_result.rank} {confidence_emoji} "
                    f"Score: {template_result.similarity_score:.3f} "
                    f"({template_result.confidence_level} confidence)"
                )
                lines.append(f"   Q: {template_result.template_question}")

                # Truncate answer for display
                answer_preview = template_result.template_answer[:100]
                if len(template_result.template_answer) > 100:
                    answer_preview += "..."
                lines.append(f"   A: {answer_preview}")
                lines.append("")
        else:
            lines.append("")
            lines.append("❌ No templates found")

    # Footer
    lines.append("=" * 80)
    lines.append(f"Total processing time: {result.total_processing_time_ms:.0f}ms")
    lines.append("=" * 80)

    return "\n".join(lines)
