"""
Persistent storage module for embedding vectors.

This module provides storage backends for persisting embedding vectors
and metadata to eliminate startup precomputation delay.

Supported backends:
- SQLite: File-based, zero-config storage (default)
- PostgreSQL: Server-based storage with pg_vector extension (optional)
"""

from .base import (
    StorageBackend,
    StorageError,
    ConnectionError,
    IntegrityError,
    NotFoundError,
    SerializationError,
    ValidationError,
)
from .models import (
    EmbeddingRecordCreate,
    EmbeddingRecord,
    EmbeddingVersion,
    StorageConfig,
)

__all__ = [
    # Abstract base
    "StorageBackend",
    # Exceptions
    "StorageError",
    "ConnectionError",
    "IntegrityError",
    "NotFoundError",
    "SerializationError",
    "ValidationError",
    # Models
    "EmbeddingRecordCreate",
    "EmbeddingRecord",
    "EmbeddingVersion",
    "StorageConfig",
]


def create_storage_backend(config: StorageConfig) -> StorageBackend:
    """
    Factory function to create storage backend based on configuration.

    Args:
        config: Storage configuration specifying backend type and parameters

    Returns:
        Initialized storage backend instance

    Raises:
        ValueError: If backend type is not supported

    Example:
        >>> config = StorageConfig(backend="sqlite", sqlite_path="data/embeddings.db")
        >>> storage = create_storage_backend(config)
        >>> storage.connect()
    """
    if config.backend == "sqlite":
        from .sqlite_backend import SQLiteBackend
        return SQLiteBackend(db_path=config.sqlite_path)
    elif config.backend == "postgres":
        from .postgres_backend import PostgresBackend
        return PostgresBackend(
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_database,
            user=config.postgres_user,
            password=config.postgres_password,
            pool_size=config.connection_pool_size,
        )
    else:
        raise ValueError(f"Unsupported storage backend: {config.backend}")
