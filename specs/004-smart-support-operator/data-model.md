# Phase 1: Data Model - Operator Web Interface

**Feature**: Operator Web Interface
**Branch**: `004-smart-support-operator`
**Date**: 2025-10-15

## Purpose

This document defines all data entities, their relationships, validation rules, and state transitions for the operator web interface. These models serve as the contract between frontend and backend.

---

## Entity Definitions

### E-001: InquiryInput

**Purpose**: Captures customer inquiry text from operator input

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `text` | string | min_length=5, max_length=5000, must contain Cyrillic | Customer inquiry text in Russian |

**Validation Rules**:
- VR-001: Text must be stripped of leading/trailing whitespace
- VR-002: Text must contain at least one Cyrillic character (Russian language)
- VR-003: Empty or whitespace-only text rejected with error

**State Transitions**:
```
Created (operator types) → Validated (passes VR-001-003) → Submitted (sent to backend)
                              ↓
                         Validation Failed (user-friendly error displayed)
```

**Requirement Mapping**: FR-001 (accept inquiry text)

**Example**:
```json
{
  "text": "Как открыть накопительный счет в мобильном приложении?"
}
```

---

### E-002: ClassificationResult

**Purpose**: Contains category/subcategory assignment from classification module

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `inquiry` | string | min_length=5 | Original inquiry text (echoed back) |
| `category` | string | min_length=1, must match FAQ categories | Top-level product category |
| `subcategory` | string | min_length=1, must match FAQ subcategories | Second-level classification |
| `confidence` | float | 0.0 ≤ x ≤ 1.0 | Classification confidence score |
| `processing_time_ms` | integer | > 0 | Time taken for classification (milliseconds) |
| `timestamp` | string | ISO 8601 format | When classification was performed (UTC) |

**Computed Fields**:
- `confidence_level`: string (`"high"` if ≥0.8, `"medium"` if 0.6-0.8, `"low"` if <0.6)

**Validation Rules**:
- VR-004: Category must exist in FAQ database (6 valid categories)
- VR-005: Subcategory must belong to the given category (35 total valid subcategories)
- VR-006: Confidence score normalized to 0.0-1.0 range
- VR-007: Timestamp must be valid ISO 8601 string

**State Transitions**:
```
Pending (API request sent) → Loading (awaiting response) → Success (result displayed)
                                                              ↓
                                                        Cached (5 min TTL)
                                   ↓
                              Failed (network error, timeout, validation error)
```

**Requirement Mapping**: FR-002 (display classification), FR-010 (visual confidence indicators), FR-013 (processing time)

**Example**:
```json
{
  "inquiry": "Как открыть накопительный счет в мобильном приложении?",
  "category": "Счета и вклады",
  "subcategory": "Открытие счета",
  "confidence": 0.89,
  "processing_time_ms": 1247,
  "timestamp": "2025-10-15T10:30:45Z"
}
```

---

### E-003: RetrievalRequest

**Purpose**: Input for template retrieval API (constructed from classification result)

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `query` | string | min_length=5, max_length=5000, must contain Cyrillic | Customer inquiry text |
| `category` | string | min_length=1, must exist in FAQ | Category from classification |
| `subcategory` | string | min_length=1, must match category | Subcategory from classification |
| `classification_confidence` | float (optional) | 0.0 ≤ x ≤ 1.0 | Confidence score from classification |
| `top_k` | integer | 1 ≤ x ≤ 10, default=5 | Number of templates to return |
| `use_historical_weighting` | boolean | default=false | Enable weighted scoring (not used in MVP) |

**Validation Rules**:
- VR-008: Query must match inquiry from classification (referential integrity)
- VR-009: Category/subcategory must match classification result
- VR-010: top_k clamped to 1-10 range (enforces FR-005: display top 5)

**Construction**:
```typescript
// Frontend auto-constructs from ClassificationResult
const retrievalRequest: RetrievalRequest = {
  query: classificationResult.inquiry,
  category: classificationResult.category,
  subcategory: classificationResult.subcategory,
  classification_confidence: classificationResult.confidence,
  top_k: 5
};
```

