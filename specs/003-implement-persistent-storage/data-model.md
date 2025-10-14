# Data Model: Persistent Embedding Storage

**Feature**: 003-implement-persistent-storage
**Created**: 2025-10-15
**Purpose**: Define database schema for storing embedding vectors and metadata

## Overview

The embedding storage system uses a relational schema supporting both SQLite and PostgreSQL backends. The model tracks embedding versions, template metadata, and content hashes for change detection.

## Entity Relationship

```
┌─────────────────────┐
│  embedding_versions │
│  (version tracking) │
└──────────┬──────────┘
           │ 1:N
           │
┌──────────▼──────────┐
│  embedding_records  │
│  (vector storage)   │
└─────────────────────┘
```

## Core Entities

### 1. embedding_versions

Tracks different embedding model versions to support model upgrades and migration.

**Purpose**: Ensure embedding consistency when model changes (e.g., bge-m3 v1 → v2)

**Schema**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| version_id | INTEGER | PRIMARY KEY AUTO | Unique version identifier |
| model_name | TEXT | NOT NULL | Model identifier (e.g., "bge-m3") |
| model_version | TEXT | NOT NULL | Model version string |
| embedding_dimension | INTEGER | NOT NULL | Vector dimensionality (e.g., 1024) |
| is_current | BOOLEAN | NOT NULL DEFAULT TRUE | Whether this version is active |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | Version creation time |

**Indexes**:
- `UNIQUE(model_name, model_version, embedding_dimension)` - Prevent duplicate versions
- `INDEX(is_current)` - Fast lookup of current version

**Constraints**:
- Only one version can have `is_current=TRUE` at a time
- Cannot delete version if embeddings reference it

**Example Data**:
```sql
INSERT INTO embedding_versions VALUES (
  1,                    -- version_id
  'bge-m3',            -- model_name
  'v1',                -- model_version
  1024,                -- embedding_dimension
  TRUE,                -- is_current
  '2025-10-15 00:00:00' -- created_at
);
```

---

### 2. embedding_records

Stores embedding vectors and associated template metadata.

**Purpose**: Persistent storage of computed embeddings with all required metadata for retrieval

**Schema**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| record_id | INTEGER | PRIMARY KEY AUTO | Unique record identifier |
| template_id | TEXT | NOT NULL UNIQUE | FAQ template identifier (e.g., "tmpl_001") |
| version_id | INTEGER | NOT NULL FOREIGN KEY | References embedding_versions |
| embedding_vector | BLOB/VECTOR | NOT NULL | Serialized numpy array (SQLite) or native vector (PostgreSQL) |
| category | TEXT | NOT NULL | Main category (e.g., "Продукты - Вклады") |
| subcategory | TEXT | NOT NULL | Subcategory (e.g., "Рублевые - Мои условия") |
| question_text | TEXT | NOT NULL | Template question |
| answer_text | TEXT | NOT NULL | Template answer |
| content_hash | TEXT | NOT NULL | SHA256 hash of question + answer |
| success_rate | REAL | DEFAULT 0.5 | Historical success rate (0.0-1.0) |
| usage_count | INTEGER | DEFAULT 0 | Number of times template used |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | Last update time |

**Indexes**:
- `UNIQUE(template_id)` - Template IDs are unique
- `INDEX(version_id)` - Filter by embedding version
- `INDEX(category, subcategory)` - Fast category-based retrieval
- `INDEX(content_hash)` - Change detection lookup
- PostgreSQL only: `INDEX USING hnsw (embedding_vector vector_cosine_ops)` - ANN search

**Constraints**:
- `embedding_vector` size must match `embedding_versions.embedding_dimension`
- `success_rate` must be between 0.0 and 1.0
- `usage_count` must be non-negative

**Storage Considerations**:
- **SQLite**: embedding_vector stored as BLOB (~4100 bytes for 1024 floats)
- **PostgreSQL**: embedding_vector stored as native `vector(1024)` type (requires pg_vector extension)
- Total storage: ~201 templates × 4KB ≈ 800KB + metadata ≈ 1MB total

**Example Data**:
```sql
INSERT INTO embedding_records VALUES (
  1,                    -- record_id
  'tmpl_109',          -- template_id
  1,                    -- version_id
  <binary_data>,       -- embedding_vector (numpy array or vector type)
  'Продукты - Вклады', -- category
  'Рублевые - Мои условия', -- subcategory
  'Как открыть вклад Мои условия?', -- question_text
  'Посетите отделение банка или воспользуйтесь мобильным приложением.', -- answer_text
  'a3f2b1...',         -- content_hash (SHA256)
  0.5,                  -- success_rate
  0,                    -- usage_count
  '2025-10-15 00:00:00', -- created_at
  '2025-10-15 00:00:00'  -- updated_at
);
```

