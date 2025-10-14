# Research: Persistent Embedding Storage

**Feature**: Persistent Embedding Storage
**Date**: 2025-10-15
**Purpose**: Resolve technical decisions for implementing persistent storage of embedding vectors to eliminate 9-second startup delay

## Overview

This research phase evaluates storage technologies, design patterns, and implementation strategies for persistent embedding storage. The goal is to reduce system startup time from 9 seconds to under 2 seconds while maintaining 86.7% top-3 retrieval accuracy. All decisions prioritize backward compatibility with the existing `EmbeddingCache` interface and cross-platform deployment.

---

## Research Topic 1: Vector Storage Approaches

**Objective**: Compare SQLite BLOB storage vs PostgreSQL pg_vector for 1024-dimensional embeddings

### Decision: Support both with SQLite as default

**Rationale**:
- **SQLite BLOB**: Zero-config, file-based, perfect for single-node deployments
- **PostgreSQL pg_vector**: Optional for users who need advanced vector operations or already have PostgreSQL infrastructure
- **Flexibility**: Storage abstraction layer allows users to choose based on deployment needs

### Storage Format Comparison

#### SQLite with BLOB Storage

**Approach**: Serialize numpy arrays to binary format and store as BLOB

```python
import sqlite3
import numpy as np
import io

# Serialization approach
def serialize_embedding(embedding: np.ndarray) -> bytes:
    """
    Serialize numpy array to bytes for SQLite BLOB storage.

    Uses numpy's native binary format (.npy) which includes:
    - Array shape and dtype metadata
    - Efficient binary representation
    - Cross-platform compatibility
    """
    buffer = io.BytesIO()
    np.save(buffer, embedding, allow_pickle=False)
    return buffer.getvalue()

def deserialize_embedding(blob: bytes) -> np.ndarray:
    """Deserialize bytes back to numpy array."""
    buffer = io.BytesIO(blob)
    return np.load(buffer, allow_pickle=False)

# Storage example
def store_embedding(conn: sqlite3.Connection, template_id: str, embedding: np.ndarray):
    """Store embedding in SQLite BLOB column."""
    conn.execute(
        "INSERT INTO embeddings (template_id, embedding_vector) VALUES (?, ?)",
        (template_id, serialize_embedding(embedding))
    )
```

**Performance Characteristics**:
- Serialization overhead: ~0.1ms per 1024-dim vector
- Deserialization overhead: ~0.15ms per vector
- Storage size: ~4KB per vector (1024 dims × 4 bytes float32)
- Query performance: Sequential scan, no vector indexing

**Pros**:
- No external dependencies (sqlite3 in stdlib)
- Zero configuration required
- Cross-platform file format
- Excellent for development and simple deployments

**Cons**:
- No native vector operations (cosine similarity computed in Python)
- No vector indexing (full scan required)
- Less efficient for very large datasets (>10K vectors)

---

#### PostgreSQL with pg_vector Extension

**Approach**: Use native `vector` data type with built-in similarity operators

```python
import psycopg2
from psycopg2.extensions import register_adapter, AsIs
import numpy as np

# Register numpy array adapter for pg_vector
def adapt_numpy_array(arr: np.ndarray):
    """Convert numpy array to pg_vector format."""
    return AsIs(f"'[{','.join(map(str, arr))}]'")

register_adapter(np.ndarray, adapt_numpy_array)

# Storage example
def store_embedding_postgres(conn, template_id: str, embedding: np.ndarray):
    """Store embedding using pg_vector native type."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO embeddings (template_id, embedding_vector) VALUES (%s, %s::vector(1024))",
            (template_id, embedding)
        )

# Query with cosine similarity (native)
def search_similar_postgres(conn, query_embedding: np.ndarray, limit: int = 5):
    """Search using pg_vector cosine distance operator."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT template_id, 1 - (embedding_vector <=> %s::vector(1024)) as similarity
            FROM embeddings
            ORDER BY embedding_vector <=> %s::vector(1024)
            LIMIT %s
            """,
            (query_embedding, query_embedding, limit)
        )
        return cur.fetchall()
```

**Performance Characteristics**:
- Native vector operations (no serialization overhead)
- HNSW indexing support for approximate nearest neighbor search
- Cosine distance operator (`<=>`) computed in C (faster than Python)
- Concurrent access with proper locking

**Pros**:
- Native vector similarity operators
- Indexing support (HNSW) for large datasets
- Better scalability (10K+ vectors)
- Concurrent access out of the box

**Cons**:
- Requires PostgreSQL server setup
- Requires pg_vector extension installation
- More complex deployment (docker-compose with postgres service)
- Network latency for remote database

---

### Implementation Notes

**Storage Overhead for 201 Templates**:
- Raw data: 201 templates × 1024 dims × 4 bytes (float32) = 824 KB
- SQLite with metadata: ~1.5 MB (includes indexes, metadata columns)
- PostgreSQL with pg_vector: ~2 MB (includes system overhead, indexes)
- Both well under 10MB requirement ✓

**Decision Guide for Users**:

| Use Case | Recommended Backend | Rationale |
|----------|-------------------|-----------|
| Local development | SQLite | Zero config, fast startup |
| Small production (<1000 templates) | SQLite | Simple deployment, adequate performance |
| Large production (>1000 templates) | PostgreSQL + pg_vector | Better indexing, scalability |
| Existing PostgreSQL infrastructure | PostgreSQL + pg_vector | Leverage existing setup |
| Multi-container deployment | SQLite + volume mount | Simplest shared storage |

