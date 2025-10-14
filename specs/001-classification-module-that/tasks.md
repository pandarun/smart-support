# Tasks: Classification Module

**Input**: Design documents from `/specs/001-classification-module-that/`
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

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure (src/classification, src/utils, src/cli, tests/unit, tests/integration, tests/e2e, data/validation, data/results)
- [x] T002 [P] Create requirements.txt with production dependencies (openai>=1.0.0, python-dotenv>=1.0.0, pydantic>=2.0.0, openpyxl>=3.1.0)
- [x] T003 [P] Create requirements-dev.txt with testing dependencies (pytest>=7.4.0, pytest-asyncio>=0.21.0, testcontainers>=3.7.0, pytest-cov>=4.1.0)
- [x] T004 [P] Create .env.example file with SCIBOX_API_KEY placeholder and FAQ_PATH, LOG_LEVEL, API_TIMEOUT variables
- [x] T005 [P] Create pytest.ini configuration file with test discovery settings and markers for unit/integration tests
- [x] T006 [P] Create all __init__.py files (src/classification/__init__.py, src/utils/__init__.py, src/cli/__init__.py, tests/__init__.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create Pydantic data models in src/classification/models.py (ClassificationRequest, ClassificationResult, BatchClassificationRequest, BatchClassificationResult, ValidationRecord, ValidationResult, CategoryAccuracy, ProcessingTimeStats, ClassificationError)
- [x] T008 Create FAQ parser in src/classification/faq_parser.py to extract categories/subcategories from docs/smart_support_vtb_belarus_faq_final.xlsx
- [x] T009 Create Scibox API client wrapper in src/classification/client.py with OpenAI client initialization, authentication, timeout handling, and error wrapping
- [x] T010 [P] Create structured logging setup in src/utils/logging.py with JSON format, log levels, and classification event logging
- [x] T011 [P] Create input validation helpers in src/utils/validation.py with Cyrillic character detection and length validation

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Single Inquiry Classification (Priority: P1) 🎯 MVP

**Goal**: Operator can classify a single Russian customer inquiry and receive category, subcategory, and confidence score within 2 seconds

**Independent Test**: Submit inquiry "Как открыть счет?" and verify returns category "Новые клиенты", subcategory "Регистрация и онбординг", confidence >0.7, processing time <2000ms

### Integration Tests for User Story 1 (Constitution Mandated)

**NOTE: These integration tests verify the complete classification workflow with real dependencies**

- [x] T012 [P] [US1] Create integration test fixtures in tests/integration/conftest.py with FAQ parser setup, Scibox API client, and mock validation for offline testing
- [x] T013 [US1] Create integration test in tests/integration/test_classification_integration.py that verifies single inquiry classification with real FAQ categories, measures processing time, validates response format

### Implementation for User Story 1

- [x] T014 [US1] Create prompt builder in src/classification/prompt_builder.py with system prompt template, category list injection, few-shot examples (2-3 Russian banking inquiries), and JSON output format specification
- [x] T015 [US1] Implement core classification logic in src/classification/classifier.py with classify() function: input validation, FAQ categories loading, prompt construction, Scibox API call (temperature=0 for determinism), JSON response parsing, confidence extraction, category validation, result formatting, error handling, logging
- [x] T016 [US1] Create CLI interface in src/cli/classify.py with argument parsing for single inquiry text, classification invocation, formatted output display (category, subcategory, confidence, time), and error message handling
- [x] T017 [P] [US1] Create unit tests in tests/unit/test_classifier.py with mocked Scibox API responses, test valid inquiry, test empty inquiry, test non-Cyrillic text, test timeout handling
- [x] T018 [P] [US1] Create unit tests in tests/unit/test_prompt_builder.py to verify prompt structure, category list inclusion, few-shot examples format, and JSON schema in prompt
- [x] T019 [P] [US1] Create unit tests in tests/unit/test_faq_parser.py to verify FAQ Excel parsing, category extraction, subcategory mapping, and error handling for missing file
- [x] T020 [P] [US1] Create unit tests in tests/unit/test_validation.py to verify Cyrillic detection, length validation, and edge cases (whitespace-only, special characters)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Operator can classify single inquiries via CLI.

---

## Phase 4: User Story 2 - Validation Dataset Testing (Priority: P2)

**Goal**: System validates classification accuracy against ground truth dataset and generates accuracy report showing ≥70% accuracy

**Independent Test**: Run validation on dataset with 3+ inquiries, verify accuracy calculation, per-category breakdown, and processing time stats

### Integration Tests for User Story 2 (Constitution Mandated)

- [x] T021 [US2] Create integration test in tests/integration/test_validation_integration.py that runs validation against sample dataset (3 test cases), verifies accuracy calculation formula, checks per-category accuracy breakdown, and validates processing time statistics

### Implementation for User Story 2

- [x] T022 [US2] Create sample validation dataset in data/validation/validation_dataset.json with 10 test inquiries covering all 6 categories, ground truth labels, and notes
- [x] T023 [US2] Implement validation module in src/classification/validator.py with run_validation() function: load validation dataset, classify each inquiry, compare predictions to ground truth, calculate overall accuracy, calculate per-category accuracy, compute processing time stats (min, max, mean, p95), generate ValidationResult object, save results to data/results/validation_results.json
- [x] T024 [US2] Add --validate flag to CLI in src/cli/classify.py to accept dataset path, invoke run_validation(), display formatted accuracy report with color-coded pass/fail (≥70% = pass), per-category breakdown table, processing time statistics, and save results to file
- [x] T025 [P] [US2] Create unit tests in tests/unit/test_validator.py to verify accuracy calculation (correct/total * 100), per-category accuracy breakdown, processing time stats calculation (min, max, mean, p95), and edge cases (empty dataset, all incorrect, all correct)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. System can validate classification quality against test datasets.

---

## Phase 5: User Story 3 - Batch Classification Processing (Priority: P3)

**Goal**: System can process multiple inquiries in batch mode efficiently, returning results in same order as input within time budget

**Independent Test**: Submit batch of 10 inquiries, verify all classified, results in correct order, total time <20 seconds

### Integration Tests for User Story 3 (Constitution Mandated)

- [x] T026 [US3] Create integration test in tests/integration/test_batch_integration.py that processes batch of 10 inquiries, verifies parallel processing (total time < sum of individual times), checks result order matches input order, validates all results have correct schema

### Implementation for User Story 3

- [x] T027 [US3] Implement batch classification in src/classification/classifier.py with classify_batch() async function: validate input list, create async tasks for parallel classification, gather results with asyncio.gather(), handle partial failures (some inquiries fail), maintain input order, aggregate processing times, log batch statistics
- [x] T028 [US3] Add --batch flag to CLI in src/cli/classify.py to accept file path with one inquiry per line, read inquiries from file, invoke classify_batch(), display progress indicator, show results table with inquiry (truncated), category, subcategory, confidence, save results to output file if requested
- [x] T029 [P] [US3] Create unit tests in tests/unit/test_classifier.py for batch processing: test batch of 3 inquiries, test empty batch, test batch with invalid inquiries (mixed valid/invalid), test result ordering, test error handling (one inquiry fails, others succeed)

**Checkpoint**: All user stories should now be independently functional. System supports single, validation, and batch classification modes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T030 [P] Add comprehensive docstrings to all public functions in src/classification/ modules with parameter descriptions, return types, example usage, and raises documentation
- [x] T031 [P] Create README.md in project root with project overview, installation instructions, usage examples (CLI and Python module), testing guide, FAQ categories list, and hackathon evaluation criteria
- [x] T032 [P] Create Dockerfile with Python 3.11 base image, dependency installation, application code copy, .env mounting, and entry point for CLI
- [x] T033 [P] Create docker-compose.yml with classification service definition, environment variables, volume mounts, and health check
- [x] T034 Run complete test suite (pytest tests/ -v --cov=src) to verify all unit and integration tests pass and achieve >80% code coverage
- [x] T035 Run validation against full validation dataset to verify ≥70% accuracy quality gate
- [x] T036 [P] Add performance optimization: implement FAQ category caching to avoid re-parsing Excel on each classification (load once on module import)
- [x] T037 [P] Add error handling improvements: retry logic with exponential backoff for Scibox API transient failures (max 3 retries)
- [x] T038 Verify quickstart.md examples work end-to-end by running all code examples from documentation

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
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 classifier.py being complete for validation to work
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 classifier.py for batch mode to extend single classification

**Dependency Graph**:
```
Setup (T001-T006)
    ↓
Foundational (T007-T011) ← BLOCKS everything below
    ↓
    ├─→ US1: Single Classification (T012-T020)
    │       ↓
    │       ├─→ US2: Validation (T021-T025) [depends on US1 classifier]
    │       └─→ US3: Batch (T026-T029) [depends on US1 classifier]
    │
    └→ All User Stories Complete
            ↓
        Polish (T030-T038)
```

### Within Each User Story

- Integration tests can be written in parallel with implementation (T012, T013 parallel to T014-T020 for US1)
- Unit tests can be written in parallel with each other (T017, T018, T019, T020 all [P])
- Core implementation must be sequential: prompt_builder (T014) → classifier (T015) → CLI (T016)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T004, T005, T006)
- Foundational tasks can run partially parallel: models (T007) can be done while FAQ parser (T008) and client (T009) are developed, then logging (T010) and validation (T011) parallel
- Within US1: Integration test fixtures (T012) parallel to prompt builder (T014), then unit tests (T017, T018, T019, T020) all parallel
- Within US2: Integration test (T021) parallel to validation dataset creation (T022)
- Within US3: Integration test (T026) can start as soon as batch function design is clear
- Polish tasks marked [P] can all run in parallel (T030, T031, T032, T033, T036, T037)

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch US1 tasks in parallel:

