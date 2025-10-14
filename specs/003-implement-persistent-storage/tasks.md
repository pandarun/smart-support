# Tasks: Persistent Embedding Storage

**Feature Branch**: `003-implement-persistent-storage`
**Input**: Design documents from `/specs/003-implement-persistent-storage/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/storage-api.yaml, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
Single project structure (per plan.md):
- `src/` - Source code root
- `tests/` - Test root
- `data/` - Storage files (SQLite databases)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create storage module directory structure: `src/retrieval/storage/` with `__init__.py`, `base.py`, `models.py`
- [ ] T002 [P] Create utility module for hashing: `src/utils/hashing.py`
- [ ] T003 [P] Create CLI module directory: `src/cli/` with `__init__.py`
- [ ] T004 [P] Update `requirements.txt` with new dependencies: `click>=8.0.0`, `rich>=13.0.0`, `psycopg2-binary>=2.9.0` (optional)
- [ ] T005 [P] Update `requirements-dev.txt` with testing dependencies: `testcontainers>=3.7.0`, `pytest-asyncio>=0.21.0`
- [ ] T006 [P] Create test directory structure: `tests/unit/retrieval/`, `tests/integration/retrieval/`
- [ ] T007 Update `.gitignore` to exclude `data/embeddings.db` and `data/*.db`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core storage infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Implement content hashing utilities in `src/utils/hashing.py`:
  - `compute_content_hash(question: str, answer: str) -> str` using SHA256
  - Handles UTF-8 encoding for Cyrillic text
- [ ] T009 Define storage data models in `src/retrieval/storage/models.py`:
  - `EmbeddingRecordCreate` (Pydantic model for insertion)
  - `EmbeddingRecord` (Pydantic model with all fields)
  - `EmbeddingVersion` (Pydantic model for version tracking)
  - `StorageConfig` (Pydantic model for configuration)
- [ ] T010 Implement abstract storage interface in `src/retrieval/storage/base.py`:
  - `StorageBackend` ABC with 20 abstract methods per contracts/storage-api.yaml
  - Context manager protocol (`__enter__`, `__exit__`)
  - Exception hierarchy: `StorageError`, `ConnectionError`, `IntegrityError`, `NotFoundError`, `SerializationError`, `ValidationError`
- [ ] T011 Create database schema scripts:
  - SQLite schema in `src/retrieval/storage/sqlite_backend.py` (as module constant)
  - PostgreSQL schema in `src/retrieval/storage/postgres_backend.py` (as module constant)
  - Includes tables: `embedding_versions`, `embedding_records`
  - Includes indexes per data-model.md

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Fast System Startup (Priority: P1) 🎯 MVP

**Goal**: System startup time reduces from ~9 seconds to under 2 seconds by loading pre-computed embeddings from persistent storage instead of recomputing on every restart.

**Independent Test**:
1. Start application with pre-populated storage (201 embeddings)
2. Measure time from startup to first ready state
3. Should be under 2 seconds (vs. current ~9 seconds)
4. Verify 201 embeddings loaded correctly
5. Test retrieval query works with stored embeddings (maintain 86.7% accuracy)

### Implementation for User Story 1

- [ ] T012 [P] [US1] Implement SQLite backend in `src/retrieval/storage/sqlite_backend.py`:
  - Inherit from `StorageBackend`
  - Connection management with WAL mode and optimized PRAGMAs per research.md
  - Implement `connect()`, `disconnect()`, `is_connected()`
  - Implement `initialize_schema()` with SQLite schema from data-model.md
- [ ] T013 [P] [US1] Implement PostgreSQL backend in `src/retrieval/storage/postgres_backend.py`:
  - Inherit from `StorageBackend`
  - Connection pooling with psycopg2
  - Implement `connect()`, `disconnect()`, `is_connected()`
  - Implement `initialize_schema()` with PostgreSQL schema from data-model.md
  - Register pg_vector extension
- [ ] T014 [US1] Implement version management methods in SQLite backend:
  - `get_or_create_version(model_name, model_version, embedding_dimension) -> int`
  - `get_current_version() -> Optional[EmbeddingVersion]`
  - `set_current_version(version_id: int)`
- [ ] T015 [US1] Implement version management methods in PostgreSQL backend:
  - Same methods as T014 for PostgreSQL
- [ ] T016 [US1] Implement embedding serialization in SQLite backend:
  - Serialize numpy arrays to BLOB using `numpy.save()` per research.md
  - Deserialize BLOBs to numpy arrays using `numpy.load()`
- [ ] T017 [US1] Implement vector formatting in PostgreSQL backend:
  - Format numpy arrays as pg_vector string: `'[0.1,0.2,...]'`
  - Parse pg_vector results back to numpy arrays
- [ ] T018 [US1] Implement storage operations in SQLite backend:
  - `store_embedding(record: EmbeddingRecordCreate) -> int`
  - `store_embeddings_batch(records: List[EmbeddingRecordCreate], batch_size: int) -> List[int]`
  - Use transactions for batch operations
- [ ] T019 [US1] Implement storage operations in PostgreSQL backend:
  - Same methods as T018 for PostgreSQL
- [ ] T020 [US1] Implement loading operations in SQLite backend:
  - `load_embedding(template_id: str) -> Optional[EmbeddingRecord]`
  - `load_embeddings_all(version_id: Optional[int]) -> List[EmbeddingRecord]`
  - `load_embeddings_by_category(category: str, subcategory: Optional[str]) -> List[EmbeddingRecord]`
- [ ] T021 [US1] Implement loading operations in PostgreSQL backend:
  - Same methods as T020 for PostgreSQL
- [ ] T022 [US1] Implement utility methods in SQLite backend:
  - `exists(template_id: str) -> bool`
  - `count(version_id: Optional[int]) -> int`
  - `get_all_template_ids(version_id: Optional[int]) -> List[str]`
  - `get_content_hashes(version_id: Optional[int]) -> Dict[str, str]`
  - `validate_integrity() -> Dict[str, any]`
  - `get_storage_info() -> Dict[str, any]`
- [ ] T023 [US1] Implement utility methods in PostgreSQL backend:
  - Same methods as T022 for PostgreSQL
- [ ] T024 [US1] Update storage factory in `src/retrieval/storage/__init__.py`:
  - `create_storage_backend(config: StorageConfig) -> StorageBackend`
  - Factory function to instantiate SQLite or PostgreSQL backend based on config
  - Export all public classes and exceptions
- [ ] T025 [US1] Modify `EmbeddingCache` in `src/retrieval/cache.py`:
  - Add optional `storage_backend: Optional[StorageBackend]` parameter to constructor
  - Load embeddings from storage on initialization if available
  - Fall back to empty cache if storage not provided or fails
  - Add graceful error handling with logging
  - Maintain backward compatibility (existing interface unchanged)
- [ ] T026 [US1] Update `precompute_embeddings()` in `src/retrieval/embeddings.py`:
  - Add optional `storage_backend` parameter
  - Store computed embeddings to storage if backend provided
  - Use `store_embeddings_batch()` for efficient batch writes
  - Compute and store content hashes using `compute_content_hash()`
- [ ] T027 [US1] Update `TemplateRetriever` initialization in `src/retrieval/retriever.py`:
  - Load storage configuration from environment variables
  - Create storage backend using factory
  - Pass storage backend to `EmbeddingCache`
  - Add logging for startup time measurement
  - Handle storage failures gracefully (fall back to in-memory)
- [ ] T028 [US1] Add environment variable configuration:
  - `STORAGE_BACKEND` (values: "sqlite", "postgres", default: "sqlite")
  - `SQLITE_DB_PATH` (default: "data/embeddings.db")
  - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
  - `POSTGRES_POOL_SIZE` (default: 5)
  - Document in `.env.example`
- [ ] T029 [US1] Create Docker volume configuration in `docker-compose.yml`:
  - Add volume mount for `./data:/app/data` to persist embeddings.db
  - Add optional PostgreSQL service (commented out by default)
  - Include ankane/pgvector:latest image configuration
  - Document in comments

**Unit Tests for User Story 1**:

- [ ] T030 [P] [US1] Test content hashing in `tests/unit/retrieval/test_hashing.py`:
  - Test SHA256 hash computation
  - Test UTF-8 encoding for Cyrillic text
  - Test hash consistency across platforms
- [ ] T031 [P] [US1] Test storage models in `tests/unit/retrieval/test_storage_models.py`:
  - Validate Pydantic models
  - Test field validation and constraints
- [ ] T032 [P] [US1] Test abstract interface in `tests/unit/retrieval/test_storage_base.py`:
  - Test exception hierarchy
  - Test abstract method enforcement
- [ ] T033 [P] [US1] Test SQLite backend in `tests/unit/retrieval/test_sqlite_backend.py`:
  - Use in-memory SQLite (`:memory:`)
  - Test version management
  - Test CRUD operations
  - Test serialization/deserialization
  - Test WAL mode configuration
- [ ] T034 [P] [US1] Test PostgreSQL backend in `tests/unit/retrieval/test_postgres_backend.py`:
  - Mock psycopg2 connections
  - Test connection pooling
  - Test vector formatting
  - Test pg_vector operations

**Integration Tests for User Story 1**:

- [ ] T035 [US1] Test SQLite integration in `tests/integration/retrieval/test_sqlite_storage.py`:
  - Create temporary SQLite file
  - Test full CRUD lifecycle with 201 templates
  - Measure load time (<50ms target)
  - Test concurrent reads
  - Cleanup temporary files
- [ ] T036 [US1] Test PostgreSQL integration in `tests/integration/retrieval/test_postgres_storage.py`:
  - Use testcontainers-python with ankane/pgvector image
  - Test full CRUD lifecycle with 201 templates
  - Measure load time (<100ms target)
  - Test connection pooling
  - Verify pg_vector operations
  - Container auto-cleanup
- [ ] T037 [US1] Test startup time in `tests/integration/retrieval/test_startup_performance.py`:
  - Pre-populate storage with 201 embeddings
  - Measure system startup time
  - Assert < 2 seconds (vs. baseline ~9 seconds)
  - Verify all embeddings loaded correctly
- [ ] T038 [US1] Test retrieval accuracy in `tests/integration/retrieval/test_storage_accuracy.py`:
  - Load embeddings from storage
  - Run validation queries (same as validation script)
  - Assert 86.7% top-3 accuracy maintained
  - Compare with in-memory baseline

**Checkpoint**: At this point, User Story 1 should be fully functional - system starts in <2 seconds with persistent embeddings, maintaining 86.7% accuracy

---

## Phase 4: User Story 2 - Incremental FAQ Updates (Priority: P2)

**Goal**: When FAQ database changes (new/modified/deleted templates), system updates only affected embeddings without re-processing all 201 existing templates, saving time and API costs.

**Independent Test**:
1. Pre-populate storage with 201 embeddings
2. Add 5 new FAQ entries to Excel file
3. Run incremental update
4. Verify only 5 new embeddings computed (API call count)
5. Verify total embeddings = 206
6. Modify 2 existing entries
7. Run incremental update
8. Verify only 2 embeddings recomputed
9. Delete 1 entry
10. Verify 1 embedding removed, total = 205

### Implementation for User Story 2

- [ ] T039 [US2] Implement change detection in SQLite backend:
  - Enhance `get_content_hashes()` to return full hash mapping
  - Test hash comparison logic
- [ ] T040 [US2] Implement change detection in PostgreSQL backend:
  - Same enhancement as T039 for PostgreSQL
- [ ] T041 [US2] Implement update operations in SQLite backend:
  - `update_embedding(template_id: str, record: EmbeddingRecordCreate) -> bool`
  - Update embedding vector and content hash
  - Update `updated_at` timestamp
- [ ] T042 [US2] Implement update operations in PostgreSQL backend:
  - Same method as T041 for PostgreSQL
- [ ] T043 [US2] Implement delete operations in SQLite backend:
  - `delete_embedding(template_id: str) -> bool`
  - Remove embedding record
- [ ] T044 [US2] Implement delete operations in PostgreSQL backend:
  - Same method as T043 for PostgreSQL
- [ ] T045 [US2] Create migration CLI command in `src/cli/migrate_embeddings.py`:
  - Use Click framework per research.md
  - Command: `python -m src.cli.migrate_embeddings`
  - Options: `--storage-backend`, `--sqlite-path`, `--postgres-dsn`, `--faq-path`, `--batch-size`, `--force`, `--validate`, `--incremental`
  - Load FAQ templates using existing `parse_faq()`
  - Implement change detection logic
  - Use Rich library for progress bars and console output
- [ ] T046 [US2] Implement incremental update logic in migration CLI:
  - Compare current FAQ with stored content hashes
  - Identify: new templates (not in storage), modified templates (hash mismatch), deleted templates (in storage but not in FAQ)
  - Compute embeddings only for new/modified templates
  - Use batch processing for efficiency
  - Display summary: new, modified, deleted, unchanged counts
- [ ] T047 [US2] Implement deletion handling in migration CLI:
  - Delete embeddings for removed templates
  - Log deletion operations
- [ ] T048 [US2] Add progress reporting to migration CLI:
  - Rich progress bar for embedding computation
  - Show: current template, total progress, time elapsed, time remaining
  - Display batch progress (e.g., "Processing batch 3/21")
- [ ] T049 [US2] Add validation step to migration CLI:
  - Call `storage.validate_integrity()` after migration
  - Display validation results
  - Exit with error code if validation fails
- [ ] T050 [US2] Add error handling to migration CLI:
  - Catch FAQ load errors (FileNotFoundError, parsing errors)
  - Catch API errors (EmbeddingsError, rate limits)
  - Catch storage errors (connection, write failures)
  - Rollback transactions on error
  - Display user-friendly error messages with hints
- [ ] T051 [US2] Add force recompute mode to migration CLI:
  - `--force` flag to ignore stored hashes
  - Recompute all embeddings from scratch
  - Use case: model version upgrade

**Unit Tests for User Story 2**:

- [ ] T052 [P] [US2] Test change detection logic in `tests/unit/retrieval/test_change_detection.py`:
  - Test hash comparison
  - Test identification of new/modified/deleted templates
  - Test edge cases (empty storage, no changes, all changed)
- [ ] T053 [P] [US2] Test update operations in `tests/unit/retrieval/test_storage_update.py`:
  - Test update_embedding for SQLite
  - Test update_embedding for PostgreSQL
  - Test timestamp updates
- [ ] T054 [P] [US2] Test delete operations in `tests/unit/retrieval/test_storage_delete.py`:
  - Test delete_embedding for SQLite
  - Test delete_embedding for PostgreSQL
  - Test deletion of non-existent template
- [ ] T055 [US2] Test migration CLI logic in `tests/unit/cli/test_migrate_embeddings.py`:
  - Mock FAQ parser, embeddings client, storage backend
  - Test incremental update flow
  - Test force recompute flow
  - Test error handling
  - Test progress reporting (mock Rich console)

**Integration Tests for User Story 2**:

- [ ] T056 [US2] Test incremental updates in `tests/integration/retrieval/test_incremental_updates.py`:
  - Pre-populate storage with 201 embeddings
  - Add 5 new templates to test FAQ file
  - Run migration CLI with `--incremental`
  - Verify only 5 API calls made
  - Verify total embeddings = 206
  - Modify 2 templates
  - Run migration again
  - Verify only 2 API calls made
  - Delete 1 template
  - Run migration again
  - Verify 1 embedding removed, total = 205
- [ ] T057 [US2] Test force recompute in `tests/integration/retrieval/test_force_recompute.py`:
  - Pre-populate storage with 201 embeddings
  - Run migration CLI with `--force`
  - Verify 201 API calls made (all recomputed)
  - Verify embeddings updated

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - fast startup + efficient incremental updates

---

## Phase 5: User Story 3 - Embedding Version Management (Priority: P3)

**Goal**: When embedding model changes (e.g., upgrade from bge-m3 v1 to v2, or dimension changes from 1024 to 2048), system detects incompatibility and automatically regenerates all embeddings with new model, ensuring consistency.

**Independent Test**:
1. Pre-populate storage with 201 embeddings using model "bge-m3 v1" (1024 dims)
2. Change configuration to model "bge-m3 v2" (1024 dims)
3. Start system
4. Verify system detects version mismatch
5. Verify all embeddings marked as v2 after recomputation
6. Change dimension to 2048
7. Verify system detects dimension mismatch
8. Verify schema migrated and embeddings recomputed

### Implementation for User Story 3

- [ ] T058 [US3] Implement version comparison logic in `src/retrieval/storage/base.py`:
  - Add helper method `is_version_compatible(stored: EmbeddingVersion, current: dict) -> bool`
  - Compare model_name, model_version, embedding_dimension
- [ ] T059 [US3] Implement version detection in `EmbeddingCache` (`src/retrieval/cache.py`):
  - On initialization, get current version from storage
  - Compare with configured model (from EmbeddingsClient)
  - If incompatible: log warning and trigger recomputation
- [ ] T060 [US3] Implement version migration in migration CLI (`src/cli/migrate_embeddings.py`):
  - Detect version mismatch at startup
  - Display warning: "Model version changed: v1 → v2, all embeddings will be recomputed"
  - Prompt user to confirm (unless `--force` flag)
  - Create new version entry in storage
  - Mark new version as current
  - Recompute all embeddings
- [ ] T061 [US3] Implement version cleanup in SQLite backend:
  - `clear_all(version_id: Optional[int]) -> int`
  - Delete all embeddings for a specific version (optional cleanup after migration)
- [ ] T062 [US3] Implement version cleanup in PostgreSQL backend:
  - Same method as T061 for PostgreSQL
- [ ] T063 [US3] Add version management commands to CLI:
  - `--list-versions` flag to display all stored versions
  - `--set-version <version_id>` to switch active version
  - `--clean-old-versions` to remove embeddings from inactive versions
- [ ] T064 [US3] Add version info to storage info output:
  - Display current version in `get_storage_info()`
  - Show: model_name, model_version, embedding_dimension, created_at
- [ ] T065 [US3] Handle dimension changes in schema:
  - For PostgreSQL: verify vector(N) dimension matches
  - For SQLite: validate BLOB size matches expected dimension
  - Add migration path for dimension changes

**Unit Tests for User Story 3**:

- [ ] T066 [P] [US3] Test version comparison in `tests/unit/retrieval/test_version_management.py`:
  - Test is_version_compatible() with various scenarios
  - Test version mismatch detection
- [ ] T067 [P] [US3] Test version migration logic in `tests/unit/cli/test_version_migration.py`:
  - Mock version detection
  - Test recomputation trigger
  - Test user confirmation prompt
- [ ] T068 [US3] Test version cleanup in `tests/unit/retrieval/test_version_cleanup.py`:
  - Test clear_all() for SQLite
  - Test clear_all() for PostgreSQL
  - Test selective cleanup by version_id

**Integration Tests for User Story 3**:

- [ ] T069 [US3] Test version upgrade flow in `tests/integration/retrieval/test_version_upgrade.py`:
  - Pre-populate with v1 embeddings
  - Change model config to v2
  - Run migration CLI
  - Verify version detection
  - Verify all embeddings recomputed
  - Verify new version marked as current
  - Verify old version preserved (optional)
- [ ] T070 [US3] Test dimension change flow in `tests/integration/retrieval/test_dimension_change.py`:
  - Pre-populate with 1024-dim embeddings
  - Change dimension to 2048
  - Run migration CLI
  - Verify schema migration
  - Verify embeddings recomputed with new dimension
  - Verify storage size increased appropriately

**Checkpoint**: All three user stories should now be independently functional - fast startup + incremental updates + version management

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T071 [P] Add comprehensive logging across all storage operations:
  - Log all writes, updates, deletes with template IDs
  - Log performance metrics (load time, batch write time)
  - Use structured logging (JSON format) for production
- [ ] T072 [P] Add storage metrics collection:
  - Track: total embeddings, storage size, load time, query time
  - Expose via get_storage_info()
  - Consider adding Prometheus metrics (optional)
- [ ] T073 [P] Create quickstart validation script in `scripts/validate_storage.py`:
  - Follow quickstart.md steps automatically
  - Verify migration completes
  - Verify startup time < 2 seconds
  - Verify retrieval accuracy 86.7%
  - Output: PASS/FAIL report
- [ ] T074 [P] Update main README.md:
  - Add "Persistent Storage" section
  - Document storage backends (SQLite vs. PostgreSQL)
  - Link to quickstart.md for migration guide
  - Add performance comparison table
- [ ] T075 [P] Create migration guide documentation in `docs/storage-migration.md`:
  - Detailed migration steps
  - Troubleshooting common issues
  - Backup recommendations
  - Rollback procedure
- [ ] T076 Code cleanup and refactoring:
  - Remove any dead code from in-memory-only implementation
  - Ensure consistent error handling patterns
  - Add type hints to all functions
  - Run mypy for type checking
- [ ] T077 Performance optimization:
  - Profile startup time and identify bottlenecks
  - Optimize batch sizes for embedding storage
  - Consider adding connection caching
  - Benchmark query performance against baselines
- [ ] T078 Security hardening:
  - Review database connection strings (no hardcoded credentials)
  - Add SQL injection prevention (use parameterized queries)
  - Validate file permissions on SQLite database
  - Add PostgreSQL SSL support (optional)
- [ ] T079 [P] Docker deployment testing:
  - Test SQLite with volume mount
  - Test PostgreSQL with docker-compose
  - Verify persistence across container restarts
  - Test multi-container setup (app + postgres)
- [ ] T080 Run full validation suite per quickstart.md:
  - Startup time validation
  - Incremental update validation
  - Version migration validation
  - Accuracy validation (86.7% top-3)
  - Generate validation report

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - No dependencies on US1 (but typically done after US1)
  - User Story 3 (P3): Can start after Foundational - No dependencies on US1/US2 (but requires version system from US1)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses storage backends from US1 but can be developed in parallel
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses version system from US1 but can be developed in parallel

### Within Each User Story

- Backend implementations before cache/retriever modifications
- Storage operations before CLI commands
- Core implementation before integration tests
- Unit tests can run in parallel (marked [P])
- Integration tests may need sequential execution (container lifecycle)

### Parallel Opportunities

- **Setup Phase**: Tasks T002-T006 can all run in parallel (different files)
- **Foundational Phase**: Tasks T008-T009 can run in parallel, T010-T011 sequential
- **User Story 1**:
  - T012-T013 (SQLite/PostgreSQL backends) can run in parallel
  - T014-T015 (version management) can run in parallel after T012-T013
  - T016-T017 (serialization) can run in parallel
  - T018-T019 (storage ops) can run in parallel after T016-T017
  - T020-T021 (loading ops) can run in parallel after T018-T019
  - T022-T023 (utility methods) can run in parallel after T020-T021
  - T030-T034 (unit tests) can all run in parallel
- **User Story 2**:
  - T039-T040 can run in parallel
  - T041-T042 can run in parallel
  - T043-T044 can run in parallel
  - T052-T054 (unit tests) can run in parallel
- **User Story 3**:
  - T061-T062 can run in parallel
  - T066-T068 (unit tests) can run in parallel
- **Polish Phase**: Tasks T071-T075, T079 can run in parallel (different files)

---

## Parallel Example: User Story 1 Core Implementation

```bash
# Launch both backend implementations in parallel:
Task T012: "Implement SQLite backend in src/retrieval/storage/sqlite_backend.py"
Task T013: "Implement PostgreSQL backend in src/retrieval/storage/postgres_backend.py"

# After backends complete, launch parallel feature implementations:
Task T014: "Implement version management methods in SQLite backend"
Task T015: "Implement version management methods in PostgreSQL backend"

# Launch all unit tests in parallel:
Task T030: "Test content hashing in tests/unit/retrieval/test_hashing.py"
Task T031: "Test storage models in tests/unit/retrieval/test_storage_models.py"
Task T032: "Test abstract interface in tests/unit/retrieval/test_storage_base.py"
Task T033: "Test SQLite backend in tests/unit/retrieval/test_sqlite_backend.py"
Task T034: "Test PostgreSQL backend in tests/unit/retrieval/test_postgres_backend.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~30 minutes)
2. Complete Phase 2: Foundational (~2 hours)
   - **CRITICAL**: This blocks all stories - prioritize completion
3. Complete Phase 3: User Story 1 (~6-8 hours)
   - Implement SQLite backend first (simpler, zero config)
   - Add PostgreSQL backend after SQLite works
   - Unit tests as you go
   - Integration tests at end
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Pre-populate 201 embeddings
   - Restart system
   - Measure startup time (should be <2 seconds)
   - Run retrieval validation (should maintain 86.7% accuracy)
5. Deploy/demo if ready - **this is the MVP!**

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (~2.5 hours)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! ~8 hours total)
   - System now starts in <2 seconds instead of 9 seconds
   - No breaking changes to existing code
3. Add User Story 2 → Test independently → Deploy/Demo (~4 hours)
   - System now supports efficient content updates
   - Saves API costs on FAQ changes
4. Add User Story 3 → Test independently → Deploy/Demo (~3 hours)
   - System now handles model upgrades gracefully
   - Future-proofed for model changes
5. Polish Phase → Final production hardening (~2 hours)
   - Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (~2.5 hours)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (SQLite focus)
   - **Developer B**: User Story 1 (PostgreSQL focus) - can work in parallel on separate backend
   - After US1 complete:
     - **Developer A**: User Story 2 (incremental updates)
     - **Developer B**: User Story 3 (version management)
3. Stories complete and integrate independently
4. All developers: Polish phase together

---

## Estimated Effort

| Phase | Tasks | Estimated Time | Critical Path |
|-------|-------|----------------|---------------|
| Setup | T001-T007 | 30 minutes | No |
| Foundational | T008-T011 | 2 hours | **YES** (blocks all stories) |
| User Story 1 | T012-T038 | 6-8 hours | **YES** (MVP) |
| User Story 2 | T039-T057 | 4 hours | No (after US1) |
| User Story 3 | T058-T070 | 3 hours | No (after US1) |
| Polish | T071-T080 | 2 hours | No |
| **Total** | **80 tasks** | **17-19 hours** | |

**MVP Timeline** (US1 only): ~11 hours
**Full Feature Timeline** (all stories): ~17-19 hours

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [Story] label maps task to specific user story for traceability (US1, US2, US3)
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Avoid**: vague tasks, same file conflicts, cross-story dependencies that break independence
- **Testing strategy**: Unit tests with in-memory SQLite (fast), integration tests with testcontainers (production parity)
- **Performance targets**:
  - Startup time: <2 seconds (currently ~9 seconds) - **78% improvement**
  - Storage size: <10MB for 201 templates (expect ~1-2MB)
  - Query performance: within 5% of in-memory baseline
  - Accuracy: maintain 86.7% top-3 retrieval accuracy
- **Backward compatibility**: Zero breaking changes to existing 126 unit tests