---

## Research Topic 2: Content Hashing Strategy

**Objective**: Determine optimal hashing approach for detecting FAQ changes

### Decision: SHA256 for content hashing

**Rationale**:
- **Collision resistance**: Cryptographic-grade, zero practical collision risk
- **Cross-platform consistency**: Same hash on all platforms (unlike Python's `hash()`)
- **Performance**: Fast enough for 201 templates (~0.05ms per hash)
- **Debugging**: Human-readable hex strings, easy to verify manually

### Hash Function Comparison

#### Option 1: SHA256 (Recommended)

```python
import hashlib

def compute_content_hash(question: str, answer: str) -> str:
    """
    Compute SHA256 hash of FAQ content.

    Args:
        question: Template question text
        answer: Template answer text

    Returns:
        64-character hex string (SHA256 hash)
    """
    content = f"{question}|{answer}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# Example usage
hash1 = compute_content_hash(
    "Как открыть счет?",
    "Посетите отделение банка с паспортом."
)
# Output: "a1b2c3d4e5f6..." (64 chars)
```

**Characteristics**:
- Hash length: 64 characters (32 bytes)
- Collision probability: ~10^-77 (effectively zero)
- Performance: ~0.05ms per hash on modern CPU
- Cross-platform: Identical on all systems

**Pros**:
- Cryptographic security (no collisions in practice)
- Standard library (hashlib)
- Deterministic and reproducible
- Human-readable hex output

**Cons**:
- Slightly slower than MD5 (~20% overhead)
- Longer hash string (64 vs 32 chars for MD5)

---

#### Option 2: MD5 (Not Recommended)

```python
import hashlib

def compute_content_hash_md5(question: str, answer: str) -> str:
    """Compute MD5 hash (faster but less secure)."""
    content = f"{question}|{answer}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()
```

**Characteristics**:
- Hash length: 32 characters (16 bytes)
- Collision probability: ~10^-38 (still negligible for 201 templates)
- Performance: ~0.04ms per hash (~20% faster than SHA256)

**Pros**:
- Slightly faster than SHA256
- Shorter hash string

**Cons**:
- Deprecated for security reasons (collisions possible)
- Not future-proof if dataset grows significantly
- No performance advantage for 201 templates

---

#### Option 3: Python's hash() (Not Recommended)

```python
def compute_content_hash_builtin(question: str, answer: str) -> int:
    """Use Python's built-in hash (NOT RECOMMENDED)."""
    content = f"{question}|{answer}"
    return hash(content)
```

**Characteristics**:
- Hash length: 8 bytes (64-bit integer)
- Collision probability: Higher than cryptographic hashes
- Performance: Fastest (~0.01ms)

**Cons**:
- **Platform-dependent**: Different results on different machines/Python versions
- **Session-dependent**: Hash seed changes between Python runs (security feature)
- **Not persistent**: Cannot store and compare across restarts
- **Higher collision risk**: 64-bit space, birthday paradox applies

---

### Implementation Approach

**Hash Storage in Database**:

```sql
-- SQLite schema
CREATE TABLE embeddings (
    template_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    embedding_vector BLOB NOT NULL,
    content_hash TEXT NOT NULL,  -- SHA256 hex string
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookup
CREATE INDEX idx_content_hash ON embeddings(content_hash);
```

**Change Detection Logic**:

```python
def detect_changes(conn, faq_templates: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Detect new, modified, and deleted templates.

    Returns:
        {
            'new': [templates not in DB],
            'modified': [templates with different hash],
            'deleted': [template_ids in DB but not in FAQ],
            'unchanged': [templates with matching hash]
        }
    """
    results = {'new': [], 'modified': [], 'deleted': [], 'unchanged': []}

    # Get current hashes from database
    stored_hashes = {
        row['template_id']: row['content_hash']
        for row in conn.execute("SELECT template_id, content_hash FROM embeddings")
    }

    # Check each FAQ template
    faq_ids = set()
    for template in faq_templates:
        template_id = template['id']
        current_hash = compute_content_hash(template['question'], template['answer'])
        faq_ids.add(template_id)

        if template_id not in stored_hashes:
            results['new'].append(template)
        elif stored_hashes[template_id] != current_hash:
            results['modified'].append(template)
        else:
            results['unchanged'].append(template)

    # Find deleted templates
    stored_ids = set(stored_hashes.keys())
    deleted_ids = stored_ids - faq_ids
    results['deleted'] = list(deleted_ids)

    return results
```

**Performance Impact**:
- Hashing 201 templates: ~10ms total (negligible)
- Database lookup: ~5ms (single query with index)
- Total overhead for change detection: ~15ms (acceptable)

---

## Research Topic 3: Storage Abstraction Patterns

**Objective**: Design storage interface that works for both SQLite and PostgreSQL

### Decision: Abstract Base Class (ABC) with context manager protocol

**Rationale**:
- **Type safety**: ABC enforces interface contract at class definition time
- **IDE support**: Better autocomplete and type checking than Protocol
- **Context manager**: Ensures proper connection cleanup and transaction handling
- **Testing**: Easy to create mock implementations for unit tests

### Storage Interface Design

```python
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict
from contextlib import contextmanager
import numpy as np

class StorageBackend(ABC):
    """
    Abstract base class for embedding storage backends.

    Implementations:
    - SQLiteStorage: File-based storage with BLOB vectors
    - PostgresStorage: Server-based storage with pg_vector
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to storage backend."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection and cleanup resources."""
        pass

    @abstractmethod
    def store_embedding(
        self,
        template_id: str,
        embedding: np.ndarray,
        metadata: Dict[str, str],
        content_hash: str
    ) -> None:
        """
        Store single embedding with metadata.

        Args:
            template_id: Unique template identifier
            embedding: 1024-dimensional vector (float32)
            metadata: Dict with category, subcategory, question, answer
            content_hash: SHA256 hash of content for change detection
        """
        pass

    @abstractmethod
    def load_embeddings(self) -> List[Tuple[str, np.ndarray, Dict[str, str]]]:
        """
        Load all embeddings from storage.

        Returns:
            List of (template_id, embedding_vector, metadata) tuples
        """
        pass

    @abstractmethod
    def get_by_category(
        self,
        category: str,
        subcategory: str
    ) -> List[Tuple[str, np.ndarray, Dict[str, str]]]:
        """
        Load embeddings filtered by category/subcategory.

        Args:
            category: Top-level category
            subcategory: Second-level classification

        Returns:
            Filtered list of (template_id, embedding, metadata) tuples
        """
        pass

    @abstractmethod
    def update_embedding(
        self,
        template_id: str,
        embedding: np.ndarray,
        content_hash: str
    ) -> None:
        """Update existing embedding (for modified templates)."""
        pass

    @abstractmethod
    def delete_embedding(self, template_id: str) -> None:
        """Delete embedding (for removed templates)."""
        pass

    @abstractmethod
    def get_content_hash(self, template_id: str) -> Optional[str]:
        """Get stored content hash for change detection."""
        pass

    @abstractmethod
    def validate_integrity(self) -> Dict[str, any]:
        """
        Validate storage integrity.

        Returns:
            {
                'valid': bool,
                'total_embeddings': int,
                'corrupted_embeddings': List[str],
                'missing_metadata': List[str]
            }
        """
        pass

    @abstractmethod
    def get_storage_info(self) -> Dict[str, any]:
        """
        Get storage statistics.

        Returns:
            {
                'backend_type': 'sqlite' | 'postgres',
                'total_embeddings': int,
                'storage_size_mb': float,
                'model_version': str,
                'embedding_dimension': int
            }
        """
        pass

    @contextmanager
    def transaction(self):
        """
        Context manager for transactional operations.

        Usage:
            with storage.transaction():
                storage.store_embedding(...)
                storage.store_embedding(...)
                # Automatic commit on success, rollback on exception
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
```

---

### Connection Management Patterns

#### Pattern 1: Connection Per Operation (SQLite Default)

```python
class SQLiteStorage(StorageBackend):
    """SQLite backend with connection-per-operation pattern."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _get_connection(self):
        """Get connection for single operation."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn

    def store_embedding(self, template_id: str, embedding: np.ndarray, metadata: Dict, content_hash: str):
        """Store with automatic connection management."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO embeddings
                (template_id, embedding_vector, category, subcategory, question, answer, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    serialize_embedding(embedding),
                    metadata['category'],
                    metadata['subcategory'],
                    metadata['question'],
                    metadata['answer'],
                    content_hash
                )
            )
            conn.commit()
```

**Pros**:
- Simple, no state management
- Automatic cleanup
- Safe for concurrent reads

**Cons**:
- Connection overhead for each operation
- Not efficient for batch operations

---

#### Pattern 2: Connection Pooling (PostgreSQL Recommended)

```python
from psycopg2 import pool

class PostgresStorage(StorageBackend):
    """PostgreSQL backend with connection pooling."""

    def __init__(self, dsn: str, pool_size: int = 5):
        self.dsn = dsn
        self.pool = pool.SimpleConnectionPool(1, pool_size, dsn)

    @contextmanager
    def _get_connection(self):
        """Get pooled connection with automatic return."""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def load_embeddings(self):
        """Load all embeddings using pooled connection."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT template_id, embedding_vector, category, subcategory FROM embeddings")
                return [
                    (row[0], np.array(row[1]), {'category': row[2], 'subcategory': row[3]})
                    for row in cur.fetchall()
                ]
```

**Pros**:
- Efficient connection reuse
- Handles concurrent access
- Better for high-load scenarios

**Cons**:
- More complex lifecycle management
- Requires cleanup on shutdown

---

### Implementation Notes

**Why ABC over Protocol**:
- `typing.Protocol` is for structural subtyping (duck typing with type hints)
- `ABC` enforces implementation at class definition, catches missing methods early
- `ABC` better for explicit inheritance contracts
- `Protocol` better for third-party integrations (not needed here)

**Error Handling Strategy**:

```python
class StorageError(Exception):
    """Base exception for storage operations."""
    pass

class ConnectionError(StorageError):
    """Failed to connect to storage backend."""
    pass

class IntegrityError(StorageError):
    """Data integrity violation (corrupt embeddings, missing data)."""
    pass

class StorageFullError(StorageError):
    """Storage capacity exceeded."""
    pass
```

---

## Research Topic 4: Migration Command Design

**Objective**: Design CLI command for explicit embedding migration

### Decision: Click for CLI framework, Rich for progress reporting

**Rationale**:
- **Click**: More ergonomic than argparse, better help formatting, decorator-based
- **Rich**: Modern progress bars, colored output, better UX than tqdm
- **Explicit migration**: User control, no surprise slow startups
- **Progress visibility**: Shows API call progress, embedding count, estimated time

### CLI Framework Comparison

#### Option 1: Click (Recommended)

```python
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

console = Console()

@click.command()
@click.option(
    '--storage-backend',
    type=click.Choice(['sqlite', 'postgres']),
    default='sqlite',
    help='Storage backend to use'
)
@click.option(
    '--db-path',
    type=click.Path(),
    default='data/embeddings.db',
    help='SQLite database path (if using sqlite backend)'
)
@click.option(
    '--postgres-dsn',
    type=str,
    help='PostgreSQL connection string (if using postgres backend)'
)
@click.option(
    '--faq-path',
    type=click.Path(exists=True),
    default='docs/smart_support_vtb_belarus_faq_final.xlsx',
    help='Path to FAQ Excel file'
)
@click.option(
    '--batch-size',
    type=int,
    default=20,
    help='Embedding batch size for API calls'
)
@click.option(
    '--force',
    is_flag=True,
    help='Force recompute all embeddings (ignore existing)'
)
@click.option(
    '--validate',
    is_flag=True,
    help='Validate storage integrity after migration'
)
def migrate_embeddings(
    storage_backend: str,
    db_path: str,
    postgres_dsn: str,
    faq_path: str,
    batch_size: int,
    force: bool,
    validate: bool
):
    """
    Migrate embeddings to persistent storage.

    This command:
    1. Loads FAQ templates from Excel
    2. Detects new/modified/deleted templates
    3. Computes embeddings via Scibox API (batch mode)
    4. Stores embeddings in chosen backend
    5. Validates integrity (if --validate flag set)

    Example usage:

        # SQLite (default)
        python -m src.cli.migrate_embeddings

        # PostgreSQL
        python -m src.cli.migrate_embeddings \\
            --storage-backend postgres \\
            --postgres-dsn "postgresql://user:pass@localhost/smartsupport"

        # Force full recompute
        python -m src.cli.migrate_embeddings --force
    """
    console.print("[bold blue]Smart Support - Embedding Migration[/bold blue]\n")

    # Initialize storage backend
    if storage_backend == 'sqlite':
        storage = SQLiteStorage(db_path)
        console.print(f"Storage backend: SQLite ({db_path})")
    else:
        if not postgres_dsn:
            console.print("[bold red]Error:[/bold red] --postgres-dsn required for postgres backend")
            raise click.Abort()
        storage = PostgresStorage(postgres_dsn)
        console.print(f"Storage backend: PostgreSQL ({postgres_dsn})")

    # Load FAQ templates
    console.print(f"\nLoading FAQ templates from: {faq_path}")
    from src.classification.faq_parser import parse_faq
    templates = parse_faq(faq_path)
    console.print(f"Loaded [bold]{len(templates)}[/bold] templates")

    # Detect changes
    if not force:
        console.print("\nDetecting changes...")
        changes = detect_changes(storage, templates)

        console.print(f"  New: [green]{len(changes['new'])}[/green]")
        console.print(f"  Modified: [yellow]{len(changes['modified'])}[/yellow]")
        console.print(f"  Deleted: [red]{len(changes['deleted'])}[/red]")
        console.print(f"  Unchanged: [dim]{len(changes['unchanged'])}[/dim]")

        templates_to_process = changes['new'] + changes['modified']

        if not templates_to_process and not changes['deleted']:
            console.print("\n[bold green]✓[/bold green] All embeddings up to date!")
            return
    else:
        templates_to_process = templates
        console.print("\n[yellow]Force mode:[/yellow] Recomputing all embeddings")

    # Initialize embeddings client
    from src.retrieval.embeddings import EmbeddingsClient
    embeddings_client = EmbeddingsClient()

    # Process embeddings with progress bar
    console.print(f"\nComputing embeddings (batch_size={batch_size})...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:

        task = progress.add_task(
            f"Processing {len(templates_to_process)} templates...",
            total=len(templates_to_process)
        )

        batches = [
            templates_to_process[i:i+batch_size]
            for i in range(0, len(templates_to_process), batch_size)
        ]

        for batch in batches:
            # Compute embeddings for batch
            texts = [f"{t['question']} {t['answer']}" for t in batch]
            embeddings = embeddings_client.embed_batch(texts)

            # Store in database
            with storage.transaction():
                for template, embedding in zip(batch, embeddings):
                    content_hash = compute_content_hash(template['question'], template['answer'])
                    metadata = {
                        'category': template['category'],
                        'subcategory': template['subcategory'],
                        'question': template['question'],
                        'answer': template['answer']
                    }
                    storage.store_embedding(template['id'], embedding, metadata, content_hash)

            progress.update(task, advance=len(batch))

    # Delete removed templates
    if not force and changes['deleted']:
        console.print(f"\nDeleting {len(changes['deleted'])} removed templates...")
        for template_id in changes['deleted']:
            storage.delete_embedding(template_id)

    # Validation
    if validate:
        console.print("\nValidating storage integrity...")
        integrity = storage.validate_integrity()

        if integrity['valid']:
            console.print(f"[bold green]✓[/bold green] Storage valid ({integrity['total_embeddings']} embeddings)")
        else:
            console.print(f"[bold red]✗[/bold red] Storage validation failed:")
            if integrity['corrupted_embeddings']:
                console.print(f"  Corrupted: {len(integrity['corrupted_embeddings'])} embeddings")
            if integrity['missing_metadata']:
                console.print(f"  Missing metadata: {len(integrity['missing_metadata'])} templates")

    # Summary
    console.print("\n[bold green]✓ Migration complete![/bold green]")
    storage_info = storage.get_storage_info()
    console.print(f"  Total embeddings: {storage_info['total_embeddings']}")
    console.print(f"  Storage size: {storage_info['storage_size_mb']:.2f} MB")
    console.print(f"  Backend: {storage_info['backend_type']}")
```

**Pros**:
- Decorator-based, very readable
- Automatic help generation
- Type validation and conversion
- Subcommands support (for future expansion)
- Better error messages than argparse

**Cons**:
- Additional dependency (though lightweight)

---

#### Option 2: Argparse (Not Recommended)

```python
import argparse

def main():
    parser = argparse.ArgumentParser(
        description='Migrate embeddings to persistent storage',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--storage-backend',
        choices=['sqlite', 'postgres'],
        default='sqlite',
        help='Storage backend to use'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='data/embeddings.db',
        help='SQLite database path'
    )

    # ... more arguments

    args = parser.parse_args()

    # Manual validation and error handling
    if args.storage_backend == 'postgres' and not args.postgres_dsn:
        parser.error('--postgres-dsn required for postgres backend')

    # ... rest of logic
```

**Cons** (vs Click):
- More verbose
- Manual validation logic
- Less intuitive API
- Harder to test

---

### Progress Reporting Comparison

#### Option 1: Rich (Recommended)

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Computing embeddings...", total=201)

    for batch in batches:
        # ... process batch
        progress.update(task, advance=len(batch))
```

**Features**:
- Modern terminal UI (colors, spinners, bars)
- Multiple concurrent progress bars
- Time estimates
- Customizable columns
- Works with Click integration

---

#### Option 2: tqdm (Alternative)

```python
from tqdm import tqdm

for batch in tqdm(batches, desc="Computing embeddings"):
    # ... process batch
    pass
```

**Pros**:
- Simpler API
- Widely used
- Minimal code

**Cons**:
- Less visually appealing
- Harder to customize
- No color support by default

---

### Error Handling Patterns

```python
class MigrationError(Exception):
    """Base exception for migration errors."""
    pass

class FAQLoadError(MigrationError):
    """Failed to load FAQ database."""
    pass

class EmbeddingComputeError(MigrationError):
    """Failed to compute embeddings via API."""
    pass

class StorageWriteError(MigrationError):
    """Failed to write to storage backend."""
    pass

# Usage in migration command
try:
    templates = parse_faq(faq_path)
except FileNotFoundError:
    console.print(f"[bold red]Error:[/bold red] FAQ file not found: {faq_path}")
    raise click.Abort()
except Exception as e:
    console.print(f"[bold red]Error loading FAQ:[/bold red] {e}")
    raise click.Abort()

try:
    embeddings = embeddings_client.embed_batch(texts)
except EmbeddingsError as e:
    console.print(f"[bold red]API Error:[/bold red] {e}")
    console.print("Hint: Check SCIBOX_API_KEY environment variable")
    raise click.Abort()

try:
    storage.store_embedding(...)
except StorageError as e:
    console.print(f"[bold red]Storage Error:[/bold red] {e}")
    console.print("Rolling back transaction...")
    raise click.Abort()
```

---

## Research Topic 5: SQLite vs PostgreSQL Best Practices

**Objective**: Document best practices and configuration for each backend

### SQLite Best Practices

#### WAL Mode (Write-Ahead Logging)

```python
def initialize_sqlite_storage(db_path: str):
    """Initialize SQLite with optimal settings."""
    conn = sqlite3.connect(db_path)

    # Enable WAL mode (better concurrency)
    conn.execute("PRAGMA journal_mode=WAL")

    # Other performance optimizations
    conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes, safe for embeddings
    conn.execute("PRAGMA cache_size=-64000")   # 64MB cache
    conn.execute("PRAGMA temp_store=MEMORY")   # Temp tables in memory
    conn.execute("PRAGMA mmap_size=30000000000")  # Memory-mapped I/O

    return conn
```

**WAL Mode Benefits**:
- Readers don't block writers
- Writers don't block readers
- Better concurrency for read-heavy workload
- Transaction log in separate file (.db-wal)

**PRAGMA Settings**:
- `journal_mode=WAL`: Enable write-ahead logging
- `synchronous=NORMAL`: Balance between safety and performance (safe for embeddings, not critical financial data)
- `cache_size`: In-memory page cache size (negative = KB, positive = pages)
- `temp_store=MEMORY`: Store temporary tables in memory
- `mmap_size`: Use memory-mapped I/O for faster reads

---

#### Schema Definition

```sql
-- SQLite schema with optimizations
CREATE TABLE IF NOT EXISTS embeddings (
    template_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    embedding_vector BLOB NOT NULL,  -- Serialized numpy array
    content_hash TEXT NOT NULL,      -- SHA256 for change detection
    model_name TEXT NOT NULL DEFAULT 'bge-m3',
    model_version TEXT NOT NULL DEFAULT 'v1',
    embedding_dimension INTEGER NOT NULL DEFAULT 1024,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_category ON embeddings(category, subcategory);
CREATE INDEX IF NOT EXISTS idx_content_hash ON embeddings(content_hash);
CREATE INDEX IF NOT EXISTS idx_model_version ON embeddings(model_name, model_version);

-- Metadata table for version tracking
CREATE TABLE IF NOT EXISTS storage_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store schema version
INSERT OR REPLACE INTO storage_metadata (key, value)
VALUES ('schema_version', '1.0');
```

---

#### File Locking Considerations

```python
import time
import sqlite3

def safe_write_with_retry(conn, operation, max_retries=3):
    """
    Safely write to SQLite with retry on locked database.

    SQLite uses file-level locking, can encounter SQLITE_BUSY
    if another process is writing.
    """
    for attempt in range(max_retries):
        try:
            return operation(conn)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                continue
            raise
```

---

### PostgreSQL with pg_vector Best Practices

#### Installation and Setup

```sql
-- Install pg_vector extension (requires superuser)
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Docker Setup**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: ankane/pgvector:latest  # PostgreSQL with pg_vector pre-installed
    environment:
      POSTGRES_DB: smartsupport
      POSTGRES_USER: smartsupport_user
      POSTGRES_PASSWORD: your_secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

#### Schema Definition with pg_vector

```sql
-- PostgreSQL schema with native vector type
CREATE TABLE IF NOT EXISTS embeddings (
    template_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    embedding_vector vector(1024) NOT NULL,  -- Native pg_vector type
    content_hash TEXT NOT NULL,
    model_name TEXT NOT NULL DEFAULT 'bge-m3',
    model_version TEXT NOT NULL DEFAULT 'v1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Standard indexes
CREATE INDEX idx_category ON embeddings(category, subcategory);
CREATE INDEX idx_content_hash ON embeddings(content_hash);

-- HNSW index for vector similarity search (optional, for >1000 templates)
CREATE INDEX embeddings_vector_idx ON embeddings
USING hnsw (embedding_vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**HNSW Index Parameters**:
- `m`: Number of connections per layer (default: 16, higher = better recall, more memory)
- `ef_construction`: Size of dynamic candidate list during construction (default: 64)
- `vector_cosine_ops`: Use cosine distance operator

---

#### Connection Pooling

```python
from psycopg2 import pool
import os

class PostgresStorage:
    def __init__(self, dsn: str = None, min_conn: int = 1, max_conn: int = 10):
        """
        Initialize PostgreSQL storage with connection pooling.

        Args:
            dsn: Connection string (e.g., "postgresql://user:pass@localhost/db")
            min_conn: Minimum connections in pool
            max_conn: Maximum connections in pool
        """
        self.dsn = dsn or os.getenv("POSTGRES_DSN")
        if not self.dsn:
            raise ValueError("PostgreSQL DSN required")

        # Create connection pool
        self.pool = pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            self.dsn,
            # Performance settings
            cursor_factory=psycopg2.extras.RealDictCursor,  # Dict-like rows
            connection_factory=None,
            options='-c statement_timeout=30000'  # 30s query timeout
        )

    @contextmanager
    def get_connection(self):
        """Get connection from pool with automatic return."""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def close(self):
        """Close all connections in pool."""
        self.pool.closeall()
```

---

#### Native Vector Operations

```python
def search_similar_native(conn, query_embedding: np.ndarray, category: str, top_k: int = 5):
    """
    Search using pg_vector native cosine distance operator.

    Benefits:
    - Computed in C (faster than Python numpy)
    - HNSW index support (if created)
    - Direct SQL, no serialization overhead
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                template_id,
                category,
                subcategory,
                question,
                answer,
                1 - (embedding_vector <=> %s::vector(1024)) as similarity
            FROM embeddings
            WHERE category = %s
            ORDER BY embedding_vector <=> %s::vector(1024)
            LIMIT %s
            """,
            (query_embedding.tolist(), category, query_embedding.tolist(), top_k)
        )
        return cur.fetchall()
