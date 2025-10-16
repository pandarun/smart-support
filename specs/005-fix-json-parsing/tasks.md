# Tasks: JSON Parsing with Markdown Code Block Support

**Input**: Design documents from `/specs/005-fix-json-parsing/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: Test tasks included per constitution requirement (Principle III)

**Organization**: Tasks organized by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization - no setup needed, working with existing codebase

**Status**: ✅ COMPLETE - Working in existing Smart Support codebase

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure - no foundational work required for this bugfix

**Status**: ✅ COMPLETE - All required infrastructure exists

**Checkpoint**: Foundation ready - user story implementation can begin immediately

---

## Phase 3: User Story 1 - Reliable Classification Response Parsing (Priority: P1) 🎯 MVP

**Goal**: Fix JSON parsing to handle markdown-wrapped LLM responses, eliminating classification failures

**Independent Test**: Send classification request, verify successful parsing when LLM returns JSON wrapped in markdown code blocks (```json...```). Success means zero JSON parsing errors.

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation (TDD per constitution)**

- [ ] T001 [P] [US1] Unit test for `strip_markdown_code_blocks()` with ```json code block in `tests/unit/classification/test_markdown_stripping.py`
- [ ] T002 [P] [US1] Unit test for `strip_markdown_code_blocks()` with generic ``` code block in `tests/unit/classification/test_markdown_stripping.py`
- [ ] T003 [P] [US1] Unit test for `strip_markdown_code_blocks()` with leading/trailing whitespace in `tests/unit/classification/test_markdown_stripping.py`
- [ ] T004 [P] [US1] Unit test for `strip_markdown_code_blocks()` with unwrapped JSON (backward compat) in `tests/unit/classification/test_markdown_stripping.py`
- [ ] T005 [P] [US1] Unit test for `strip_markdown_code_blocks()` with incomplete markers in `tests/unit/classification/test_markdown_stripping.py`

### Implementation for User Story 1

- [ ] T006 [US1] Add `strip_markdown_code_blocks()` function in `src/classification/classifier.py` before line 104 (before JSON parsing)
- [ ] T007 [US1] Integrate `strip_markdown_code_blocks()` call at line 104 in `src/classification/classifier.py` (replace `json.loads(response_text)` with `json.loads(strip_markdown_code_blocks(response_text))`)
- [ ] T008 [US1] Verify all unit tests pass - run `pytest tests/unit/classification/test_markdown_stripping.py -v`

### Integration Tests for User Story 1

- [ ] T009 [P] [US1] Integration test for full classification flow with markdown-wrapped JSON in `tests/integration/classification/test_markdown_parsing_integration.py`
- [ ] T010 [P] [US1] Integration test for backward compatibility (unwrapped JSON) in `tests/integration/classification/test_markdown_parsing_integration.py`
- [ ] T011 [P] [US1] Integration test for error handling with malformed JSON in `tests/integration/classification/test_markdown_parsing_integration.py`
- [ ] T012 [US1] Run integration tests - `pytest tests/integration/classification/test_markdown_parsing_integration.py -v`

**Checkpoint**: User Story 1 complete - markdown-wrapped JSON parsing works, backward compatibility verified

---

## Phase 4: User Story 2 - Comprehensive Format Support (Priority: P2)

**Goal**: Handle various markdown code block formats (uppercase specifiers, newlines, whitespace variations)

**Independent Test**: Provide responses with various markdown formats (```JSON, ``` ```, extra whitespace) and verify all parse correctly.

### Tests for User Story 2

- [ ] T013 [P] [US2] Unit test for uppercase language specifier (```JSON) in `tests/unit/classification/test_markdown_stripping.py`
- [ ] T014 [P] [US2] Unit test for newlines within code block in `tests/unit/classification/test_markdown_stripping.py`
- [ ] T015 [P] [US2] Unit test for multiple whitespace variations in `tests/unit/classification/test_markdown_stripping.py`

### Implementation for User Story 2

- [ ] T016 [US2] Review `strip_markdown_code_blocks()` implementation for format edge cases
- [ ] T017 [US2] Add handling for uppercase specifiers if needed (current implementation already handles via fallback to generic ```)
- [ ] T018 [US2] Verify newline preservation in JSON content
- [ ] T019 [US2] Run all tests - `pytest tests/unit/classification/test_markdown_stripping.py tests/integration/classification/test_markdown_parsing_integration.py -v`

**Checkpoint**: User Story 2 complete - all markdown format variations handled correctly

---

## Phase 5: User Story 3 - Robust Error Handling (Priority: P3)

**Goal**: Provide clear error messages and debug logging for invalid JSON (with or without markdown)

**Independent Test**: Provide malformed JSON responses, verify appropriate error messages logged and user-friendly errors returned.

### Tests for User Story 3

- [ ] T020 [P] [US3] Integration test for markdown-wrapped invalid JSON in `tests/integration/classification/test_markdown_parsing_integration.py`
- [ ] T021 [P] [US3] Integration test for non-JSON content wrapped in markdown in `tests/integration/classification/test_markdown_parsing_integration.py`
- [ ] T022 [US3] Unit test for error log content verification in `tests/unit/classification/test_markdown_stripping.py`

### Implementation for User Story 3

