# Phase 0: Technical Research - Operator Web Interface

**Feature**: Operator Web Interface
**Branch**: `004-smart-support-operator`
**Date**: 2025-10-15

## Purpose

This document resolves technical ambiguities and makes concrete technology decisions for implementing the operator web interface. All research is driven by constitution principles and specification requirements.

## Research Questions & Decisions

### RQ-001: Frontend Framework Selection

**Question**: Should we use React with TypeScript or an alternative framework?

**Options Evaluated**:
1. React 18 + TypeScript + Vite
2. Vue 3 + TypeScript
3. Svelte + TypeScript
4. Plain JavaScript (no framework)

**Decision**: ✅ **React 18 + TypeScript + Vite**

**Rationale**:
- **Developer Familiarity**: Most widely adopted framework (simplifies handoff after hackathon)
- **TypeScript Integration**: First-class TypeScript support with type-safe API client generation from Pydantic models
- **Vite**: Ultra-fast dev server (<100ms HMR) meets UI response requirement (FR-017: responsive during processing)
- **Component Ecosystem**: Rich component libraries (Material-UI, Headless UI) accelerate development
- **Testing**: React Testing Library + Jest well-established for unit/component tests

**Constitution Alignment**: Principle II (User-Centric Design) - React's component model enables reusable UI elements like ConfidenceBadge, TemplateCard for consistent visual language.

---

### RQ-002: UI Component Library Selection

**Question**: Should we use Tailwind CSS, Material-UI, or build custom components?

**Options Evaluated**:
1. Tailwind CSS + Headless UI
2. Material-UI (MUI)
3. Ant Design
4. Custom CSS (no library)

**Decision**: ✅ **Tailwind CSS + Headless UI**

**Rationale**:
- **Rapid Development**: Utility-first CSS enables faster iteration for hackathon timeline
- **Small Bundle Size**: ~10KB gzipped (vs MUI ~300KB) - faster initial load meets performance goals
- **Customization**: No opinionated design system - easier to achieve "professional appearance" (SC-010: ≥16/20 UI/UX points)
- **Headless UI**: Accessible components (focus management, ARIA) with full visual control
- **No JavaScript Overhead**: Pure CSS utilities don't impact UI response time (FR-017)

**Alternative Considered**: Material-UI rejected because predefined design system may not align with "professional banking interface" aesthetic expectations, and larger bundle size risks slower initial load.

**Constitution Alignment**: Principle V (Deployment Simplicity) - Tailwind's build step integrates cleanly into Vite without complex configuration.

---

### RQ-003: State Management Approach

**Question**: Do we need Redux/Zustand or is React state sufficient?

**Options Evaluated**:
1. React useState + useContext
2. Redux Toolkit
3. Zustand
4. React Query (server state) + useState (UI state)

**Decision**: ✅ **React Query + useState (hybrid approach)**

**Rationale**:
- **Specification Analysis**: State needs are minimal:
  - **Server State**: Classification result, retrieval results (React Query caches and invalidates)
  - **UI State**: Current inquiry text, edit mode, loading states (simple useState)
- **No Global State Needed**: Single-operator interface (A-003: one inquiry at a time) doesn't require complex state sharing
- **React Query Benefits**:
  - Automatic caching of API responses
  - Built-in loading/error states (simplifies FR-012: loading indicators)
  - Request deduplication (prevents double-submission during loading)
- **Simplicity**: useState for local component state keeps codebase simple for hackathon demo

**Constitution Alignment**: Principle I (Modular Architecture) - React Query cleanly separates server state management from UI logic.

---

### RQ-004: Backend API Framework

**Question**: Confirm FastAPI is appropriate or consider alternatives?

**Options Evaluated**:
1. FastAPI
2. Flask + Flask-RESTX
3. Django REST Framework

**Decision**: ✅ **FastAPI**

