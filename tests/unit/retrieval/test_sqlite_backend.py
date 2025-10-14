"""
Unit tests for SQLite storage backend (T033).

Tests version management, CRUD operations, serialization/deserialization,
and WAL mode configuration using in-memory SQLite (:memory:).
"""

import pytest
import numpy as np
from pathlib import Path
from datetime import datetime

from src.retrieval.storage.sqlite_backend import SQLiteBackend
from src.retrieval.storage.models import EmbeddingRecordCreate
from src.retrieval.storage.base import (
    ConnectionError,
    IntegrityError,
    NotFoundError,
    SerializationError,
)


@pytest.fixture
def in_memory_backend():
    """Create in-memory SQLite backend for testing."""
    backend = SQLiteBackend(db_path=":memory:")
    backend.connect()
    backend.initialize_schema()
    yield backend
    if backend.is_connected():
        backend.disconnect()


@pytest.fixture
def sample_embedding():
    """Create sample 1024-dimensional embedding."""
    return np.random.randn(1024).astype(np.float32)


@pytest.fixture
def sample_record(sample_embedding):
    """Create sample embedding record."""
    return EmbeddingRecordCreate(
        template_id="tmpl_test_001",
        version_id=1,
        embedding_vector=sample_embedding,
        category="Тест",
        subcategory="Подкатегория",
        question_text="Тестовый вопрос?",
        answer_text="Тестовый ответ.",
        content_hash="a" * 64,
        success_rate=0.5,
        usage_count=0,
    )


class TestConnection:
    """Test connection management."""

    def test_connect_creates_database(self, tmp_path):
        """Test that connect() creates database file."""
        db_path = tmp_path / "test.db"
        backend = SQLiteBackend(db_path=str(db_path))

        assert not db_path.exists()

        backend.connect()

        assert db_path.exists()
        assert backend.is_connected()

        backend.disconnect()

    def test_connect_in_memory(self):
        """Test connecting to in-memory database."""
        backend = SQLiteBackend(db_path=":memory:")
        backend.connect()

        assert backend.is_connected()

        backend.disconnect()

    def test_initialize_schema_creates_tables(self, in_memory_backend):
        """Test that initialize_schema() creates required tables."""
        cursor = in_memory_backend._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "embedding_versions" in tables
        assert "embedding_records" in tables

    def test_wal_mode_enabled(self, tmp_path):
        """Test that WAL mode is enabled."""
        db_path = tmp_path / "test_wal.db"
        backend = SQLiteBackend(db_path=str(db_path))
        backend.connect()
        backend.initialize_schema()

        # Check journal mode
        cursor = backend._conn.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]

        assert journal_mode.lower() == "wal"

        backend.disconnect()

    def test_disconnect_closes_connection(self, in_memory_backend):
        """Test that disconnect() closes connection."""
        assert in_memory_backend.is_connected()

        in_memory_backend.disconnect()

        assert not in_memory_backend.is_connected()

    def test_double_connect_is_safe(self, in_memory_backend):
        """Test that calling connect() twice is safe."""
        assert in_memory_backend.is_connected()

        # Connect again (should be no-op or handle gracefully)
        in_memory_backend.connect()

        assert in_memory_backend.is_connected()

    def test_double_disconnect_is_safe(self, in_memory_backend):
        """Test that calling disconnect() twice is safe."""
        in_memory_backend.disconnect()
        assert not in_memory_backend.is_connected()

        # Disconnect again (should be no-op)
        in_memory_backend.disconnect()

        assert not in_memory_backend.is_connected()


