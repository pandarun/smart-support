<!--
  Sync Impact Report - Constitution v1.1.0
  ===============================================
  Version Change: 1.0.0 → 1.1.0 (MINOR)
  Previous Amendment: 2025-10-14
  Current Amendment: 2025-10-14

  Modified Principles:
    - Principle III: Added e2e testing requirement using Chrome DevTools MCP
    - Principle III: Added integration testing requirement using Python testcontainers

  Added Sections:
    - Quality Standards > End-to-End Testing subsection
    - Quality Standards > Integration Testing subsection

  Removed Sections: None

  Templates Status:
    ✅ plan-template.md - Constitution Check section aligns with principles
    ✅ spec-template.md - User story format compatible with principle II
    ✅ tasks-template.md - Task structure supports modular architecture (principle I)
    ⚠️  tasks-template.md - Should include e2e and integration test tasks for user stories

  Version Bump Rationale:
    MINOR bump justified because this adds new testing requirements (e2e tests
    via Chrome DevTools MCP and integration tests via Python testcontainers)
    without removing or fundamentally changing existing principles. Existing
    work remains valid; new endpoints and user stories must include tests.

  Follow-up TODOs:
    - Update tasks-template.md to include e2e and integration test task examples
-->

# Smart Support Constitution

## Core Principles

### I. Modular Architecture

The Smart Support system MUST be built as three independently testable modules that can function and be evaluated separately:

- **Classification Module**: Standalone component for inquiry categorization
- **Ranking/Retrieval Module**: Independent semantic search and template matching
- **Operator Interface**: Self-contained UI layer with clear API contracts

**Rationale**: Hackathon evaluation awards 30 points for classification quality and 30 points for recommendation relevance independently. Modules must be separately testable to enable parallel development, independent validation against test datasets, and targeted debugging.

### II. User-Centric Design

Every feature implementation MUST begin with documented user stories mapping to operator workflows. The operator interface is the primary deliverable and must prioritize:

- **Speed**: Operator can process inquiry in under 30 seconds
- **Clarity**: Classification results and ranked templates immediately visible
- **Efficiency**: One-click selection and minimal editing required

**Rationale**: UI/UX represents 20% of hackathon scoring (20 points). The system's value is measured by operator productivity gains, not backend sophistication.

### III. Data-Driven Validation (NON-NEGOTIABLE)

All classification and ranking implementations MUST be validated against provided test datasets before interface integration:

- Classification accuracy tested on validation inquiry set
- Template ranking measured against expected results
- Performance baselines documented (response time, accuracy scores)
- **Integration tests REQUIRED for each endpoint** using Python testcontainers to verify API contracts with real dependencies
- **End-to-end tests REQUIRED for each user story** using Chrome DevTools MCP to verify complete operator workflows

**Rationale**: Hackathon scoring depends entirely on measurable performance against validation data (10 points per correct classification, 10 points per correct recommendation). UI/UX quality (20 points) requires functional verification. Integration tests with testcontainers ensure endpoints work correctly with real databases and services. E2e tests using Chrome DevTools MCP ensure operator workflows function correctly across the full stack and catch integration issues before demo.

### IV. API-First Integration

