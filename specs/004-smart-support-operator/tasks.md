# Tasks: Operator Web Interface

**Input**: Design documents from `/specs/004-smart-support-operator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included for integration validation and E2E scenarios as specified in the constitution (Principle III: Data-Driven Validation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions
- **Web app structure**: `backend/src/`, `frontend/src/`
- Backend: `backend/src/api/` for FastAPI endpoints
- Frontend: `frontend/src/components/` for React components
- Tests: `backend/tests/integration/`, `tests/e2e/` for integration and E2E tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create backend directory structure: `backend/src/api/`, `backend/src/api/routes/`, `backend/tests/integration/`, `backend/tests/unit/`
- [ ] T002 Create frontend directory structure using Vite: `npm create vite@latest frontend -- --template react-ts`
- [ ] T003 [P] Install backend dependencies in `backend/requirements.txt` (FastAPI 0.104+, Uvicorn, Pydantic 2.x, pytest, httpx, testcontainers)
- [ ] T004 [P] Install frontend dependencies in `frontend/`: axios, react-query, @headlessui/react, tailwindcss
- [ ] T005 [P] Configure Tailwind CSS in `frontend/tailwind.config.js` and `frontend/src/index.css`
- [ ] T006 [P] Create Python package files: `backend/src/__init__.py`, `backend/src/api/__init__.py`, `backend/src/api/routes/__init__.py`, `backend/tests/__init__.py`
- [ ] T007 Configure git to ignore frontend node_modules and backend __pycache__ in `.gitignore`

**Checkpoint**: Project structure initialized, dependencies installed

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Implement FastAPI application factory in `backend/src/api/main.py` with CORS middleware, error handlers, and app lifecycle
- [ ] T009 [P] Create Pydantic request/response models in `backend/src/api/models.py` mirroring `ClassificationRequest`, `ClassificationResult`, `RetrievalRequest`, `RetrievalResponse`, `ErrorResponse`
- [ ] T010 [P] Implement CORS and error handling middleware in `backend/src/api/middleware.py`
- [ ] T011 [P] Create TypeScript type definitions in `frontend/src/types/classification.ts` and `frontend/src/types/retrieval.ts` matching backend Pydantic models
- [ ] T012 [P] Setup Axios instance with base URL and interceptors in `frontend/src/services/api.ts`
- [ ] T013 [P] Configure React Query provider in `frontend/src/main.tsx`
- [ ] T014 [P] Create Vite proxy configuration in `frontend/vite.config.ts` to proxy `/api` to `http://localhost:8000`
- [ ] T015 Implement health check endpoint GET `/api/health` in `backend/src/api/routes/health.py` checking classification and retrieval module availability

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Inquiry Analysis and Template Retrieval (Priority: P1) 🎯 MVP

**Goal**: Enable operators to submit Russian inquiries, receive classification with confidence scores, view top 5 ranked template responses, and copy answers to clipboard - delivering the complete core workflow in under 10 seconds.

**Independent Test**: Submit inquiry "Как открыть накопительный счет?" → See classification "Счета и вклады / Открытие счета" with confidence → See 5 ranked templates → Click copy on top template → Verify text copied to clipboard. Full workflow completes in <10s.

### Tests for User Story 1 (TDD Approach)

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] [US1] Integration test for classification endpoint in `backend/tests/integration/test_classification_api.py`:
  - Test POST `/api/classify` returns valid `ClassificationResult`
  - Test validation rejects empty inquiry (<5 chars)
  - Test validation rejects non-Russian text
  - Test performance <2s (FR-015)
  - Test service unavailable error handling (FR-019)

- [ ] T017 [P] [US1] Integration test for retrieval endpoint in `backend/tests/integration/test_retrieval_api.py`:
  - Test POST `/api/retrieve` returns ranked templates
  - Test top_k=5 returns exactly 5 results (FR-005)
  - Test results sorted by similarity_score descending (FR-004)
  - Test performance <1s (FR-016)
  - Test no templates found returns empty array with warning

