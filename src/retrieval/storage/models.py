"""
Data models for persistent embedding storage.

This module defines Pydantic models for embedding records, versions,
and storage configuration.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, validator
import numpy as np


class EmbeddingVersion(BaseModel):
    """
    Embedding model version information.

    Tracks which embedding model was used to generate vectors, enabling
    detection of model upgrades and ensuring consistency.
    """
    version_id: Optional[int] = Field(None, description="Auto-generated version ID")
    model_name: str = Field(..., description="Model identifier (e.g., 'bge-m3')")
    model_version: str = Field(..., description="Model version string (e.g., 'v1')")
    embedding_dimension: int = Field(..., gt=0, description="Vector dimensionality (e.g., 1024)")
    is_current: bool = Field(True, description="Whether this is the active version")
    created_at: Optional[datetime] = Field(None, description="Version creation timestamp")

    class Config:
        from_attributes = True


class EmbeddingRecordCreate(BaseModel):
    """
    Model for creating new embedding records.

    Used when inserting embeddings into storage. Does not include
    auto-generated fields like record_id, created_at, updated_at.
    """
    template_id: str = Field(..., min_length=1, description="Unique template identifier")
    version_id: int = Field(..., gt=0, description="Reference to embedding version")
    embedding_vector: np.ndarray = Field(..., description="1024-dimensional embedding vector")
    category: str = Field(..., min_length=1, description="Main category")
    subcategory: str = Field(..., min_length=1, description="Subcategory")
    question_text: str = Field(..., min_length=1, description="Template question")
    answer_text: str = Field(..., min_length=1, description="Template answer")
    content_hash: str = Field(..., min_length=64, max_length=64, description="SHA256 content hash")
    success_rate: float = Field(0.5, ge=0.0, le=1.0, description="Historical success rate")
    usage_count: int = Field(0, ge=0, description="Usage counter")

    @validator('embedding_vector')
    def validate_embedding_vector(cls, v):
        """Validate embedding vector is numpy array with correct shape."""
        if not isinstance(v, np.ndarray):
            raise ValueError("embedding_vector must be numpy array")
        if v.ndim != 1:
            raise ValueError(f"embedding_vector must be 1-dimensional, got {v.ndim}D")
        if v.shape[0] != 1024:
            raise ValueError(f"embedding_vector must have 1024 dimensions, got {v.shape[0]}")
        if v.dtype not in [np.float32, np.float64]:
            raise ValueError(f"embedding_vector must be float32 or float64, got {v.dtype}")
        return v

    @validator('content_hash')
    def validate_content_hash(cls, v):
        """Validate content hash is valid SHA256 hex string."""
        if len(v) != 64:
            raise ValueError(f"content_hash must be 64 characters (SHA256), got {len(v)}")
        try:
            int(v, 16)  # Verify it's valid hexadecimal
        except ValueError:
            raise ValueError("content_hash must be hexadecimal string")
        return v

    class Config:
        arbitrary_types_allowed = True  # Allow numpy arrays


class EmbeddingRecord(EmbeddingRecordCreate):
    """
    Complete embedding record model.

    Extends EmbeddingRecordCreate with auto-generated fields that are
    populated by the database.
    """
    record_id: int = Field(..., gt=0, description="Auto-generated record ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class StorageConfig(BaseModel):
    """
    Storage backend configuration.

    Specifies which storage backend to use and connection parameters.
    """
    backend: Literal["sqlite", "postgres"] = Field("sqlite", description="Storage backend type")

    # SQLite configuration
    sqlite_path: str = Field("data/embeddings.db", description="SQLite database file path")

    # PostgreSQL configuration
    postgres_host: str = Field("localhost", description="PostgreSQL host")
    postgres_port: int = Field(5432, ge=1, le=65535, description="PostgreSQL port")
    postgres_database: str = Field("smart_support", description="PostgreSQL database name")
    postgres_user: str = Field("postgres", description="PostgreSQL user")
    postgres_password: str = Field("", description="PostgreSQL password")
    connection_pool_size: int = Field(5, ge=1, le=100, description="Connection pool size")

    @classmethod
    def from_env(cls) -> "StorageConfig":
        """
        Create configuration from environment variables.

        Environment variables:
        - STORAGE_BACKEND: "sqlite" or "postgres" (default: sqlite)
        - SQLITE_DB_PATH: path to SQLite database (default: data/embeddings.db)
        - POSTGRES_HOST: PostgreSQL host (default: localhost)
        - POSTGRES_PORT: PostgreSQL port (default: 5432)
        - POSTGRES_DATABASE: database name (default: smart_support)
        - POSTGRES_USER: database user (default: postgres)
        - POSTGRES_PASSWORD: database password (default: empty)
        - POSTGRES_POOL_SIZE: connection pool size (default: 5)

        Returns:
            StorageConfig instance populated from environment

        Example:
            >>> import os
            >>> os.environ["STORAGE_BACKEND"] = "sqlite"
            >>> config = StorageConfig.from_env()
            >>> config.backend
            'sqlite'
        """
        import os

        return cls(
            backend=os.getenv("STORAGE_BACKEND", "sqlite"),
            sqlite_path=os.getenv("SQLITE_DB_PATH", "data/embeddings.db"),
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_database=os.getenv("POSTGRES_DATABASE", "smart_support"),
            postgres_user=os.getenv("POSTGRES_USER", "postgres"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
            connection_pool_size=int(os.getenv("POSTGRES_POOL_SIZE", "5")),
        )

    class Config:
        validate_assignment = True