**Rationale**:
- **Existing Ecosystem**: Project already uses Pydantic models in `src/classification/models.py` and `src/retrieval/models.py`
- **Type Safety**: FastAPI auto-validates requests against Pydantic models (prevents invalid input reaching classification module)
- **Performance**: ASGI async support enables concurrent request handling
- **Auto-Documentation**: Automatic OpenAPI spec generation (satisfies contracts/ requirement)
- **CORS Support**: Built-in middleware for frontend-backend communication
- **Minimal Boilerplate**: Faster to implement than Django for simple REST API

**Constitution Alignment**: Principle IV (API-First Integration) - FastAPI's OpenAPI generation ensures clear contract between frontend and backend.

---

### RQ-005: API Contract Design

**Question**: What REST endpoints are needed to satisfy functional requirements?

**Decision**: ✅ **Two primary endpoints + one health check**

**Endpoint Specifications**:

**1. Classification Endpoint**
```
POST /api/classify
Request: {"inquiry": "Как открыть счет?"}
Response: {
  "inquiry": "Как открыть счет?",
  "category": "Новые клиенты",
  "subcategory": "Регистрация и онбординг",
  "confidence": 0.92,
  "processing_time_ms": 1247,
  "timestamp": "2025-10-15T10:30:45Z"
}
```
- **Requirement Mapping**: FR-001 (accept text), FR-002 (display classification), FR-015 (<2s)
- **Error Cases**: 400 (validation), 503 (service unavailable - FR-019)

**2. Retrieval Endpoint**
```
POST /api/retrieve
Request: {
  "query": "Как открыть счет?",
  "category": "Новые клиенты",
  "subcategory": "Регистрация и онбординг",
  "classification_confidence": 0.92,
  "top_k": 5
}
Response: {
  "query": "Как открыть счет?",
  "category": "Новые клиенты",
  "subcategory": "Регистрация и онбординг",
  "results": [
    {
      "template_id": "tmpl_001",
      "template_question": "Как зарегистрироваться в банке?",
      "template_answer": "Для регистрации вам потребуется...",
      "category": "Новые клиенты",
      "subcategory": "Регистрация и онбординг",
      "similarity_score": 0.892,
      "combined_score": 0.892,
      "rank": 1
    }
  ],
  "total_candidates": 12,
  "processing_time_ms": 487.3,
  "timestamp": "2025-10-15T10:30:46Z",
  "warnings": []
}
```
- **Requirement Mapping**: FR-003 (auto-retrieve), FR-004 (ranked), FR-005 (top 5), FR-016 (<1s)
- **Error Cases**: 400 (invalid category), 503 (service unavailable - FR-020)

**3. Health Check Endpoint**
```
GET /api/health
Response: {
  "status": "healthy",
  "classification_available": true,
  "retrieval_available": true,
  "embeddings_count": 201
}
```
- **Requirement Mapping**: FR-019, FR-020 (service availability detection)

**Constitution Alignment**: Principle IV (API-First Integration) - Endpoints mirror existing module interfaces (`Classifier.classify()`, `TemplateRetriever.retrieve()`) for clean integration.

---

### RQ-006: Frontend-Backend Communication

**Question**: How should frontend call backend APIs (polling, SSE, WebSockets, HTTP)?

**Decision**: ✅ **Simple HTTP REST (Axios)**

**Rationale**:
- **Specification Analysis**: No real-time requirements or progressive updates
- **Workflow**: Linear request-response pattern (submit → classify → retrieve → display)
- **Simplicity**: HTTP sufficient for <10s full workflow (SC-001)
- **Axios Benefits**:
  - Request/response interceptors for error handling (FR-019, FR-020, FR-021)
  - Automatic JSON serialization
  - TypeScript-friendly type definitions
  - Timeout configuration (detect slow APIs)

**Rejected Alternatives**:
- **WebSockets**: Overkill for request-response pattern
- **Server-Sent Events**: No need for server-initiated updates
- **Polling**: No background data changes to monitor

**Constitution Alignment**: Principle II (User-Centric Design) - Simple HTTP keeps latency predictable (no handshake overhead), supporting <2s classification requirement.

---

### RQ-007: Error Handling Strategy