```

**Vector Operators**:
- `<->`: Euclidean distance (L2)
- `<#>`: Negative inner product
- `<=>`: Cosine distance (1 - cosine similarity)

---

### Decision Guide

| Criterion | SQLite | PostgreSQL + pg_vector |
|-----------|--------|----------------------|
| Setup complexity | ✅ Zero (stdlib) | ⚠️ Server + extension required |
| Performance (<1000 templates) | ✅ Excellent | ✅ Excellent |
| Performance (>1000 templates) | ⚠️ Linear scan | ✅ HNSW indexing |
| Concurrent access | ✅ Good (WAL mode) | ✅ Excellent |
| Deployment | ✅ Single file | ⚠️ Separate service |
| Backup | ✅ Copy file | ⚠️ pg_dump/restore |
| Vector operations | ❌ Python numpy | ✅ Native C implementation |
| Memory usage | ✅ Low | ⚠️ Higher (server overhead) |
| Docker complexity | ✅ Volume mount | ⚠️ Multi-service compose |

**Recommendation**:
- **Start with SQLite** (default): 99% of users will be satisfied with performance for 201 templates
- **Upgrade to PostgreSQL** if: >1000 templates, existing PostgreSQL infrastructure, need advanced vector operations

---

## Research Topic 6: Testing with Testcontainers