---

## Database Creation Scripts

### SQLite Schema

```sql
-- Enable WAL mode for better concurrency
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

CREATE INDEX idx_embedding_versions_current ON embedding_versions(is_current);

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

CREATE INDEX idx_embedding_records_version ON embedding_records(version_id);
CREATE INDEX idx_embedding_records_category ON embedding_records(category, subcategory);
CREATE INDEX idx_embedding_records_hash ON embedding_records(content_hash);

-- Trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_embedding_records_timestamp
AFTER UPDATE ON embedding_records
FOR EACH ROW
BEGIN
    UPDATE embedding_records SET updated_at = CURRENT_TIMESTAMP WHERE record_id = NEW.record_id;
END;
```

### PostgreSQL Schema

```sql
-- Enable pg_vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Embedding versions table
CREATE TABLE IF NOT EXISTS embedding_versions (
    version_id SERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(model_name, model_version, embedding_dimension),
    CHECK (embedding_dimension > 0)
);

CREATE INDEX idx_embedding_versions_current ON embedding_versions(is_current) WHERE is_current = TRUE;

-- Embedding records table
CREATE TABLE IF NOT EXISTS embedding_records (
    record_id SERIAL PRIMARY KEY,
    template_id TEXT NOT NULL UNIQUE,
    version_id INTEGER NOT NULL REFERENCES embedding_versions(version_id) ON DELETE RESTRICT,
    embedding_vector vector(1024) NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    success_rate REAL NOT NULL DEFAULT 0.5 CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    usage_count INTEGER NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_embedding_records_version ON embedding_records(version_id);
CREATE INDEX idx_embedding_records_category ON embedding_records(category, subcategory);
CREATE INDEX idx_embedding_records_hash ON embedding_records(content_hash);

-- HNSW index for approximate nearest neighbor search (optional, for future scaling)
-- CREATE INDEX idx_embedding_records_vector ON embedding_records
-- USING hnsw (embedding_vector vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_embedding_records_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_embedding_records_timestamp
BEFORE UPDATE ON embedding_records
FOR EACH ROW
EXECUTE FUNCTION update_embedding_records_timestamp();
```

---

## Data Operations

### Insert Operations

**Create new version**:
```sql
INSERT INTO embedding_versions (model_name, model_version, embedding_dimension, is_current)
VALUES ('bge-m3', 'v1', 1024, TRUE);
```

**Store embedding** (SQLite):
```sql
INSERT INTO embedding_records (
    template_id, version_id, embedding_vector, category, subcategory,
    question_text, answer_text, content_hash
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?
);
-- embedding_vector is serialized numpy array: vector.tobytes()
```

**Store embedding** (PostgreSQL):
```sql
INSERT INTO embedding_records (
    template_id, version_id, embedding_vector, category, subcategory,
    question_text, answer_text, content_hash
) VALUES (
    %s, %s, %s::vector, %s, %s, %s, %s, %s
);
-- embedding_vector is formatted as '[0.1,0.2,...]'
```

### Query Operations

**Load all embeddings for current version**:
```sql
SELECT er.* FROM embedding_records er
JOIN embedding_versions ev ON er.version_id = ev.version_id
WHERE ev.is_current = TRUE;
```

**Filter by category**:
```sql
SELECT * FROM embedding_records
WHERE category = ? AND subcategory = ?;
```

**Check if template exists**:
```sql
SELECT COUNT(*) FROM embedding_records WHERE template_id = ?;
```

**Detect changed templates** (for incremental updates):
```sql
SELECT template_id, content_hash FROM embedding_records;
-- Compare hashes with current FAQ content in application code
```

### Update Operations

**Update embedding when content changes**:
```sql
UPDATE embedding_records
SET
    embedding_vector = ?,
    question_text = ?,
    answer_text = ?,
    content_hash = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE template_id = ?;
```

**Update success metrics**:
```sql
UPDATE embedding_records
SET
    success_rate = ?,
    usage_count = usage_count + 1
WHERE template_id = ?;
```

### Delete Operations

**Delete single template**:
```sql
DELETE FROM embedding_records WHERE template_id = ?;
```

**Clear all embeddings for a version**:
```sql
DELETE FROM embedding_records WHERE version_id = ?;
```

---

## Migration Strategy

### Version Upgrade Flow

When embedding model changes (e.g., dimension 1024 → 2048):

1. **Create new version**:
   ```sql
   INSERT INTO embedding_versions (model_name, model_version, embedding_dimension, is_current)
   VALUES ('bge-m3', 'v2', 2048, FALSE);
   ```

