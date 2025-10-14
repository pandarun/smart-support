"""
Unit tests for EmbeddingCache.

Tests:
- add() stores normalized embeddings (L2 norm = 1.0)
- get_by_category() filters correctly
- is_ready property reflects cache state
- stats property returns correct counts
"""

import pytest
import numpy as np

from src.retrieval.cache import EmbeddingCache, TemplateMetadata


class TestTemplateMetadata:
    """Tests for TemplateMetadata dataclass."""

    def test_metadata_initialization(self):
        """Test that metadata initializes correctly."""
        # Act
        metadata = TemplateMetadata(
            template_id="tmpl_001",
            category="Счета и вклады",
            subcategory="Открытие счета",
            question="Как открыть счет?",
            answer="Посетите отделение банка."
        )

        # Assert
        assert metadata.template_id == "tmpl_001"
        assert metadata.category == "Счета и вклады"
        assert metadata.subcategory == "Открытие счета"
        assert metadata.question == "Как открыть счет?"
        assert metadata.answer == "Посетите отделение банка."
        assert metadata.success_rate == 0.5  # Default
        assert metadata.usage_count == 0  # Default

    def test_metadata_with_custom_rates(self):
        """Test metadata with custom success_rate and usage_count."""
        # Act
        metadata = TemplateMetadata(
            template_id="tmpl_001",
            category="Test",
            subcategory="Test",
            question="Q",
            answer="A",
            success_rate=0.85,
            usage_count=42
        )

        # Assert
        assert metadata.success_rate == 0.85
        assert metadata.usage_count == 42