**Objective**: Design integration tests using testcontainers-python for PostgreSQL

### Decision: Testcontainers for PostgreSQL, In-Memory SQLite for Unit Tests

**Rationale**:
- **Testcontainers**: Real PostgreSQL instance in Docker, exact production parity
- **In-memory SQLite**: Fast unit tests without external dependencies
- **Isolation**: Each test gets fresh database, no state pollution
- **CI/CD**: Works in GitHub Actions with Docker support

### PostgreSQL Container Setup

```python
import pytest
from testcontainers.postgres import PostgresContainer
from psycopg2 import connect

@pytest.fixture(scope="session")
def postgres_container():
    """
    Session-scoped PostgreSQL container with pg_vector.

    Container lifecycle:
    1. Start once at beginning of test session
    2. Reuse across all tests in session
    3. Cleanup at end of session
    """
    # Use image with pg_vector pre-installed
    with PostgresContainer("ankane/pgvector:pg15") as postgres:
        # Wait for container to be ready
        postgres.get_connection_url()

        # Initialize pg_vector extension
        conn = connect(postgres.get_connection_url())
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.close()

        yield postgres

@pytest.fixture
def postgres_storage(postgres_container):
    """
    Function-scoped PostgreSQL storage with fresh schema.

    Each test gets clean database state.
    """
    from src.retrieval.storage import PostgresStorage

    # Get connection URL from container
    dsn = postgres_container.get_connection_url()

    # Create storage instance
    storage = PostgresStorage(dsn)
    storage.connect()

    # Initialize schema
    storage._create_schema()

    yield storage

    # Cleanup: drop all tables
    with storage.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS embeddings CASCADE")
            cur.execute("DROP TABLE IF EXISTS storage_metadata CASCADE")
        conn.commit()

    storage.disconnect()
```