**Requirement Mapping**: FR-003 (auto-retrieve after classification)

---

### E-004: TemplateResult

**Purpose**: Single retrieved template with ranking and similarity metadata

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `template_id` | string | min_length=1 | Unique template identifier (e.g., "tmpl_001") |
| `template_question` | string | min_length=10 | FAQ question text (denormalized for UI) |
| `template_answer` | string | min_length=20 | FAQ answer text (denormalized for UI) |
| `category` | string | min_length=1 | Template category (denormalized) |
| `subcategory` | string | min_length=1 | Template subcategory (denormalized) |
| `similarity_score` | float | 0.0 ≤ x ≤ 1.0 | Cosine similarity between query and template |
| `combined_score` | float | 0.0 ≤ x ≤ 1.0 | Final ranking score (same as similarity_score for MVP) |
| `rank` | integer | ≥ 1 | Position in result list (1 = best match) |

**Computed Fields**:
- `confidence_level`: string (`"high"` if combined_score ≥0.7, `"medium"` if 0.5-0.7, `"low"` if <0.5)

**Validation Rules**:
- VR-011: Results must be sorted by rank ascending (1, 2, 3, ...)
- VR-012: Similarity scores must be valid cosine similarity (0.0 to 1.0)
- VR-013: Question and answer must contain Cyrillic characters

**Requirement Mapping**: FR-004 (ranked templates), FR-005 (top 5 with metadata), FR-011 (visual similarity indicators)

**Example**:
```json
{
  "template_id": "tmpl_savings_001",
  "template_question": "Как открыть накопительный счет через мобильное приложение?",
  "template_answer": "Для открытия накопительного счета в мобильном приложении: 1) Войдите в приложение ВТБ...",
  "category": "Счета и вклады",
  "subcategory": "Открытие счета",
  "similarity_score": 0.892,
  "combined_score": 0.892,
  "rank": 1
}
```

---

### E-005: RetrievalResponse

**Purpose**: Complete retrieval result with ranked templates and metadata

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `query` | string | min_length=5 | Original inquiry (echoed back) |
| `category` | string | min_length=1 | Category used for filtering (echoed back) |
| `subcategory` | string | min_length=1 | Subcategory used for filtering (echoed back) |
| `results` | TemplateResult[] | max_length=10 | Ranked template results |
| `total_candidates` | integer | ≥ 0 | Number of templates in category before ranking |
| `processing_time_ms` | float | ≥ 0.0 | Time to embed query + rank (milliseconds) |
| `timestamp` | datetime | ISO 8601 format | When retrieval completed (UTC) |
| `warnings` | string[] | - | Warnings (e.g., low confidence, no templates) |

**Validation Rules**:
- VR-014: Results array must be sorted by rank (1, 2, 3, ...)
- VR-015: If total_candidates = 0, results must be empty array
- VR-016: Warnings must contain actionable messages (no technical jargon)

**State Transitions**:
```
Pending (API request sent) → Loading (awaiting response) → Success (templates displayed)
                                                              ↓
                                                        Cached (5 min TTL)
                                   ↓
                              Failed (network error, timeout, no templates found)
```

**Requirement Mapping**: FR-003 (auto-retrieve), FR-004 (ranked), FR-005 (top 5), FR-014 (processing time)