- [ ] T023 [US3] Review existing error handling in `src/classification/classifier.py` lines 105-118
- [ ] T024 [US3] Verify error logs contain full raw response after stripping attempt
- [ ] T025 [US3] Verify user-facing error messages remain generic (no raw LLM output exposure)
- [ ] T026 [US3] Run all tests including error cases - `pytest tests/ -v -k "markdown_parsing or markdown_stripping"`

**Checkpoint**: All user stories complete - production-ready with comprehensive error handling

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation, documentation, and deployment preparation

- [ ] T027 [P] Run full test suite - `pytest tests/`
- [ ] T028 [P] Manual validation with actual Scibox API using validation inquiry set
- [ ] T029 [P] Performance benchmark - verify <1ms overhead (quickstart.md guide)
- [ ] T030 Update CLAUDE.md if implementation differs from plan
- [ ] T031 Code review - verify simplicity, readability, no over-engineering
- [ ] T032 Run quickstart.md validation checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ COMPLETE (existing codebase)
- **Foundational (Phase 2)**: ✅ COMPLETE (no prerequisites needed)
- **User Stories (Phase 3-5)**: Can proceed immediately
  - User Story 1 (P1) - Independent, can start immediately
  - User Story 2 (P2) - Enhances US1, minimal dependency
  - User Story 3 (P3) - Validates US1/US2 error handling
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies - core fix
- **User Story 2 (P2)**: Enhances US1 implementation - can run in parallel or after
- **User Story 3 (P3)**: Validates US1/US2 error paths - should complete after US1

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Unit tests before implementation
- Implementation tasks sequential (same file)
- Integration tests after implementation
- Story complete before checkpoint

### Parallel Opportunities

- **User Story 1 Tests**: T001, T002, T003, T004, T005 can all run in parallel (same file, different test functions)
- **User Story 1 Integration Tests**: T009, T010, T011 can run in parallel (same file, different test functions)
- **User Story 2 Tests**: T013, T014, T015 can run in parallel
- **User Story 3 Tests**: T020, T021, T022 can run in parallel
- **Polish Phase**: T027, T028, T029 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all unit tests for User Story 1 together:
Task T001: "Unit test for strip_markdown_code_blocks() with ```json code block"
Task T002: "Unit test for strip_markdown_code_blocks() with generic ``` code block"
Task T003: "Unit test for strip_markdown_code_blocks() with leading/trailing whitespace"
Task T004: "Unit test for strip_markdown_code_blocks() with unwrapped JSON"
Task T005: "Unit test for strip_markdown_code_blocks() with incomplete markers"

# After implementation, launch all integration tests together:
Task T009: "Integration test for full classification flow with markdown-wrapped JSON"
Task T010: "Integration test for backward compatibility (unwrapped JSON)"
Task T011: "Integration test for error handling with malformed JSON"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. ✅ Phase 1: Setup (COMPLETE - using existing codebase)
2. ✅ Phase 2: Foundational (COMPLETE - no prerequisites)
3. Phase 3: User Story 1 (T001-T012)
   - Write failing tests (T001-T005)
   - Implement function (T006)
   - Integrate into classifier (T007)
   - Verify unit tests pass (T008)
   - Write integration tests (T009-T011)
   - Run integration tests (T012)
4. **STOP and VALIDATE**: Classification works with markdown-wrapped JSON
5. **CHECKPOINT**: MVP complete - core bug fixed

**Estimated Time**: 2-4 hours for MVP (US1 only)

### Incremental Delivery

1. ✅ Foundation ready (existing codebase)
2. **Add User Story 1** → Test independently → **MVP READY** ← STOP HERE FOR QUICK FIX
3. Add User Story 2 → Test independently → Enhanced format support
4. Add User Story 3 → Test independently → Production-hardened
5. Each story adds value without breaking previous functionality

### Parallel Team Strategy

With multiple developers (not recommended for this small fix):

1. Developer A: User Story 1 (core fix) - 2-4 hours
2. Developer B: User Story 2 (format enhancements) - starts after US1 complete
3. Developer C: User Story 3 (error handling validation) - starts after US1 complete

**Recommendation**: Single developer, sequential implementation (P1 → P2 → P3) given small scope.

---

## Notes

- **Minimal scope**: This is a single-function addition to one file
- **Quick win**: User Story 1 alone fixes the blocking issue (MVP)
- **TDD approach**: Tests first per constitution Principle III
- **Constitution compliance**: Integration tests required, e2e tests not needed (internal fix)
- [P] tasks = different test functions, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story independently completable and testable
- Verify tests fail before implementing
- Commit after User Story 1 checkpoint for quick deployment
- Stop at US1 checkpoint if immediate fix needed (can defer US2/US3)

## Success Criteria Validation

After implementation, verify against spec.md success criteria:

- [ ] **SC-001**: 100% of valid JSON responses parsed (test with US1/US2 tests)
- [ ] **SC-002**: Zero JSON decode errors for markdown-wrapped JSON (verify with US1 integration tests)
- [ ] **SC-003**: <1ms parsing overhead (benchmark in T029)
- [ ] **SC-004**: 100% backward compatibility (verify with T004, T010)
- [ ] **SC-005**: Error logs contain full raw response (verify in US3)
- [ ] **SC-006**: User errors remain generic (verify in US3)