---

### Test Isolation Patterns

#### Pattern 1: Transaction Rollback (Fast)

```python
@pytest.fixture
def postgres_storage_transactional(postgres_container):
    """
    Transactional fixture: rollback after each test.

    Faster than recreating schema, but doesn't test DDL.
    """
    dsn = postgres_container.get_connection_url()
    storage = PostgresStorage(dsn)
    storage.connect()

    # Begin transaction
    with storage.get_connection() as conn:
        conn.autocommit = False
        yield storage
        # Rollback at end of test
        conn.rollback()

    storage.disconnect()
```

**Pros**:
- Very fast (no schema recreation)
- Good for testing DML operations

**Cons**:
- Doesn't test DDL (CREATE TABLE, etc.)
- Shared transaction state across operations

---

#### Pattern 2: Fresh Schema (Complete Isolation)

```python
@pytest.fixture
def postgres_storage_isolated(postgres_container):
    """
    Isolated fixture: fresh schema for each test.

    Slower but complete isolation and DDL testing.
    """
    dsn = postgres_container.get_connection_url()
    storage = PostgresStorage(dsn)
    storage.connect()
    storage._create_schema()

    yield storage

    # Drop schema
    storage._drop_schema()
    storage.disconnect()
```

**Pros**:
- Complete isolation
- Tests schema creation
- No state leakage