- [ ] T018 [P] [US1] Full workflow integration test in `backend/tests/integration/test_full_workflow.py`:
  - Test full pipeline: classify → retrieve
  - Test total time <3s for backend operations
  - Test classification auto-triggers retrieval (FR-003)

- [ ] T019 [P] [US1] E2E test for complete user story in `tests/e2e/test_user_story_1.py`:
  - Test operator enters inquiry → sees classification within 2s
  - Test templates display within 1s after classification
  - Test 5 templates shown with question, answer, similarity score
  - Test copy button copies answer text to clipboard
  - Test full workflow <10s (SC-001)

### Implementation for User Story 1

**Backend API Endpoints**

- [ ] T020 [US1] Implement POST `/api/classify` endpoint in `backend/src/api/routes/classification.py`:
  - Accept `ClassificationRequest` with inquiry text
  - Import and call existing `src.classification.classifier.get_classifier().classify()`
  - Return `ClassificationResult` with category, subcategory, confidence, processing_time_ms
  - Handle validation errors (400), service errors (503), timeouts (504)
  - Add FR-018 validation: min 5 chars, Cyrillic required

- [ ] T021 [US1] Implement POST `/api/retrieve` endpoint in `backend/src/api/routes/retrieval.py`:
  - Accept `RetrievalRequest` with query, category, subcategory, top_k
  - Import existing `src.retrieval.retriever.TemplateRetriever` and `src.retrieval.integration.initialize_retrieval_module()`
  - Call `retriever.retrieve()` to get ranked templates
  - Return `RetrievalResponse` with top-K results, total_candidates, processing_time_ms, warnings
  - Handle no templates found (empty results with warning)
  - Handle service errors (503), timeouts (504)

**Frontend Components**

- [ ] T022 [P] [US1] Create `InquiryInput.tsx` component in `frontend/src/components/InquiryInput.tsx`:
  - Textarea input for inquiry text with 5-5000 character limits (FR-001)
  - Submit button (disabled if <5 chars or no Cyrillic)
  - Client-side validation with error display (FR-018)
  - Loading state during classification (FR-012)
  - Maintain inquiry text after submission (FR-026)

- [ ] T023 [P] [US1] Create `ClassificationDisplay.tsx` component in `frontend/src/components/ClassificationDisplay.tsx`:
  - Display category and subcategory
  - Display confidence score as percentage
  - Display processing time (FR-013)
  - Visual layout with clear labels

- [ ] T024 [P] [US1] Create `TemplateList.tsx` component in `frontend/src/components/TemplateList.tsx`:
  - Display list of TemplateResult items
  - Pass each template to TemplateCard component
  - Show "No templates found" message if empty
  - Display total_candidates and retrieval processing time (FR-014)

- [ ] T025 [P] [US1] Create `TemplateCard.tsx` component in `frontend/src/components/TemplateCard.tsx`:
  - Display template question, answer, similarity score
  - Show rank number (1-5)
  - Copy button with clipboard functionality (FR-006)
  - Visual highlight for rank #1 template (FR-025)

- [ ] T026 [P] [US1] Create `LoadingSpinner.tsx` component in `frontend/src/components/LoadingSpinner.tsx`:
  - Animated spinner for classification and retrieval loading states (FR-012)
  - Text indicator "Classifying..." or "Retrieving templates..."

**Frontend Services**

- [ ] T027 [P] [US1] Implement classification API client in `frontend/src/services/classification.ts`:
  - `classify(inquiry: string): Promise<ClassificationResult>`
  - POST to `/api/classify` with axios
  - Handle errors (400, 503, 504) and convert to user messages (FR-019, FR-021, FR-022)
  - Set 5s timeout for classification API

- [ ] T028 [P] [US1] Implement retrieval API client in `frontend/src/services/retrieval.ts`:
  - `retrieve(request: RetrievalRequest): Promise<RetrievalResponse>`
  - POST to `/api/retrieve` with axios
  - Handle errors (400, 503, 504) and convert to user messages (FR-020, FR-021)
  - Set 3s timeout for retrieval API