**Question**: How should we handle classification/retrieval service failures (FR-019, FR-020, FR-021)?

**Decision**: ✅ **Graceful degradation with user-actionable messages**

**Strategy**:

**1. Network Timeouts** (FR-021)
- Frontend timeout: 5s classification, 3s retrieval
- Backend timeout: Matches module defaults (1.8s classification, 1.0s retrieval)
- User message: "The classification service is taking longer than expected. Please try again."

**2. Service Unavailable** (FR-019, FR-020)
- Backend catches module exceptions → HTTP 503
- User message: "Unable to connect to [classification/retrieval] service. Please check your connection and try again."

**3. Validation Errors** (FR-018, FR-022)
- Frontend pre-validation: Minimum 5 characters, Cyrillic detection
- Backend validation: Pydantic models enforce constraints
- User message: "Please enter your inquiry in Russian (at least 5 characters)."

**4. Unknown Errors**
- Backend logs stack trace, returns generic 500
- User message: "An unexpected error occurred. Please try again or contact support."

**Constitution Alignment**: Principle II (User-Centric Design) - All error messages provide actionable guidance (FR-022) rather than technical details.

---

### RQ-008: Testing Strategy

**Question**: How to implement integration tests with testcontainers and E2E tests with Chrome DevTools MCP?

**Decision**: ✅ **Three-layer testing pyramid**

**Layer 1: Unit Tests** (Fast, isolated)
- **Backend**: `tests/unit/test_api_models.py` - Pydantic validation logic
- **Frontend**: Jest + React Testing Library - Component rendering, user interactions
- **Execution**: `pytest tests/unit/` (backend), `npm test` (frontend)

**Layer 2: Integration Tests** (testcontainers - real SQLite)
- **File**: `backend/tests/integration/test_classification_api.py`
- **Setup**: testcontainers spins up API server + mounts `data/embeddings.db`
- **Tests**:
  - `test_classify_endpoint_returns_valid_classification()` - FR-002 validation
  - `test_classify_endpoint_performance()` - FR-015 (<2s requirement)
  - `test_classify_endpoint_validation_errors()` - FR-018 validation
- **File**: `backend/tests/integration/test_retrieval_api.py`
- **Tests**:
  - `test_retrieve_endpoint_returns_ranked_templates()` - FR-004, FR-005
  - `test_retrieve_endpoint_performance()` - FR-016 (<1s requirement)
- **File**: `backend/tests/integration/test_full_workflow.py`
- **Tests**:
  - `test_full_operator_workflow()` - SC-001 (<10s full workflow)
- **Execution**: `pytest tests/integration/ -m integration`

**Layer 3: E2E Tests** (Chrome DevTools MCP - real browser)
- **File**: `tests/e2e/test_user_story_1.py`
- **Test**: Complete P1 user story (FR-001 through FR-005)
  ```python
  @pytest.mark.e2e
  def test_inquiry_analysis_and_template_retrieval():
      # Given operator has received inquiry
      page.navigate("http://localhost:3000")

      # When they enter inquiry text
      page.fill("textarea[data-testid='inquiry-input']", "Как открыть счет?")
      page.click("button[data-testid='submit-button']")

      # Then classification displays within 2 seconds
      start = time.time()
      page.wait_for("div[data-testid='classification-result']", timeout=2000)
      assert time.time() - start < 2.0

      # And templates display within 1 second
      start = time.time()
      page.wait_for("div[data-testid='template-list']", timeout=1000)
      assert time.time() - start < 1.0

      # And top 5 templates shown with scores
      templates = page.query_all("div[data-testid='template-card']")
      assert len(templates) == 5
  ```
- **Execution**: `pytest tests/e2e/ -m e2e`

**Constitution Alignment**: Principle III (Data-Driven Validation) - Three-layer approach provides fast feedback (unit), contract verification (integration), and user scenario validation (E2E).

---

### RQ-009: Copy-to-Clipboard Implementation

**Question**: How to implement FR-006 (one-click copy) across browsers?

**Decision**: ✅ **Clipboard API with fallback**