class TestEmbeddingCache:
    """Tests for EmbeddingCache."""

    @pytest.fixture
    def cache(self):
        """Create empty cache for testing."""
        return EmbeddingCache()

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata for testing."""
        return TemplateMetadata(
            template_id="tmpl_001",
            category="Счета и вклады",
            subcategory="Открытие счета",
            question="Как открыть счет?",
            answer="Посетите отделение банка."
        )

    def test_cache_initialization(self, cache):
        """Test that cache initializes empty."""
        # Assert
        assert len(cache) == 0
        assert not cache.is_ready
        assert cache.precompute_time is None

    def test_add_normalizes_embedding(self, cache, sample_metadata):
        """Test that add() normalizes embeddings (L2 norm = 1.0)."""
        # Arrange
        embedding = np.random.randn(1024).astype(np.float32)  # Unnormalized
        original_norm = np.linalg.norm(embedding)

        # Act
        cache.add("tmpl_001", embedding, sample_metadata)

        # Assert
        stored_embedding = cache.get_embedding("tmpl_001")
        stored_norm = np.linalg.norm(stored_embedding)

        # Stored embedding should be normalized
        assert np.isclose(stored_norm, 1.0, atol=0.01)
        # Original embedding should not equal stored (unless it was already normalized)
        if not np.isclose(original_norm, 1.0):
            assert not np.allclose(embedding, stored_embedding)

    def test_add_stores_metadata(self, cache, sample_metadata):
        """Test that add() stores metadata correctly."""
        # Arrange
        embedding = np.ones(1024, dtype=np.float32)

        # Act
        cache.add("tmpl_001", embedding, sample_metadata)

        # Assert
        stored_metadata = cache.get_metadata("tmpl_001")
        assert stored_metadata.template_id == sample_metadata.template_id
        assert stored_metadata.category == sample_metadata.category
        assert stored_metadata.subcategory == sample_metadata.subcategory
        assert stored_metadata.question == sample_metadata.question
        assert stored_metadata.answer == sample_metadata.answer

    def test_add_empty_template_id_raises_error(self, cache, sample_metadata):
        """Test that add() with empty template_id raises ValueError."""
        # Arrange
        embedding = np.ones(1024, dtype=np.float32)

        # Act & Assert
        with pytest.raises(ValueError, match="template_id cannot be empty"):
            cache.add("", embedding, sample_metadata)

        with pytest.raises(ValueError, match="template_id cannot be empty"):
            cache.add("   ", embedding, sample_metadata)

    def test_add_template_id_mismatch_raises_error(self, cache):
        """Test that template_id mismatch raises ValueError."""
        # Arrange
        embedding = np.ones(1024, dtype=np.float32)
        metadata = TemplateMetadata(
            template_id="tmpl_002",  # Different from add() parameter
            category="Test",
            subcategory="Test",
            question="Q",
            answer="A"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="template_id mismatch"):
            cache.add("tmpl_001", embedding, metadata)

    def test_add_invalid_embedding_shape_raises_error(self, cache, sample_metadata):
        """Test that invalid embedding shape raises ValueError."""
        # Arrange
        embedding = np.ones(100, dtype=np.float32)  # Wrong shape

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid embedding shape"):
            cache.add("tmpl_001", embedding, sample_metadata)

    def test_add_zero_norm_embedding_raises_error(self, cache, sample_metadata):
        """Test that zero-norm embedding raises ValueError."""
        # Arrange
        embedding = np.zeros(1024, dtype=np.float32)  # Zero vector

        # Act & Assert
        with pytest.raises(ValueError, match="zero norm"):
            cache.add("tmpl_001", embedding, sample_metadata)

    def test_get_by_category_filters_correctly(self, cache):
        """Test that get_by_category() returns only matching templates."""
        # Arrange - add templates in different categories
        templates_data = [
            ("tmpl_001", "Счета и вклады", "Открытие счета", "Q1", "A1"),
            ("tmpl_002", "Счета и вклады", "Открытие счета", "Q2", "A2"),
            ("tmpl_003", "Счета и вклады", "Процентные ставки", "Q3", "A3"),
            ("tmpl_004", "Кредиты", "Потребительский кредит", "Q4", "A4"),
        ]

        for tid, cat, subcat, q, a in templates_data:
            embedding = np.random.randn(1024).astype(np.float32)
            metadata = TemplateMetadata(
                template_id=tid,
                category=cat,
                subcategory=subcat,
                question=q,
                answer=a
            )
            cache.add(tid, embedding, metadata)

        # Act
        results = cache.get_by_category("Счета и вклады", "Открытие счета")

        # Assert
        assert len(results) == 2  # Only tmpl_001 and tmpl_002
        result_ids = [r[0] for r in results]
        assert "tmpl_001" in result_ids
        assert "tmpl_002" in result_ids

    def test_get_by_category_returns_empty_for_nonexistent(self, cache):
        """Test that get_by_category() returns empty list for nonexistent category."""
        # Arrange - add one template
        cache.add(
            "tmpl_001",
            np.ones(1024, dtype=np.float32),
            TemplateMetadata(
                template_id="tmpl_001",
                category="Счета и вклады",
                subcategory="Открытие счета",
                question="Q",
                answer="A"
            )
        )

        # Act
        results = cache.get_by_category("Несуществующая категория", "Несуществующая подкатегория")

        # Assert
        assert len(results) == 0

    def test_get_by_category_returns_tuples(self, cache, sample_metadata):
        """Test that get_by_category() returns (template_id, embedding, metadata) tuples."""
        # Arrange
        embedding = np.ones(1024, dtype=np.float32)
        cache.add("tmpl_001", embedding, sample_metadata)

        # Act
        results = cache.get_by_category("Счета и вклады", "Открытие счета")

        # Assert
        assert len(results) == 1
        template_id, stored_embedding, stored_metadata = results[0]

        assert template_id == "tmpl_001"
        assert stored_embedding.shape == (1024,)
        assert isinstance(stored_metadata, TemplateMetadata)

    def test_get_all_returns_all_templates(self, cache):
        """Test that get_all() returns all templates."""
        # Arrange
        for i in range(5):
            cache.add(
                f"tmpl_{i:03d}",
                np.random.randn(1024).astype(np.float32),
                TemplateMetadata(
                    template_id=f"tmpl_{i:03d}",
                    category="Test",
                    subcategory="Test",
                    question=f"Q{i}",
                    answer=f"A{i}"
                )
            )

        # Act
        all_templates = cache.get_all()

        # Assert
        assert len(all_templates) == 5

    def test_is_ready_property(self, cache, sample_metadata):
        """Test that is_ready reflects cache state."""
        # Initially not ready
        assert not cache.is_ready

        # After adding one template, becomes ready
        cache.add("tmpl_001", np.ones(1024, dtype=np.float32), sample_metadata)
        assert cache.is_ready

    def test_stats_property(self, cache):
        """Test that stats property returns correct counts."""
        # Arrange - add templates in multiple categories
        templates = [
            ("tmpl_001", "Счета и вклады", "Открытие счета"),
            ("tmpl_002", "Счета и вклады", "Процентные ставки"),
            ("tmpl_003", "Кредиты", "Потребительский кредит"),
            ("tmpl_004", "Кредиты", "Ипотека"),
            ("tmpl_005", "Карты", "Дебетовые карты"),
        ]

        for tid, cat, subcat in templates:
            cache.add(
                tid,
                np.random.randn(1024).astype(np.float32),
                TemplateMetadata(
                    template_id=tid,
                    category=cat,
                    subcategory=subcat,
                    question="Q",
                    answer="A"
                )
            )

        cache.precompute_time = 10.5

        # Act
        stats = cache.stats

        # Assert
        assert stats["total_templates"] == 5
        assert stats["categories"] == 3  # Счета и вклады, Кредиты, Карты
        assert stats["subcategories"] == 5  # All 5 are unique
        assert stats["precompute_time_seconds"] == 10.5
        assert stats["memory_estimate_mb"] > 0

    def test_get_metadata(self, cache, sample_metadata):
        """Test get_metadata() retrieves correct metadata."""
        # Arrange
        cache.add("tmpl_001", np.ones(1024, dtype=np.float32), sample_metadata)

        # Act
        metadata = cache.get_metadata("tmpl_001")

        # Assert
        assert metadata.template_id == "tmpl_001"
        assert metadata.question == sample_metadata.question

    def test_get_metadata_nonexistent_returns_none(self, cache):
        """Test that get_metadata() returns None for nonexistent template."""
        # Act
        metadata = cache.get_metadata("nonexistent")

        # Assert
        assert metadata is None

    def test_get_embedding(self, cache, sample_metadata):
        """Test get_embedding() retrieves correct embedding."""
        # Arrange
        embedding = np.ones(1024, dtype=np.float32)
        cache.add("tmpl_001", embedding, sample_metadata)

        # Act
        stored_embedding = cache.get_embedding("tmpl_001")

        # Assert
        assert stored_embedding.shape == (1024,)
        # Should be normalized
        assert np.isclose(np.linalg.norm(stored_embedding), 1.0, atol=0.01)

    def test_get_embedding_nonexistent_returns_none(self, cache):
        """Test that get_embedding() returns None for nonexistent template."""
        # Act
        embedding = cache.get_embedding("nonexistent")

        # Assert
        assert embedding is None

    def test_has_template(self, cache, sample_metadata):
        """Test has_template() checks existence correctly."""
        # Initially doesn't exist
        assert not cache.has_template("tmpl_001")

        # After adding, exists
        cache.add("tmpl_001", np.ones(1024, dtype=np.float32), sample_metadata)
        assert cache.has_template("tmpl_001")

        # Nonexistent still doesn't exist
        assert not cache.has_template("tmpl_999")

    def test_clear(self, cache, sample_metadata):
        """Test clear() removes all data."""
        # Arrange - add templates
        for i in range(3):
            cache.add(
                f"tmpl_{i:03d}",
                np.ones(1024, dtype=np.float32),
                TemplateMetadata(
                    template_id=f"tmpl_{i:03d}",
                    category="Test",
                    subcategory="Test",
                    question="Q",
                    answer="A"
                )
            )
        cache.precompute_time = 5.0

        # Act
        cache.clear()

        # Assert
        assert len(cache) == 0
        assert not cache.is_ready
        assert cache.precompute_time is None

    def test_len(self, cache):
        """Test __len__() returns correct count."""
        # Initially empty
        assert len(cache) == 0

        # Add 3 templates
        for i in range(3):
            cache.add(
                f"tmpl_{i:03d}",
                np.ones(1024, dtype=np.float32),
                TemplateMetadata(
                    template_id=f"tmpl_{i:03d}",
                    category="Test",
                    subcategory="Test",
                    question="Q",
                    answer="A"
                )
            )

        assert len(cache) == 3

    def test_repr(self, cache):
        """Test __repr__() returns human-readable string."""
        # Arrange - add some templates
        for i in range(5):
            cache.add(
                f"tmpl_{i:03d}",
                np.ones(1024, dtype=np.float32),
                TemplateMetadata(
                    template_id=f"tmpl_{i:03d}",
                    category="Test",
                    subcategory=f"Sub{i % 2}",  # 2 subcategories
                    question="Q",
                    answer="A"
                )
            )

        # Act
        repr_str = repr(cache)

        # Assert
        assert "EmbeddingCache" in repr_str
        assert "templates=5" in repr_str
        assert "categories=1" in repr_str
        assert "ready=True" in repr_str