- [ ] T029 [US1] Create `useClipboard` hook in `frontend/src/hooks/useClipboard.ts`:
  - `copyToClipboard(text: string)` function using Clipboard API with fallback
  - `copied` state with 2s auto-reset for visual feedback
  - Cross-browser compatibility (Chrome, Firefox, Safari, Edge - SC-015)

**Frontend Integration**

- [ ] T030 [US1] Implement main App component in `frontend/src/App.tsx`:
  - Import InquiryInput, ClassificationDisplay, TemplateList, LoadingSpinner
  - Wire up state: `currentInquiry`, `classificationResult`, `retrievalResponse`, `isClassifying`, `isRetrieving`
  - On inquiry submit: call classification API
  - On classification success: auto-trigger retrieval API (FR-003)
  - Handle loading states and errors
  - Clear previous results when new inquiry submitted (FR-008)
  - Tailwind CSS layout for desktop (FR-023)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Operators can submit inquiries, see classifications, view ranked templates, and copy answers.

---

## Phase 4: User Story 2 - Response Customization (Priority: P2)

**Goal**: Enable operators to edit template answer text before copying and restore original text if needed, allowing personalization without losing the original template.

**Independent Test**: Complete US1 workflow → Click "Edit" on a template → Modify answer text → Click "Copy" → Verify edited version copied → Click "Restore" → Verify original text restored.

### Tests for User Story 2

- [ ] T031 [P] [US2] E2E test for response editing in `tests/e2e/test_user_story_2.py`:
  - Test edit button makes answer editable
  - Test edited text is saved when exiting edit mode
  - Test copy button uses edited text
  - Test restore button reverts to original
  - Test edited state indicator shows modification

### Implementation for User Story 2

- [ ] T032 [US2] Enhance `TemplateCard.tsx` with editing functionality:
  - Add `isEditing` local state
  - Add `editedAnswer` state (initialized from template_answer)
  - Add `original_answer` stored on mount (immutable - VR-020)
  - Add "Edit" button to toggle edit mode
  - Replace answer display with textarea when `isEditing=true`
  - Add "Save" and "Cancel" buttons in edit mode
  - Add "Restore Original" button (FR-009)
  - Update copy button to use `editedAnswer` instead of `template_answer` (FR-007)
  - Visual indicator when answer is modified (is_modified computed field)

**Checkpoint**: User Stories 1 AND 2 should both work independently. Operators can now edit responses before copying while US1 core workflow remains intact.

---

## Phase 5: User Story 3 - Classification Confidence Assessment (Priority: P2)

**Goal**: Display visual confidence indicators (high/medium/low) for classification scores and template similarity scores to help operators make informed decisions.

**Independent Test**: Submit various inquiries → Verify classification confidence shows green (>80%), yellow (60-80%), or red (<60%) indicator → Verify each template shows color-coded similarity score → Verify low confidence (<60%) shows warning message.

### Tests for User Story 3

- [ ] T033 [P] [US3] E2E test for confidence indicators in `tests/e2e/test_user_story_3.py`:
  - Test high confidence (>80%) shows green indicator
  - Test medium confidence (60-80%) shows yellow indicator
  - Test low confidence (<60%) shows red indicator
  - Test template similarity scores have matching color coding
  - Test low confidence displays warning message

### Implementation for User Story 3

- [ ] T034 [P] [US3] Create `ConfidenceBadge.tsx` component in `frontend/src/components/ConfidenceBadge.tsx`:
  - Accept `score: number` (0.0-1.0) and `type: 'classification' | 'similarity'` props
  - Compute confidence_level: "high" (≥0.8), "medium" (0.6-0.8), "low" (<0.6)
  - Render colored badge with percentage text
  - Colors: green (high), yellow (medium), red (low) - FR-010, FR-011, FR-024
  - Tailwind CSS classes for visual distinction

- [ ] T035 [US3] Integrate ConfidenceBadge into `ClassificationDisplay.tsx`:
  - Import and render ConfidenceBadge with classification confidence score
  - Display confidence as percentage with visual indicator (FR-010)

- [ ] T036 [US3] Integrate ConfidenceBadge into `TemplateCard.tsx`:
  - Import and render ConfidenceBadge with similarity_score
  - Show similarity score for each template (FR-011)

