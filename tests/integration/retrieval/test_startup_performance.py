"""
Integration tests for system startup performance (T037).

Tests that loading 201 embeddings from storage reduces startup time
from ~9 seconds (in-memory precomputation) to <2 seconds (storage load).

This is the key performance requirement for User Story 1.
"""

import pytest
import time
import tempfile
import numpy as np
from pathlib import Path

from src.retrieval.storage.sqlite_backend import SQLiteBackend
from src.retrieval.storage.models import EmbeddingRecordCreate, StorageConfig
from src.retrieval.storage import create_storage_backend
from src.retrieval.cache import EmbeddingCache
from src.utils.hashing import compute_content_hash


@pytest.fixture
def prepopulated_db(tmp_path):
    """Create database pre-populated with 201 embeddings."""
    db_path = tmp_path / "embeddings.db"

    backend = SQLiteBackend(db_path=str(db_path))
    backend.connect()
    backend.initialize_schema()

    version_id = backend.get_or_create_version("bge-m3", "v1", 1024)

    # Create 201 realistic embeddings
    records = []
    for i in range(201):
        # Use deterministic seed for reproducible embeddings
        rng = np.random.RandomState(i)
        embedding = rng.randn(1024).astype(np.float32)

        question = f"Как получить информацию о {i}?"
        answer = f"Для получения информации о {i} обратитесь в поддержку."

        record = EmbeddingRecordCreate(
            template_id=f"tmpl_{i:03d}",
            version_id=version_id,
            embedding_vector=embedding,
            category=f"Категория {i % 6}",
            subcategory=f"Подкатегория {i % 35}",
            question_text=question,
            answer_text=answer,
            content_hash=compute_content_hash(question, answer),
            success_rate=0.5,
            usage_count=0,
        )
        records.append(record)

    # Store in batches
    backend.store_embeddings_batch(records, batch_size=20)

    backend.disconnect()

    return str(db_path)


class TestStartupPerformance:
    """Test system startup time with persistent storage."""

    def test_cache_load_from_storage_under_2_seconds(self, prepopulated_db):
        """
        Test that loading cache from storage takes < 2 seconds.

        This is the core requirement for User Story 1:
        - Baseline: ~9 seconds (precompute 201 embeddings from API)
        - Target: <2 seconds (load from storage)
        - Improvement: ~78% faster startup
        """
        # Create storage backend
        backend = SQLiteBackend(db_path=prepopulated_db)
        backend.connect()

        # Measure cache initialization time (loads from storage)
        start_time = time.time()

        cache = EmbeddingCache(storage_backend=backend)

        load_time = time.time() - start_time

        # Verify all embeddings loaded
        assert cache.is_ready
        assert len(cache) == 201

        # Performance requirement: <2 seconds
        assert load_time < 2.0, (
            f"Cache load took {load_time:.2f}s (target <2.0s). "
            f"Baseline in-memory precomputation: ~9s. "
            f"Expected improvement: ~78% faster."
        )

        # Log actual time for monitoring
        print(f"\n✓ Cache loaded in {load_time:.3f}s (target <2.0s)")
        print(f"  Speedup vs baseline (~9s): {9.0/load_time:.1f}x faster")

        backend.disconnect()

    def test_cache_statistics_after_load(self, prepopulated_db):
        """Test that cache statistics are correct after loading."""
        backend = SQLiteBackend(db_path=prepopulated_db)
        backend.connect()

        cache = EmbeddingCache(storage_backend=backend)

        stats = cache.stats

        # Verify statistics
        assert stats["total_templates"] == 201
        assert stats["categories"] == 6
        assert stats["subcategories"] == 35
        assert stats["memory_estimate_mb"] > 0

        backend.disconnect()

    def test_embeddings_are_normalized(self, prepopulated_db):
        """Test that loaded embeddings are properly normalized."""
        backend = SQLiteBackend(db_path=prepopulated_db)
        backend.connect()

        cache = EmbeddingCache(storage_backend=backend)

        # Check normalization of random samples
        for template_id in ["tmpl_000", "tmpl_050", "tmpl_100", "tmpl_150", "tmpl_200"]:
            embedding = cache.get_embedding(template_id)
            assert embedding is not None

            # L2 norm should be ~1.0 (normalized)
            norm = np.linalg.norm(embedding)
            assert 0.99 < norm < 1.01, f"Embedding {template_id} not normalized: norm={norm}"

        backend.disconnect()

    def test_comparison_with_empty_cache(self, prepopulated_db):
        """Compare startup time: storage vs empty cache."""
        # Time 1: Storage load
        backend = SQLiteBackend(db_path=prepopulated_db)
        backend.connect()

        start_storage = time.time()
        cache_with_storage = EmbeddingCache(storage_backend=backend)
        time_storage = time.time() - start_storage

        # Time 2: Empty cache
        start_empty = time.time()
        cache_empty = EmbeddingCache()
        time_empty = time.time() - start_empty

        # Storage load should be slower than empty cache initialization
        # but MUCH faster than precomputation (~9s)
        assert time_storage < 2.0, f"Storage load took {time_storage:.2f}s (target <2s)"
        assert time_empty < 0.001, f"Empty cache init took {time_empty:.3f}s (should be instant)"

        # Verify loaded vs empty
        assert len(cache_with_storage) == 201
        assert len(cache_empty) == 0

        backend.disconnect()


