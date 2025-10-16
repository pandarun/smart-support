# Implementation Plan: JSON Parsing with Markdown Code Block Support

**Branch**: `005-fix-json-parsing` | **Date**: 2025-10-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-fix-json-parsing/spec.md`

## Summary

Fix critical JSON parsing bug in the classification module where LLM responses wrapped in markdown code blocks (```json...```) fail to parse. The solution adds a preprocessing step to strip markdown markers before JSON parsing while maintaining backward compatibility with unwrapped responses. This is a P1 blocking issue causing classification failures.

## Technical Context

**Language/Version**: Python 3.12 (existing project stack)
**Primary Dependencies**: Python standard library (json, re modules) - no new dependencies required
**Storage**: N/A (in-memory response processing only)
**Testing**: pytest (existing test framework)
**Target Platform**: Linux server (Docker containerized)
**Project Type**: Single project (backend service enhancement)
**Performance Goals**: <1ms overhead per response parsing operation
**Constraints**: 100% backward compatibility with unwrapped JSON, zero breaking changes
**Scale/Scope**: Affects all classification requests (~hundreds per day, single function modification)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Modular Architecture ✅ PASS
- **Assessment**: This fix is entirely contained within the Classification Module at the response parsing layer
- **Module Independence**: No impact on Ranking/Retrieval or Operator Interface modules
- **Justification**: Modifies only `src/classification/classifier.py`, maintains module boundaries

### Principle II: User-Centric Design ✅ PASS
- **Assessment**: Fixes operator-facing issue where classification failures block workflow
- **User Impact**: Eliminates JSON parsing errors, enables 100% reliable classification
- **Speed**: No measurable impact (<1ms overhead per Success Criteria SC-003)

### Principle III: Data-Driven Validation ✅ PASS
- **Testing Requirements**:
  - Unit tests for markdown stripping function (various formats)
  - Integration tests for full classification flow with markdown-wrapped responses
  - Regression tests for backward compatibility (unwrapped JSON)
  - No e2e tests required (internal parsing logic, no UI changes)
- **Validation**: Test against existing validation inquiry set with both wrapped and unwrapped responses

### Principle IV: API-First Integration ✅ PASS
- **Assessment**: Fix is downstream of Scibox API calls, handles API response format variations
- **No API Changes**: Works with existing Qwen2.5-72B-Instruct-AWQ responses
- **Justification**: Accommodates actual LLM output formatting behavior

### Principle V: Deployment Simplicity ✅ PASS
- **Docker Impact**: None, code-only change within existing container
- **Configuration**: No new environment variables or dependencies
- **Deployment**: Standard git pull + container restart

### Principle VI: Knowledge Base Integration ✅ PASS
- **Assessment**: No impact on FAQ database or embeddings
- **Justification**: Parsing fix only affects classification response handling

### Testing Gates - Integration Testing ✅ REQUIRED
- **Integration Tests Needed**:
  - Test classification endpoint with markdown-wrapped LLM responses
  - Verify full request/response cycle with stripped JSON
  - Confirm backward compatibility with unwrapped responses
- **Location**: `tests/integration/classification/test_markdown_parsing_integration.py`
- **Dependencies**: May mock Scibox API responses (acceptable per constitution)

### Testing Gates - E2E Testing ❌ NOT REQUIRED
- **Rationale**: This is an internal parsing fix with no UI changes
- **No User Story Impact**: Operators see no workflow changes (just fewer errors)
- **Constitution Compliance**: E2E tests required "for each user story" - this fixes existing functionality rather than adding new user stories

**GATE RESULT**: ✅ **PASS** - All applicable constitution principles satisfied

## Project Structure

### Documentation (this feature)

```
specs/005-fix-json-parsing/
├── plan.md              # This file
├── research.md          # Phase 0: markdown parsing patterns
├── data-model.md        # Phase 1: N/A (no data model changes)
├── quickstart.md        # Phase 1: testing guide
├── contracts/           # Phase 1: N/A (no API contract changes)
└── tasks.md             # Phase 2: NOT created by /speckit.plan
```

### Source Code (repository root)

```
src/
├── classification/
│   ├── classifier.py              # MODIFIED: Add markdown stripping logic
│   └── response_parser.py         # NEW: Extract parsing utilities (optional refactor)
└── utils/
    └── text_processing.py         # ALTERNATIVE: Add markdown utils here

tests/
├── unit/
│   └── classification/
│       └── test_markdown_stripping.py     # NEW: Unit tests for stripping function
└── integration/
    └── classification/
        └── test_markdown_parsing_integration.py  # NEW: Integration tests
```

**Structure Decision**: Minimal modification approach - add helper function directly in `classifier.py` before the JSON parsing logic (line 104). This keeps changes localized and avoids unnecessary abstraction for a simple fix. Alternative: Extract to `response_parser.py` if other response processing utilities are anticipated.

## Complexity Tracking

*No constitution violations - table not required*

## Phase 0: Research & Technical Discovery

### Research Objectives

1. **Markdown Code Block Formats**: Survey common LLM markdown output patterns
2. **Python String Processing**: Evaluate regex vs simple string methods for stripping
3. **Edge Cases**: Document all markdown format variations to handle
4. **Backward Compatibility**: Verify stripping logic doesn't break unwrapped JSON

### Research Artifacts

Output: `research.md` containing:
- Decision matrix for string processing approach (regex vs string methods)
- Examples of markdown formats from actual Scibox/Qwen2.5 responses
- Edge case catalog with handling strategies
- Performance benchmarks for chosen approach

## Phase 1: Design Artifacts

### Data Model

**Status**: N/A - No data model changes required

This feature modifies text processing only, no database schema or entity changes.

### API Contracts

**Status**: N/A - No API contract changes required

This is an internal implementation fix. The classification endpoint request/response format remains unchanged.

### Quickstart Guide

Output: `quickstart.md` containing:
- How to test the markdown stripping function
- Example requests with markdown-wrapped responses
- Integration test setup instructions
- Regression testing checklist

## Phase 1 Completion: Agent Context Update

After Phase 1 artifacts are generated, run:
```bash
.specify/scripts/bash/update-agent-context.sh claude
```

This will update `.claude/context.md` with the markdown parsing implementation approach.

## Gate Re-Evaluation (Post Phase 1)

**Constitution Check Status**: ✅ **PASS** (no changes from initial assessment)

All principles remain satisfied after design phase. No new complexity introduced.
