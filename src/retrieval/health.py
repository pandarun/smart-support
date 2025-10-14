"""
Health and readiness endpoints for Template Retrieval Module.

Provides status checks for monitoring and orchestration systems:
- get_health_status(): Simple liveness check (always returns healthy)
- get_readiness_status(): Detailed readiness check with cache statistics
- heartbeat logging for monitoring systems

Constitution Compliance:
- Principle V: Deployment Simplicity (health checks for Docker/K8s)
"""

import logging
from typing import Optional
from datetime import datetime

from src.retrieval.retriever import TemplateRetriever

logger = logging.getLogger(__name__)


# Health/Readiness Status Constants
class HealthStatus:
    """Health check status constants."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class ReadinessStatus:
    """Readiness check status constants."""
    READY = "ready"
    NOT_READY = "not_ready"
    PRECOMPUTING = "precomputing"
    PARTIAL = "partial"  # Some templates failed, but system functional


def get_health_status() -> dict:
    """
    Get health status (liveness check).

    This is a simple health check that always returns healthy if the
    application is running. Use for Kubernetes liveness probes.

    Returns:
        Dictionary with health status:
        - status: "healthy" (always)
        - timestamp: ISO 8601 timestamp

    Example:
        >>> status = get_health_status()
        >>> status['status']
        'healthy'
    """
    return {
        "status": HealthStatus.HEALTHY,
        "timestamp": datetime.now().isoformat()
    }


def get_readiness_status(retriever: Optional[TemplateRetriever]) -> dict:
    """
    Get readiness status with cache statistics.

    Provides detailed readiness information for orchestration systems.
    Use for Kubernetes readiness probes.

    Readiness states:
    - ready: System initialized and ready to handle requests
    - not_ready: System not initialized or cache empty
    - partial: Some templates failed embedding, but system functional

    Args:
        retriever: TemplateRetriever instance (None if not initialized)

    Returns:
        Dictionary with readiness status:
        - status: Readiness state (ready/not_ready/partial)
        - ready: Boolean readiness flag
        - total_templates: Number of templates in cache
        - embedded_templates: Number successfully embedded
        - failed_templates: Number that failed embedding
        - categories: Number of categories
        - subcategories: Number of subcategories
        - precompute_time_seconds: Time taken for precomputation
        - memory_estimate_mb: Estimated memory usage
        - timestamp: ISO 8601 timestamp
        - message: Human-readable status message

    Example:
        >>> status = get_readiness_status(retriever)
        >>> status['status']
        'ready'
        >>> status['total_templates']
        187
        >>> status['ready']
        True
    """
    timestamp = datetime.now().isoformat()

    # Case 1: Retriever not initialized
    if retriever is None:
        return {
            "status": ReadinessStatus.NOT_READY,
            "ready": False,
            "total_templates": 0,
            "embedded_templates": 0,
            "failed_templates": 0,
            "categories": 0,
            "subcategories": 0,
            "precompute_time_seconds": None,
            "memory_estimate_mb": 0.0,
            "timestamp": timestamp,
            "message": "Retrieval module not initialized"
        }

    # Case 2: Retriever initialized but cache not ready
    if not retriever.is_ready():
        return {
            "status": ReadinessStatus.NOT_READY,
            "ready": False,
            "total_templates": 0,
            "embedded_templates": 0,
            "failed_templates": 0,
            "categories": 0,
            "subcategories": 0,
            "precompute_time_seconds": None,
            "memory_estimate_mb": 0.0,
            "timestamp": timestamp,
            "message": "Cache not ready - embeddings not precomputed"
        }

    # Case 3: Retriever ready - get statistics
    stats = retriever.get_cache_stats()
    total_templates = stats["total_templates"]
    embedded_templates = total_templates  # All in cache are embedded
    failed_templates = 0  # Not tracked in current implementation

    # Determine readiness status
    if embedded_templates == 0:
        status = ReadinessStatus.NOT_READY
        ready = False
        message = "No templates embedded"
    elif failed_templates > 0 and failed_templates / (embedded_templates + failed_templates) > 0.2:
        # More than 20% failed - partial readiness
        status = ReadinessStatus.PARTIAL
        ready = True  # Still functional
        message = f"Partially ready: {failed_templates} templates failed embedding ({failed_templates/(embedded_templates+failed_templates)*100:.1f}%)"
    else:
        # Fully ready
        status = ReadinessStatus.READY
        ready = True
        message = f"Ready: {embedded_templates} templates embedded"

    return {
        "status": status,
        "ready": ready,
        "total_templates": total_templates,
        "embedded_templates": embedded_templates,
        "failed_templates": failed_templates,
        "categories": stats["categories"],
        "subcategories": stats["subcategories"],
        "precompute_time_seconds": stats["precompute_time_seconds"],
        "memory_estimate_mb": stats["memory_estimate_mb"],
        "timestamp": timestamp,
        "message": message
    }


def log_heartbeat(retriever: Optional[TemplateRetriever]) -> None:
    """
    Log periodic heartbeat with system status.

    Used by monitoring systems to track system health over time.
    Should be called periodically (e.g., every 60 seconds).

    Args:
        retriever: TemplateRetriever instance (None if not initialized)

    Example:
        >>> import asyncio
        >>> async def heartbeat_loop(retriever):
        ...     while True:
        ...         log_heartbeat(retriever)
        ...         await asyncio.sleep(60)  # Every 60 seconds
    """
    readiness = get_readiness_status(retriever)

    logger.info(
        f"Heartbeat: status={readiness['status']}, "
        f"templates={readiness['total_templates']}, "
        f"ready={readiness['ready']}"
    )


def format_readiness_report(retriever: Optional[TemplateRetriever]) -> str:
    """
    Format human-readable readiness report.

    Useful for CLI output and debugging.

    Args:
        retriever: TemplateRetriever instance (None if not initialized)

    Returns:
        Formatted readiness report as string

    Example:
        >>> report = format_readiness_report(retriever)
        >>> print(report)
        ===== Retrieval Module Readiness =====
        Status: ready
        Total Templates: 187
        ...
    """
    readiness = get_readiness_status(retriever)

    lines = [
        "=" * 50,
        "Retrieval Module Readiness Report",
        "=" * 50,
        f"Status: {readiness['status']}",
        f"Ready: {'✅ Yes' if readiness['ready'] else '❌ No'}",
        f"",
        f"Templates:",
        f"  - Total: {readiness['total_templates']}",
        f"  - Embedded: {readiness['embedded_templates']}",
        f"  - Failed: {readiness['failed_templates']}",
        f"",
        f"Structure:",
        f"  - Categories: {readiness['categories']}",
        f"  - Subcategories: {readiness['subcategories']}",
        f"",
        f"Performance:",
        f"  - Precompute Time: {readiness['precompute_time_seconds']:.1f}s" if readiness['precompute_time_seconds'] else "  - Precompute Time: N/A",
        f"  - Memory Estimate: {readiness['memory_estimate_mb']:.2f} MB",
        f"",
        f"Timestamp: {readiness['timestamp']}",
        f"Message: {readiness['message']}",
        "=" * 50
    ]

    return "\n".join(lines)
