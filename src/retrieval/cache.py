"""
In-memory embedding cache for Template Retrieval Module.

Provides fast storage and retrieval of precomputed template embeddings
with category-based filtering and normalization.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TemplateMetadata:
    """
    Metadata for a template (without embedding vector).

    Used for filtering, display, and historical weighting.
    Kept separate from embeddings to enable flexible storage strategies.
    """
    template_id: str
    category: str
    subcategory: str
    question: str
    answer: str
    success_rate: float = 0.5  # Historical operator selection rate (0.0-1.0)
    usage_count: int = 0  # Number of times template selected by operators


class EmbeddingCache:
    """
    In-memory storage for precomputed template embeddings.

    Features:
    - Fast category/subcategory filtering for retrieval
    - Automatic L2 normalization of embeddings
    - Readiness checks for system health
    - Statistics for monitoring and validation

    Memory footprint estimate:
    - 200 templates × 1024 dims × 4 bytes (float32) = ~600 KB
    - 200 templates × ~1 KB metadata = ~200 KB
    - Total: ~1 MB (scales easily to 1000+ templates)

    Thread-safety: Not thread-safe. Use locks if accessing from multiple threads.

    Example:
        >>> cache = EmbeddingCache()
        >>> metadata = TemplateMetadata(
        ...     template_id="tmpl_001",
        ...     category="Счета и вклады",
        ...     subcategory="Открытие счета",
        ...     question="Как открыть счет?",
        ...     answer="Для открытия счета..."
        ... )
        >>> embedding = np.random.randn(1024).astype(np.float32)
        >>> cache.add("tmpl_001", embedding, metadata)
        >>> cache.is_ready
        True
        >>> cache.stats
        {'total_templates': 1, 'categories': 1, 'precompute_time_seconds': None}
    """

    def __init__(self):
        """Initialize empty cache."""
        # Primary storage: template_id -> normalized embedding vector
        self.embeddings: Dict[str, np.ndarray] = {}

        # Metadata storage: template_id -> TemplateMetadata
        self.metadata: Dict[str, TemplateMetadata] = {}

        # Performance tracking
        self.precompute_time: Optional[float] = None

        logger.info("Initialized empty EmbeddingCache")

    def add(
        self,
        template_id: str,
        embedding: np.ndarray,
        metadata: TemplateMetadata
    ) -> None:
        """
        Add template embedding to cache with automatic normalization.

        Embeddings are L2-normalized to enable efficient cosine similarity
        computation (dot product = cosine similarity when normalized).

        Args:
            template_id: Unique template identifier
            embedding: Raw embedding vector (1024 dims, float32)
            metadata: Template metadata for filtering and display

        Raises:
            ValueError: If embedding has invalid shape or template_id mismatch
            ZeroDivisionError: If embedding has zero norm (invalid embedding)

        Example:
            >>> cache = EmbeddingCache()
            >>> embedding = np.array([...])  # 1024-dim vector
            >>> metadata = TemplateMetadata(template_id="tmpl_001", ...)
            >>> cache.add("tmpl_001", embedding, metadata)
        """
        if not template_id or not template_id.strip():
            raise ValueError("template_id cannot be empty")

        if metadata.template_id != template_id:
            raise ValueError(
                f"template_id mismatch: '{template_id}' != '{metadata.template_id}'"
            )

        if embedding.shape != (1024,):
            raise ValueError(
                f"Invalid embedding shape: {embedding.shape}, expected (1024,)"
            )

        # Normalize embedding (L2 normalization)
        norm = np.linalg.norm(embedding)
        if norm == 0:
            raise ValueError(
                f"Invalid embedding for template '{template_id}': zero norm (all zeros)"
            )

        normalized_embedding = embedding / norm

        # Store in cache
        self.embeddings[template_id] = normalized_embedding
        self.metadata[template_id] = metadata

        logger.debug(
            f"Added template '{template_id}' to cache "
            f"(category: {metadata.category}, subcategory: {metadata.subcategory})"
        )

    def get_by_category(
        self,
        category: str,
        subcategory: str
    ) -> List[Tuple[str, np.ndarray, TemplateMetadata]]:
        """
        Get all templates in a specific category/subcategory.

        Used for filtering retrieval candidates based on classification result.
        Returns tuples of (template_id, embedding, metadata) for efficient ranking.

        Args:
            category: Top-level category (e.g., "Счета и вклады")
            subcategory: Second-level classification (e.g., "Открытие счета")

        Returns:
            List of (template_id, normalized_embedding, metadata) tuples
            Empty list if no templates found in category

        Example:
            >>> cache = EmbeddingCache()
            >>> # ... add templates ...
            >>> candidates = cache.get_by_category("Счета и вклады", "Открытие счета")
            >>> len(candidates)
            15
            >>> template_id, embedding, metadata = candidates[0]
            >>> embedding.shape
            (1024,)
        """
        candidates = []

        for template_id, embedding in self.embeddings.items():
            metadata = self.metadata[template_id]

            if metadata.category == category and metadata.subcategory == subcategory:
                candidates.append((template_id, embedding, metadata))

        logger.debug(
            f"get_by_category('{category}', '{subcategory}'): "
            f"found {len(candidates)} templates"
        )

        return candidates

    def get_all(self) -> List[Tuple[str, np.ndarray, TemplateMetadata]]:
        """
        Get all templates in cache.

        Used for validation testing or full-database queries.

        Returns:
            List of (template_id, normalized_embedding, metadata) tuples
        """
        return [
            (template_id, embedding, self.metadata[template_id])
            for template_id, embedding in self.embeddings.items()
        ]

    @property
    def is_ready(self) -> bool:
        """
        Check if cache has embeddings (readiness check).

        System should not accept retrieval requests until cache is ready.

        Returns:
            True if cache contains at least one template embedding

        Example:
            >>> cache = EmbeddingCache()
            >>> cache.is_ready
            False
            >>> # ... precompute embeddings ...
            >>> cache.is_ready
            True
        """
        return len(self.embeddings) > 0

    @property
    def stats(self) -> Dict[str, any]:
        """
        Get cache statistics for monitoring and logging.

        Returns:
            Dictionary with:
            - total_templates: Number of templates in cache
            - categories: Number of unique categories
            - subcategories: Number of unique subcategories
            - precompute_time_seconds: Time taken to precompute (if available)
            - memory_estimate_mb: Estimated memory usage in megabytes

        Example:
            >>> cache.stats
            {
                'total_templates': 187,
                'categories': 6,
                'subcategories': 35,
                'precompute_time_seconds': 45.3,
                'memory_estimate_mb': 0.95
            }
        """
        # Calculate unique categories and subcategories
        categories = set(m.category for m in self.metadata.values())
        subcategories = set(
            (m.category, m.subcategory) for m in self.metadata.values()
        )

        # Estimate memory usage
        # embeddings: N × 1024 × 4 bytes (float32)
        # metadata: N × ~1 KB (estimated average per template)
        num_templates = len(self.embeddings)
        embedding_memory_mb = (num_templates * 1024 * 4) / (1024 * 1024)
        metadata_memory_mb = (num_templates * 1024) / (1024 * 1024)
        total_memory_mb = embedding_memory_mb + metadata_memory_mb

        return {
            "total_templates": num_templates,
            "categories": len(categories),
            "subcategories": len(subcategories),
            "precompute_time_seconds": self.precompute_time,
            "memory_estimate_mb": round(total_memory_mb, 2)
        }

    def get_metadata(self, template_id: str) -> Optional[TemplateMetadata]:
        """
        Get metadata for a specific template.

        Args:
            template_id: Template identifier

        Returns:
            TemplateMetadata if found, None otherwise

        Example:
            >>> metadata = cache.get_metadata("tmpl_001")
            >>> metadata.question
            'Как открыть счет?'
        """
        return self.metadata.get(template_id)

    def get_embedding(self, template_id: str) -> Optional[np.ndarray]:
        """
        Get normalized embedding for a specific template.

        Args:
            template_id: Template identifier

        Returns:
            Normalized embedding vector if found, None otherwise

        Example:
            >>> embedding = cache.get_embedding("tmpl_001")
            >>> embedding.shape
            (1024,)
            >>> np.linalg.norm(embedding)  # Should be ~1.0 (normalized)
            1.0
        """
        return self.embeddings.get(template_id)

    def has_template(self, template_id: str) -> bool:
        """
        Check if template exists in cache.

        Args:
            template_id: Template identifier

        Returns:
            True if template exists in cache

        Example:
            >>> cache.has_template("tmpl_001")
            True
            >>> cache.has_template("nonexistent")
            False
        """
        return template_id in self.embeddings

    def clear(self) -> None:
        """
        Clear all embeddings and metadata from cache.

        Used for testing or cache reset.

        Example:
            >>> cache.clear()
            >>> cache.is_ready
            False
            >>> cache.stats['total_templates']
            0
        """
        self.embeddings.clear()
        self.metadata.clear()
        self.precompute_time = None
        logger.info("Cache cleared")

    def __len__(self) -> int:
        """
        Get number of templates in cache.

        Returns:
            Number of templates

        Example:
            >>> len(cache)
            187
        """
        return len(self.embeddings)

    def __repr__(self) -> str:
        """
        String representation of cache.

        Returns:
            Human-readable cache status

        Example:
            >>> repr(cache)
            'EmbeddingCache(templates=187, categories=6, ready=True)'
        """
        stats = self.stats
        return (
            f"EmbeddingCache("
            f"templates={stats['total_templates']}, "
            f"categories={stats['categories']}, "
            f"ready={self.is_ready})"
        )