class TestVersionManagement:
    """Test embedding version management."""

    def test_get_or_create_version_creates_new(self, in_memory_backend):
        """Test creating new version."""
        version_id = in_memory_backend.get_or_create_version(
            model_name="bge-m3",
            model_version="v1",
            embedding_dimension=1024,
        )

        assert isinstance(version_id, int)
        assert version_id > 0

    def test_get_or_create_version_returns_existing(self, in_memory_backend):
        """Test that same version returns same ID."""
        version_id1 = in_memory_backend.get_or_create_version(
            model_name="bge-m3",
            model_version="v1",
            embedding_dimension=1024,
        )

        version_id2 = in_memory_backend.get_or_create_version(
            model_name="bge-m3",
            model_version="v1",
            embedding_dimension=1024,
        )

        assert version_id1 == version_id2

    def test_different_versions_get_different_ids(self, in_memory_backend):
        """Test that different versions get different IDs."""
        version_id1 = in_memory_backend.get_or_create_version(
            model_name="bge-m3",
            model_version="v1",
            embedding_dimension=1024,
        )

        version_id2 = in_memory_backend.get_or_create_version(
            model_name="bge-m3",
            model_version="v2",
            embedding_dimension=1024,
        )

        assert version_id1 != version_id2

    def test_get_current_version_returns_latest(self, in_memory_backend):
        """Test getting current version."""
        version_id = in_memory_backend.get_or_create_version(
            model_name="bge-m3",
            model_version="v1",
            embedding_dimension=1024,
        )

        current = in_memory_backend.get_current_version()

        assert current is not None
        assert current.version_id == version_id
        assert current.model_name == "bge-m3"
        assert current.model_version == "v1"
        assert current.embedding_dimension == 1024
        assert current.is_current is True

    def test_set_current_version(self, in_memory_backend):
        """Test setting current version."""
        # Create two versions
        v1_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)
        v2_id = in_memory_backend.get_or_create_version("bge-m3", "v2", 1024)

        # v2 should be current (most recent)
        current = in_memory_backend.get_current_version()
        assert current.version_id == v2_id

        # Set v1 as current
        in_memory_backend.set_current_version(v1_id)

        current = in_memory_backend.get_current_version()
        assert current.version_id == v1_id


class TestEmbeddingSerialization:
    """Test numpy array serialization/deserialization."""

    def test_serialize_embedding(self, in_memory_backend, sample_embedding):
        """Test embedding serialization to BLOB."""
        blob = in_memory_backend._serialize_embedding(sample_embedding)

        assert isinstance(blob, bytes)
        assert len(blob) > 0

    def test_deserialize_embedding(self, in_memory_backend, sample_embedding):
        """Test embedding deserialization from BLOB."""
        # Serialize then deserialize
        blob = in_memory_backend._serialize_embedding(sample_embedding)
        restored = in_memory_backend._deserialize_embedding(blob)

        assert isinstance(restored, np.ndarray)
        assert restored.shape == (1024,)
        assert restored.dtype == np.float32

        # Values should match
        np.testing.assert_array_almost_equal(restored, sample_embedding)

    def test_serialization_round_trip(self, in_memory_backend, sample_embedding):
        """Test complete serialization round trip."""
        blob = in_memory_backend._serialize_embedding(sample_embedding)
        restored = in_memory_backend._deserialize_embedding(blob)

        # Should be identical after round trip
        np.testing.assert_array_equal(restored, sample_embedding)


