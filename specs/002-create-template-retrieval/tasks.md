# Tasks: Template Retrieval Module

**Input**: Design documents from `/specs/002-create-template-retrieval/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The constitution mandates integration tests with testcontainers and e2e tests with Chrome DevTools MCP. Integration tests are included for all user stories. E2E tests are deferred to UI integration phase (Checkpoint 3).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Paths shown below use single project structure as per plan.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for Retrieval Module

- [ ] T001 Create retrieval module directory structure (src/retrieval, tests/unit/retrieval, tests/integration/retrieval, data/validation, data/cache)
- [ ] T002 [P] Update requirements.txt with new production dependencies (numpy>=1.24.0, backoff>=2.2.0)
- [ ] T003 [P] Update .env.example file with retrieval configuration variables (EMBEDDING_MODEL=bge-m3, EMBEDDING_CACHE_PATH, RETRIEVAL_TOP_K, RETRIEVAL_TIMEOUT_SECONDS)
- [ ] T004 [P] Create all __init__.py files (src/retrieval/__init__.py, tests/unit/retrieval/__init__.py, tests/integration/retrieval/__init__.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create Pydantic data models in src/retrieval/models.py (Template, RetrievalRequest, RetrievalResponse, RetrievalResult, EmbeddingVector, ValidationRecord, ValidationResult, ValidationQueryResult, ProcessingTimeStats, TemplateMetadata)
- [ ] T006 Create embeddings API client in src/retrieval/embeddings.py with OpenAI-compatible client initialization, authentication using SCIBOX_API_KEY, batch embedding support (embed() and embed_batch() methods), exponential backoff retry logic (max 3 attempts), error wrapping for API failures
- [ ] T007 Create in-memory embedding cache in src/retrieval/cache.py with EmbeddingCache class: add() method to store normalized embeddings, get_by_category() method to filter by category/subcategory, is_ready property, stats property for monitoring, TemplateMetadata class for template attributes
- [ ] T008 [P] Create cosine similarity utilities in src/retrieval/ranker.py with cosine_similarity_batch() function using numpy vectorized operations, rank_templates() function to sort by similarity score, support for weighted scoring (0.7*similarity + 0.3*historical)
- [ ] T009 [P] Update shared logging in src/utils/logging.py to include retrieval-specific log events (embedding_precomputation_started, embedding_precomputation_completed, template_retrieval_requested, template_retrieval_completed, validation_started, validation_completed)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Retrieve Relevant Templates (Priority: P1) 🎯 MVP

**Goal**: Operator receives classified inquiry and retrieves top-5 relevant template responses ranked by semantic similarity within 1 second

**Independent Test**: Submit query "Как открыть накопительный счет в мобильном приложении?" with classification (category="Счета и вклады", subcategory="Открытие счета"), verify returns 5 ranked templates within 1000ms, confirm at least one of top-3 templates is semantically relevant

### Integration Tests for User Story 1 (Constitution Mandated)

**NOTE: These integration tests verify the complete retrieval workflow with real dependencies**

- [ ] T010 [P] [US1] Create integration test fixtures in tests/integration/retrieval/conftest.py with EmbeddingCache setup, Scibox embeddings API client, mock template data (10-20 templates), and FAQ parser mocking for offline testing
- [ ] T011 [US1] Create integration test in tests/integration/retrieval/test_retrieval_integration.py that verifies single template retrieval with real embeddings client (or mocked for offline), measures processing time (<1000ms), validates response format (RetrievalResponse schema), checks result ranking order

### Implementation for User Story 1

- [ ] T012 [US1] Implement precomputation logic in src/retrieval/embeddings.py with precompute_embeddings() async function: load templates from FAQ parser (reuse src/classification/faq_parser.py), batch templates (20-50 per batch), call Scibox embeddings API with embed_batch(), store in EmbeddingCache with normalized vectors, handle failures with exponential backoff, log statistics (total/succeeded/failed/time)
- [ ] T013 [US1] Implement core retrieval logic in src/retrieval/retriever.py with TemplateRetriever class: retrieve() method accepts RetrievalRequest, filters templates by category/subcategory using cache.get_by_category(), embeds query via embeddings_client.embed(), calls rank_templates() for cosine similarity ranking, returns RetrievalResponse with results/warnings/processing_time_ms, handles edge cases (no templates, low similarity scores <0.5)
- [ ] T014 [US1] Create CLI interface in src/cli/retrieve.py with argument parsing for query text, --category, --subcategory, --top-k flags, initialization of embeddings client and cache with precomputation, invocation of retriever.retrieve(), formatted output display (rank, question, answer preview, similarity score, confidence level), error message handling
- [ ] T015 [P] [US1] Create unit tests in tests/unit/retrieval/test_retriever.py with mocked EmbeddingsClient and EmbeddingCache: test valid retrieval request, test empty category (no templates), test low similarity scores (<0.5 warning), test top_k parameter (1-10 range), test processing time measurement
- [ ] T016 [P] [US1] Create unit tests in tests/unit/retrieval/test_ranker.py to verify cosine_similarity_batch() correctness (known embeddings → expected similarities), rank_templates() sorting (highest similarity first), top_k truncation, weighted scoring formula (0.7*sim + 0.3*hist when enabled)
- [ ] T017 [P] [US1] Create unit tests in tests/unit/retrieval/test_embeddings.py to verify embed() returns correct shape (768,) and dtype (float32), embed_batch() handles multiple texts, exponential backoff retry on API failures (mock retries), error wrapping for Scibox API exceptions
- [ ] T018 [P] [US1] Create unit tests in tests/unit/retrieval/test_cache.py to verify add() stores normalized embeddings (L2 norm = 1.0), get_by_category() filters correctly, is_ready property reflects cache state, stats property returns correct counts

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Operator can retrieve relevant templates via CLI given classification results.

---

## Phase 4: User Story 2 - Precompute and Validate Embeddings on Startup (Priority: P2)

**Goal**: System administrator deploys retrieval module, embeddings are automatically precomputed for all FAQ templates within 60 seconds, system reports readiness before accepting retrieval requests

**Independent Test**: Start system with FAQ database of 150-200 templates, measure precomputation time (<60 seconds), verify all templates have valid embeddings stored, confirm system reports "ready" status only after precomputation completes

### Integration Tests for User Story 2 (Constitution Mandated)

- [ ] T019 [US2] Create integration test in tests/integration/retrieval/test_precomputation_integration.py that runs full embedding precomputation with real FAQ database (or subset for testing), verifies all templates embedded successfully, checks precomputation time (<60 seconds for 200 templates), validates cache statistics (total/embedded/failed counts), tests partial failure handling (some templates fail, others succeed)

### Implementation for User Story 2

- [ ] T020 [US2] Add initialization module in src/retrieval/__init__.py with initialize_retrieval() async function: calls precompute_embeddings() with FAQ path from environment, handles startup failures gracefully, logs readiness status, returns TemplateRetriever instance ready for use
- [ ] T021 [US2] Create system health endpoints in src/retrieval/health.py with get_health_status() function (simple "healthy" check), get_readiness_status() function (returns ready/precomputing/partial/not_ready based on cache state, includes statistics: total_templates, embedded_templates, failed_templates, precompute_time_seconds), heartbeat logging for monitoring
- [ ] T022 [US2] Add optional SQLite persistence in src/retrieval/cache.py with save_to_sqlite() method (serialize embeddings to BLOB, store embedding_hash for cache invalidation, timestamp), load_from_sqlite() method (skip precomputation if cache valid), invalidation logic (check if FAQ database modified)
- [ ] T023 [P] [US2] Create unit tests in tests/unit/retrieval/test_initialization.py to verify initialize_retrieval() success path, test precomputation failure handling (all embeddings fail), test partial success (some embeddings fail), test readiness status transitions (not_ready → precomputing → ready)
- [ ] T024 [P] [US2] Create unit tests in tests/unit/retrieval/test_health.py to verify get_health_status() always returns healthy, get_readiness_status() reflects cache state correctly, statistics accuracy (counts match cache)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. System can precompute embeddings on startup and retrieve templates with validated readiness checks.

---

## Phase 5: User Story 3 - Validate Retrieval Quality (Priority: P3)

**Goal**: QA team runs validation against test dataset of query-template pairs, system generates accuracy report showing ≥80% top-3 accuracy (quality gate for hackathon evaluation)

**Independent Test**: Run validation with dataset of 10+ queries, each with ground truth correct template ID, generate report showing top-3 accuracy percentage, per-query breakdown (correct/incorrect), similarity score statistics, processing time stats (min/max/mean/p95)

### Integration Tests for User Story 3 (Constitution Mandated)

- [ ] T025 [US3] Create integration test in tests/integration/retrieval/test_validation_integration.py that runs validation against sample dataset (5 test cases with known correct template IDs), verifies accuracy calculation formula (correct / total * 100), checks per-query results format (query_id, correct_template_rank, is_top_1/top_3/top_5 flags), validates processing time stats calculation (min/max/mean/p95)

### Implementation for User Story 3

- [ ] T026 [US3] Create sample validation dataset in data/validation/retrieval_validation_dataset.json with 10 test queries covering main categories (Счета и вклады, Кредиты, Карты, etc.), each with: query text, category, subcategory, correct_template_id (ground truth), notes explaining expected match
- [ ] T027 [US3] Implement validation module in src/retrieval/validator.py with run_validation() function: load validation dataset from JSON, classify each query using retriever.retrieve(), compare retrieved template IDs to correct_template_id, calculate overall accuracy (top-1, top-3, top-5 counts), calculate per-category accuracy breakdown, compute processing time stats (numpy percentile for p95), generate ValidationResult object, save results to data/results/retrieval_validation_results.json
- [ ] T028 [US3] Add --validate flag to CLI in src/cli/retrieve.py to accept dataset path (default: data/validation/retrieval_validation_dataset.json), invoke run_validation(), display formatted accuracy report with color-coded pass/fail (≥80% top-3 accuracy = green/pass, <80% = red/fail), show per-query breakdown table (query text truncated, correct template ID, retrieved rank, top-3 status), display similarity score statistics (avg for correct vs incorrect), show processing time stats with p95 highlighted, save results to file with timestamp
- [ ] T029 [P] [US3] Create unit tests in tests/unit/retrieval/test_validator.py to verify accuracy calculation formula (9 correct out of 10 = 90%), per-query result generation (is_top_1/top_3/top_5 flags correct), processing time stats calculation (min/max/mean/p95 with known values), edge cases (empty dataset should error, all incorrect = 0% accuracy, all correct = 100% accuracy), ValidationResult.passes_quality_gate property (True if ≥80%)

**Checkpoint**: All user stories should now be independently functional. System supports embedding precomputation, template retrieval, and quality validation against test datasets.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and prepare for integration

- [ ] T030 [P] Add comprehensive docstrings to all public functions in src/retrieval/ modules with parameter descriptions (types, constraints), return types, example usage snippets, raises documentation (API errors, validation errors, timeout errors)
- [ ] T031 [P] Update project README.md to document Retrieval Module: overview of embeddings-based semantic search, installation dependencies (numpy, backoff added), usage examples for CLI (single retrieval, validation), Python module import examples (initialize_retrieval, retriever.retrieve), integration with Classification Module example (full pipeline), testing guide (unit tests, integration tests, validation), performance characteristics (<1s retrieval, <60s precomputation)
- [ ] T032 [P] Update Dockerfile to include Retrieval Module dependencies (numpy, backoff), ensure .env mounting includes new retrieval variables, add health check for readiness endpoint (verify embeddings precomputed before marking container healthy)
- [ ] T033 [P] Update docker-compose.yml to extend classification service with retrieval capabilities (shared FAQ database volume, shared .env file), add optional embedding cache volume for SQLite persistence (speeds up restarts), configure healthcheck with readiness endpoint
- [ ] T034 Run complete test suite (pytest tests/unit/retrieval tests/integration/retrieval -v --cov=src/retrieval) to verify all unit and integration tests pass, achieve >80% code coverage for retrieval module, identify untested edge cases
- [ ] T035 Run validation against full validation dataset (10+ queries) to verify ≥80% top-3 accuracy quality gate, generate validation report with per-category breakdown, document accuracy results in project documentation, identify categories with low accuracy for improvement
- [ ] T036 [P] Add performance optimization: pre-normalize embeddings during precomputation to avoid repeated norm calculations at retrieval time (store normalized embeddings in cache), benchmark cosine similarity performance (<5ms for 50 templates)
- [ ] T037 [P] Create integration helper in src/retrieval/integration.py with classify_and_retrieve() function: accepts raw query text, calls Classification Module classifier.classify(), passes classification result to retriever.retrieve(), returns tuple of (ClassificationResult, RetrievalResponse), handles errors from either module gracefully, logs full pipeline execution time
- [ ] T038 Verify quickstart.md examples work end-to-end by running all code snippets from quickstart guide (embedding precomputation, single retrieval, validation run, integration with classification), update quickstart if examples are outdated, document any environment-specific setup requirements

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (both extend foundational retriever.py)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 retriever.py being complete for validation to work

**Dependency Graph**:
```
Setup (T001-T004)
    ↓
