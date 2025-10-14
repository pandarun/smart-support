# Implementation Plan: Persistent Embedding Storage

**Branch**: `003-implement-persistent-storage` | **Date**: 2025-10-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-implement-persistent-storage/spec.md`

## Summary

Implement persistent storage layer for embedding vectors to eliminate 9-second startup precomputation delay. System will support both SQLite (default, zero-config) and PostgreSQL with pg_vector (optional, for scaling) through an abstraction layer. Key features include automatic loading from storage on startup, incremental updates using SHA256 content hashing, and graceful fallback to in-memory mode on failures. Primary goal: reduce startup time from 9s to under 2s while maintaining 86.7% top-3 retrieval accuracy.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- Core: sqlite3 (stdlib), psycopg2-binary (optional PostgreSQL), numpy>=1.24.0
- Existing: openai>=1.0.0, pydantic>=2.0.0, openpyxl>=3.1.0
- Storage: No ORM (direct SQL for performance), optional pg_vector extension
**Storage**: SQLite (default, file-based) or PostgreSQL with pg_vector extension (optional)
**Testing**: pytest, pytest-asyncio, testcontainers-python (for PostgreSQL integration tests)
**Target Platform**: Linux server (primary), macOS/Windows (dev), Docker containers
**Project Type**: Single project - extends existing src/retrieval module
**Performance Goals**:
- Startup time: <2 seconds (vs current 9s)
- Query performance: within 5% of in-memory (current: 249.9ms avg)
- Incremental update: <5 seconds for 10 new templates
**Constraints**:
- Must maintain backward compatibility with EmbeddingCache interface
- Storage overhead <10MB for 201 templates
- Zero breaking changes to existing 126 unit tests
- Cross-platform file format (SQLite) or network protocol (PostgreSQL)
**Scale/Scope**: 201 FAQ templates (current), 1024-dimensional embeddings, single-node deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Modular Architecture
**Status**: PASS

This feature extends the existing **Ranking/Retrieval Module** without affecting Classification or UI modules. Storage abstraction maintains clear boundaries:
- Storage layer (new): Handles persistence operations
- EmbeddingCache interface (existing): Unchanged API contract
- TemplateRetriever (existing): No modifications needed

All three modules remain independently testable.

### ✅ Principle II: User-Centric Design
**Status**: PASS

User story priorities align with operator value:
- **P1** (MVP): Fast startup (9s → 2s) - directly improves operator experience
- **P2**: Incremental updates - enables efficient content management
- **P3**: Version management - long-term maintainability

Primary user benefit: Operators no longer wait 9 seconds on system restarts, improving productivity.

### ✅ Principle III: Data-Driven Validation
**Status**: PASS

Validation strategy includes:
- Performance baselines documented: startup time, query latency, accuracy
- Integration tests using testcontainers for PostgreSQL backend
- Validation against existing retrieval accuracy (must maintain 86.7% top-3)
- Startup time measurements before/after persistence

**Integration Testing Plan**:
- Test both SQLite and PostgreSQL backends with testcontainers
- Verify embedding storage and retrieval correctness
- Validate hash-based change detection
- Test graceful fallback to in-memory mode

**E2E Testing**: Not directly applicable (no UI changes), but validation script will verify end-to-end functionality.

### ✅ Principle IV: API-First Integration
**Status**: PASS

Feature preserves existing Scibox API integration:
- No changes to EmbeddingsClient
- No changes to embedding generation (bge-m3)
- Storage layer is transparent to API interactions

API calls only occur when embeddings need recomputation (new/modified templates).

### ✅ Principle V: Deployment Simplicity
**Status**: PASS

Docker deployment enhancements:
- SQLite: Volume mount for `data/embeddings.db` file
- PostgreSQL: Optional service in docker-compose.yml
- Configuration via environment variables (STORAGE_BACKEND=sqlite|postgres)
- Zero additional setup for default SQLite backend

Launch complexity remains same (docker-compose up), storage is transparent.

### ✅ Principle VI: Knowledge Base Integration
**Status**: PASS

FAQ database remains single source of truth:
- Template IDs unchanged
- Embedding generation uses exact template text
- Content hashing detects FAQ modifications
- Storage syncs with FAQ structure (categories, subcategories)

No modifications to FAQ processing logic.

### Constitution Compliance Summary

**Overall**: ✅ PASS - All principles satisfied

This feature is an internal optimization that improves startup performance without affecting module boundaries, validation methodology, API integration, deployment, or FAQ handling. No constitution violations.

## Project Structure

### Documentation (this feature)

```
specs/003-implement-persistent-storage/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0: Storage technology research
├── data-model.md        # Phase 1: Embedding storage schema
├── quickstart.md        # Phase 1: Migration and usage guide
├── contracts/           # Phase 1: Storage interface contracts
│   └── storage-api.yaml # Storage abstraction interface
└── tasks.md             # Phase 2: Implementation tasks (/speckit.tasks)
```

### Source Code (repository root)

```
src/
├── retrieval/
│   ├── storage/                 # NEW: Storage abstraction layer
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract storage interface
│   │   ├── sqlite_backend.py  # SQLite implementation
│   │   ├── postgres_backend.py # PostgreSQL implementation
│   │   └── models.py           # Storage-specific data models
│   ├── cache.py                # MODIFIED: Use persistent storage
│   ├── embeddings.py           # MODIFIED: Support incremental updates
│   └── retriever.py            # UNCHANGED
│
├── cli/
│   └── migrate_embeddings.py  # NEW: Migration command
│
└── utils/
    └── hashing.py              # NEW: Content hash utilities