class TestCRUDOperations:
    """Test CRUD (Create, Read, Update, Delete) operations."""

    def test_store_embedding(self, in_memory_backend, sample_record):
        """Test storing single embedding."""
        record_id = in_memory_backend.store_embedding(sample_record)

        assert isinstance(record_id, int)
        assert record_id > 0

    def test_store_duplicate_template_id_fails(self, in_memory_backend, sample_record):
        """Test that storing duplicate template_id raises error."""
        in_memory_backend.store_embedding(sample_record)

        # Try to store again with same template_id
        with pytest.raises(IntegrityError):
            in_memory_backend.store_embedding(sample_record)

    def test_load_embedding(self, in_memory_backend, sample_record):
        """Test loading embedding by template_id."""
        in_memory_backend.store_embedding(sample_record)

        loaded = in_memory_backend.load_embedding("tmpl_test_001")

        assert loaded is not None
        assert loaded.template_id == "tmpl_test_001"
        assert loaded.category == "Тест"
        assert loaded.subcategory == "Подкатегория"
        assert loaded.question_text == "Тестовый вопрос?"
        assert loaded.embedding_vector.shape == (1024,)

        # Embedding values should match
        np.testing.assert_array_almost_equal(
            loaded.embedding_vector,
            sample_record.embedding_vector
        )

    def test_load_non_existent_embedding(self, in_memory_backend):
        """Test loading non-existent embedding returns None."""
        loaded = in_memory_backend.load_embedding("non_existent")

        assert loaded is None

    def test_load_embeddings_all(self, in_memory_backend, sample_embedding):
        """Test loading all embeddings."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        # Store 3 embeddings
        for i in range(3):
            record = EmbeddingRecordCreate(
                template_id=f"tmpl_{i}",
                version_id=version_id,
                embedding_vector=sample_embedding,
                category="Test",
                subcategory="Sub",
                question_text=f"Question {i}",
                answer_text=f"Answer {i}",
                content_hash="a" * 64,
            )
            in_memory_backend.store_embedding(record)

        # Load all
        all_embeddings = in_memory_backend.load_embeddings_all()

        assert len(all_embeddings) == 3
        assert all(e.version_id == version_id for e in all_embeddings)

    def test_load_embeddings_by_category(self, in_memory_backend, sample_embedding):
        """Test loading embeddings filtered by category."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        # Store embeddings in different categories
        for cat in ["Cat1", "Cat2"]:
            for i in range(2):
                record = EmbeddingRecordCreate(
                    template_id=f"tmpl_{cat}_{i}",
                    version_id=version_id,
                    embedding_vector=sample_embedding,
                    category=cat,
                    subcategory="Sub",
                    question_text=f"Q {cat}",
                    answer_text=f"A {cat}",
                    content_hash="a" * 64,
                )
                in_memory_backend.store_embedding(record)

        # Load only Cat1
        cat1_embeddings = in_memory_backend.load_embeddings_by_category("Cat1")

        assert len(cat1_embeddings) == 2
        assert all(e.category == "Cat1" for e in cat1_embeddings)

    def test_update_embedding(self, in_memory_backend, sample_record):
        """Test updating existing embedding."""
        in_memory_backend.store_embedding(sample_record)

        # Modify record
        new_embedding = np.random.randn(1024).astype(np.float32)
        updated_record = EmbeddingRecordCreate(
            template_id="tmpl_test_001",
            version_id=1,
            embedding_vector=new_embedding,
            category="Updated Category",
            subcategory="Updated Sub",
            question_text="Updated question?",
            answer_text="Updated answer.",
            content_hash="b" * 64,  # New hash
            success_rate=0.8,
            usage_count=5,
        )

        success = in_memory_backend.update_embedding("tmpl_test_001", updated_record)

        assert success is True

        # Load and verify
        loaded = in_memory_backend.load_embedding("tmpl_test_001")
        assert loaded.category == "Updated Category"
        assert loaded.content_hash == "b" * 64
        assert loaded.success_rate == 0.8
        np.testing.assert_array_almost_equal(loaded.embedding_vector, new_embedding)

    def test_update_non_existent_embedding(self, in_memory_backend, sample_record):
        """Test updating non-existent embedding returns False."""
        success = in_memory_backend.update_embedding("non_existent", sample_record)

        assert success is False

    def test_delete_embedding(self, in_memory_backend, sample_record):
        """Test deleting embedding."""
        in_memory_backend.store_embedding(sample_record)

        success = in_memory_backend.delete_embedding("tmpl_test_001")

        assert success is True

        # Verify deleted
        loaded = in_memory_backend.load_embedding("tmpl_test_001")
        assert loaded is None

    def test_delete_non_existent_embedding(self, in_memory_backend):
        """Test deleting non-existent embedding returns False."""
        success = in_memory_backend.delete_embedding("non_existent")

        assert success is False


