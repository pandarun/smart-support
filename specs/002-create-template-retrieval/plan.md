# Implementation Plan: Template Retrieval Module

**Branch**: `002-create-template-retrieval` | **Date**: 2025-10-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-create-template-retrieval/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The Template Retrieval Module implements hybrid embeddings-based semantic search to rank and retrieve relevant FAQ template responses for classified customer inquiries. Technical approach uses Scibox bge-m3 embeddings API to precompute template vectors on startup, then performs real-time cosine similarity calculations to rank templates within the classified category/subcategory. This standalone module integrates with the existing Classification Module output to deliver top-5 relevant templates to operators within <1 second, achieving ≥80% top-3 accuracy on validation queries for 30 points in hackathon evaluation.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: openai>=1.0.0 (Scibox embeddings client), numpy>=1.24.0 (vector operations), python-dotenv (environment config), pydantic (data validation), openpyxl (FAQ parsing)
**Storage**: In-memory embedding cache (primary), SQLite (optional persistence for embeddings), existing FAQ Excel database
**Testing**: pytest (unit/integration), testcontainers-python (containerized integration tests), pytest-asyncio (async test support)
**Target Platform**: Linux/Docker container (production), macOS/Windows (development)
**Project Type**: Single project (standalone module integrating with Classification Module)
**Performance Goals**: <1 second retrieval (95th percentile), <60 seconds embedding precomputation for 100-200 templates, 10 concurrent requests without degradation
**Constraints**: <1s response time (hard limit), ≥80% top-3 accuracy (quality gate), Scibox embeddings API rate limits, in-memory storage for ~100MB embedding vectors
**Scale/Scope**: Single-module MVP for Checkpoint 2, ~800-1200 LOC, 3 user stories, validation on 10+ query-template pairs, integration with Classification Module

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Modular Architecture

- **Compliance**: Template Retrieval Module designed as standalone component with clear interfaces to Classification Module
- **Evidence**: Spec FR-002 accepts Classification Module output, FR-014 exposes retrieval via CLI and API, SC-005 requires independent testing
- **Verification**: Module exports retrieval function callable from Classification Module, CLI, operator UI, or test harness

### ✅ Principle II: User-Centric Design

- **Compliance**: Three prioritized user stories (P1: Retrieval, P2: Precomputation, P3: Validation)
- **Evidence**: P1 targets operator workflow (<1s response), P2 validates system readiness, P3 measures quality (80% top-3 accuracy)
- **Verification**: User stories map to acceptance scenarios testable by operators and QA team

### ✅ Principle III: Data-Driven Validation (NON-NEGOTIABLE)

- **Compliance**: Validation dataset testing required (User Story 3), integration tests using testcontainers, e2e tests via Chrome DevTools MCP
- **Evidence**: QR-001 mandates ≥80% top-3 accuracy on validation data, FR-013 requires validation mode with accuracy report generation
- **Verification**: Validation script runs retrieval against test dataset, calculates top-3 accuracy, generates per-query report
- **Testing Requirements**:
  - Integration tests: `tests/integration/test_retrieval_integration.py` with testcontainers for embedding storage verification
  - E2E tests: `tests/e2e/test_template_retrieval_e2e.py` for User Story 1 (deferred to UI integration phase - Checkpoint 3)
  - Note: E2E tests deferred to operator UI integration (Checkpoint 3), focus on integration tests for Checkpoint 2

### ✅ Principle IV: API-First Integration

