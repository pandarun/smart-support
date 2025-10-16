# Feature Specification: JSON Parsing with Markdown Code Block Support

**Feature Branch**: `005-fix-json-parsing`
**Created**: 2025-10-16
**Status**: Draft
**Input**: User description: "Fix JSON parsing to handle markdown code blocks in LLM responses. The classifier currently fails when the LLM wraps JSON responses in ```json...``` markers. Need to strip these markers before json.loads() call in classifier.py line 104."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable Classification Response Parsing (Priority: P1)

The classification system must successfully parse all valid LLM responses regardless of whether they include markdown formatting. Currently, when the LLM wraps JSON responses in markdown code blocks (```json ... ```), the parser fails, causing classification requests to fail with JSON decode errors.

**Why this priority**: This is blocking basic functionality. Every classification request that receives a markdown-wrapped response fails, resulting in poor user experience and system unreliability.

**Independent Test**: Can be fully tested by sending a classification request and verifying the response is successfully parsed when the LLM returns JSON wrapped in markdown code blocks. Success means zero JSON parsing errors for valid responses.

**Acceptance Scenarios**:

1. **Given** the LLM returns a response wrapped in ```json...```, **When** the system attempts to parse the response, **Then** the JSON content is successfully extracted and parsed
2. **Given** the LLM returns a response wrapped in ```...``` (without json specifier), **When** the system attempts to parse the response, **Then** the JSON content is successfully extracted and parsed
3. **Given** the LLM returns unwrapped JSON, **When** the system attempts to parse the response, **Then** the JSON is parsed directly (backward compatibility)

---

### User Story 2 - Comprehensive Format Support (Priority: P2)

The system must handle various markdown code block formats that LLMs might use, including different language specifiers and formatting variations.

**Why this priority**: Different LLM responses may use different markdown conventions. Supporting multiple formats improves system robustness across LLM updates and configuration changes.

**Independent Test**: Can be tested by providing responses with various markdown formats (```json, ``` ```, ```JSON, etc.) and verifying all are parsed correctly.

**Acceptance Scenarios**:

1. **Given** the response includes leading/trailing whitespace around code blocks, **When** parsing occurs, **Then** whitespace is stripped and JSON is extracted correctly
2. **Given** the response uses uppercase language specifier (```JSON), **When** parsing occurs, **Then** the JSON is extracted correctly
3. **Given** the response has newlines within the code block, **When** parsing occurs, **Then** the JSON structure is preserved

---

### User Story 3 - Robust Error Handling (Priority: P3)

When the response contains invalid JSON (with or without markdown), the system must provide clear error messages and log debugging information without exposing internal implementation details to end users.

**Why this priority**: Good error handling aids debugging and maintains professional user experience, but doesn't block core functionality.

**Independent Test**: Can be tested by providing malformed JSON responses and verifying appropriate error messages are logged and user-friendly errors are returned.

**Acceptance Scenarios**:

1. **Given** the response contains markdown-wrapped invalid JSON, **When** parsing fails, **Then** the error message indicates JSON parsing failure without exposing raw LLM response to users
2. **Given** the response contains non-JSON content, **When** parsing is attempted, **Then** a clear error is logged with the raw response for debugging

---

### Edge Cases

- What happens when the response contains multiple code blocks? (Extract only the first block)
- How does the system handle nested code blocks? (Standard markdown doesn't support this, but strip outer markers)
- What if code block markers are incomplete (e.g., only opening ```json without closing ```)? (Attempt to strip what's present, let JSON parser handle validity)
- What if the response contains code blocks with other languages (e.g., ```python)? (Strip the markers anyway since we expect JSON content)
- What if there's text before or after the code block? (Extract content from within the markers)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST strip markdown code block opening markers (```json and ```) from LLM responses before JSON parsing
- **FR-002**: System MUST strip markdown code block closing markers (```) from LLM responses before JSON parsing
- **FR-003**: System MUST handle both language-specific (```json) and generic (```) code block markers
- **FR-004**: System MUST preserve backward compatibility by successfully parsing unwrapped JSON responses
- **FR-005**: System MUST trim leading and trailing whitespace after removing markdown markers
- **FR-006**: System MUST maintain existing error logging behavior for invalid JSON after markdown stripping
- **FR-007**: System MUST not expose raw LLM responses to end users when parsing fails (maintain user-friendly error messages)
- **FR-008**: System MUST perform markdown stripping before any JSON parsing attempts

### Key Entities

- **LLM Response**: Text content returned from the language model, may contain JSON wrapped in markdown code blocks
- **Parsed Classification**: Structured data extracted from the LLM response containing category, subcategory, and confidence fields

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid JSON responses are successfully parsed regardless of markdown wrapping
- **SC-002**: Classification requests produce zero JSON decode errors for responses containing valid JSON within markdown code blocks
- **SC-003**: Response parsing adds less than 1 millisecond of overhead per request
- **SC-004**: System maintains 100% backward compatibility (all previously working unwrapped JSON responses continue to work)
- **SC-005**: Error logs contain the full raw response for debugging when parsing fails
- **SC-006**: User-facing error messages remain generic and do not expose internal LLM response details