**Example**:
```json
{
  "query": "Как открыть накопительный счет в мобильном приложении?",
  "category": "Счета и вклады",
  "subcategory": "Открытие счета",
  "results": [
    {
      "template_id": "tmpl_savings_001",
      "template_question": "Как открыть накопительный счет через мобильное приложение?",
      "template_answer": "Для открытия накопительного счета...",
      "category": "Счета и вклады",
      "subcategory": "Открытие счета",
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

---

### E-006: ErrorResponse

**Purpose**: Standardized error format for all API failures

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `error` | string | min_length=1 | Human-readable error message |
| `error_type` | string | enum: validation, api_error, timeout, unknown | Error category |
| `details` | string (optional) | - | Additional technical details (for logging) |
| `timestamp` | string | ISO 8601 format | When error occurred |

**Error Types**:
- `validation`: Input validation failed (FR-018, FR-022)
  - Example: "Please enter your inquiry in Russian (at least 5 characters)"
- `api_error`: Classification/retrieval service unavailable (FR-019, FR-020)
  - Example: "Unable to connect to classification service. Please check your connection and try again."
- `timeout`: Request exceeded time limit (FR-021)
  - Example: "The classification service is taking longer than expected. Please try again."
- `unknown`: Unexpected server error
  - Example: "An unexpected error occurred. Please try again or contact support."

**Validation Rules**:
- VR-017: Error message must be user-actionable (FR-022)
- VR-018: No technical stack traces or internal error codes in `error` field
- VR-019: `details` field may contain technical info for logging (not displayed to user)

**Requirement Mapping**: FR-018 (validation errors), FR-019 (classification errors), FR-020 (retrieval errors), FR-021 (timeout errors), FR-022 (actionable guidance)

**Example**:
```json
{
  "error": "Unable to connect to classification service. Please check your connection and try again.",
  "error_type": "api_error",
  "details": "Connection timeout after 5000ms to POST /api/classify",
  "timestamp": "2025-10-15T10:35:22Z"
}
```

---

### E-007: EditableTemplate (Frontend-Only)

**Purpose**: Local state for template editing feature (FR-007, FR-009)

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `original_answer` | string | min_length=20 | Original template answer (immutable) |
| `edited_answer` | string | min_length=20 | Current edited text (mutable) |
| `is_editing` | boolean | - | Whether template is in edit mode |
| `is_modified` | boolean | computed | True if edited_answer ≠ original_answer |

**Validation Rules**:
- VR-020: original_answer never changes after initialization
- VR-021: edited_answer initialized to original_answer value
- VR-022: Restore operation sets edited_answer = original_answer

**State Transitions**:
```
Display Mode (is_editing=false) → Edit Mode (is_editing=true) → Display Mode
                                      ↓                           ↓
                              User edits text              Save (keeps edits)
                                      ↓                           ↓
                              Restore Original           Copy (uses edited_answer)
                                      ↓
                              edited_answer = original_answer
```

**Requirement Mapping**: FR-007 (edit template), FR-009 (restore original)

**Example**:
```typescript
interface EditableTemplate {
  original_answer: string;   // "Для открытия счета вам потребуется..."
  edited_answer: string;     // "Для открытия счета Вам потребуется паспорт и..."
  is_editing: boolean;       // true
  is_modified: boolean;      // true (computed)
}
```

---

### E-008: UIState (Frontend-Only)

**Purpose**: Global UI state management (not persisted)

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `current_inquiry` | string | - | Text currently in inquiry input field |
| `classification_loading` | boolean | - | True while classification API request in flight |
| `retrieval_loading` | boolean | - | True while retrieval API request in flight |
| `classification_error` | ErrorResponse \| null | - | Last classification error (null if success) |
| `retrieval_error` | ErrorResponse \| null | - | Last retrieval error (null if success) |
| `clipboard_feedback` | boolean | - | True for 2s after successful copy |

**State Transitions**:
```
Idle (no inquiry submitted)
   ↓ User clicks "Submit"
Classification Loading (classification_loading=true)
   ↓ Classification API response
Classification Success (classification_loading=false) OR Classification Error
   ↓ Auto-trigger retrieval (if success)
Retrieval Loading (retrieval_loading=true)
   ↓ Retrieval API response
Retrieval Success (retrieval_loading=false) OR Retrieval Error
   ↓ User copies template
