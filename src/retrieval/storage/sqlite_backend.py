"""
SQLite storage backend for embedding persistence.

This module provides a file-based storage implementation using SQLite
with optimized settings for read-heavy workload.
"""

import sqlite3
import io
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np

from .base import (
    StorageBackend,
    StorageError,
    ConnectionError as StorageConnectionError,
    IntegrityError as StorageIntegrityError,
    NotFoundError,
    SerializationError,
)
from .models import EmbeddingRecordCreate, EmbeddingRecord, EmbeddingVersion


# SQLite Schema (per data-model.md)
SQLITE_SCHEMA = """
-- Enable optimizations
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;  -- 64MB cache
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;  -- 256MB mmap

-- Embedding versions table
CREATE TABLE IF NOT EXISTS embedding_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_name, model_version, embedding_dimension)
);

CREATE INDEX IF NOT EXISTS idx_embedding_versions_current
ON embedding_versions(is_current);

-- Embedding records table
CREATE TABLE IF NOT EXISTS embedding_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id TEXT NOT NULL UNIQUE,
    version_id INTEGER NOT NULL,
    embedding_vector BLOB NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    success_rate REAL NOT NULL DEFAULT 0.5 CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    usage_count INTEGER NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (version_id) REFERENCES embedding_versions(version_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_embedding_records_version
ON embedding_records(version_id);

CREATE INDEX IF NOT EXISTS idx_embedding_records_category
ON embedding_records(category, subcategory);

CREATE INDEX IF NOT EXISTS idx_embedding_records_hash
ON embedding_records(content_hash);

-- Trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_embedding_records_timestamp
AFTER UPDATE ON embedding_records
FOR EACH ROW
BEGIN
    UPDATE embedding_records SET updated_at = CURRENT_TIMESTAMP
    WHERE record_id = NEW.record_id;
END;
"""


