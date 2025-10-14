"""
Abstract storage backend interface for embedding persistence.

This module defines the contract that all storage backends must implement,
along with a custom exception hierarchy for storage operations.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

from .models import EmbeddingRecordCreate, EmbeddingRecord, EmbeddingVersion


# ============================================================================
# Exception Hierarchy
# ============================================================================

class StorageError(Exception):
    """Base exception for all storage operations."""
    pass


class ConnectionError(StorageError):
    """Failed to connect to storage backend or connection lost."""
    pass


class IntegrityError(StorageError):
    """Data integrity violation (unique constraint, foreign key, validation)."""
    pass


class NotFoundError(StorageError):
    """Requested resource not found in storage."""
    pass


class SerializationError(StorageError):
    """Failed to serialize or deserialize embedding vector."""
    pass


class ValidationError(StorageError):
    """Data validation failed (invalid format, out of range, etc.)."""
    pass


# ============================================================================
# Abstract Storage Backend
# ============================================================================

class StorageBackend(ABC):
    """
    Abstract base class for embedding storage backends.

    All storage implementations (SQLite, PostgreSQL) must inherit from this
    class and implement all abstract methods. This ensures consistent interface
    regardless of backend technology.

    Implementations:
    - SQLiteBackend: File-based storage with BLOB vectors
    - PostgresBackend: Server-based storage with pg_vector extension

    Usage:
        >>> config = StorageConfig(backend="sqlite", sqlite_path="data/embeddings.db")
        >>> storage = create_storage_backend(config)
        >>> storage.connect()
        >>> storage.initialize_schema()
        >>> # ... use storage ...
        >>> storage.disconnect()

    Context manager usage:
        >>> with create_storage_backend(config) as storage:
        ...     storage.initialize_schema()
        ...     records = storage.load_embeddings_all()
    """

    # ========================================================================
    # Connection Management
    # ========================================================================

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to storage backend.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection and cleanup resources."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if storage backend is connected.

        Returns:
            True if connected and ready for operations, False otherwise
        """
        pass

    # ========================================================================
    # Schema Management
    # ========================================================================

    @abstractmethod
    def initialize_schema(self) -> None:
        """
        Create tables and indexes if they don't exist.

        This method is idempotent - safe to call multiple times.

        Raises:
            ConnectionError: If not connected
            IntegrityError: If schema creation fails
        """
        pass

    # ========================================================================
    # Version Management
    # ========================================================================

    @abstractmethod
    def get_or_create_version(
        self,
        model_name: str,
        model_version: str,
        embedding_dimension: int
    ) -> int:
        """
        Get existing version ID or create new version entry.

        Args:
            model_name: Model identifier (e.g., "bge-m3")
            model_version: Model version string (e.g., "v1")
            embedding_dimension: Vector dimensionality (e.g., 1024)

        Returns:
            version_id for the specified model configuration

        Raises:
            IntegrityError: If version data is invalid
            ConnectionError: If not connected
        """
        pass

    @abstractmethod
    def get_current_version(self) -> Optional[EmbeddingVersion]:
        """
        Get currently active embedding version.

        Returns:
            EmbeddingVersion instance if exists, None if no versions

        Raises:
            ConnectionError: If not connected
        """
        pass

    @abstractmethod
    def set_current_version(self, version_id: int) -> None:
        """
        Mark a version as current (only one version can be current).

        Args:
            version_id: Version to mark as current

        Raises:
            NotFoundError: If version_id doesn't exist
            IntegrityError: If transaction fails
            ConnectionError: If not connected
        """
        pass

    # ========================================================================
    # Storage Operations
    # ========================================================================

    @abstractmethod
    def store_embedding(self, record: EmbeddingRecordCreate) -> int:
        """
        Store single embedding record.

        Args:
            record: Embedding data to store

        Returns:
            record_id of stored embedding

        Raises:
            IntegrityError: If template_id already exists or validation fails
            SerializationError: If embedding vector cannot be serialized
            ConnectionError: If not connected
        """
        pass

    @abstractmethod
    def store_embeddings_batch(
        self,
        records: List[EmbeddingRecordCreate],
        batch_size: int = 100
    ) -> List[int]:
        """
        Store multiple embeddings in a transaction.

        More efficient than calling store_embedding() repeatedly.

        Args:
            records: List of embedding records to store
            batch_size: Number of records per transaction (default: 100)

        Returns:
            List of record_ids for all stored embeddings

        Raises:
            IntegrityError: If any record fails validation
            SerializationError: If any vector cannot be serialized
            ConnectionError: If not connected
        """
        pass

    # ========================================================================
    # Loading Operations
    # ========================================================================

    @abstractmethod
    def load_embedding(self, template_id: str) -> Optional[EmbeddingRecord]:
        """
        Load single embedding by template_id.

        Args:
            template_id: Unique template identifier

        Returns:
            EmbeddingRecord if found, None if not exists

        Raises:
            ConnectionError: If not connected
            SerializationError: If vector deserialization fails
        """
        pass

    @abstractmethod
    def load_embeddings_all(
        self,
        version_id: Optional[int] = None
    ) -> List[EmbeddingRecord]:
        """
        Load all embeddings for specified version.

        Args:
            version_id: Version to load (None = current version)

        Returns:
            List of all embedding records

        Raises:
            ConnectionError: If not connected
            SerializationError: If vector deserialization fails
        """
        pass

    @abstractmethod
    def load_embeddings_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None
    ) -> List[EmbeddingRecord]:
        """
        Load embeddings filtered by category/subcategory.

        Args:
            category: Main category to filter by
            subcategory: Optional subcategory filter

        Returns:
            List of matching embedding records

        Raises:
            ConnectionError: If not connected
            SerializationError: If vector deserialization fails
        """
        pass

    # ========================================================================
    # Update and Delete Operations
    # ========================================================================

    @abstractmethod
    def update_embedding(
        self,
        template_id: str,
        record: EmbeddingRecordCreate
    ) -> bool:
        """
        Update existing embedding record.

        Args:
            template_id: Template to update
            record: New embedding data

        Returns:
            True if updated, False if template_id not found

        Raises:
            IntegrityError: If validation fails
            SerializationError: If vector cannot be serialized
            ConnectionError: If not connected
        """
        pass

    @abstractmethod
    def delete_embedding(self, template_id: str) -> bool:
        """
        Delete embedding by template_id.

        Args:
            template_id: Template to delete

        Returns:
            True if deleted, False if template_id not found

        Raises:
            ConnectionError: If not connected
        """
        pass

    # ========================================================================
    # Utility Methods
    # ========================================================================

    @abstractmethod
    def exists(self, template_id: str) -> bool:
        """
        Check if template_id exists in storage.

        Args:
            template_id: Template to check

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def count(self, version_id: Optional[int] = None) -> int:
        """
        Get total number of embeddings.

        Args:
            version_id: Version to count (None = current version)

        Returns:
            Number of embedding records
        """
        pass

    @abstractmethod
    def get_all_template_ids(
        self,
        version_id: Optional[int] = None
    ) -> List[str]:
        """
        Get list of all template IDs in storage.

        Args:
            version_id: Version to query (None = current version)

        Returns:
            List of template_id strings
        """
        pass

    @abstractmethod
    def get_content_hashes(
        self,
        version_id: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Get mapping of template_id to content_hash (for change detection).

        Args:
            version_id: Version to query (None = current version)

        Returns:
            Dictionary mapping template_id -> content_hash
        """
        pass

    @abstractmethod
    def validate_integrity(self) -> Dict[str, Any]:
        """
        Check storage integrity (foreign keys, constraints, etc.).

        Returns:
            Dictionary with validation results:
            {
                'is_valid': bool,
                'total_embeddings': int,
                'errors': List[str]
            }
        """
        pass

    @abstractmethod
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage statistics and metadata.

        Returns:
            Dictionary with storage information:
            {
                'backend_type': 'sqlite' | 'postgres',
                'total_embeddings': int,
                'storage_size_mb': float,
                'model_version': str,
                'embedding_dimension': int
            }
        """
        pass

    @abstractmethod
    def clear_all(self, version_id: Optional[int] = None) -> int:
        """
        Delete all embeddings (for testing/migration).

        Args:
            version_id: Version to clear (None = all versions)

        Returns:
            Number of records deleted

        Raises:
            ConnectionError: If not connected
        """
        pass

    # ========================================================================
    # Transaction Support
    # ========================================================================

    @contextmanager
    def transaction(self):
        """
        Context manager for transactional operations.

        Usage:
            with storage.transaction():
                storage.store_embedding(...)
                storage.store_embedding(...)
                # Automatic commit on success, rollback on exception

        Raises:
            ConnectionError: If not connected
            IntegrityError: If transaction fails
        """
        try:
            self._begin_transaction()
            yield
            self._commit_transaction()
        except Exception:
            self._rollback_transaction()
            raise

    @abstractmethod
    def _begin_transaction(self) -> None:
        """Begin database transaction."""
        pass

    @abstractmethod
    def _commit_transaction(self) -> None:
        """Commit database transaction."""
        pass

    @abstractmethod
    def _rollback_transaction(self) -> None:
        """Rollback database transaction."""
        pass

    # ========================================================================
    # Context Manager Protocol
    # ========================================================================

    def __enter__(self):
        """Context manager entry - connect to storage."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from storage."""
        self.disconnect()
        return False  # Don't suppress exceptions
