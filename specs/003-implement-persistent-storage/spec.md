# Feature Specification: Persistent Embedding Storage

**Feature Branch**: `003-implement-persistent-storage`
**Created**: 2025-10-15
**Status**: Draft
**Input**: User description: "Implement persistent storage for embeddings using SQLite or PostgreSQL with pg_vector extension"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast System Startup (Priority: P1)

The Smart Support system operator starts the application and it becomes ready to serve requests within seconds, without requiring a multi-second embedding precomputation phase on every restart.

**Why this priority**: This is the most critical user value. Current system takes ~9 seconds to precompute 201 embeddings on every startup. For production deployments (especially in containers), this creates poor user experience and increases API costs. This story alone makes the feature viable.

**Independent Test**: Start the application with pre-populated embedding storage and measure time-to-ready. System should be operational in under 2 seconds vs. current ~9 seconds.

**Acceptance Scenarios**:

1. **Given** embeddings have been previously computed and stored, **When** system starts up, **Then** embeddings load from storage within 2 seconds
2. **Given** system is restarted after a crash, **When** system initializes, **Then** all 201 embeddings are available without recomputation
3. **Given** FAQ database has not changed, **When** system starts, **Then** no API calls are made to embedding service

---

### User Story 2 - Incremental FAQ Updates (Priority: P2)

A content administrator adds 5 new FAQ entries to the knowledge base. The system updates only the new entries without re-processing all 201 existing templates, saving time and API costs.

**Why this priority**: Enables efficient content management in production. Without this, every FAQ change requires full recomputation (expensive and slow). This is important but system can function without it initially.

**Independent Test**: Add new FAQ entries to database, trigger update process, verify only new entries are embedded and existing embeddings remain unchanged.

**Acceptance Scenarios**:

1. **Given** FAQ database with 201 entries, **When** 5 new entries are added, **Then** only 5 new embeddings are computed
2. **Given** existing FAQ entry is modified, **When** update is triggered, **Then** only that entry's embedding is recomputed
3. **Given** FAQ entry is deleted, **When** update is triggered, **Then** corresponding embedding is removed from storage

---

### User Story 3 - Embedding Version Management (Priority: P3)

A system administrator upgrades to a new embedding model (e.g., BGE-M3 v2). The system detects the model change and automatically regenerates all embeddings with the new model, ensuring consistency.

**Why this priority**: Important for long-term maintainability but not needed for initial production launch. Can be added later as system matures.

**Independent Test**: Change embedding model configuration, restart system, verify all embeddings are regenerated and marked with new version.

**Acceptance Scenarios**:

1. **Given** embeddings stored with model version "bge-m3-v1", **When** system configured with "bge-m3-v2", **Then** all embeddings are regenerated
2. **Given** embedding dimension changes from 1024 to 2048, **When** system starts, **Then** storage schema is migrated and embeddings recomputed
3. **Given** mixed versions in storage, **When** query is executed, **Then** system only uses embeddings from current model version

---

### Edge Cases

- What happens when database file is corrupted or missing?
  - System should detect corruption and fall back to recomputation mode
  - Log warning and proceed with in-memory mode if storage unavailable

- How does system handle concurrent writes (multiple processes)?
  - Storage layer should use appropriate locking mechanisms
  - Read operations should never be blocked by writes

- What happens when FAQ database and embedding storage become out-of-sync?
  - System should detect mismatches (template IDs present in FAQ but missing embeddings)
  - Automatically compute missing embeddings on startup