# Integration test prep (parallel to implementation)
Task T012: Create integration test fixtures

# Implementation (sequential core, parallel peripherals)
Task T014: Create prompt builder (BLOCKS T015)
  ↓
Task T015: Implement classifier (BLOCKS T016, enables T017-T020)
  ↓
Task T016: Create CLI

# Unit tests (all parallel once T015 done)
Task T017 [P]: Unit test classifier
Task T018 [P]: Unit test prompt builder
Task T019 [P]: Unit test FAQ parser
Task T020 [P]: Unit test validation helpers

# Integration test (parallel to unit tests)
Task T013: Integration test classification workflow
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T011) - **CRITICAL BLOCKING PHASE**
3. Complete Phase 3: User Story 1 (T012-T020)
4. **STOP and VALIDATE**:
   - Run integration test (T013) to verify end-to-end classification
   - Run unit tests (T017-T020) to verify components
   - Test CLI manually with sample inquiries
   - Verify <2s response time and reasonable accuracy
5. Deploy/demo if ready for Checkpoint 1

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (T012-T020) → Test independently → **MVP Complete!** (Checkpoint 1 ready)
   - Can classify single inquiries
   - Has integration and unit tests
   - Ready for operator use
3. Add User Story 2 (T021-T025) → Test independently → Validation capability added
   - Can measure classification accuracy
   - Generates quality reports
   - Ready for Checkpoint 1 evaluation (70% accuracy verification)
