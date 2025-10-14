"""
Integration tests for SQLite storage backend (T035).

Tests full CRUD lifecycle with 201 templates, load time performance,
concurrent reads, and cleanup using temporary database files.
"""

import pytest
import time
import tempfile
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.retrieval.storage.sqlite_backend import SQLiteBackend
from src.retrieval.storage.models import EmbeddingRecordCreate
from src.utils.hashing import compute_content_hash


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    db_path = tmp_path / "test_embeddings.db"
    yield str(db_path)
    # Cleanup (pytest tmp_path is automatically cleaned)


@pytest.fixture
def populated_backend(temp_db_path):
    """Create backend pre-populated with 201 embeddings."""
    backend = SQLiteBackend(db_path=temp_db_path)
    backend.connect()
    backend.initialize_schema()

    version_id = backend.get_or_create_version("bge-m3", "v1", 1024)

    # Generate 201 realistic template embeddings
    records = []
    for i in range(201):
        embedding = np.random.randn(1024).astype(np.float32)
        question = f"Тестовый вопрос {i}?"
        answer = f"Тестовый ответ {i}."

        record = EmbeddingRecordCreate(
            template_id=f"tmpl_{i:03d}",
            version_id=version_id,
            embedding_vector=embedding,
            category=f"Категория {i % 6}",  # 6 categories (like real FAQ)
            subcategory=f"Подкатегория {i % 35}",  # 35 subcategories
            question_text=question,
            answer_text=answer,
            content_hash=compute_content_hash(question, answer),
            success_rate=0.5,
            usage_count=0,
        )
        records.append(record)

    # Store in batches
    backend.store_embeddings_batch(records, batch_size=20)

    yield backend

    backend.disconnect()


class TestFullCRUDLifecycle:
    """Test complete CRUD lifecycle with 201 templates."""

    def test_create_201_embeddings(self, temp_db_path):
        """Test creating 201 embeddings from scratch."""
        backend = SQLiteBackend(db_path=temp_db_path)
        backend.connect()
        backend.initialize_schema()

        version_id = backend.get_or_create_version("bge-m3", "v1", 1024)

        # Create 201 embeddings
        start_time = time.time()

        for i in range(201):
            embedding = np.random.randn(1024).astype(np.float32)
            record = EmbeddingRecordCreate(
                template_id=f"tmpl_{i:03d}",
                version_id=version_id,
                embedding_vector=embedding,
                category="Test",
                subcategory="Sub",
                question_text=f"Question {i}",
                answer_text=f"Answer {i}",
                content_hash="a" * 64,
            )
            backend.store_embedding(record)

        create_time = time.time() - start_time

        # Verify count
        count = backend.count()
        assert count == 201

        # Performance check (should be reasonably fast)
        assert create_time < 10.0, f"Creating 201 embeddings took {create_time:.2f}s (expected <10s)"

        backend.disconnect()

    def test_read_all_201_embeddings(self, populated_backend):
        """Test loading all 201 embeddings."""
        start_time = time.time()

        embeddings = populated_backend.load_embeddings_all()

        load_time = time.time() - start_time

        # Verify all loaded
        assert len(embeddings) == 201

        # Performance check: <50ms target
        assert load_time < 0.050, f"Loading 201 embeddings took {load_time*1000:.1f}ms (target <50ms)"

        # Verify data integrity
        for emb in embeddings:
            assert emb.embedding_vector.shape == (1024,)
            assert len(emb.content_hash) == 64
            assert emb.template_id.startswith("tmpl_")

    def test_update_subset_of_embeddings(self, populated_backend):
        """Test updating 10 random embeddings."""
        # Pick 10 random templates to update
        update_ids = [f"tmpl_{i:03d}" for i in [5, 15, 25, 50, 100, 120, 150, 175, 190, 200]]

        for template_id in update_ids:
            # Load current
            current = populated_backend.load_embedding(template_id)
            assert current is not None

            # Create updated record
            new_embedding = np.random.randn(1024).astype(np.float32)
            updated_record = EmbeddingRecordCreate(
                template_id=template_id,
                version_id=current.version_id,
                embedding_vector=new_embedding,
                category="Updated",
                subcategory="Updated Sub",
                question_text="Updated question",
                answer_text="Updated answer",
                content_hash="b" * 64,
                success_rate=0.8,
                usage_count=10,
            )

            # Update
            success = populated_backend.update_embedding(template_id, updated_record)
            assert success is True

        # Verify updates
        for template_id in update_ids:
            loaded = populated_backend.load_embedding(template_id)
            assert loaded.category == "Updated"
            assert loaded.content_hash == "b" * 64
            assert loaded.success_rate == 0.8

        # Verify count unchanged
        assert populated_backend.count() == 201

    def test_delete_subset_of_embeddings(self, populated_backend):
        """Test deleting 10 embeddings."""
        # Delete 10 templates
        delete_ids = [f"tmpl_{i:03d}" for i in range(10)]

        for template_id in delete_ids:
            success = populated_backend.delete_embedding(template_id)
            assert success is True

        # Verify deletions
        for template_id in delete_ids:
            loaded = populated_backend.load_embedding(template_id)
            assert loaded is None

        # Verify count
        assert populated_backend.count() == 191  # 201 - 10

        # Verify other templates unaffected
        other = populated_backend.load_embedding("tmpl_050")
        assert other is not None