- How does system handle schema migrations between versions?
  - Storage should include version metadata
  - Automated migration scripts for schema updates

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist all computed embeddings to durable storage that survives application restarts
- **FR-002**: System MUST load embeddings from storage on startup if available, avoiding recomputation
- **FR-003**: System MUST store embedding metadata including template ID, category, subcategory, question text, and answer text
- **FR-004**: System MUST track embedding provenance including model name, model version, and computation timestamp
- **FR-005**: System MUST support incremental updates where only new or modified FAQ entries trigger embedding computation
- **FR-006**: System MUST detect when stored embeddings are incompatible (different model/dimension) and trigger full recomputation
- **FR-007**: System MUST provide read-after-write consistency for embedding storage operations
- **FR-008**: System MUST handle storage failures gracefully by falling back to in-memory mode with appropriate logging
- **FR-009**: System MUST support efficient retrieval of embeddings filtered by category and subcategory
- **FR-010**: System MUST maintain backward compatibility with existing in-memory cache interface
- **FR-011**: Storage solution MUST work across different operating systems (Linux, macOS, Windows) for Docker deployment
- **FR-012**: System MUST provide mechanism to validate storage integrity on startup
- **FR-013**: System MUST support concurrent read operations without performance degradation
- **FR-014**: System MUST log all storage operations (writes, updates, deletes) for audit trail

### Key Entities *(include if feature involves data)*

- **EmbeddingRecord**: Represents a single stored embedding with associated metadata
  - Attributes: template_id, embedding_vector (1024 floats), category, subcategory, question_text, answer_text, created_at, updated_at
  - Relationships: Belongs to an EmbeddingVersion

- **EmbeddingVersion**: Represents a collection of embeddings computed with specific model configuration
  - Attributes: version_id, model_name, model_version, embedding_dimension, created_at, is_current
  - Relationships: Has many EmbeddingRecords

- **TemplateMetadata**: Extended information about FAQ templates
  - Attributes: template_id, success_rate, usage_count, last_used_at
  - Relationships: One-to-one with EmbeddingRecord

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System startup time reduces from 9 seconds to under 2 seconds when embeddings are pre-computed
- **SC-002**: Adding 10 new FAQ entries completes in under 5 seconds (vs. ~9 seconds for full recomputation)
- **SC-003**: Template retrieval query performance remains within 5% of in-memory cache performance (< 260ms average)
- **SC-004**: Zero embedding data loss occurs across system restarts, crashes, or container recreations
- **SC-005**: Storage overhead is less than 10MB for 201 templates with 1024-dimensional embeddings
- **SC-006**: System successfully recovers from storage corruption without manual intervention
- **SC-007**: Embedding updates complete within 1 second per template (including storage write)
- **SC-008**: 100% of embedding metadata is preserved across persistence cycles

## Scope *(mandatory)*

### In Scope

- Persistent storage implementation for embedding vectors and metadata
- Automatic loading of embeddings from storage on system startup
- Incremental update capability for new/modified FAQ entries
- Storage abstraction layer compatible with existing EmbeddingCache interface
- Model version tracking and compatibility detection
- Graceful fallback to in-memory mode on storage failures
- Storage integrity validation and corruption detection
- Migration from current in-memory implementation

### Out of Scope

- Distributed storage across multiple nodes (single-node deployment only)
- Real-time replication or backup mechanisms
- Advanced query capabilities beyond exact template_id and category filtering
- User interface for managing embeddings
- Automated embedding quality monitoring
- A/B testing framework for different embedding models
- Historical embedding versioning (only current version maintained)

## Dependencies *(mandatory)*

### External Dependencies

- Database storage solution (SQLite or PostgreSQL with pg_vector extension) - requires installation
- Python database drivers (sqlite3 standard library or psycopg2/asyncpg)
- Existing embedding generation infrastructure (EmbeddingsClient, Scibox API)
- FAQ parsing module (parse_faq function)

### Internal Dependencies

- Existing EmbeddingCache interface must remain compatible
- TemplateRetriever module must work with persistent cache
- Classification module FAQ parser integration
- Validation framework needs updated test fixtures

### Assumptions

- FAQ database changes are infrequent (< 10 times per day) - optimizing for read-heavy workload
- Single application instance accessing storage at a time (no distributed coordination needed)
- Embedding computation is deterministic (same input produces same output)
- Storage I/O is not the bottleneck for query performance (< 10ms read latency)
- System has write access to data directory for SQLite or network access for PostgreSQL
- Embedding vectors fit in memory alongside storage (current: ~800KB for 201 templates)