tests/
├── integration/
│   └── retrieval/
│       ├── test_sqlite_storage.py      # NEW: SQLite integration tests
│       └── test_postgres_storage.py    # NEW: PostgreSQL integration tests (testcontainers)
│
└── unit/
    └── retrieval/
        ├── test_storage_base.py        # NEW: Storage interface tests
        ├── test_sqlite_backend.py      # NEW: SQLite unit tests
        ├── test_postgres_backend.py    # NEW: PostgreSQL unit tests
        ├── test_cache.py               # MODIFIED: Test with persistent backend
        └── test_embeddings.py          # MODIFIED: Test incremental updates

data/
└── embeddings.db               # NEW: SQLite database file (gitignored)
```

**Structure Decision**: Single project structure (Option 1) is used. This feature extends the existing `src/retrieval` module with a new `storage/` subpackage. The modular architecture is preserved:
- Storage layer is isolated in `src/retrieval/storage/`
- Abstract interface (`base.py`) defines contracts
- Backend implementations (SQLite, PostgreSQL) are independent modules
- Existing code minimally modified (cache.py, embeddings.py)

This avoids creating a separate project while maintaining clear separation of concerns.

## Complexity Tracking

*No constitution violations - table not needed*

## Phase 0: Research Tasks

### Research Task 1: Vector Storage Approaches
**Objective**: Evaluate binary storage formats for 1024-dimensional embeddings in SQLite vs. PostgreSQL

**Questions to Answer**:
- How to efficiently serialize/deserialize numpy arrays for SQLite BLOBs?
- What are pg_vector data types and indexing capabilities?
- Performance comparison: BLOB storage vs. native vector types
- Storage overhead for 201 templates × 1024 dims

**Deliverable**: Decision on storage format with performance benchmarks

---

### Research Task 2: Content Hashing Strategy
**Objective**: Determine optimal hashing approach for detecting FAQ changes

**Questions to Answer**:
- SHA256 vs. MD5 vs. simpler hash functions (performance/collision tradeoffs)
- What content to hash (question + answer vs. entire template)?
- Where to store hashes (separate column vs. metadata table)?
- Hash computation impact on incremental update performance

**Deliverable**: Hashing strategy with implementation approach

---

### Research Task 3: Storage Abstraction Patterns
**Objective**: Design storage interface that works for both SQLite and PostgreSQL

**Questions to Answer**:
- Abstract base class vs. protocol (typing.Protocol)?
- Connection management: per-operation vs. connection pooling?
- Transaction boundaries for batch operations
- Error handling and retry strategies

**Deliverable**: Storage interface design with method signatures

---

### Research Task 4: Migration Strategy
**Objective**: Design explicit migration command workflow

**Questions to Answer**:
- CLI interface: argparse vs. click?
- Progress reporting during migration (tqdm vs. custom)?
- Validation after migration completes
- Rollback strategy if migration fails partway

**Deliverable**: Migration command design and error handling approach

---

### Research Task 5: SQLite vs PostgreSQL Best Practices
**Objective**: Document best practices for each backend

**Questions to Answer**:
- SQLite: WAL mode, PRAGMA settings, file locking
- PostgreSQL: Connection pooling, pg_vector configuration, indexing
- When to use each backend (decision guide for users)
- Performance tuning recommendations

**Deliverable**: Backend selection guide and configuration best practices

---

### Research Task 6: Testing Strategy with Testcontainers
**Objective**: Plan integration tests using testcontainers-python

**Questions to Answer**:
- How to use PostgresContainer for integration tests?
- Fixture lifecycle management (session vs. function scope)?
- Test isolation and cleanup strategies
- SQLite in-memory mode for fast unit tests

**Deliverable**: Testing strategy document with code examples

## Phase 1: Design Artifacts

### Artifact 1: data-model.md
**Content**:
- EmbeddingRecord schema (table structure, columns, indexes)
- EmbeddingVersion schema (version tracking)
- Relationship between records and versions
- Migration schema (tracking applied migrations)

### Artifact 2: contracts/storage-api.yaml
**Content**:
- Storage interface definition (OpenAPI-style)
- Method signatures: store, load, update, delete, get_by_category
- Error types and exception hierarchy
- Configuration parameters

### Artifact 3: quickstart.md
**Content**:
- How to run migration command
- Configuration options (SQLite vs. PostgreSQL)
- Incremental update workflow
- Troubleshooting common issues

### Artifact 4: Agent Context Update
**Action**: Run `.specify/scripts/bash/update-agent-context.sh claude`
**Purpose**: Add new technologies to Claude Code context:
- testcontainers-python
- psycopg2-binary
- pg_vector extension
- SQLite PRAGMA optimization

## Phase 2: Task Generation

**Status**: Not started (requires `/speckit.tasks` command)

After Phase 1 artifacts are complete, run `/speckit.tasks` to generate dependency-ordered implementation tasks from the feature specification and design artifacts.

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| PostgreSQL setup complexity | Medium | Medium | Make SQLite default, PostgreSQL optional; provide docker-compose template |
| Storage migration data loss | Low | High | Extensive testing, validation step in migration command, backup recommendation |
| Performance degradation | Low | High | Benchmarking before/after, maintain in-memory fallback option |
| Cross-platform file issues | Medium | Low | Use SQLite with standard settings, test on all platforms |

### Integration Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking EmbeddingCache interface | Low | High | Maintain exact interface compatibility, comprehensive unit tests |
| Test fixture breakage | Medium | Medium | Update tests incrementally, maintain backward compatibility |
| Docker volume mount issues | Medium | Low | Clear documentation, provide working docker-compose examples |

## Success Validation

### Phase 0 Complete When:
- [x] All 6 research tasks completed
- [x] research.md document finalized (48KB, 345 lines)
- [x] Technical decisions documented with rationale

**Phase 0 Status**: ✅ COMPLETE (2025-10-15)

### Phase 1 Complete When:
- [x] data-model.md defines complete schema
- [x] contracts/storage-api.yaml specifies all interface methods
- [x] quickstart.md provides clear migration instructions
- [x] Agent context updated with new technologies

**Phase 1 Status**: ✅ COMPLETE (2025-10-15)

**Generated Artifacts**:
- `research.md` (48,895 bytes) - Complete technology research
- `data-model.md` (21,234 bytes) - Database schema for both backends
- `contracts/storage-api.yaml` (13,487 bytes) - Storage interface specification
- `quickstart.md` (12,789 bytes) - User migration and usage guide
- `CLAUDE.md` updated with new dependencies

### Phase 2 Complete When:
- [x] tasks.md generated with dependency-ordered tasks
- [x] All tasks mapped to functional requirements
- [x] Task estimates and priorities assigned

**Phase 2 Status**: ✅ COMPLETE (2025-10-15)

**Generated Artifact**:
- `tasks.md` (80 tasks) - Implementation tasks organized by user story
  - Phase 1: Setup (7 tasks)
  - Phase 2: Foundational (4 tasks - blocking prerequisites)
  - Phase 3: User Story 1 - Fast Startup (27 tasks + 9 unit/integration tests)
  - Phase 4: User Story 2 - Incremental Updates (19 tasks + 6 tests)
  - Phase 5: User Story 3 - Version Management (13 tasks + 5 tests)
  - Phase 6: Polish & Cross-Cutting (10 tasks)
- Total estimated effort: 17-19 hours (MVP: ~11 hours for US1 only)
- 38 parallel opportunities identified across all phases

### Implementation Complete When:
- [ ] Startup time <2 seconds with pre-populated storage
- [ ] Incremental updates work for new/modified templates
- [ ] 126 existing unit tests pass without modification
- [ ] New integration tests pass with both backends
- [ ] Retrieval accuracy maintained at 86.7% top-3
- [ ] Docker deployment working with volume mounts
- [ ] Migration command documented and tested

## Notes

### Key Design Principles
1. **Backward compatibility**: Existing code should work unchanged with new storage layer
2. **Graceful degradation**: Fall back to in-memory mode if storage fails
3. **Explicit migration**: No surprise slow startups, clear user control
4. **Backend flexibility**: Easy to switch between SQLite and PostgreSQL

### Implementation Order
1. Phase 0: Research (resolve unknowns)
2. Phase 1: Design (schema, interfaces, documentation)
3. Phase 2: Tasks (implementation plan)
4. Implementation: Follow tasks.md
5. Validation: Measure against success criteria

### Dependencies on Other Features
- None - this is an internal optimization to existing retrieval module
- Benefits future features (faster startup for operator interface)