class TestLoadPerformance:
    """Test load time performance."""

    def test_cold_start_load_time(self, temp_db_path):
        """Test loading embeddings on cold start (first connection)."""
        # Create and populate database
        backend = SQLiteBackend(db_path=temp_db_path)
        backend.connect()
        backend.initialize_schema()

        version_id = backend.get_or_create_version("bge-m3", "v1", 1024)

        # Store 201 embeddings
        records = []
        for i in range(201):
            embedding = np.random.randn(1024).astype(np.float32)
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

        # Cold start: reconnect and measure load time
        backend = SQLiteBackend(db_path=temp_db_path)
        backend.connect()

        start_time = time.time()
        embeddings = backend.load_embeddings_all()
        load_time = time.time() - start_time

        assert len(embeddings) == 201

        # Performance requirement: <50ms
        assert load_time < 0.050, (
            f"Cold start load took {load_time*1000:.1f}ms (target <50ms). "
            f"Consider optimizing schema indexes or query."
        )

        backend.disconnect()

    def test_warm_load_time(self, populated_backend):
        """Test loading embeddings when connection is warm."""
        # First load (cache warming)
        _ = populated_backend.load_embeddings_all()

        # Measure second load (should be faster due to caching)
        start_time = time.time()
        embeddings = populated_backend.load_embeddings_all()
        load_time = time.time() - start_time

        assert len(embeddings) == 201

        # Should be very fast on warm connection
        assert load_time < 0.030, f"Warm load took {load_time*1000:.1f}ms (expected <30ms)"

    def test_category_filter_performance(self, populated_backend):
        """Test performance of category-filtered queries."""
        start_time = time.time()

        # Load single category
        category_embeddings = populated_backend.load_embeddings_by_category(
            category="Категория 0",
            subcategory="Подкатегория 0"
        )

        query_time = time.time() - start_time

        # Should be fast (filtered query)
        assert query_time < 0.020, f"Category query took {query_time*1000:.1f}ms (expected <20ms)"

        # Should return subset of templates
        assert len(category_embeddings) > 0
        assert len(category_embeddings) < 201


class TestConcurrentReads:
    """Test concurrent read operations."""

    def test_concurrent_load_all(self, populated_backend):
        """Test multiple threads loading all embeddings concurrently."""
        num_threads = 5

        def load_all():
            embeddings = populated_backend.load_embeddings_all()
            return len(embeddings)

        # Execute concurrent loads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(load_all) for _ in range(num_threads)]

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # All threads should get 201 embeddings
        assert all(count == 201 for count in results)
        assert len(results) == num_threads

    def test_concurrent_mixed_operations(self, populated_backend):
        """Test concurrent mix of reads (no writes to avoid conflicts)."""
        def load_all():
            return len(populated_backend.load_embeddings_all())

        def load_one(template_id):
            emb = populated_backend.load_embedding(template_id)
            return emb is not None

        def count_embeddings():
            return populated_backend.count()

        # Mix of operations
        tasks = [
            (load_all, ()),
            (load_one, ("tmpl_050",)),
            (count_embeddings, ()),
            (load_all, ()),
            (load_one, ("tmpl_100",)),
        ]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(func, *args) for func, args in tasks]

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # All operations should succeed
        assert len(results) == 5

    def test_read_while_connected(self, populated_backend):
        """Test that reads work correctly while connection is active."""
        # Perform multiple sequential reads
        for i in range(10):
            template_id = f"tmpl_{i*20:03d}"
            emb = populated_backend.load_embedding(template_id)
            assert emb is not None
            assert emb.template_id == template_id