- [ ] T037 [US3] Add low confidence warning to `ClassificationDisplay.tsx`:
  - If confidence <0.6, display warning message "Low confidence - manual review suggested" (FR-010)
  - Use yellow/red alert styling

- [ ] T038 [US3] Add low similarity warning to `TemplateList.tsx`:
  - If all templates have combined_score <0.5, display warning from RetrievalResponse.warnings array
  - Use alert styling for visibility

**Checkpoint**: User Stories 1, 2, AND 3 should all work independently. Operators now have visual confidence indicators to aid decision-making while core workflows remain functional.

---

## Phase 6: User Story 4 - Error Recovery and System Feedback (Priority: P3)

**Goal**: Provide clear, actionable error messages when classification or retrieval services fail, with loading indicators during processing and validation feedback for invalid inputs.

**Independent Test**: Simulate classification service unavailable (stop backend) → Submit inquiry → Verify user-friendly error message "Unable to connect to classification service..." → Simulate invalid input (English text) → Verify validation error "Please enter inquiry in Russian" → Test loading spinner shows during processing.

### Tests for User Story 4

- [ ] T039 [P] [US4] E2E test for error handling in `tests/e2e/test_error_handling.py`:
  - Test classification service unavailable shows user-friendly message (FR-019)
  - Test retrieval service unavailable shows user-friendly message (FR-020)
  - Test network timeout shows timeout message (FR-021)
  - Test validation errors show actionable guidance (FR-022)
  - Test loading spinner displays during processing (FR-012)

### Implementation for User Story 4

- [ ] T040 [P] [US4] Create `ErrorMessage.tsx` component in `frontend/src/components/ErrorMessage.tsx`:
  - Accept `error: ErrorResponse | null` prop
  - Display error message with red/orange alert styling
  - Show error_type icon (validation: info, api_error: warning, timeout: clock, unknown: error)
  - Display actionable message without technical details (VR-017)
  - Dismiss button to clear error

- [ ] T041 [US4] Enhance error handling in `frontend/src/services/classification.ts`:
  - Map HTTP 400 → "Please enter inquiry in Russian (at least 5 characters)" (FR-018, FR-022)
  - Map HTTP 503 → "Unable to connect to classification service. Please check your connection and try again." (FR-019)
  - Map HTTP 504 → "The classification service is taking longer than expected. Please try again." (FR-021)
  - Map other errors → "An unexpected error occurred. Please try again or contact support."
  - Return ErrorResponse with error_type

- [ ] T042 [US4] Enhance error handling in `frontend/src/services/retrieval.ts`:
  - Map HTTP 503 → "Unable to connect to retrieval service. Please check your connection and try again." (FR-020)
  - Map HTTP 504 → "The retrieval service is taking longer than expected. Please try again." (FR-021)
  - Map other errors → "An unexpected error occurred. Please try again or contact support."
  - Return ErrorResponse with error_type

- [ ] T043 [US4] Integrate ErrorMessage into `App.tsx`:
  - Add `classificationError` and `retrievalError` state
  - Display ErrorMessage component when errors occur
  - Clear errors on new inquiry submission
  - Ensure errors don't block UI (FR-017 - UI remains responsive)

- [ ] T044 [US4] Enhance LoadingSpinner integration in `App.tsx`:
  - Show spinner with "Classifying inquiry..." during classification (FR-012)
  - Show spinner with "Retrieving templates..." during retrieval (FR-012)
  - Ensure UI remains responsive (no freezing - FR-017, SC-004)

**Checkpoint**: User Stories 1-4 should all work independently. Operators now receive clear error messages and loading feedback while all previous functionality remains intact.

---

## Phase 7: User Story 5 - Performance Monitoring (Priority: P3)

**Goal**: Display processing time metrics for classification and retrieval operations, highlighting slow responses (>2s classification, >1s retrieval) to help operators understand system performance.

**Independent Test**: Submit inquiry → Verify classification time shown (e.g., "Classified in 1.2s") → Verify retrieval time shown (e.g., "Retrieved in 0.5s") → Simulate slow response → Verify time highlighted as slow.