**Cons**:
- Slower (schema recreation overhead)

---

### Test Examples

#### Integration Test: Store and Load

```python
import numpy as np
from src.retrieval.storage import PostgresStorage

def test_store_and_load_embedding(postgres_storage):
    """Test storing and loading a single embedding."""
    # Arrange
    template_id = "test_001"
    embedding = np.random.randn(1024).astype(np.float32)
    metadata = {
        'category': 'Test Category',
        'subcategory': 'Test Subcategory',
        'question': 'Test question?',
        'answer': 'Test answer.'
    }
    content_hash = "abc123def456"

    # Act: Store
    postgres_storage.store_embedding(template_id, embedding, metadata, content_hash)

    # Act: Load
    results = postgres_storage.load_embeddings()

    # Assert
    assert len(results) == 1
    loaded_id, loaded_embedding, loaded_metadata = results[0]

    assert loaded_id == template_id
    assert np.allclose(loaded_embedding, embedding, atol=1e-6)
    assert loaded_metadata['category'] == metadata['category']
    assert loaded_metadata['question'] == metadata['question']

def test_get_by_category(postgres_storage):
    """Test filtering embeddings by category."""
    # Arrange: Store embeddings in different categories
    embeddings_data = [
        ("tmpl_001", "Category A", "Subcategory 1"),
        ("tmpl_002", "Category A", "Subcategory 1"),
        ("tmpl_003", "Category A", "Subcategory 2"),
        ("tmpl_004", "Category B", "Subcategory 1"),
    ]

    for template_id, category, subcategory in embeddings_data:
        embedding = np.random.randn(1024).astype(np.float32)
        metadata = {
            'category': category,
            'subcategory': subcategory,
            'question': f'Q {template_id}',
            'answer': f'A {template_id}'
        }
        postgres_storage.store_embedding(template_id, embedding, metadata, "hash")

    # Act
    results = postgres_storage.get_by_category("Category A", "Subcategory 1")

    # Assert
    assert len(results) == 2
    result_ids = [r[0] for r in results]
    assert "tmpl_001" in result_ids
    assert "tmpl_002" in result_ids
    assert "tmpl_003" not in result_ids

def test_change_detection(postgres_storage):
    """Test incremental update via content hash."""
    # Arrange: Store initial embedding
    template_id = "tmpl_001"
    embedding = np.random.randn(1024).astype(np.float32)
    metadata = {'category': 'Cat', 'subcategory': 'Sub', 'question': 'Q1', 'answer': 'A1'}
    hash1 = "hash_v1"

    postgres_storage.store_embedding(template_id, embedding, metadata, hash1)

    # Act: Check hash
    stored_hash = postgres_storage.get_content_hash(template_id)
    assert stored_hash == hash1

    # Act: Update with new content hash
    new_embedding = np.random.randn(1024).astype(np.float32)
    hash2 = "hash_v2"
    postgres_storage.update_embedding(template_id, new_embedding, hash2)

    # Assert: Hash and embedding updated
    updated_hash = postgres_storage.get_content_hash(template_id)
    assert updated_hash == hash2

    results = postgres_storage.load_embeddings()
    assert len(results) == 1
    assert np.allclose(results[0][1], new_embedding, atol=1e-6)
```