class TestDatabasePersistence:
    """Test that data persists across connections."""

    def test_data_persists_after_disconnect(self, temp_db_path):
        """Test that data remains after disconnect/reconnect."""
        # First connection: store data
        backend1 = SQLiteBackend(db_path=temp_db_path)
        backend1.connect()
        backend1.initialize_schema()

        version_id = backend1.get_or_create_version("bge-m3", "v1", 1024)

        embedding = np.random.randn(1024).astype(np.float32)
        record = EmbeddingRecordCreate(
            template_id="tmpl_persist",
            version_id=version_id,
            embedding_vector=embedding,
            category="Test",
            subcategory="Sub",
            question_text="Persistent question",
            answer_text="Persistent answer",
            content_hash="a" * 64,
        )
        backend1.store_embedding(record)
        backend1.disconnect()

        # Second connection: verify data exists
        backend2 = SQLiteBackend(db_path=temp_db_path)
        backend2.connect()

        loaded = backend2.load_embedding("tmpl_persist")

        assert loaded is not None
        assert loaded.question_text == "Persistent question"
        assert loaded.embedding_vector.shape == (1024,)

        # Embedding values should match
        np.testing.assert_array_almost_equal(loaded.embedding_vector, embedding)

        backend2.disconnect()

    def test_database_file_exists(self, temp_db_path):
        """Test that database file is created and persists."""
        db_file = Path(temp_db_path)
        assert not db_file.exists()

        # Create database
        backend = SQLiteBackend(db_path=temp_db_path)
        backend.connect()
        backend.initialize_schema()

        # File should exist
        assert db_file.exists()
        assert db_file.stat().st_size > 0

        backend.disconnect()

        # File should still exist after disconnect
        assert db_file.exists()


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_invalid_database_path(self):
        """Test handling of invalid database path."""
        # Path that cannot be created
        invalid_path = "/invalid/nonexistent/path/test.db"

        backend = SQLiteBackend(db_path=invalid_path)

        with pytest.raises(Exception):  # ConnectionError or OSError
            backend.connect()

    def test_corrupted_database_recovery(self, temp_db_path):
        """Test behavior with corrupted database file."""
        # Create database
        backend = SQLiteBackend(db_path=temp_db_path)
        backend.connect()
        backend.initialize_schema()
        backend.disconnect()

        # Corrupt the database file (write garbage)
        with open(temp_db_path, 'wb') as f:
            f.write(b'CORRUPTED DATA\x00\x00\x00')

        # Try to connect to corrupted database
        backend2 = SQLiteBackend(db_path=temp_db_path)

        with pytest.raises(Exception):  # Should fail to connect/initialize
            backend2.connect()
            backend2.load_embeddings_all()


class TestStorageInfo:
    """Test storage information reporting."""

    def test_storage_info_with_201_embeddings(self, populated_backend):
        """Test get_storage_info() with full dataset."""
        info = populated_backend.get_storage_info()

        assert info["backend"] == "sqlite"
        assert info["total_embeddings"] == 201
        assert "database_path" in info
        assert "database_size_bytes" in info
        assert "current_version" in info

        # Database size should be reasonable (< 10MB for 201 embeddings)
        db_size_mb = info["database_size_bytes"] / (1024 * 1024)
        assert db_size_mb < 10.0, f"Database size {db_size_mb:.2f}MB is too large"

    def test_validate_integrity_after_full_lifecycle(self, populated_backend):
        """Test integrity validation after CRUD operations."""
        # Perform various operations
        populated_backend.update_embedding(
            "tmpl_000",
            EmbeddingRecordCreate(
                template_id="tmpl_000",
                version_id=1,
                embedding_vector=np.random.randn(1024).astype(np.float32),
                category="Updated",
                subcategory="Updated",
                question_text="Updated",
                answer_text="Updated",
                content_hash="b" * 64,
            )
        )

        populated_backend.delete_embedding("tmpl_001")

        # Validate integrity
        integrity = populated_backend.validate_integrity()

        assert integrity["valid"] is True
        assert integrity["total_records"] == 200  # 201 - 1 deleted
        assert "errors" not in integrity or len(integrity["errors"]) == 0