### Tests for User Story 5

- [ ] T045 [P] [US5] E2E test for performance monitoring in `tests/e2e/test_user_story_5.py`:
  - Test classification processing time displayed (FR-013)
  - Test retrieval processing time displayed (FR-014)
  - Test slow classification (>2s) is highlighted
  - Test slow retrieval (>1s) is highlighted

### Implementation for User Story 5

- [ ] T046 [US5] Enhance `ClassificationDisplay.tsx` with processing time:
  - Display `processing_time_ms` from ClassificationResult (FR-013)
  - Format as "Classified in X.Xs"
  - If >2000ms, highlight in yellow/red with warning icon
  - Tailwind CSS for highlighting

- [ ] T047 [US5] Enhance `TemplateList.tsx` with retrieval time:
  - Display `processing_time_ms` from RetrievalResponse (FR-014)
  - Format as "Retrieved in X.Xs"
  - If >1000ms, highlight in yellow/red with warning icon
  - Tailwind CSS for highlighting

**Checkpoint**: All 5 user stories should now be independently functional. Operators have complete workflow (US1), editing (US2), confidence indicators (US3), error handling (US4), and performance monitoring (US5).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final quality assurance

- [ ] T048 [P] Add frontend unit tests for components in `frontend/src/components/__tests__/`:
  - Test InquiryInput validation logic
  - Test ConfidenceBadge color logic
  - Test useClipboard hook functionality
  - Test ErrorMessage display logic
  - Run: `npm test`

- [ ] T049 [P] Add backend unit tests in `backend/tests/unit/test_api_models.py`:
  - Test Pydantic validation for ClassificationRequest
  - Test Pydantic validation for RetrievalRequest
  - Test ErrorResponse formatting
  - Run: `pytest backend/tests/unit/ -v`

- [ ] T050 Create Dockerfile for operator UI in `Dockerfile.ui`:
  - Multi-stage build: frontend (npm build) + backend (Python)
  - Serve frontend static files through FastAPI
  - Expose port 8000
  - Health check endpoint

- [ ] T051 Update `docker-compose.yml` with operator-ui service:
  - Build from Dockerfile.ui
  - Mount data/embeddings.db
  - Environment: SCIBOX_API_KEY, FAQ_PATH
  - Port mapping: 8080:8000
  - Depends on classification and retrieval modules
  - Health check: GET /api/health

- [ ] T052 [P] Code cleanup and optimization:
  - Remove console.log statements from frontend
  - Add JSDoc comments to key functions
  - Run `prettier` on frontend code
  - Run `black` on backend code
  - Verify no linting errors

- [ ] T053 [P] Performance validation per `quickstart.md`:
  - Test classification <2s: `time curl POST /api/classify`
  - Test retrieval <1s: `time curl POST /api/retrieve`
  - Test full workflow <10s via E2E test
  - Document results in validation report

- [ ] T054 Run complete test suite:
  - Backend unit tests: `pytest backend/tests/unit/ -v`
  - Backend integration tests: `pytest backend/tests/integration/ -v`
  - Frontend unit tests: `npm test`
  - E2E tests: `pytest tests/e2e/ -v -m e2e`
  - All tests must pass

- [ ] T055 Validate against constitution principles:
  - ✅ Principle I: Backend doesn't modify `src/classification/` or `src/retrieval/`
  - ✅ Principle II: All error messages user-actionable (no technical jargon)
  - ✅ Principle III: Integration tests use testcontainers, E2E use Chrome DevTools MCP
  - ✅ Principle IV: API matches OpenAPI specs in `contracts/`
  - ✅ Principle V: Docker works with `docker-compose up operator-ui`
  - ✅ Principle VI: No changes to FAQ Excel file

- [ ] T056 Create demo video and presentation materials:
  - Record 2-3 minute demo showing full workflow
  - Highlight: <10s end-to-end, visual confidence, editing, error handling
  - Prepare slides explaining architecture and business value