---

### SQLite In-Memory Tests (Unit Tests)

```python
@pytest.fixture
def sqlite_storage_memory():
    """In-memory SQLite storage for fast unit tests."""
    from src.retrieval.storage import SQLiteStorage

    # Use special :memory: path for in-memory database
    storage = SQLiteStorage(":memory:")
    storage.connect()
    storage._create_schema()

    yield storage

    storage.disconnect()

def test_sqlite_store_and_load(sqlite_storage_memory):
    """Test SQLite storage (fast, no Docker required)."""
    # Same test logic as PostgreSQL
    template_id = "test_001"
    embedding = np.random.randn(1024).astype(np.float32)
    metadata = {...}

    sqlite_storage_memory.store_embedding(template_id, embedding, metadata, "hash")
    results = sqlite_storage_memory.load_embeddings()

    assert len(results) == 1
    assert results[0][0] == template_id
```

---

### Cleanup Strategies

#### Session-Level Cleanup (Container)

```python
@pytest.fixture(scope="session", autouse=True)
def cleanup_containers():
    """Ensure all containers are cleaned up at session end."""
    yield
    # Testcontainers automatically cleans up, but can force:
    import docker
    client = docker.from_env()
    containers = client.containers.list(filters={"label": "testcontainers=true"})
    for container in containers:
        container.stop()
        container.remove()
```