Clipboard Feedback (clipboard_feedback=true for 2s)
```

**Requirement Mapping**: FR-012 (loading state), FR-017 (responsive UI), FR-019-021 (error display)

---

## Entity Relationships

### ER-001: InquiryInput → ClassificationResult
**Type**: One-to-One (per submission)
**Flow**: User submits InquiryInput → Backend returns ClassificationResult
**Constraint**: Classification must complete within 2s (FR-015)

### ER-002: ClassificationResult → RetrievalRequest
**Type**: One-to-One (auto-constructed)
**Flow**: Frontend constructs RetrievalRequest from ClassificationResult fields
**Constraint**: Auto-triggered on classification success (FR-003)

### ER-003: RetrievalRequest → RetrievalResponse
**Type**: One-to-One
**Flow**: Backend processes RetrievalRequest → Returns RetrievalResponse with ranked templates
**Constraint**: Retrieval must complete within 1s (FR-016)

### ER-004: RetrievalResponse → TemplateResult[]
**Type**: One-to-Many
**Flow**: RetrievalResponse contains 0-5 TemplateResult objects
**Constraint**: Results sorted by rank ascending (VR-011)

### ER-005: TemplateResult → EditableTemplate
**Type**: One-to-One (per template in UI)
**Flow**: Frontend wraps each TemplateResult in EditableTemplate for editing capability
**Constraint**: original_answer never modified (VR-020)

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  Operator Interface (Frontend)                                        │
│                                                                       │
│  ┌──────────────┐                                                    │
│  │ InquiryInput │  (E-001)                                           │
│  │ text: string │                                                    │
│  └──────┬───────┘                                                    │
│         │ Submit                                                     │
│         ▼                                                            │
│  ┌──────────────────────┐                                           │
│  │ POST /api/classify   │  HTTP Request                             │
│  │ {"inquiry": "..."}   │                                            │
│  └──────┬───────────────┘                                           │
│         │ <2s (FR-015)                                               │
│         ▼                                                            │
│  ┌──────────────────────────┐                                       │
│  │ ClassificationResult     │  (E-002)                               │
│  │ category, subcategory,   │                                        │
│  │ confidence               │                                        │
│  └──────┬───────────────────┘                                       │
│         │ Auto-trigger (FR-003)                                      │
│         ▼                                                            │
│  ┌──────────────────────┐                                           │
│  │ RetrievalRequest     │  (E-003)                                   │
│  │ query, category,     │                                            │
│  │ subcategory, top_k=5 │                                            │
│  └──────┬───────────────┘                                           │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────┐                                           │
│  │ POST /api/retrieve   │  HTTP Request                             │
│  └──────┬───────────────┘                                           │
│         │ <1s (FR-016)                                               │
│         ▼                                                            │
│  ┌──────────────────────────┐                                       │
│  │ RetrievalResponse        │  (E-005)                               │
│  │ results: [               │                                        │
│  │   TemplateResult (E-004) │                                        │
│  │   rank=1, score=0.89     │                                        │
│  │ ]                        │                                        │
│  └──────┬───────────────────┘                                       │
│         │ Display                                                    │
│         ▼                                                            │
│  ┌──────────────────────────┐                                       │
│  │ EditableTemplate (E-007) │  (Frontend wrapping)                  │
│  │ original_answer,         │                                        │
│  │ edited_answer,           │                                        │
│  │ is_editing               │                                        │
│  └──────┬───────────────────┘                                       │
│         │ User edits (FR-007) or Copies (FR-006)                     │
│         ▼                                                            │
│  ┌──────────────────────────┐                                       │
│  │ Clipboard.writeText()    │  Browser API                          │
│  │ (answer text copied)     │                                        │
│  └──────────────────────────┘                                       │
│                                                                       │
│  Error Handling (any step):                                          │
│  ┌──────────────────────────┐                                       │
│  │ ErrorResponse (E-006)    │  HTTP 400/503/504                     │
│  │ error: "user message",   │                                        │
│  │ error_type: "..."        │                                        │
│  └──────────────────────────┘                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Validation Matrix

| Entity | Validation Rule | Error Type | User Message |
|--------|----------------|------------|--------------|
| InquiryInput | VR-001 (whitespace) | validation | "Please enter your inquiry text" |
| InquiryInput | VR-002 (Cyrillic) | validation | "Please enter inquiry in Russian" |
| InquiryInput | VR-003 (min length) | validation | "Inquiry must be at least 5 characters" |
| ClassificationResult | VR-004 (invalid category) | api_error | "Classification service returned invalid data" |
| ClassificationResult | VR-005 (invalid subcategory) | api_error | "Classification service returned invalid data" |
| ClassificationResult | VR-006 (confidence range) | api_error | "Classification service returned invalid data" |
| RetrievalRequest | VR-008 (query mismatch) | validation | "Internal error: query mismatch" |
| RetrievalRequest | VR-009 (category mismatch) | validation | "Internal error: category mismatch" |
| TemplateResult | VR-011 (rank order) | api_error | "Retrieval service returned invalid data" |
| TemplateResult | VR-012 (similarity range) | api_error | "Retrieval service returned invalid data" |
| RetrievalResponse | VR-014 (sort order) | api_error | "Retrieval service returned invalid data" |
| RetrievalResponse | VR-015 (empty results) | warning | "No templates found in this category" |
| ErrorResponse | VR-017 (actionable message) | - | (enforced by backend) |
| EditableTemplate | VR-020 (immutable original) | - | (enforced by frontend) |

---

## Performance Constraints

| Entity | Performance Requirement | Acceptance Criteria |
|--------|------------------------|---------------------|
| ClassificationResult | FR-015: <2s response | `processing_time_ms` < 2000 for 95% of requests |
| RetrievalResponse | FR-016: <1s response | `processing_time_ms` < 1000 for 95% of requests |
| Full Workflow | SC-001: <10s total | InquiryInput submit → TemplateResult copy < 10000ms |
| UI Actions | FR-017: Responsive | Edit mode toggle, copy button < 500ms |

---

## TypeScript Interface Definitions (Frontend)

```typescript
// frontend/src/types/classification.ts
export interface ClassificationRequest {
  inquiry: string;
}