class TestColdStartScenario:
    """Test cold start scenario (first app launch after deployment)."""

    def test_cold_start_full_workflow(self, tmp_path):
        """
        Simulate cold start: fresh database, populate, disconnect, reconnect, load.

        This simulates the real deployment workflow:
        1. Run migration CLI to populate storage
        2. Deploy application
        3. Application starts and loads from storage
        """
        db_path = tmp_path / "cold_start.db"

        # Step 1: Initial population (simulates migration CLI)
        backend = SQLiteBackend(db_path=str(db_path))
        backend.connect()
        backend.initialize_schema()

        version_id = backend.get_or_create_version("bge-m3", "v1", 1024)

        # Populate 201 embeddings
        records = []
        for i in range(201):
            rng = np.random.RandomState(i)
            embedding = rng.randn(1024).astype(np.float32)

            record = EmbeddingRecordCreate(
                template_id=f"tmpl_{i:03d}",
                version_id=version_id,
                embedding_vector=embedding,
                category="Test",
                subcategory="Sub",
                question_text=f"Q{i}",
                answer_text=f"A{i}",
                content_hash="a" * 64,
            )
            records.append(record)

        backend.store_embeddings_batch(records)
        backend.disconnect()

        # Step 2: Cold start (new connection, load from storage)
        backend2 = SQLiteBackend(db_path=str(db_path))
        backend2.connect()

        start_time = time.time()
        cache = EmbeddingCache(storage_backend=backend2)
        cold_start_time = time.time() - start_time

        # Verify cold start performance
        assert cold_start_time < 2.0, (
            f"Cold start took {cold_start_time:.2f}s (target <2.0s)"
        )

        # Verify data integrity
        assert len(cache) == 201
        assert cache.is_ready

        print(f"\n✓ Cold start completed in {cold_start_time:.3f}s")

        backend2.disconnect()


class TestGracefulFallback:
    """Test graceful fallback when storage unavailable."""

    def test_fallback_to_empty_cache_on_load_failure(self):
        """Test that cache falls back to empty if storage load fails."""
        # Create backend with non-existent database
        backend = SQLiteBackend(db_path="/nonexistent/path/db.sqlite")

        # Cache should handle connection failure gracefully
        # (backend is not connected, so load should fail silently)
        cache = EmbeddingCache(storage_backend=backend)

        # Should fall back to empty cache
        assert not cache.is_ready
        assert len(cache) == 0

    def test_cache_works_without_storage(self):
        """Test that cache still works without storage backend (backward compatibility)."""
        # Create cache without storage (original behavior)
        start_time = time.time()
        cache = EmbeddingCache()
        init_time = time.time() - start_time

        # Should initialize instantly
        assert init_time < 0.001

        # Should be empty but functional
        assert not cache.is_ready
        assert len(cache) == 0

        # Can still add embeddings manually
        from src.retrieval.cache import TemplateMetadata

        embedding = np.random.randn(1024).astype(np.float32)
        metadata = TemplateMetadata(
            template_id="test",
            category="Cat",
            subcategory="Sub",
            question="Q",
            answer="A",
        )

        cache.add("test", embedding, metadata)

        assert cache.is_ready
        assert len(cache) == 1