2. **Recompute all embeddings** with new model

3. **Mark new version as current**:
   ```sql
   BEGIN TRANSACTION;
   UPDATE embedding_versions SET is_current = FALSE WHERE is_current = TRUE;
   UPDATE embedding_versions SET is_current = TRUE WHERE version_id = ?;
   COMMIT;
   ```

4. **Clean up old embeddings** (optional):
   ```sql
   DELETE FROM embedding_records WHERE version_id IN (
       SELECT version_id FROM embedding_versions WHERE is_current = FALSE
   );
   DELETE FROM embedding_versions WHERE is_current = FALSE;
   ```

---

## Performance Considerations

### Expected Performance

**Storage Size**:
- 201 templates × 4KB per embedding ≈ 800KB
- Metadata overhead ≈ 200KB
- Total database size ≈ 1MB

**Query Performance** (single category filter):
- SQLite: <5ms (indexed category lookup + BLOB deserialization)
- PostgreSQL: <10ms (indexed category lookup + network)
- In-memory baseline: <1ms (direct array access)

**Load Time** (all embeddings on startup):
- SQLite: <50ms (read 1MB file + deserialize 201 BLOBs)
- PostgreSQL: <100ms (network + deserialize 201 rows)
- Target: <2 seconds total (including FAQ parsing and initialization)

### Optimization Strategies

1. **SQLite**:
   - Use WAL mode for concurrent reads
   - Optimize PRAGMA settings (cache_size, mmap_size)
   - Batch inserts in transactions (20x faster)

2. **PostgreSQL**:
   - Use connection pooling (pgbouncer)
   - Batch operations with COPY or multi-row INSERT
   - Consider HNSW index for >10K templates

3. **Application-Level**:
   - Load embeddings at startup, not per-query
   - Cache frequently accessed templates
   - Use prepared statements for common queries

---

## Data Integrity

### Validation Rules

1. **Referential Integrity**:
   - All embeddings must reference valid version
   - Cannot delete version with active embeddings

2. **Content Consistency**:
   - Template ID must be unique
   - Embedding dimension must match version
   - Content hash must be valid SHA256 (64 hex chars)

3. **Metric Bounds**:
   - Success rate: 0.0 ≤ rate ≤ 1.0
   - Usage count: count ≥ 0

### Error Handling

**Duplicate template_id**:
- SQLite: UNIQUE constraint violation (SQLITE_CONSTRAINT)
- PostgreSQL: UNIQUE constraint violation (23505 error code)
- Recovery: Update existing record instead of insert

**Missing version**:
- Foreign key constraint violation
- Recovery: Create version first, then insert record

**Corrupted embedding vector**:
- Deserialization error (invalid BLOB format)
- Recovery: Recompute embedding from source template

---

## Schema Evolution

### Migration Workflow

When schema changes (e.g., adding new column):

1. **Create migration script**: `migrations/001_add_priority_column.sql`
2. **Apply migration**:
   ```sql
   ALTER TABLE embedding_records ADD COLUMN priority INTEGER DEFAULT 1;
   ```
3. **Update schema version**: Track applied migrations in `schema_migrations` table
4. **Test backward compatibility**: Ensure old code can read new schema

### Migration Tracking

Optional schema_migrations table for tracking applied migrations:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## Testing Data

### Sample Test Records

For unit and integration tests:

```sql
-- Test version
INSERT INTO embedding_versions VALUES (1, 'test-model', 'v1', 4, TRUE, CURRENT_TIMESTAMP);

-- Test embedding (4-dimensional for simplicity)
INSERT INTO embedding_records VALUES (
    1, 'test_001', 1,
    X'3F800000 3F800000 3F800000 3F800000',  -- [1.0, 1.0, 1.0, 1.0] as BLOB
    'Test Category', 'Test Subcategory',
    'Test question?', 'Test answer.',
    '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
    0.5, 0,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
);
```

### Test Fixtures

Pytest fixtures for in-memory SQLite testing:

```python
@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database for testing."""
    import sqlite3
    conn = sqlite3.connect(':memory:')
    # Apply schema
    conn.executescript(SQLITE_SCHEMA)
    yield conn
    conn.close()
```

---

## Summary

This data model provides:
- ✅ Version tracking for model upgrades
- ✅ Efficient storage for 1024-dim embeddings
- ✅ Change detection via content hashing
- ✅ Category-based filtering with indexes
- ✅ Cross-platform compatibility (SQLite + PostgreSQL)
- ✅ Data integrity constraints
- ✅ Performance optimization (<2s startup, <5ms queries)

**Next Steps**: See [contracts/storage-api.yaml](./contracts/storage-api.yaml) for storage interface specification.