export interface ClassificationResult {
  inquiry: string;
  category: string;
  subcategory: string;
  confidence: number;
  processing_time_ms: number;
  timestamp: string;
}

// frontend/src/types/retrieval.ts
export interface RetrievalRequest {
  query: string;
  category: string;
  subcategory: string;
  classification_confidence?: number;
  top_k?: number;
  use_historical_weighting?: boolean;
}

export interface TemplateResult {
  template_id: string;
  template_question: string;
  template_answer: string;
  category: string;
  subcategory: string;
  similarity_score: number;
  combined_score: number;
  rank: number;
}

export interface RetrievalResponse {
  query: string;
  category: string;
  subcategory: string;
  results: TemplateResult[];
  total_candidates: number;
  processing_time_ms: number;
  timestamp: string;
  warnings: string[];
}

// frontend/src/types/error.ts
export interface ErrorResponse {
  error: string;
  error_type: 'validation' | 'api_error' | 'timeout' | 'unknown';
  details?: string;
  timestamp: string;
}

// frontend/src/types/ui.ts
export interface EditableTemplate extends TemplateResult {
  original_answer: string;
  edited_answer: string;
  is_editing: boolean;
  is_modified: boolean;
}
```

---

## Constitution Compliance

**Principle I (Modular Architecture)**: ✅
- Backend entities (E-001 through E-006) mirror existing Pydantic models
- Frontend entities (E-007, E-008) isolated to UI layer
- Clean API contract via HTTP JSON

**Principle II (User-Centric Design)**: ✅
- ErrorResponse (E-006) enforces user-actionable messages (VR-017)
- EditableTemplate (E-007) supports editing + restore workflow (FR-007, FR-009)
- Performance constraints explicitly modeled (processing_time_ms fields)

**Principle III (Data-Driven Validation)**: ✅
- All validation rules (VR-001 through VR-022) explicitly documented
- Validation matrix maps rules → error types → user messages
- TypeScript interfaces enable compile-time validation

**Principle IV (API-First Integration)**: ✅
- RetrievalRequest constructed from ClassificationResult (ER-002)
- OpenAPI contracts will auto-generate from these models (Phase 1)

**Ready for Phase 1 Contracts**: ✅
