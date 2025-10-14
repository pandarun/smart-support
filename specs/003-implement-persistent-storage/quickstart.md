# Quickstart: Persistent Embedding Storage

**Feature**: 003-implement-persistent-storage
**Purpose**: Guide for migrating to and using persistent embedding storage

## Overview

This guide covers:
1. Running the one-time migration to populate storage
2. Configuring SQLite vs PostgreSQL backends
3. Incremental update workflow
4. Troubleshooting common issues

## Prerequisites

- Python 3.11+
- Smart Support system installed
- SCIBOX_API_KEY configured in `.env`
- FAQ database at `docs/smart_support_vtb_belarus_faq_final.xlsx`

## Quick Start (SQLite - Default)

### Step 1: Run Migration Command

The migration command precomputes all 201 embeddings and stores them in SQLite:

```bash
# From project root
python -m src.cli.migrate_embeddings \
    --faq-path docs/smart_support_vtb_belarus_faq_final.xlsx \
    --storage-backend sqlite \
    --sqlite-path data/embeddings.db
```

**What it does**:
- Parses FAQ database (201 templates)
- Computes embeddings using Scibox API (bge-m3 model)
- Stores embeddings in `data/embeddings.db`
- Validates storage integrity
- Reports completion time

**Expected output**:
```
╭─────────────────────────────────────────────────────────────╮
│  Smart Support - Embedding Storage Migration               │
╰─────────────────────────────────────────────────────────────╯

[INFO] Loading FAQ database...
[INFO] Found 201 templates across 6 categories

[INFO] Initializing SQLite storage at data/embeddings.db
[INFO] Creating schema and indexes

[INFO] Computing embeddings (batch size: 10)
Computing embeddings: ████████████████████ 201/201 (100%) | 0:00:08 elapsed

[INFO] Storing embeddings in database
Storing embeddings: ████████████████████ 201/201 (100%) | 0:00:01 elapsed

[INFO] Validating storage integrity
✓ All 201 embeddings stored successfully
✓ Content hashes verified
✓ Foreign key constraints satisfied

Migration complete! 🎉
├─ Total time: 9.2 seconds
├─ Templates processed: 201
├─ Database size: 1.1 MB
└─ Storage path: /app/data/embeddings.db

Next steps:
1. Restart Smart Support to use persistent storage
2. Verify startup time < 2 seconds (was ~9 seconds)
3. Monitor data/embeddings.db file (should persist across restarts)
```

### Step 2: Verify Persistence

Restart the system and verify fast startup:

```bash
# Stop system
docker-compose down

# Start with persistent storage
docker-compose up

# Should see in logs:
# [INFO] Loading embeddings from storage (data/embeddings.db)
# [INFO] Loaded 201 embeddings in 0.05s
# [INFO] System ready (total startup: 1.8s)
```

**Before persistence**: ~9 seconds (precomputation)
**After persistence**: <2 seconds (load from disk)

---

## Configuration

### SQLite Configuration (Default)

Add to `.env`:
```bash
# Storage Backend
STORAGE_BACKEND=sqlite
SQLITE_DB_PATH=data/embeddings.db
```

**Advantages**:
- Zero configuration
- File-based (easy backup)
- Cross-platform
- Perfect for single-node deployment

**Recommended for**:
- Development
- Small production deployments (<1000 templates)
- Docker container deployments

### PostgreSQL Configuration (Optional)

For advanced use cases with scaling requirements:

**1. Start PostgreSQL with pg_vector**:

Add to `docker-compose.yml`:
```yaml
services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: smart_support
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**2. Configure environment**:

Add to `.env`:
```bash
# Storage Backend
STORAGE_BACKEND=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DATABASE=smart_support
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_POOL_SIZE=5
```

**3. Run migration**:
```bash
python -m src.cli.migrate_embeddings \
    --storage-backend postgres \
    --postgres-host localhost \
    --postgres-database smart_support \
    --postgres-user postgres \
    --postgres-password secret
```

**Advantages**:
- Better concurrent read performance
- Native vector operations (pg_vector)
- HNSW indexing for ANN search
- Advanced backup/replication

**Recommended for**:
- Production with high concurrency
- Scaling to 10K+ templates
- Multi-instance deployments

---

## Incremental Updates

When FAQ database changes (new/modified/deleted templates):

### Automatic Detection

The system automatically detects changes using content hashing:

```bash
# Update FAQ file (add/modify templates)
vim docs/smart_support_vtb_belarus_faq_final.xlsx