All LLM interactions MUST use the Scibox API (https://llm.t1v.scibox.tech/v1) with:

- OpenAI-compatible client library (Python openai>=1.0)
- Qwen2.5-72B-Instruct-AWQ for classification/chat
- bge-m3 embeddings for semantic search
- API key managed via environment variable SCIBOX_API_KEY

**Rationale**: Hackathon infrastructure is fixed. Custom model implementations, local inference, or alternative APIs are out of scope and won't be evaluated.

### V. Deployment Simplicity

The complete system MUST be deployable via Docker with:

- Single docker-compose.yml for all services
- Environment configuration via .env file
- Clear launch instructions in README
- Cross-platform compatibility (Linux, macOS, Windows)

**Rationale**: Demo submission requires easy deployment across multiple evaluation environments. Complex setup procedures disqualify the submission or reduce presentation scores.

### VI. Knowledge Base Integration

FAQ template database (docs/smart_support_vtb_belarus_faq_final.xlsx) is the single source of truth:

- Import structure preserves categories and subcategories
- Template IDs remain stable for tracking
- Embedding generation uses exact template text
- No synthetic expansion or manual additions during hackathon

**Rationale**: Evaluation dataset references specific templates from the provided FAQ. Modified or augmented databases will fail validation tests.

## Hackathon Constraints

### Timeline Requirements

- **Checkpoint 1**: Classification + FAQ import complete
- **Checkpoint 2**: Ranking system functional, test accuracy documented
- **Checkpoint 3**: Full UI, demo video, presentation ready

### Scope Limitations

The following are explicitly OUT OF SCOPE:

- Multi-language support beyond Russian
- Historical conversation tracking
- Operator authentication/authorization
- Template editing or FAQ management UI
- Analytics dashboards
- Integration with external CRM systems

**Rationale**: Hackathon has fixed timeline and evaluation criteria. Feature creep reduces time for core deliverables that determine scoring.

### Documentation Requirements

Minimum viable documentation:

1. **README.md**: Setup instructions, Docker launch, architecture overview
2. **Demo Video**: 3-5 minute workflow demonstration (inquiry → classification → template selection → operator send)
3. **Technical Presentation**: System design, API usage, validation results

## Quality Standards

### Performance Targets

- **Classification**: <2 seconds per inquiry
- **Ranking**: Return top 5 templates in <1 second
- **UI Response**: All operator actions complete in <500ms
- **Accuracy**: ≥70% classification accuracy, ≥80% top-3 template relevance

### Code Quality

- Python type hints for all module interfaces
- Docstrings for public functions
- Error handling for all API calls
- Logging for classification and ranking decisions

### Testing Gates

Before UI integration:

- Classification module tested on 10+ validation inquiries
- Ranking module evaluated against expected template matches
- API integration verified (successful Scibox calls)
- All endpoints covered with integration tests using testcontainers

Before demo:

- End-to-end workflow tested (real inquiry → operator response)
- All user stories have passing e2e tests via Chrome DevTools MCP
- Docker deployment validated on clean environment
- Demo video captures actual system output

### Integration Testing

Each API endpoint MUST have integration tests using Python testcontainers that verify behavior with real dependencies:

**Required Integration Test Coverage:**

- **Testcontainers Framework**: Use `testcontainers-python` library for Docker-based test dependencies
- **Real Dependencies**: Tests run against actual database, Redis, or service containers (not mocks)
- **API Contract Verification**: Each endpoint tested for correct request/response format, status codes, error handling
- **Data Persistence**: Verify data correctly stored and retrieved from database containers
- **Service Integration**: Verify correct interaction with external services (Scibox API may use mocked responses)

**Integration Test Structure:**

- Tests located in `tests/integration/` directory
- One test file per module: `test_[module_name]_integration.py`
- Use fixtures to manage container lifecycle (setup once per test session)
- Tests must be idempotent (can run multiple times without side effects)
- Clean up test data after each test

**Example Test (Classification Endpoint):**

```python
from testcontainers.postgres import PostgresContainer
import pytest

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

def test_classification_endpoint_stores_result(postgres_container, api_client):
    # POST inquiry to classification endpoint
    response = api_client.post("/api/classify", json={
        "text": "Как открыть счет?"
    })
    # Verify response format and data
    assert response.status_code == 200
    assert "category" in response.json()
    # Verify data persisted in database
    # Query postgres_container to confirm storage
```

**Rationale**: Integration tests catch issues that unit tests miss: incorrect database queries, serialization errors, container configuration problems, and API contract violations. Testcontainers provide isolated, reproducible test environments matching production Docker setup.

### End-to-End Testing

Each user story MUST have at least one automated e2e test using Chrome DevTools MCP that verifies the complete operator workflow:

**Required E2E Test Elements:**

- **Browser Automation**: Use Chrome DevTools MCP tools (navigate_page, take_snapshot, click, fill, wait_for)
- **Complete User Journey**: Test covers entire user story from initial action to final outcome
- **UI Verification**: Snapshots verify classification results and template rankings are displayed correctly
- **Performance Validation**: Tests confirm response times meet targets (<30s total operator workflow)
- **Error Handling**: Tests verify system behavior under failure conditions (API errors, missing data)

**E2E Test Workflow Example (Classification User Story):**

1. Navigate to operator interface
2. Fill inquiry text field with test inquiry
3. Click submit/classify button
4. Wait for classification results to appear
5. Take snapshot to verify category/subcategory displayed
6. Verify top 5 ranked templates shown
7. Verify response time <30 seconds total

**Test Organization:**

- E2E tests located in `tests/e2e/` directory
- One test file per user story: `test_[user_story_name]_e2e.py`
- Tests run against Docker deployment (not mocked services)
- Tests MUST pass before user story considered complete

**Rationale**: E2e tests validate the operator experience end-to-end, ensuring all three modules (classification, ranking, UI) integrate correctly. Chrome DevTools MCP provides reliable browser automation for testing real operator workflows. Automated e2e tests catch integration issues early and provide confidence for demo presentation.

## Governance

### Amendment Procedure

Constitution changes require:

1. Documented justification (which constraint/principle is blocking progress)
2. Assessment of impact on hackathon scoring
3. Update to affected templates (plan, spec, tasks)
4. Version bump according to semantic versioning

### Versioning Policy

- **MAJOR**: Principle removal or architecture change (e.g., dropping modular design)
- **MINOR**: New principle or constraint added (e.g., new quality standard)
- **PATCH**: Clarification, wording improvement, typo fix

### Compliance Review

All specification and planning documents must verify:

- Proposed features align with evaluation criteria
- Implementation scope fits timeline constraints
- Dependencies on Scibox API are correctly specified
- Module boundaries are preserved

Complexity that violates simplicity or scope principles must be justified in plan.md Complexity Tracking table.

**Version**: 1.1.0 | **Ratified**: 2025-10-14 | **Last Amended**: 2025-10-14