## Constraints *(optional)*

### Technical Constraints

- Must integrate with Docker deployment infrastructure
- Must support both local development (SQLite) and production deployment (PostgreSQL optional)
- Cannot break existing validation tests (126 unit tests must continue passing)
- Storage format must be cross-platform compatible
- Must handle concurrent reads efficiently (no blocking on common queries)

### Business Constraints

- Implementation must not increase Docker image size by more than 50MB
- Cannot require additional cloud services or external dependencies
- Must maintain or improve current system performance (86.7% top-3 accuracy)
- Deployment complexity should not increase significantly

## Design Decisions *(resolved)*

### Decision 1: Storage Technology Choice

**Decision**: Implement both SQLite and PostgreSQL with abstraction layer

**Rationale**: Maximum flexibility allows users to choose based on their deployment needs. SQLite for simple deployments (development, small production), PostgreSQL with pg_vector for advanced use cases (scaling, advanced vector operations). The abstraction layer ensures consistent interface regardless of backend.

**Implementation approach**:
- Define storage interface (abstract base class)
- Implement SQLite backend as default (zero configuration)
- Implement PostgreSQL backend as optional (requires server)
- Configuration-based backend selection
- Shared test suite for both implementations

---

### Decision 2: Migration Strategy

**Decision**: Explicit migration command

**Rationale**: Provides clear control over when embeddings are pre-populated. Users run a one-time migration command before switching to persistent mode. Avoids surprise slow startups and gives visibility into the migration process.

**Implementation approach**:
- Create CLI command: `python -m src.cli.migrate_embeddings`
- Command computes all embeddings and populates storage
- Progress reporting during migration
- Validation after migration completes
- Documentation with clear migration instructions

---

### Decision 3: Incremental Update Trigger

**Decision**: Content hash comparison

**Rationale**: Simple, reliable, and has no external dependencies. System computes hash (e.g., SHA256) of each FAQ entry's content and compares with stored hashes to detect changes. Works regardless of FAQ database format.

**Implementation approach**:
- Store content hash alongside each embedding
- On update, compute hash of current FAQ entry
- Compare with stored hash to detect changes
- Recompute embedding only if hash differs
- Update both embedding and hash in storage

## Related Features *(optional)*

- Feature 001: Classification Module (depends on FAQ database structure)
- Feature 002: Template Retrieval Module (primary consumer of embedding storage)
- Future: Operator Interface (will benefit from faster startup times)
- Future: Analytics Dashboard (could use embedding metadata for insights)

## Notes *(optional)*

### Technical Considerations

- **Vector storage formats**: SQLite can store vectors as BLOBs (numpy arrays serialized), PostgreSQL pg_vector uses native vector type
- **Indexing strategy**: Current cosine similarity search is brute-force over filtered set. For 201 templates, this is acceptable. If scaling to 10K+ templates, consider approximate nearest neighbor (ANN) indexes.
- **Schema versioning**: Consider using Alembic or similar migration tool for schema evolution
- **Testing strategy**: Unit tests with in-memory SQLite, integration tests with actual database
- **Performance baseline**: Current in-memory cache: 249.9ms average query time, 303.5ms P95

### Design Decisions to Document

- Choice between row-per-embedding vs. row-per-version with JSONB/array storage
- Normalization level (3NF vs. denormalized for performance)
- Transaction isolation level for writes
- Connection pooling strategy if using PostgreSQL
- Backup and disaster recovery approach

### Migration Path from Current Implementation

1. Create storage abstraction interface matching current EmbeddingCache API
2. Implement SQLite backend first (simplest)
3. Add PostgreSQL backend as optional enhancement
4. Update precompute_embeddings() to write to storage
5. Modify TemplateRetriever initialization to load from storage
6. Add migration script for one-time population
7. Update Docker configuration with volume mounts
8. Update tests to use test databases