class SQLiteBackend(StorageBackend):
    """
    SQLite storage backend implementation.

    Features:
    - File-based storage (zero configuration)
    - WAL mode for better concurrency
    - Optimized PRAGMA settings
    - BLOB storage for numpy arrays
    - Cross-platform compatibility

    Example:
        >>> backend = SQLiteBackend("data/embeddings.db")
        >>> backend.connect()
        >>> backend.initialize_schema()
        >>> version_id = backend.get_or_create_version("bge-m3", "v1", 1024)
        >>> # ... use backend ...
        >>> backend.disconnect()
    """

    def __init__(self, db_path: str = "data/embeddings.db"):
        """
        Initialize SQLite backend.

        Args:
            db_path: Path to SQLite database file (will be created if doesn't exist)
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._in_transaction = False

    # ========================================================================
    # Connection Management
    # ========================================================================

    def connect(self) -> None:
        """Establish connection to SQLite database."""
        if self._conn is not None:
            return  # Already connected

        try:
            # Create parent directory if doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to database
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row  # Enable dict-like access

            # Enable foreign keys
            self._conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            raise StorageConnectionError(f"Failed to connect to SQLite database: {e}")

    def disconnect(self) -> None:
        """Close connection to SQLite database."""
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass  # Ignore errors during disconnect
            finally:
                self._conn = None

    def is_connected(self) -> bool:
        """Check if connected to SQLite database."""
        return self._conn is not None

    # ========================================================================
    # Schema Management
    # ========================================================================

    def initialize_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            # Execute schema creation (idempotent)
            self._conn.executescript(SQLITE_SCHEMA)
            self._conn.commit()
        except sqlite3.Error as e:
            raise StorageIntegrityError(f"Failed to initialize schema: {e}")

    # ========================================================================
    # Version Management (T014)
    # ========================================================================

    def get_or_create_version(
        self,
        model_name: str,
        model_version: str,
        embedding_dimension: int
    ) -> int:
        """Get existing version ID or create new version entry."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            # Try to get existing version
            cursor = self._conn.execute(
                """
                SELECT version_id FROM embedding_versions
                WHERE model_name = ? AND model_version = ? AND embedding_dimension = ?
                """,
                (model_name, model_version, embedding_dimension)
            )
            row = cursor.fetchone()

            if row:
                return row['version_id']

            # Create new version
            cursor = self._conn.execute(
                """
                INSERT INTO embedding_versions (model_name, model_version, embedding_dimension, is_current)
                VALUES (?, ?, ?, 1)
                """,
                (model_name, model_version, embedding_dimension)
            )
            self._conn.commit()
            return cursor.lastrowid

        except sqlite3.IntegrityError as e:
            raise StorageIntegrityError(f"Failed to create version: {e}")
        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def get_current_version(self) -> Optional[EmbeddingVersion]:
        """Get currently active embedding version."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            cursor = self._conn.execute(
                """
                SELECT version_id, model_name, model_version, embedding_dimension,
                       is_current, created_at
                FROM embedding_versions
                WHERE is_current = 1
                LIMIT 1
                """
            )
            row = cursor.fetchone()

            if not row:
                return None

            return EmbeddingVersion(
                version_id=row['version_id'],
                model_name=row['model_name'],
                model_version=row['model_version'],
                embedding_dimension=row['embedding_dimension'],
                is_current=bool(row['is_current']),
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            )

        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def set_current_version(self, version_id: int) -> None:
        """Mark a version as current (only one version can be current)."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            # Start transaction
            self._conn.execute("BEGIN")

            # Verify version exists
            cursor = self._conn.execute(
                "SELECT version_id FROM embedding_versions WHERE version_id = ?",
                (version_id,)
            )
            if not cursor.fetchone():
                self._conn.rollback()
                raise NotFoundError(f"Version {version_id} not found")

            # Set all versions to not current
            self._conn.execute("UPDATE embedding_versions SET is_current = 0")

            # Set specified version as current
            self._conn.execute(
                "UPDATE embedding_versions SET is_current = 1 WHERE version_id = ?",
                (version_id,)
            )

            self._conn.commit()

        except sqlite3.Error as e:
            self._conn.rollback()
            raise StorageIntegrityError(f"Failed to set current version: {e}")

    # ========================================================================
    # Serialization (T016)
    # ========================================================================

    def _serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """
        Serialize numpy array to bytes for BLOB storage.

        Uses numpy's native binary format (.npy) which includes shape and dtype metadata.
        """
        try:
            buffer = io.BytesIO()
            np.save(buffer, embedding, allow_pickle=False)
            return buffer.getvalue()
        except Exception as e:
            raise SerializationError(f"Failed to serialize embedding: {e}")

    def _deserialize_embedding(self, blob: bytes) -> np.ndarray:
        """Deserialize bytes back to numpy array."""
        try:
            buffer = io.BytesIO(blob)
            return np.load(buffer, allow_pickle=False)
        except Exception as e:
            raise SerializationError(f"Failed to deserialize embedding: {e}")

    # ========================================================================
    # Storage Operations (T018)
    # ========================================================================

    def store_embedding(self, record: EmbeddingRecordCreate) -> int:
        """Store single embedding record."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            # Serialize embedding vector
            embedding_blob = self._serialize_embedding(record.embedding_vector)

            # Insert record
            cursor = self._conn.execute(
                """
                INSERT INTO embedding_records
                (template_id, version_id, embedding_vector, category, subcategory,
                 question_text, answer_text, content_hash, success_rate, usage_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.template_id,
                    record.version_id,
                    embedding_blob,
                    record.category,
                    record.subcategory,
                    record.question_text,
                    record.answer_text,
                    record.content_hash,
                    record.success_rate,
                    record.usage_count
                )
            )

            if not self._in_transaction:
                self._conn.commit()

            return cursor.lastrowid

        except sqlite3.IntegrityError as e:
            if not self._in_transaction:
                self._conn.rollback()
            raise StorageIntegrityError(f"Failed to store embedding: {e}")
        except sqlite3.Error as e:
            if not self._in_transaction:
                self._conn.rollback()
            raise StorageError(f"Database error: {e}")

    def store_embeddings_batch(
        self,
        records: List[EmbeddingRecordCreate],
        batch_size: int = 100
    ) -> List[int]:
        """Store multiple embeddings in a transaction."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        record_ids = []

        try:
            with self.transaction():
                for record in records:
                    record_id = self.store_embedding(record)
                    record_ids.append(record_id)

            return record_ids

        except Exception as e:
            raise StorageError(f"Batch storage failed: {e}")

    # ========================================================================
    # Loading Operations (T020)
    # ========================================================================

    def load_embedding(self, template_id: str) -> Optional[EmbeddingRecord]:
        """Load single embedding by template_id."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            cursor = self._conn.execute(
                """
                SELECT record_id, template_id, version_id, embedding_vector,
                       category, subcategory, question_text, answer_text, content_hash,
                       success_rate, usage_count, created_at, updated_at
                FROM embedding_records
                WHERE template_id = ?
                """,
                (template_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_record(row)

        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def load_embeddings_all(
        self,
        version_id: Optional[int] = None
    ) -> List[EmbeddingRecord]:
        """Load all embeddings for specified version."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            if version_id is None:
                # Get current version
                current_version = self.get_current_version()
                if not current_version:
                    return []
                version_id = current_version.version_id

            cursor = self._conn.execute(
                """
                SELECT record_id, template_id, version_id, embedding_vector,
                       category, subcategory, question_text, answer_text, content_hash,
                       success_rate, usage_count, created_at, updated_at
                FROM embedding_records
                WHERE version_id = ?
                """,
                (version_id,)
            )

            return [self._row_to_record(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def load_embeddings_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None
    ) -> List[EmbeddingRecord]:
        """Load embeddings filtered by category/subcategory."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            if subcategory is None:
                cursor = self._conn.execute(
                    """
                    SELECT record_id, template_id, version_id, embedding_vector,
                           category, subcategory, question_text, answer_text, content_hash,
                           success_rate, usage_count, created_at, updated_at
                    FROM embedding_records
                    WHERE category = ?
                    """,
                    (category,)
                )
            else:
                cursor = self._conn.execute(
                    """
                    SELECT record_id, template_id, version_id, embedding_vector,
                           category, subcategory, question_text, answer_text, content_hash,
                           success_rate, usage_count, created_at, updated_at
                    FROM embedding_records
                    WHERE category = ? AND subcategory = ?
                    """,
                    (category, subcategory)
                )

            return [self._row_to_record(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def _row_to_record(self, row: sqlite3.Row) -> EmbeddingRecord:
        """Convert database row to EmbeddingRecord."""
        embedding_vector = self._deserialize_embedding(row['embedding_vector'])

        return EmbeddingRecord(
            record_id=row['record_id'],
            template_id=row['template_id'],
            version_id=row['version_id'],
            embedding_vector=embedding_vector,
            category=row['category'],
            subcategory=row['subcategory'],
            question_text=row['question_text'],
            answer_text=row['answer_text'],
            content_hash=row['content_hash'],
            success_rate=row['success_rate'],
            usage_count=row['usage_count'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    # ========================================================================
    # Update and Delete Operations
    # ========================================================================

    def update_embedding(
        self,
        template_id: str,
        record: EmbeddingRecordCreate
    ) -> bool:
        """Update existing embedding record."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            embedding_blob = self._serialize_embedding(record.embedding_vector)

            cursor = self._conn.execute(
                """
                UPDATE embedding_records
                SET version_id = ?, embedding_vector = ?, category = ?, subcategory = ?,
                    question_text = ?, answer_text = ?, content_hash = ?,
                    success_rate = ?, usage_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE template_id = ?
                """,
                (
                    record.version_id,
                    embedding_blob,
                    record.category,
                    record.subcategory,
                    record.question_text,
                    record.answer_text,
                    record.content_hash,
                    record.success_rate,
                    record.usage_count,
                    template_id
                )
            )

            self._conn.commit()
            return cursor.rowcount > 0

        except sqlite3.Error as e:
            self._conn.rollback()
            raise StorageError(f"Database error: {e}")

    def delete_embedding(self, template_id: str) -> bool:
        """Delete embedding by template_id."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            cursor = self._conn.execute(
                "DELETE FROM embedding_records WHERE template_id = ?",
                (template_id,)
            )
            self._conn.commit()
            return cursor.rowcount > 0

        except sqlite3.Error as e:
            self._conn.rollback()
            raise StorageError(f"Database error: {e}")

    # ========================================================================
    # Utility Methods (T022)
    # ========================================================================

    def exists(self, template_id: str) -> bool:
        """Check if template_id exists in storage."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            cursor = self._conn.execute(
                "SELECT COUNT(*) as count FROM embedding_records WHERE template_id = ?",
                (template_id,)
            )
            return cursor.fetchone()['count'] > 0

        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def count(self, version_id: Optional[int] = None) -> int:
        """Get total number of embeddings."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            if version_id is None:
                current_version = self.get_current_version()
                if not current_version:
                    return 0
                version_id = current_version.version_id

            cursor = self._conn.execute(
                "SELECT COUNT(*) as count FROM embedding_records WHERE version_id = ?",
                (version_id,)
            )
            return cursor.fetchone()['count']

        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def get_all_template_ids(
        self,
        version_id: Optional[int] = None
    ) -> List[str]:
        """Get list of all template IDs in storage."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            if version_id is None:
                current_version = self.get_current_version()
                if not current_version:
                    return []
                version_id = current_version.version_id

            cursor = self._conn.execute(
                "SELECT template_id FROM embedding_records WHERE version_id = ?",
                (version_id,)
            )
            return [row['template_id'] for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def get_content_hashes(
        self,
        version_id: Optional[int] = None
    ) -> Dict[str, str]:
        """Get mapping of template_id to content_hash."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            if version_id is None:
                current_version = self.get_current_version()
                if not current_version:
                    return {}
                version_id = current_version.version_id

            cursor = self._conn.execute(
                "SELECT template_id, content_hash FROM embedding_records WHERE version_id = ?",
                (version_id,)
            )
            return {row['template_id']: row['content_hash'] for row in cursor.fetchall()}

        except sqlite3.Error as e:
            raise StorageError(f"Database error: {e}")

    def validate_integrity(self) -> Dict[str, Any]:
        """Check storage integrity."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        errors = []

        try:
            # Check foreign key constraints
            cursor = self._conn.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            if fk_violations:
                errors.append(f"Foreign key violations: {len(fk_violations)}")

            # Count total embeddings
            cursor = self._conn.execute("SELECT COUNT(*) as count FROM embedding_records")
            total_embeddings = cursor.fetchone()['count']

            return {
                'is_valid': len(errors) == 0,
                'total_embeddings': total_embeddings,
                'errors': errors
            }

        except sqlite3.Error as e:
            return {
                'is_valid': False,
                'total_embeddings': 0,
                'errors': [f"Validation failed: {e}"]
            }

    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage statistics and metadata."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            # Get current version
            current_version = self.get_current_version()

            # Count total embeddings
            total_embeddings = self.count()

            # Get database file size
            storage_size_mb = 0.0
            if self.db_path.exists():
                storage_size_mb = self.db_path.stat().st_size / (1024 * 1024)

            return {
                'backend_type': 'sqlite',
                'total_embeddings': total_embeddings,
                'storage_size_mb': storage_size_mb,
                'model_version': f"{current_version.model_name} {current_version.model_version}" if current_version else "none",
                'embedding_dimension': current_version.embedding_dimension if current_version else 0,
                'database_path': str(self.db_path)
            }

        except Exception as e:
            raise StorageError(f"Failed to get storage info: {e}")

    def clear_all(self, version_id: Optional[int] = None) -> int:
        """Delete all embeddings."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")

        try:
            if version_id is None:
                cursor = self._conn.execute("DELETE FROM embedding_records")
            else:
                cursor = self._conn.execute(
                    "DELETE FROM embedding_records WHERE version_id = ?",
                    (version_id,)
                )

            self._conn.commit()
            return cursor.rowcount

        except sqlite3.Error as e:
            self._conn.rollback()
            raise StorageError(f"Database error: {e}")

    # ========================================================================
    # Transaction Support
    # ========================================================================

    def _begin_transaction(self) -> None:
        """Begin database transaction."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")
        self._conn.execute("BEGIN")
        self._in_transaction = True

    def _commit_transaction(self) -> None:
        """Commit database transaction."""
        if not self.is_connected():
            raise StorageConnectionError("Not connected to database")
        self._conn.commit()
        self._in_transaction = False

    def _rollback_transaction(self) -> None:
        """Rollback database transaction."""
        if not self.is_connected():
            return
        self._conn.rollback()
        self._in_transaction = False
