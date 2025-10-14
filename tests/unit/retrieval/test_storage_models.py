"""
Unit tests for storage data models (T031).

Tests Pydantic model validation, field constraints, and data validation.
"""

import pytest
import numpy as np
from datetime import datetime
from pydantic import ValidationError

from src.retrieval.storage.models import (
    EmbeddingVersion,
    EmbeddingRecordCreate,
    EmbeddingRecord,
    StorageConfig,
)


class TestEmbeddingVersion:
    """Test EmbeddingVersion model validation."""

    def test_valid_version(self):
        """Test creating valid embedding version."""
        version = EmbeddingVersion(
            model_name="bge-m3",
            model_version="v1",
            embedding_dimension=1024,
        )

        assert version.model_name == "bge-m3"
        assert version.model_version == "v1"
        assert version.embedding_dimension == 1024
        assert version.is_current is True  # Default
        assert version.version_id is None  # Not set yet

    def test_version_with_id(self):
        """Test version with ID (loaded from storage)."""
        version = EmbeddingVersion(
            version_id=1,
            model_name="bge-m3",
            model_version="v1",
            embedding_dimension=1024,
            is_current=True,
            created_at=datetime(2024, 1, 1),
        )

        assert version.version_id == 1
        assert version.created_at == datetime(2024, 1, 1)

    def test_invalid_dimension(self):
        """Test validation rejects invalid dimension."""
        with pytest.raises(ValidationError):
            EmbeddingVersion(
                model_name="bge-m3",
                model_version="v1",
                embedding_dimension=0,  # Must be > 0
            )

        with pytest.raises(ValidationError):
            EmbeddingVersion(
                model_name="bge-m3",
                model_version="v1",
                embedding_dimension=-1,  # Must be > 0
            )

    def test_version_defaults(self):
        """Test default values."""
        version = EmbeddingVersion(
            model_name="bge-m3",
            model_version="v1",
            embedding_dimension=1024,
        )

        assert version.is_current is True
        assert version.version_id is None
        assert version.created_at is None


class TestEmbeddingRecordCreate:
    """Test EmbeddingRecordCreate model validation."""

    def test_valid_record_create(self):
        """Test creating valid embedding record."""
        embedding = np.random.randn(1024).astype(np.float32)

        record = EmbeddingRecordCreate(
            template_id="tmpl_001",
            version_id=1,
            embedding_vector=embedding,
            category="Счета и вклады",
            subcategory="Открытие счета",
            question_text="Как открыть счет?",
            answer_text="Посетите наш сайт.",
            content_hash="a" * 64,
        )

        assert record.template_id == "tmpl_001"
        assert record.version_id == 1
        assert record.embedding_vector.shape == (1024,)
        assert record.success_rate == 0.5  # Default
        assert record.usage_count == 0  # Default

    def test_embedding_vector_validation_correct_shape(self):
        """Test that 1024-dimensional vector is accepted."""
        embedding = np.random.randn(1024).astype(np.float32)

        record = EmbeddingRecordCreate(
            template_id="tmpl_001",
            version_id=1,
            embedding_vector=embedding,
            category="Test",
            subcategory="Test",
            question_text="Question",
            answer_text="Answer",
            content_hash="a" * 64,
        )

        assert record.embedding_vector.shape == (1024,)

    def test_embedding_vector_validation_wrong_dimension(self):
        """Test validation rejects wrong dimension."""
        embedding_wrong = np.random.randn(512).astype(np.float32)

        with pytest.raises(ValidationError, match="1024 dimensions"):
            EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=embedding_wrong,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
            )

    def test_embedding_vector_validation_wrong_ndim(self):
        """Test validation rejects multi-dimensional array."""
        embedding_2d = np.random.randn(32, 32).astype(np.float32)

        with pytest.raises(ValidationError, match="1-dimensional"):
            EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=embedding_2d,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
            )

    def test_embedding_vector_validation_not_numpy(self):
        """Test validation rejects non-numpy array."""
        with pytest.raises(ValidationError, match="instance of ndarray"):
            EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=[0.1] * 1024,  # List, not numpy array
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
            )

    def test_content_hash_validation_correct_length(self):
        """Test that 64-character hash is accepted."""
        embedding = np.random.randn(1024).astype(np.float32)

        record = EmbeddingRecordCreate(
            template_id="tmpl_001",
            version_id=1,
            embedding_vector=embedding,
            category="Test",
            subcategory="Test",
            question_text="Question",
            answer_text="Answer",
            content_hash="a" * 64,  # Exactly 64 characters
        )

        assert len(record.content_hash) == 64

    def test_content_hash_validation_wrong_length(self):
        """Test validation rejects wrong hash length."""
        embedding = np.random.randn(1024).astype(np.float32)

        with pytest.raises(ValidationError):
            EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=embedding,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 32,  # Too short
            )

    def test_success_rate_validation_valid_range(self):
        """Test success rate accepts valid range [0.0, 1.0]."""
        embedding = np.random.randn(1024).astype(np.float32)

        # Test boundary values
        for rate in [0.0, 0.5, 1.0]:
            record = EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=embedding,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
                success_rate=rate,
            )
            assert record.success_rate == rate

    def test_success_rate_validation_out_of_range(self):
        """Test validation rejects success rate outside [0.0, 1.0]."""
        embedding = np.random.randn(1024).astype(np.float32)

        # Test below range
        with pytest.raises(ValidationError):
            EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=embedding,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
                success_rate=-0.1,
            )

        # Test above range
        with pytest.raises(ValidationError):
            EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=embedding,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
                success_rate=1.1,
            )

    def test_usage_count_validation_non_negative(self):
        """Test usage count must be non-negative."""
        embedding = np.random.randn(1024).astype(np.float32)

        # Valid: zero and positive
        for count in [0, 1, 100]:
            record = EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=embedding,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
                usage_count=count,
            )
            assert record.usage_count == count

        # Invalid: negative
        with pytest.raises(ValidationError):
            EmbeddingRecordCreate(
                template_id="tmpl_001",
                version_id=1,
                embedding_vector=embedding,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
                usage_count=-1,
            )

    def test_template_id_validation_non_empty(self):
        """Test template_id must be non-empty."""
        embedding = np.random.randn(1024).astype(np.float32)

        with pytest.raises(ValidationError):
            EmbeddingRecordCreate(
                template_id="",  # Empty string
                version_id=1,
                embedding_vector=embedding,
                category="Test",
                subcategory="Test",
                question_text="Question",
                answer_text="Answer",
                content_hash="a" * 64,
            )