Foundational (T005-T009) ← BLOCKS everything below
    ↓
    ├─→ US1: Retrieve Templates (T010-T018)
    │       ↓
    │       └─→ US3: Validation (T025-T029) [depends on US1 retriever]
    │
    └─→ US2: Precompute/Readiness (T019-T024) [independent of US1]

All User Stories Complete
    ↓
Polish (T030-T038)
```

### Within Each User Story

- Integration tests can be written in parallel with implementation (T010-T011 parallel to T012-T018 for US1)
- Unit tests can be written in parallel with each other (T015, T016, T017, T018 all [P])
- Core implementation must be sequential: embeddings (T012) → retriever (T013) → CLI (T014)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T004)
- Foundational tasks can run partially parallel: models (T005) can be done while embeddings client (T006) and cache (T007) are developed, then ranker (T008) and logging (T009) parallel
- Within US1: Integration test fixtures (T010) parallel to precomputation (T012), then unit tests (T015, T016, T017, T018) all parallel
- Within US2: Integration test (T019) can start as soon as precomputation design is clear (after T012)
- Within US3: Integration test (T025) parallel to validation dataset creation (T026)
- Polish tasks marked [P] can all run in parallel (T030, T031, T032, T033, T036, T037)

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch US1 tasks in parallel:

# Integration test prep (parallel to implementation)
Task T010: Create integration test fixtures

# Implementation (sequential core, parallel peripherals)
Task T012: Implement precomputation (BLOCKS T013)
  ↓
Task T013: Implement retriever (BLOCKS T014, enables T015-T018)
  ↓
Task T014: Create CLI

# Unit tests (all parallel once T013 done)
Task T015 [P]: Unit test retriever
Task T016 [P]: Unit test ranker
Task T017 [P]: Unit test embeddings
Task T018 [P]: Unit test cache

# Integration test (parallel to unit tests)
Task T011: Integration test retrieval workflow
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T009) - **CRITICAL BLOCKING PHASE**
3. Complete Phase 3: User Story 1 (T010-T018)
4. **STOP and VALIDATE**:
   - Run integration test (T011) to verify end-to-end retrieval
   - Run unit tests (T015-T018) to verify components
   - Test CLI manually with sample queries + classification results
   - Verify <1s response time and reasonable similarity scores
5. Deploy/demo if ready for Checkpoint 2

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (T010-T018) → Test independently → **MVP Complete!** (Checkpoint 2 ready)
   - Can retrieve relevant templates given classification
   - Has integration and unit tests
   - Ready for operator use
3. Add User Story 2 (T019-T024) → Test independently → Startup/Readiness capability added
   - Can precompute embeddings on system startup
   - Reports readiness status
   - Optional SQLite persistence for faster restarts
4. Add User Story 3 (T025-T029) → Test independently → Quality validation added
   - Can measure retrieval accuracy against test datasets
   - Generates quality reports (top-3 accuracy ≥80% gate)
   - Ready for hackathon evaluation
5. Polish (T030-T038) → Production ready for Checkpoint 2 integration with Classification Module
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T009)
2. Once Foundational is done:
   - **Developer A**: User Story 1 - Retrieve Templates (T010-T018)
     - Wait for T013 to complete before US3 can start (validation depends on retriever)
   - **Developer B**: Can start User Story 2 in parallel - Precompute/Readiness (T019-T024, independent)
   - **Developer C**: Can start User Story 3 setup (T025-T026) in parallel, then implement T027-T029 after Developer A finishes T013
3. Stories complete and integrate independently
4. **Note**: US3 has light dependency on US1 retriever.py, so US1 T013 must complete first

### Critical Path

**Longest dependency chain** (determines minimum time to MVP):
```
T001 (Setup structure)
  → T005 (Models - foundational)
  → T006 (Embeddings client - foundational)
  → T007 (Cache - foundational)
  → T012 (Precomputation - US1)
  → T013 (Retriever - US1, CRITICAL for US3)
  → T014 (CLI - US1)
  → T011 (Integration test - US1)
  → T035 (Validation quality gate)