class TestBatchOperations:
    """Test batch storage operations."""

    def test_store_embeddings_batch(self, in_memory_backend, sample_embedding):
        """Test batch storing embeddings."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        records = []
        for i in range(10):
            record = EmbeddingRecordCreate(
                template_id=f"tmpl_batch_{i}",
                version_id=version_id,
                embedding_vector=sample_embedding,
                category="Batch",
                subcategory="Sub",
                question_text=f"Question {i}",
                answer_text=f"Answer {i}",
                content_hash="a" * 64,
            )
            records.append(record)

        record_ids = in_memory_backend.store_embeddings_batch(records)

        assert len(record_ids) == 10
        assert all(isinstance(rid, int) for rid in record_ids)

        # Verify all stored
        count = in_memory_backend.count()
        assert count == 10


class TestUtilityMethods:
    """Test utility methods."""

    def test_exists(self, in_memory_backend, sample_record):
        """Test checking if template exists."""
        assert in_memory_backend.exists("tmpl_test_001") is False

        in_memory_backend.store_embedding(sample_record)

        assert in_memory_backend.exists("tmpl_test_001") is True

    def test_count(self, in_memory_backend, sample_embedding):
        """Test counting embeddings."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        assert in_memory_backend.count() == 0

        # Store 5 embeddings
        for i in range(5):
            record = EmbeddingRecordCreate(
                template_id=f"tmpl_{i}",
                version_id=version_id,
                embedding_vector=sample_embedding,
                category="Test",
                subcategory="Sub",
                question_text=f"Q{i}",
                answer_text=f"A{i}",
                content_hash="a" * 64,
            )
            in_memory_backend.store_embedding(record)

        assert in_memory_backend.count() == 5

    def test_get_all_template_ids(self, in_memory_backend, sample_embedding):
        """Test getting all template IDs."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        expected_ids = []
        for i in range(3):
            template_id = f"tmpl_{i}"
            expected_ids.append(template_id)

            record = EmbeddingRecordCreate(
                template_id=template_id,
                version_id=version_id,
                embedding_vector=sample_embedding,
                category="Test",
                subcategory="Sub",
                question_text=f"Q{i}",
                answer_text=f"A{i}",
                content_hash="a" * 64,
            )
            in_memory_backend.store_embedding(record)

        template_ids = in_memory_backend.get_all_template_ids()

        assert set(template_ids) == set(expected_ids)

    def test_get_content_hashes(self, in_memory_backend, sample_embedding):
        """Test getting content hashes mapping."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        # Store with specific hashes
        hashes = {"tmpl_0": "a" * 64, "tmpl_1": "b" * 64}

        for template_id, content_hash in hashes.items():
            record = EmbeddingRecordCreate(
                template_id=template_id,
                version_id=version_id,
                embedding_vector=sample_embedding,
                category="Test",
                subcategory="Sub",
                question_text="Q",
                answer_text="A",
                content_hash=content_hash,
            )
            in_memory_backend.store_embedding(record)

        stored_hashes = in_memory_backend.get_content_hashes()

        assert stored_hashes == hashes

    def test_validate_integrity(self, in_memory_backend):
        """Test storage integrity validation."""
        integrity = in_memory_backend.validate_integrity()

        assert isinstance(integrity, dict)
        assert "valid" in integrity
        assert integrity["valid"] is True

    def test_get_storage_info(self, in_memory_backend, sample_embedding):
        """Test getting storage information."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        # Store some embeddings
        for i in range(3):
            record = EmbeddingRecordCreate(
                template_id=f"tmpl_{i}",
                version_id=version_id,
                embedding_vector=sample_embedding,
                category="Test",
                subcategory="Sub",
                question_text=f"Q{i}",
                answer_text=f"A{i}",
                content_hash="a" * 64,
            )
            in_memory_backend.store_embedding(record)

        info = in_memory_backend.get_storage_info()

        assert isinstance(info, dict)
        assert info["backend"] == "sqlite"
        assert info["total_embeddings"] == 3
        assert "current_version" in info


class TestTransactions:
    """Test transaction support."""

    def test_transaction_commits_on_success(self, in_memory_backend, sample_embedding):
        """Test that transaction commits changes on success."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        with in_memory_backend.transaction():
            record = EmbeddingRecordCreate(
                template_id="tmpl_tx_001",
                version_id=version_id,
                embedding_vector=sample_embedding,
                category="Test",
                subcategory="Sub",
                question_text="Q",
                answer_text="A",
                content_hash="a" * 64,
            )
            in_memory_backend.store_embedding(record)

        # Verify committed
        assert in_memory_backend.exists("tmpl_tx_001") is True

    def test_transaction_rolls_back_on_error(self, in_memory_backend, sample_embedding):
        """Test that transaction rolls back changes on error."""
        version_id = in_memory_backend.get_or_create_version("bge-m3", "v1", 1024)

        with pytest.raises(ValueError):
            with in_memory_backend.transaction():
                record = EmbeddingRecordCreate(
                    template_id="tmpl_tx_002",
                    version_id=version_id,
                    embedding_vector=sample_embedding,
                    category="Test",
                    subcategory="Sub",
                    question_text="Q",
                    answer_text="A",
                    content_hash="a" * 64,
                )
                in_memory_backend.store_embedding(record)

                # Raise error to trigger rollback
                raise ValueError("Test error")

        # Verify rolled back
        assert in_memory_backend.exists("tmpl_tx_002") is False
