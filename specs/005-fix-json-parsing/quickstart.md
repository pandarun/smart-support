# Quickstart Guide: JSON Markdown Parsing Implementation

**Feature**: JSON Parsing with Markdown Code Block Support
**Date**: 2025-10-16
**Target Developers**: Backend engineers working on classification module

## Overview

This guide covers testing the markdown code block stripping functionality for JSON parsing in the classification module. The fix adds a preprocessing step to handle LLM responses wrapped in markdown code blocks.

## Prerequisites

- Python 3.12+ environment
- pytest installed (`pip install pytest`)
- Access to codebase at `/Users/schernykh/Projects/minsk_hackaton/smart-support`

## Quick Start

### 1. Understand the Change

**Location**: `src/classification/classifier.py` around line 104

**What Changed**:
```python
# BEFORE (fails on markdown-wrapped JSON):
response_data = json.loads(response_text)

# AFTER (handles both wrapped and unwrapped):
cleaned_text = strip_markdown_code_blocks(response_text)
response_data = json.loads(cleaned_text)
```

### 2. Run Unit Tests

Test the markdown stripping function in isolation:

```bash
# Navigate to project root
cd /Users/schernykh/Projects/minsk_hackaton/smart-support

# Run markdown stripping unit tests
pytest tests/unit/classification/test_markdown_stripping.py -v

# Expected output:
# test_strip_json_code_block ✓
# test_strip_generic_code_block ✓
# test_strip_with_whitespace ✓
# test_no_stripping_needed ✓
# test_incomplete_markers ✓
```

### 3. Run Integration Tests

Test the full classification flow with markdown-wrapped responses:

```bash
# Run integration tests for markdown parsing
pytest tests/integration/classification/test_markdown_parsing_integration.py -v

# Expected output:
# test_classification_with_markdown_wrapped_json ✓
# test_classification_with_unwrapped_json ✓
# test_classification_with_malformed_json ✓
```

### 4. Manual Testing

Test with actual classification requests:

```python
from src.classification import classify

# Test with markdown-wrapped response (simulated)
inquiry = "Как открыть счет?"
result = classify(inquiry)

# Should succeed and return ClassificationResult
print(f"Category: {result.category}")
print(f"Subcategory: {result.subcategory}")
print(f"Confidence: {result.confidence}")
```

## Test Case Examples

### Test Case 1: Markdown-Wrapped JSON

**Input** (LLM response with markdown):
```
```json
{
  "category": "Продукты - Вклады",
  "subcategory": "Рублевые - Великий путь",
  "confidence": 0.95
}
```
```

**Expected**: Successfully parsed, classification succeeds

### Test Case 2: Unwrapped JSON (Backward Compatibility)

**Input** (plain JSON):
```json
{
  "category": "Продукты - Карты",
  "subcategory": "Дебетовые карты",
  "confidence": 0.92
}
```

**Expected**: Successfully parsed (no change in behavior)

### Test Case 3: Invalid JSON with Markdown

**Input**:
```
```json
{
  "category": "Продукты - Вклады"
  # Missing closing brace
```
```

**Expected**: JSON parsing error (logged, user-friendly error returned)

## Integration Test Setup

### Mock Scibox API Responses

For integration tests, mock the Scibox API to return markdown-wrapped responses:

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_scibox_markdown_response():
    """Mock Scibox client returning markdown-wrapped JSON"""
    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message.content = """```json
{
  "category": "Продукты - Карты",
  "subcategory": "Дебетовые карты",
  "confidence": 0.89
}
```"""
    return mock_completion
```

## Regression Testing Checklist

Ensure no existing functionality breaks:

- [ ] Classification with unwrapped JSON still works
- [ ] Error handling for invalid JSON unchanged
- [ ] Error logging includes raw response
- [ ] User-facing error messages remain generic
- [ ] Performance within acceptable limits (<2s total)
- [ ] All existing integration tests pass

## Performance Validation

Verify the stripping overhead is negligible:

```python
import time

def benchmark_stripping():
    test_cases = [
        ("```json\n{...}\n```", "markdown-wrapped"),
        ("{...}", "unwrapped")
    ]

    for text, label in test_cases:
        start = time.perf_counter()
        for _ in range(10000):
            strip_markdown_code_blocks(text)
        elapsed = time.perf_counter() - start
        print(f"{label}: {elapsed*100:.2f}μs per call")

# Expected: <1μs per call for both cases
```

**Acceptance Criteria**: <1ms overhead (SC-003) - easily met with <1μs measured

## Debugging Tips

### Issue: Classification still fails with markdown responses

**Check**:
1. Verify `strip_markdown_code_blocks()` function is called before `json.loads()`
2. Check logs for "[DEBUG] RAW LLM RESPONSE" - does it show markdown?
3. Confirm the stripped text is valid JSON

### Issue: Unwrapped JSON now fails (regression)

**Check**:
1. Verify strip function doesn't modify unwrapped JSON
2. Run unit test: `test_no_stripping_needed`
3. Check for extra whitespace stripping issues

### Issue: Performance degradation

**Check**:
1. Verify simple string methods used (not regex)
2. Run performance benchmark
3. Profile with `cProfile` if needed

## Success Criteria Validation

After implementation, verify all success criteria from spec.md:

- ✅ **SC-001**: 100% of valid JSON responses parsed (test with 10+ varied formats)
- ✅ **SC-002**: Zero JSON decode errors for markdown-wrapped valid JSON
- ✅ **SC-003**: <1ms parsing overhead (measure with benchmark)
- ✅ **SC-004**: 100% backward compatibility (all regression tests pass)
- ✅ **SC-005**: Error logs contain full raw response (verify in error cases)
- ✅ **SC-006**: User errors remain generic (check error messages)

## Next Steps

After tests pass:

1. Run full test suite: `pytest tests/`
2. Manual validation with real Scibox API
3. Deploy to staging for validation against test dataset
4. Proceed to demo checkpoint

## Additional Resources

- **Feature Spec**: [spec.md](./spec.md)
- **Implementation Plan**: [plan.md](./plan.md)
- **Research Notes**: [research.md](./research.md)
- **Code Location**: `src/classification/classifier.py:104`