---

#### Test-Level Cleanup (Data)

```python
@pytest.fixture(autouse=True)
def reset_database_state(postgres_storage):
    """Clear all data before each test."""
    yield
    # Cleanup after test
    with postgres_storage.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE embeddings")
        conn.commit()
```

---

### CI/CD Configuration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      docker:
        image: docker:24-dind
        options: --privileged

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests (with testcontainers)
        run: |
          pytest tests/integration/retrieval/ -v
        env:
          DOCKER_HOST: unix:///var/run/docker.sock
          TESTCONTAINERS_RYUK_DISABLED: true  # Disable Ryuk for CI
```

---

## Summary and Recommendations

### Final Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| **Vector Storage** | SQLite BLOB (default) + PostgreSQL pg_vector (optional) | Flexibility, zero-config default, advanced option available |
| **Content Hashing** | SHA256 | Cross-platform, collision-resistant, standard library |
| **Storage Abstraction** | Abstract Base Class (ABC) | Type safety, IDE support, enforced contracts |
| **Migration CLI** | Click + Rich | Better UX, modern progress bars, decorator-based API |
| **SQLite Config** | WAL mode, optimized PRAGMAs | Better concurrency, safe for embedding workload |
| **PostgreSQL** | Connection pooling, pg_vector with HNSW (optional) | Scalability, native vector operations |
| **Testing** | Testcontainers (PostgreSQL) + In-memory SQLite (unit) | Production parity, fast unit tests |

---

### Implementation Checklist

- [ ] **Phase 0 Complete**: All research decisions documented
- [ ] **Storage backends**: SQLite and PostgreSQL implementations ready
- [ ] **Hashing utilities**: SHA256 content hash functions
- [ ] **Migration command**: Click-based CLI with Rich progress bars
- [ ] **Configuration**: WAL mode for SQLite, connection pooling for PostgreSQL
- [ ] **Testing**: Testcontainers fixtures for integration tests
- [ ] **Documentation**: Decision guide for users choosing backend

---

### Next Steps (Phase 1)

1. **data-model.md**: Define database schemas (embeddings table, metadata table)
2. **contracts/storage-api.yaml**: Complete `StorageBackend` interface specification
3. **quickstart.md**: User guide for migration and configuration
4. **Update requirements.txt**: Add `click`, `rich`, `psycopg2-binary` (optional), `testcontainers`

All research findings validated against spec requirements - ready for Phase 1 design and implementation.