4. Add User Story 3 (T026-T029) → Test independently → Batch processing added
   - Can handle bulk inquiries
   - Optimized for QA workflows
5. Polish (T030-T038) → Production ready for Checkpoint 2
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T011)
2. Once Foundational is done:
   - **Developer A**: User Story 1 - Single Classification (T012-T020)
     - Wait for T015 to complete before US2/US3 can start (dependency)
   - **Developer B**: Can start User Story 2 setup (T021-T022) in parallel, then implement T023-T025 after Developer A finishes T015
   - **Developer C**: Can start User Story 3 integration test (T026) in parallel, then implement T027-T029 after Developer A finishes T015
3. Stories complete and integrate independently
4. **Note**: US2 and US3 have light dependency on US1 classifier.py, so US1 T015 must complete first

### Critical Path

**Longest dependency chain** (determines minimum time to MVP):
```
T001 (Setup structure)
  → T007 (Models - foundational)
  → T008 (FAQ parser - foundational)
  → T009 (API client - foundational)
  → T014 (Prompt builder - US1)
  → T015 (Classifier - US1, CRITICAL for US2/US3)
  → T016 (CLI - US1)
  → T013 (Integration test - US1)
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
- Constitution requires ≥70% accuracy on validation dataset (US2 critical for Checkpoint 1 evaluation)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Count Summary

**Total Tasks**: 38

**By Phase**:
- Phase 1 (Setup): 6 tasks
- Phase 2 (Foundational): 5 tasks
- Phase 3 (US1 - P1): 9 tasks (2 integration tests + 7 implementation/unit tests)
- Phase 4 (US2 - P2): 5 tasks (1 integration test + 4 implementation/unit tests)
- Phase 5 (US3 - P3): 4 tasks (1 integration test + 3 implementation/unit tests)
- Phase 6 (Polish): 9 tasks

**By Story**:
- US1: 9 tasks (MVP core)
- US2: 5 tasks (validation/quality)
- US3: 4 tasks (batch efficiency)

**Parallel Opportunities**: 18 tasks marked [P] can run in parallel within their phase

**Testing**:
- Integration tests: 4 tasks (US1: 2, US2: 1, US3: 1) - Constitution mandated
- Unit tests: 11 tasks across all user stories
- Total test tasks: 15/38 (39% of effort on testing, aligning with quality focus)

**Critical Path Tasks** (blocking): T001 → T007 → T008 → T009 → T014 → T015 (6 sequential tasks)

**MVP Scope** (Checkpoint 1): T001-T011 (Foundational) + T012-T020 (US1) = 20 tasks

**Full Feature Scope** (All 3 stories): T001-T029 = 29 tasks

**Production Ready** (With polish): All 38 tasks