**Checkpoint**: All tasks complete, ready for hackathon submission

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - User Stories 1-5 can proceed in parallel (if staffed)
  - Or sequentially in priority order: US1 (P1) → US2 (P2) → US3 (P2) → US4 (P3) → US5 (P3)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends TemplateCard from US1 but independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Adds ConfidenceBadge to US1 components but independently testable
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Adds ErrorMessage to US1 App.tsx but independently testable
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Enhances US1 display components but independently testable

**Key Insight**: All user stories are designed to be independently testable. Each adds functionality without breaking previous stories.

### Within Each User Story

- **Tests → Implementation**: Write tests FIRST, verify they FAIL, then implement
- **Backend before Frontend**: API endpoints functional before UI components
- **Models → Services → Endpoints**: Data models before business logic before HTTP routes
- **Components → Integration**: Individual React components before App.tsx integration

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T003 (backend deps) + T004 (frontend deps) + T005 (Tailwind) + T006 (package files) = 4 parallel tasks

**Foundational Phase (Phase 2)**:
- T009 (Pydantic models) + T010 (middleware) + T011 (TypeScript types) + T012 (Axios) + T013 (React Query) + T014 (Vite proxy) = 6 parallel tasks after T008 completes

**User Story 1 Tests** (Phase 3):
- T016 (classification test) + T017 (retrieval test) + T018 (workflow test) + T019 (E2E test) = 4 parallel tasks

**User Story 1 Components** (Phase 3):
- T022 (InquiryInput) + T023 (ClassificationDisplay) + T024 (TemplateList) + T025 (TemplateCard) + T026 (LoadingSpinner) = 5 parallel tasks after T020-T021 complete
- T027 (classification service) + T028 (retrieval service) = 2 parallel tasks

**Polish Phase (Phase 8)**:
- T048 (frontend unit tests) + T049 (backend unit tests) + T052 (code cleanup) + T053 (performance validation) = 4 parallel tasks