- **Compliance**: Scibox bge-m3 embeddings API mandatory (FR-015), OpenAI-compatible client, SCIBOX_API_KEY env var (FR-016)
- **Evidence**: All embedding generation routed through Scibox API (https://llm.t1v.scibox.tech/v1/embeddings), no local embedding models
- **Verification**: Embedding precomputation and runtime query embedding use Scibox bge-m3 model exclusively

### ✅ Principle V: Deployment Simplicity

- **Compliance**: Module packaged for Docker deployment alongside Classification Module, .env configuration, no complex dependencies
- **Evidence**: Python module with standard dependencies (openai, numpy, pydantic), integrates with existing docker-compose setup
- **Verification**: Dockerfile extends Classification Module image, docker-compose adds retrieval service with shared FAQ database volume

### ✅ Principle VI: Knowledge Base Integration

- **Compliance**: FAQ database (docs/smart_support_vtb_belarus_faq_final.xlsx) provides templates for embedding and retrieval
- **Evidence**: FR-001 requires precomputing embeddings for all FAQ templates, FR-003 filters templates by category/subcategory from FAQ structure
- **Verification**: FAQ parser (from Classification Module) extracts templates with category/subcategory, embedding precomputation processes all templates

### Constitution Compliance Summary

**Status**: ✅ **PASSES** all constitution principles

**Pre-Research Gates**: All requirements satisfied
- Modular design confirmed (standalone retrieval module integrating with classification)
- User stories prioritized and testable
- Validation dataset approach defined (similar to Classification Module validation)
- Scibox embeddings API integration specified
- Docker deployment path clear (extends existing setup)
- FAQ database integration planned (reuses Classification Module parser)

**Post-Design Re-check**: Will verify after Phase 1 that data model and contracts maintain compliance

## Project Structure

### Documentation (this feature)

```
specs/002-create-template-retrieval/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── retrieval-api.yaml  # OpenAPI spec for retrieval endpoint
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```
src/
├── classification/      # Existing Classification Module
│   ├── __init__.py
│   ├── classifier.py
│   ├── faq_parser.py    # Reused by Retrieval Module
│   └── ...
├── retrieval/           # NEW: Template Retrieval Module
│   ├── __init__.py
│   ├── retriever.py     # Core retrieval logic with cosine similarity
│   ├── embeddings.py    # Scibox embeddings API client and precomputation
│   ├── ranker.py        # Template ranking (similarity + optional historical weighting)
│   ├── models.py        # Pydantic data models for retrieval
│   └── cache.py         # In-memory embedding storage with optional SQLite persistence
├── utils/               # Shared utilities
│   ├── __init__.py
│   ├── logging.py       # Shared logging (from Classification Module)
│   └── validation.py    # Shared validation helpers
└── cli/
    ├── classify.py      # Existing classification CLI
    └── retrieve.py      # NEW: CLI interface for retrieval

tests/
├── unit/
│   ├── test_classifier.py     # Existing
│   ├── test_retriever.py      # NEW: Retrieval logic unit tests
│   ├── test_embeddings.py     # NEW: Embeddings API unit tests
│   ├── test_ranker.py         # NEW: Ranking algorithm unit tests
│   └── test_cache.py          # NEW: Embedding cache unit tests
├── integration/
│   ├── test_classification_integration.py  # Existing
│   └── test_retrieval_integration.py       # NEW: Testcontainers-based retrieval tests
└── e2e/
    ├── test_single_classification_e2e.py   # Existing (deferred)
    └── test_template_retrieval_e2e.py      # NEW: Chrome DevTools MCP tests (deferred to UI phase)

data/
├── validation/
│   ├── validation_dataset.json          # Existing: classification test cases
│   └── retrieval_validation_dataset.json  # NEW: query-template pair test cases
└── results/
    ├── validation_results.json          # Existing: classification accuracy
    └── retrieval_validation_results.json  # NEW: retrieval top-3 accuracy

docs/
└── smart_support_vtb_belarus_faq_final.xlsx  # FAQ database (existing, shared)
```

**Structure Decision**: Single project structure selected because:
- Retrieval Module extends the existing Classification Module in the same Python project
- Both modules share FAQ database, utilities, and deployment infrastructure
- Aligns with Constitution Principle I (Modular Architecture) - modules are logically separate but share codebase
- Enables tight integration for Checkpoint 2 demo (classification → retrieval pipeline)
- Maintains consistency with Classification Module structure (Phase 1 complete)

## Complexity Tracking

*No constitutional violations - complexity tracking table not required*

All design decisions comply with constitution principles:
- Single project design (Principle I compliant - modular via directory structure)
- No additional frameworks beyond required dependencies (Principle V compliant)
- Standard Python project structure extending existing Classification Module
- Testcontainers for integration tests (Principle III compliant)
- Scibox embeddings API integration (Principle IV compliant)