class TestPerformanceBenchmark:
    """Benchmark startup performance for reporting."""

    def test_benchmark_201_embeddings_load_time(self, prepopulated_db):
        """
        Benchmark load time for 201 embeddings.

        Reports:
        - Min/max/mean load time over 5 runs
        - Comparison to 9-second baseline
        """
        backend = SQLiteBackend(db_path=prepopulated_db)
        backend.connect()

        times = []

        # Run 5 times to get stable measurement
        for i in range(5):
            start = time.time()
            cache = EmbeddingCache(storage_backend=backend)
            load_time = time.time() - start

            times.append(load_time)

            # Verify correctness
            assert len(cache) == 201

        # Calculate statistics
        min_time = min(times)
        max_time = max(times)
        mean_time = sum(times) / len(times)

        # All runs should be under 2 seconds
        assert max_time < 2.0, f"Max load time {max_time:.2f}s exceeds 2s target"

        # Report
        print(f"\n" + "="*60)
        print(f"Startup Performance Benchmark (201 embeddings)")
        print(f"="*60)
        print(f"Min:  {min_time:.3f}s")
        print(f"Max:  {max_time:.3f}s")
        print(f"Mean: {mean_time:.3f}s")
        print(f"\nBaseline (in-memory precomputation): ~9.0s")
        print(f"Improvement: {((9.0 - mean_time) / 9.0 * 100):.1f}% faster")
        print(f"Speedup: {9.0 / mean_time:.1f}x")
        print(f"="*60)

        backend.disconnect()

    def test_memory_usage_after_load(self, prepopulated_db):
        """Test memory usage estimate after loading 201 embeddings."""
        backend = SQLiteBackend(db_path=prepopulated_db)
        backend.connect()

        cache = EmbeddingCache(storage_backend=backend)

        stats = cache.stats

        # Memory estimate should be reasonable
        memory_mb = stats["memory_estimate_mb"]

        # Expected: ~1-2 MB for 201 templates
        # (201 * 1024 * 4 bytes + metadata ≈ 800KB + 200KB)
        assert 0.5 < memory_mb < 5.0, (
            f"Memory estimate {memory_mb:.2f}MB outside expected range (0.5-5.0 MB)"
        )

        print(f"\nMemory usage: {memory_mb:.2f} MB for 201 templates")

        backend.disconnect()


class TestMultipleStartups:
    """Test performance across multiple startup cycles."""

    def test_consistent_performance_across_restarts(self, prepopulated_db):
        """Test that startup performance is consistent across multiple restarts."""
        times = []

        for i in range(3):
            # Fresh connection each time
            backend = SQLiteBackend(db_path=prepopulated_db)
            backend.connect()

            start = time.time()
            cache = EmbeddingCache(storage_backend=backend)
            load_time = time.time() - start

            times.append(load_time)

            # Verify correctness
            assert len(cache) == 201

            backend.disconnect()

        # All times should be under 2 seconds
        assert all(t < 2.0 for t in times), f"Some load times exceeded 2s: {times}"

        # Times should be relatively consistent (variance < 0.5s)
        time_range = max(times) - min(times)
        assert time_range < 0.5, (
            f"Load time variance too high: {time_range:.2f}s (range: {min(times):.2f}-{max(times):.2f}s)"
        )

        print(f"\nLoad times across 3 restarts: {[f'{t:.3f}s' for t in times]}")
        print(f"Variance: {time_range:.3f}s (target <0.5s)")