# Run incremental update
python -m src.cli.migrate_embeddings \
    --faq-path docs/smart_support_vtb_belarus_faq_final.xlsx \
    --incremental
```

**What it does**:
1. Compares current FAQ with stored content hashes
2. Identifies: new templates, modified templates, deleted templates
3. Computes embeddings only for new/modified (saves API costs!)
4. Updates storage atomically
5. Removes deleted templates

**Expected output**:
```
[INFO] Analyzing FAQ changes...
├─ New templates: 5
├─ Modified templates: 2
├─ Deleted templates: 1
└─ Unchanged: 193

[INFO] Computing embeddings for 7 templates
Computing embeddings: ████████████████████ 7/7 (100%) | 0:00:02 elapsed

[INFO] Updating storage
✓ 5 new templates stored
✓ 2 modified templates updated
✓ 1 deleted template removed

Incremental update complete! 🎉
├─ Total time: 2.3 seconds
├─ API calls saved: 193 (96%)
└─ Storage size: 1.1 MB
```

### Force Full Recompute

To recompute all embeddings (e.g., after model upgrade):

```bash
python -m src.cli.migrate_embeddings \
    --faq-path docs/smart_support_vtb_belarus_faq_final.xlsx \
    --force-recompute
```

This ignores stored hashes and recomputes everything.

---

## Docker Deployment

### SQLite with Volume Mount

**docker-compose.yml**:
```yaml
services:
  smart-support:
    image: smart-support:latest
    volumes:
      - ./data:/app/data  # Persist embeddings.db
    environment:
      - STORAGE_BACKEND=sqlite
      - SQLITE_DB_PATH=/app/data/embeddings.db
```

**First deployment**:
```bash
# Run migration inside container
docker-compose run smart-support python -m src.cli.migrate_embeddings

# Or run migration on host before starting
python -m src.cli.migrate_embeddings
docker-compose up
```

**Subsequent deployments**:
```bash
# embeddings.db persists in ./data/
docker-compose up  # Fast startup (<2s)
```

### PostgreSQL with External Database

**docker-compose.yml**:
```yaml
services:
  smart-support:
    image: smart-support:latest
    environment:
      - STORAGE_BACKEND=postgres
      - POSTGRES_HOST=db.example.com
      - POSTGRES_DATABASE=smart_support
    depends_on:
      - postgres

  postgres:
    image: ankane/pgvector:latest
    # ...
```

---

## Validation & Troubleshooting

### Verify Storage Integrity

Check storage is working correctly:

```bash
python -m src.cli.migrate_embeddings --validate
```

**Output**:
```
[INFO] Validating storage integrity...

✓ Connection successful
✓ Schema version: 1.0.0
✓ Embedding version: bge-m3 v1 (1024 dims)
✓ Total templates: 201
✓ All categories present: 6/6
✓ Content hashes valid: 201/201
✓ No orphaned records
✓ Foreign key constraints satisfied

Validation passed! 🎉
```

### Common Issues

#### Issue 1: Database file not found

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'data/embeddings.db'
```

**Solution**:
```bash
# Create data directory
mkdir -p data

# Run migration
python -m src.cli.migrate_embeddings
```

#### Issue 2: Permission denied

**Error**:
```
PermissionError: [Errno 13] Permission denied: 'data/embeddings.db'
```

**Solution**:
```bash
# Fix permissions
chmod 666 data/embeddings.db

# Or run as correct user in Docker
docker-compose run --user $(id -u):$(id -g) smart-support ...
```

#### Issue 3: Slow startup (not loading from storage)

**Symptom**: Startup still takes ~9 seconds

**Diagnosis**:
```bash
# Check if storage is configured
grep STORAGE_BACKEND .env

# Check if database exists and has data
sqlite3 data/embeddings.db "SELECT COUNT(*) FROM embedding_records;"
# Should output: 201
```

**Solution**:
- Ensure `STORAGE_BACKEND=sqlite` in `.env`
- Verify `data/embeddings.db` exists and is not empty
- Check application logs for "Loading embeddings from storage" message

#### Issue 4: PostgreSQL connection failed

**Error**:
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection from host
psql -h localhost -U postgres -d smart_support