**Implementation**:
```typescript
// frontend/src/hooks/useClipboard.ts
export const useClipboard = () => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async (text: string) => {
    try {
      // Modern Clipboard API (Chrome, Firefox, Safari)
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return { copied, copyToClipboard };
};
```

**Testing**: SC-015 (copy works across browsers) verified via Chrome DevTools MCP with different user agents.

---

### RQ-010: Response Editing Implementation

**Question**: How to implement FR-007 (edit template text) and FR-009 (restore original)?

**Decision**: ✅ **Controlled component with local state**

**Implementation**:
```typescript
// frontend/src/components/TemplateCard.tsx
const TemplateCard = ({ template }: { template: RetrievalResult }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedAnswer, setEditedAnswer] = useState(template.template_answer);

  const handleReset = () => {
    setEditedAnswer(template.template_answer);
    setIsEditing(false);
  };

  return (
    <div>
      {isEditing ? (
        <textarea value={editedAnswer} onChange={(e) => setEditedAnswer(e.target.value)} />
      ) : (
        <p>{editedAnswer}</p>
      )}
      <button onClick={() => setIsEditing(!isEditing)}>
        {isEditing ? 'Save' : 'Edit'}
      </button>
      {isEditing && <button onClick={handleReset}>Restore Original</button>}
      <button onClick={() => copyToClipboard(editedAnswer)}>Copy</button>
    </div>
  );
};
```

**Rationale**: Keeps edited state local to component (no need to sync with backend). Original template preserved in props for FR-009 restore.

---

## Technology Stack Summary

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| **Frontend Framework** | React | 18.2+ | Developer familiarity, TypeScript support, rich ecosystem |
| **Frontend Build Tool** | Vite | 5.0+ | Fast HMR, optimized production builds |
| **Frontend Language** | TypeScript | 5.0+ | Type safety with Pydantic model mirroring |
| **UI Styling** | Tailwind CSS | 3.4+ | Rapid development, small bundle, customization |
| **UI Components** | Headless UI | 1.7+ | Accessible components with full visual control |
| **Frontend State** | React Query + useState | 5.0+ | Server state caching + simple local state |
| **HTTP Client** | Axios | 1.6+ | Request interceptors, timeout support, TypeScript |
| **Frontend Testing** | Jest + React Testing Library | Latest | Component testing standard |
| **Backend Framework** | FastAPI | 0.104+ | Pydantic integration, async, auto-docs |
| **Backend Language** | Python | 3.11+ | Existing project standard |
| **ASGI Server** | Uvicorn | 0.24+ | Production-ready ASGI server |
| **Backend Testing** | pytest + testcontainers | Latest | Integration testing with real dependencies |
| **E2E Testing** | Chrome DevTools MCP | Latest | Browser automation for user scenarios |
| **Deployment** | Docker + docker-compose | Latest | Existing project infrastructure |

---

## Open Questions (for Phase 1)

1. **Q**: Should we implement request rate limiting on backend?
   - **Answer**: No - single operator assumption (A-003) makes rate limiting unnecessary for MVP

2. **Q**: Do we need authentication for MVP?
   - **Answer**: No - A-014 explicitly states no authentication for MVP

3. **Q**: Should we cache classification/retrieval results in frontend?
   - **Answer**: Yes - React Query automatically caches for 5 minutes, preventing redundant API calls during demo

4. **Q**: Do we need logging/analytics for operator actions?
   - **Answer**: No - OS-002 explicitly excludes response analytics

---

## Research Validation

**All "NEEDS CLARIFICATION" markers resolved**: ✅

**Constitution Compliance Re-Check**:
- ✅ Principle I: Backend/frontend separation maintained
- ✅ Principle II: All technology choices support <10s workflow
- ✅ Principle III: Three-layer testing strategy defined
- ✅ Principle IV: OpenAPI contracts auto-generated from Pydantic
- ✅ Principle V: Docker integration planned
- ✅ Principle VI: No FAQ database changes needed

**Ready to Proceed to Phase 1**: ✅