**Parallel Example for MVP (User Story 1)**:
```bash
# After T008-T015 (Foundational) complete:

# Launch all US1 tests together:
Task: "Integration test for classification endpoint" (T016)
Task: "Integration test for retrieval endpoint" (T017)
Task: "Full workflow integration test" (T018)
Task: "E2E test for complete user story" (T019)

# After T020-T021 (API endpoints) complete, launch all components:
Task: "Create InquiryInput.tsx" (T022)
Task: "Create ClassificationDisplay.tsx" (T023)
Task: "Create TemplateList.tsx" (T024)
Task: "Create TemplateCard.tsx" (T025)
Task: "Create LoadingSpinner.tsx" (T026)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

**Goal**: Deliver complete core workflow as fast as possible

1. **Complete Phase 1: Setup** (T001-T007) → ~30 minutes
2. **Complete Phase 2: Foundational** (T008-T015) → ~1-2 hours
   - **CRITICAL**: This blocks all user stories
3. **Complete Phase 3: User Story 1** (T016-T030) → ~2-3 hours
   - Tests first (T016-T019): Write, verify FAIL
   - Backend APIs (T020-T021): Implement, verify tests PASS
   - Frontend components (T022-T026): Parallel implementation
   - Frontend services (T027-T029): API clients + clipboard
   - Integration (T030): Wire everything together
4. **STOP and VALIDATE**: Run all US1 tests (T016-T019), test manually in browser
5. **Deploy/Demo**: `docker-compose up operator-ui` and demonstrate <10s workflow

**Estimated Time**: ~4-6 hours for complete MVP (US1 only)

**MVP Validation Criteria**:
- ✅ Operator enters Russian inquiry
- ✅ Classification displays within 2s with confidence
- ✅ Top 5 templates display within 1s
- ✅ Operator can copy any template answer
- ✅ Full workflow <10s (SC-001)

---

### Incremental Delivery (Add US2-US5 Sequentially)

**After MVP deployed, add features incrementally**:

1. **Add User Story 2 (Response Customization)** → ~30-45 minutes
   - T031 (test), T032 (enhance TemplateCard with editing)
   - Test independently: Edit → Copy → Restore
   - Deploy: US1 + US2 functional

2. **Add User Story 3 (Confidence Indicators)** → ~45-60 minutes
   - T033 (test), T034-T038 (ConfidenceBadge + integration)
   - Test independently: Visual indicators for all confidence levels
   - Deploy: US1 + US2 + US3 functional

3. **Add User Story 4 (Error Handling)** → ~1 hour
   - T039 (test), T040-T044 (ErrorMessage + error handling)
   - Test independently: Service failures, validation errors, loading states
   - Deploy: US1 + US2 + US3 + US4 functional

4. **Add User Story 5 (Performance Monitoring)** → ~30 minutes
   - T045 (test), T046-T047 (processing time display)
   - Test independently: Time metrics and slow response highlighting
   - Deploy: All user stories functional

5. **Complete Phase 8: Polish** (T048-T056) → ~1-2 hours
   - Unit tests, Docker, validation, demo materials
   - Final submission ready

**Total Estimated Time**: ~10-14 hours for complete feature (all 5 user stories + polish)

---

### Parallel Team Strategy

**With 3 developers working simultaneously**:

1. **All devs: Setup + Foundational together** (T001-T015) → ~1-2 hours
   - **CRITICAL**: Everyone waits for T008-T015 to complete before proceeding

2. **After Foundational complete, split by user story**:
   - **Developer A: User Story 1 (MVP)** (T016-T030) → ~2-3 hours
   - **Developer B: User Story 2 + User Story 3** (T031-T038) → ~2 hours
   - **Developer C: User Story 4 + User Story 5** (T039-T047) → ~2 hours

3. **All devs: Polish together** (T048-T056) → ~1 hour
   - Parallel: T048 (frontend tests), T049 (backend tests), T052 (cleanup)
   - Sequential: T050-T051 (Docker), T053-T056 (validation, demo)

**Total Team Time**: ~5-7 hours with 3 developers (vs ~10-14 hours solo)

**Integration Points**: Developers working on US2-US5 may need to wait for Developer A to complete US1 components (TemplateCard, ClassificationDisplay, etc.) before enhancing them. To avoid blocking, Developer A can create component stubs early.

---

## Task Summary

**Total Tasks**: 56

**Task Count by Phase**:
- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundational): 8 tasks
- Phase 3 (US1 - MVP): 15 tasks
- Phase 4 (US2): 2 tasks
- Phase 5 (US3): 5 tasks
- Phase 6 (US4): 5 tasks
- Phase 7 (US5): 2 tasks
- Phase 8 (Polish): 12 tasks

**Task Count by User Story**:
- US1 (Inquiry Analysis and Template Retrieval - P1): 15 tasks (27% of total)
- US2 (Response Customization - P2): 2 tasks (4% of total)
- US3 (Confidence Assessment - P2): 5 tasks (9% of total)
- US4 (Error Recovery - P3): 5 tasks (9% of total)
- US5 (Performance Monitoring - P3): 2 tasks (4% of total)
- Shared/Infrastructure (Setup + Foundational + Polish): 27 tasks (48% of total)

**Parallelization**:
- 28 tasks marked [P] can run in parallel within their phase
- 5 user stories can run in parallel after Foundational phase
- Estimated 30-40% time savings with parallel execution

**Independent Test Criteria**:
- US1: Full workflow <10s (inquiry → classification → retrieval → copy)
- US2: Edit → Copy → Restore cycle
- US3: Visual confidence indicators for all score ranges
- US4: Error messages for all failure modes + loading states
- US5: Processing time display with slow response highlighting

**Suggested MVP Scope**: User Story 1 only (T001-T030) = 30 tasks, ~4-6 hours solo, ~2-3 hours with team

---

## Notes

- [P] tasks = different files, no dependencies - run in parallel
- [Story] label (US1-US5) maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests written FIRST (TDD approach), verified to FAIL before implementation
- Commit after each task or logical group of [P] tasks
- Stop at any checkpoint to validate story independently before proceeding
- Avoid vague tasks, same-file conflicts, or cross-story dependencies that break independence
- Performance requirements (FR-015: <2s classification, FR-016: <1s retrieval, SC-001: <10s workflow) validated in T053
- Constitution compliance validated in T055 before final submission