# Verify pg_vector extension
psql -h localhost -U postgres -d smart_support -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

#### Issue 5: Dimension mismatch

**Error**:
```
ValueError: Embedding dimension mismatch: expected 1024, got 768
```

**Solution**:
```bash
# Model changed - force recompute
python -m src.cli.migrate_embeddings --force-recompute
```

---

## Performance Benchmarks

### Startup Time

| Configuration | Before (In-Memory) | After (Persistent) | Improvement |
|---------------|-------------------|--------------------|-------------|
| SQLite | ~9 seconds | ~1.8 seconds | 80% faster |
| PostgreSQL | ~9 seconds | ~2.1 seconds | 77% faster |
| PostgreSQL (remote) | ~9 seconds | ~2.5 seconds | 72% faster |

### Incremental Update

| Templates Changed | Embedding Time | Storage Time | Total Time |
|------------------|----------------|--------------|------------|
| 1 new | 0.25s | 0.05s | 0.3s |
| 5 new | 1.2s | 0.1s | 1.3s |
| 10 modified | 2.4s | 0.2s | 2.6s |
| 50 new | 12s | 0.5s | 12.5s |

### Query Performance

| Operation | In-Memory | SQLite | PostgreSQL | Overhead |
|-----------|-----------|--------|------------|----------|
| Load all embeddings | 0.5ms | 50ms | 100ms | 100x-200x (one-time) |
| Filter by category | 0.1ms | 5ms | 10ms | 50x-100x (per query) |
| Check template exists | 0.01ms | 1ms | 2ms | 100x-200x |

**Note**: Storage overhead only affects startup and incremental updates, not retrieval queries (embeddings loaded into memory at startup).

---

## Migration from In-Memory to Persistent

### Step-by-Step Migration

1. **Backup current system** (optional but recommended):
   ```bash
   docker-compose down
   tar -czf backup-$(date +%Y%m%d).tar.gz data/ docs/
   ```

2. **Run migration**:
   ```bash
   python -m src.cli.migrate_embeddings
   ```

3. **Update docker-compose.yml**:
   ```yaml
   volumes:
     - ./data:/app/data  # Add this line
   ```

4. **Restart system**:
   ```bash
   docker-compose up
   ```

5. **Verify startup time**:
   - Check logs for "Loaded embeddings in X.XXs"
   - Should be <2 seconds
   - Old behavior: "Precomputed embeddings in X.XXs" (~9 seconds)

6. **Test retrieval accuracy**:
   ```bash
   python scripts/run_validation_v2.py
   ```
   - Should maintain 86.7% top-3 accuracy
   - No accuracy loss from persistence

---

## Advanced Usage

### Batch Migration for Multiple Environments

```bash
# Development
python -m src.cli.migrate_embeddings \
    --sqlite-path data/dev-embeddings.db

# Staging
python -m src.cli.migrate_embeddings \
    --sqlite-path data/staging-embeddings.db

# Production
python -m src.cli.migrate_embeddings \
    --storage-backend postgres \
    --postgres-host prod-db.example.com
```

### Backup and Restore

**SQLite**:
```bash
# Backup
cp data/embeddings.db data/embeddings-backup-$(date +%Y%m%d).db

# Restore
cp data/embeddings-backup-20251015.db data/embeddings.db
```

**PostgreSQL**:
```bash
# Backup
pg_dump -h localhost -U postgres smart_support > backup.sql

# Restore
psql -h localhost -U postgres smart_support < backup.sql
```

### Schema Migration

When upgrading to new schema version:

```bash
# Apply migration
python -m src.cli.migrate_embeddings --migrate-schema

# Force recompute if dimension changed
python -m src.cli.migrate_embeddings --force-recompute
```

---

## Next Steps

After migration is complete:

1. ✅ **Verify startup performance** (<2 seconds)
2. ✅ **Test incremental updates** (add/modify FAQ templates)
3. ✅ **Monitor storage size** (should be ~1MB for 201 templates)
4. ✅ **Run validation** (maintain 86.7% top-3 accuracy)
5. ✅ **Document deployment** (update README with storage setup)

**Ready to proceed with UI implementation!** 🚀

The operator interface can now benefit from:
- Fast system startup (operators don't wait 9 seconds)
- Efficient content updates (minimal API costs)
- Reliable data persistence (no recomputation on crashes)

See [../plan.md](./plan.md) for full implementation plan.