```

**Estimated time**: ~8-12 hours for experienced developer (MVP with US1 complete)

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Integration tests are mandated by constitution (testcontainers)
- E2E tests with Chrome DevTools MCP deferred to UI integration phase (Checkpoint 3)
- Constitution requires ≥80% top-3 accuracy on validation dataset (US3 critical for Checkpoint 2 evaluation)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Count Summary

**Total Tasks**: 38

**By Phase**:
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 5 tasks
- Phase 3 (US1 - P1): 9 tasks (2 integration tests + 7 implementation/unit tests)
- Phase 4 (US2 - P2): 6 tasks (1 integration test + 5 implementation/unit tests)
- Phase 5 (US3 - P3): 5 tasks (1 integration test + 4 implementation/unit tests)
- Phase 6 (Polish): 9 tasks

**By Story**:
- US1: 9 tasks (MVP core - retrieve templates)
- US2: 6 tasks (startup/readiness)
- US3: 5 tasks (validation/quality gate)

**Parallel Opportunities**: 16 tasks marked [P] can run in parallel within their phase

**Testing**:
- Integration tests: 4 tasks (US1: 2, US2: 1, US3: 1) - Constitution mandated
- Unit tests: 11 tasks across all user stories
- Total test tasks: 15/38 (39% of effort on testing, aligning with quality focus)

**Critical Path Tasks** (blocking): T001 → T005 → T006 → T007 → T012 → T013 (6 sequential tasks)

**MVP Scope** (Checkpoint 2): T001-T009 (Foundational) + T010-T018 (US1) = 18 tasks

**Full Feature Scope** (All 3 stories): T001-T029 = 29 tasks

**Production Ready** (With polish): All 38 tasks