class TestEmbeddingRecord:
    """Test EmbeddingRecord model (includes record_id, timestamps)."""

    def test_valid_record(self):
        """Test creating valid embedding record with all fields."""
        embedding = np.random.randn(1024).astype(np.float32)

        record = EmbeddingRecord(
            record_id=1,
            template_id="tmpl_001",
            version_id=1,
            embedding_vector=embedding,
            category="Test",
            subcategory="Test",
            question_text="Question",
            answer_text="Answer",
            content_hash="a" * 64,
            success_rate=0.75,
            usage_count=10,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 2),
        )

        assert record.record_id == 1
        assert record.created_at == datetime(2024, 1, 1)
        assert record.updated_at == datetime(2024, 1, 2)


class TestStorageConfig:
    """Test StorageConfig model and environment loading."""

    def test_default_sqlite_config(self):
        """Test default SQLite configuration."""
        config = StorageConfig()

        assert config.backend == "sqlite"
        assert config.sqlite_path == "data/embeddings.db"

    def test_postgres_config(self):
        """Test PostgreSQL configuration."""
        config = StorageConfig(
            backend="postgres",
            postgres_host="localhost",
            postgres_port=5432,
            postgres_database="test_db",
            postgres_user="test_user",
            postgres_password="test_pass",
        )

        assert config.backend == "postgres"
        assert config.postgres_host == "localhost"
        assert config.postgres_port == 5432
        assert config.postgres_database == "test_db"

    def test_config_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv("STORAGE_BACKEND", "postgres")
        monkeypatch.setenv("POSTGRES_HOST", "db.example.com")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        monkeypatch.setenv("POSTGRES_DATABASE", "prod_db")
        monkeypatch.setenv("POSTGRES_USER", "prod_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "prod_pass")

        config = StorageConfig.from_env()

        assert config.backend == "postgres"
        assert config.postgres_host == "db.example.com"
        assert config.postgres_port == 5433
        assert config.postgres_database == "prod_db"
        assert config.postgres_user == "prod_user"
        assert config.postgres_password == "prod_pass"

    def test_config_from_env_defaults(self, monkeypatch):
        """Test that from_env() uses defaults when env vars not set."""
        # Clear any existing env vars
        for var in ["STORAGE_BACKEND", "SQLITE_DB_PATH"]:
            monkeypatch.delenv(var, raising=False)

        config = StorageConfig.from_env()

        # Should use defaults
        assert config.backend == "sqlite"
        assert config.sqlite_path == "data/embeddings.db"

    def test_invalid_backend(self):
        """Test validation rejects invalid backend."""
        with pytest.raises(ValidationError):
            StorageConfig(backend="mongodb")  # Not sqlite or postgres
