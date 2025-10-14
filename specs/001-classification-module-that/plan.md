# Implementation Plan: Classification Module

**Branch**: `001-classification-module-that` | **Date**: 2025-10-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-classification-module-that/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The Classification Module analyzes Russian customer banking inquiries and automatically determines the product category and subcategory using the Scibox Qwen2.5-72B-Instruct-AWQ LLM. This standalone, independently testable module forms the foundation of the Smart Support system, worth 30 points in hackathon evaluation. Technical approach involves prompt engineering for structured classification output, FAQ category extraction for valid targets, and performance optimization to meet <2 second response time requirements while achieving ≥70% accuracy on validation datasets.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: openai>=1.0.0 (Scibox API client), python-dotenv (environment config), openpyxl (FAQ Excel parsing), pydantic (data validation)
**Storage**: SQLite for classification history and validation results (optional for MVP, enables logging and analytics)
**Testing**: pytest (unit/integration), testcontainers-python (containerized integration tests), pytest-asyncio (async test support)
**Target Platform**: Linux/Docker container (production), macOS/Windows (development)
**Project Type**: Single project (standalone module with CLI and API interface)
**Performance Goals**: <2 seconds per inquiry (95th percentile), <1.5 seconds average, 10 concurrent requests without degradation
**Constraints**: <2s response time (hard limit), ≥70% accuracy (quality gate), Scibox API rate limits, deterministic results required
**Scale/Scope**: Single-module MVP for Checkpoint 1, ~500-1000 LOC, 3 user stories, validation on 3+ inquiry dataset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Modular Architecture

- **Compliance**: Classification module is designed as standalone component with clear interfaces
- **Evidence**: Spec FR-005 mandates Scibox API usage, SC-005 requires independent testing without ranking/UI modules
- **Verification**: Module exports classification function callable from CLI, API endpoint, or test harness

### ✅ Principle II: User-Centric Design

- **Compliance**: Three prioritized user stories (P1: Single classification, P2: Validation, P3: Batch)
- **Evidence**: P1 targets operator workflow (<2s response), P2 validates quality (70% accuracy), P3 enables QA
- **Verification**: User stories map to acceptance scenarios testable by operators

### ✅ Principle III: Data-Driven Validation (NON-NEGOTIABLE)

- **Compliance**: Validation dataset testing required (User Story 2), integration tests using testcontainers, e2e tests via Chrome DevTools MCP
- **Evidence**: QR-001 mandates ≥70% accuracy on validation data, FR-004 requires ground truth comparison
- **Verification**: Validation script runs classification against test dataset, calculates accuracy, generates report
- **Testing Requirements**:
  - Integration tests: `tests/integration/test_classification_integration.py` with testcontainers for database verification
  - E2E tests: `tests/e2e/test_single_classification_e2e.py` for User Story 1 (if UI interface exists)
  - Note: E2E tests deferred to UI integration phase (Checkpoint 3), focus on integration tests for Checkpoint 1

### ✅ Principle IV: API-First Integration

- **Compliance**: Scibox Qwen2.5-72B-Instruct-AWQ mandatory (FR-005), OpenAI-compatible client, SCIBOX_API_KEY env var (FR-007)
- **Evidence**: test_scibox_api.py validates API connectivity, chat completions working
- **Verification**: All LLM calls routed through Scibox API, no local models or alternative services

### ✅ Principle V: Deployment Simplicity

- **Compliance**: Module packaged for Docker deployment, .env configuration, no complex dependencies
- **Evidence**: Python module with standard dependencies (openai, pydantic, openpyxl), runs in Docker container
- **Verification**: Dockerfile installs dependencies via requirements.txt, docker-compose mounts .env file

### ✅ Principle VI: Knowledge Base Integration

- **Compliance**: FAQ database (docs/smart_support_vtb_belarus_faq_final.xlsx) provides valid categories/subcategories
- **Evidence**: FR-011 requires matching FAQ structure, classification prompts include valid category list from FAQ
- **Verification**: FAQ parser extracts unique categories/subcategories, classification validates output against this list

### Constitution Compliance Summary

**Status**: ✅ **PASSES** all constitution principles

**Pre-Research Gates**: All requirements satisfied
- Modular design confirmed (standalone module)
- User stories prioritized and testable
- Validation dataset approach defined
- Scibox API integration verified
- Docker deployment path clear
- FAQ database integration planned

**Post-Design Re-check**: Will verify after Phase 1 that data model and contracts maintain compliance

## Project Structure

### Documentation (this feature)

```
specs/001-classification-module-that/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── classification-api.yaml  # OpenAPI spec for classification endpoint
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```
src/
├── classification/
│   ├── __init__.py
│   ├── classifier.py        # Core classification logic
│   ├── prompt_builder.py    # LLM prompt construction
│   ├── faq_parser.py        # Excel FAQ category extraction
│   ├── models.py            # Pydantic data models
│   └── client.py            # Scibox API client wrapper
├── utils/
│   ├── __init__.py
│   ├── logging.py           # Structured logging setup
│   └── validation.py        # Input validation helpers
└── cli/
    └── classify.py          # CLI interface for classification

tests/
├── unit/
│   ├── test_classifier.py
│   ├── test_prompt_builder.py
│   ├── test_faq_parser.py
│   └── test_validation.py
├── integration/
│   └── test_classification_integration.py  # Testcontainers-based tests
└── e2e/
    └── test_single_classification_e2e.py    # Chrome DevTools MCP tests (deferred to UI phase)

data/
├── validation/
│   └── validation_dataset.json    # Ground truth test cases
└── results/
    └── validation_results.json    # Accuracy metrics output

docs/
└── smart_support_vtb_belarus_faq_final.xlsx  # FAQ database (existing)
```

**Structure Decision**: Single project structure selected because:
- Classification is a standalone module (not full web app yet)
- No frontend/backend split needed at this phase
- Module will be imported by future ranking and UI modules
- Aligns with Constitution Principle I (Modular Architecture)
- Enables independent testing and deployment for Checkpoint 1

## Complexity Tracking

*No constitutional violations - complexity tracking table not required*

All design decisions comply with constitution principles:
- Single module design (Principle I compliant)
- No additional frameworks beyond required dependencies (Principle V compliant)
- Standard Python project structure (industry best practice)
- Testcontainers for integration tests (Principle III compliant)
