# Research: Classification Module

**Feature**: Classification Module
**Date**: 2025-10-14
**Purpose**: Document technical decisions, best practices, and research findings for implementation

## Overview

This research document consolidates findings for implementing the Classification Module that analyzes Russian banking inquiries using Scibox Qwen2.5-72B-Instruct-AWQ LLM to determine product categories and subcategories with ≥70% accuracy and <2 second response time.

## Technical Decisions

### 1. Prompt Engineering Strategy

**Decision**: Use structured JSON output prompting with few-shot examples and category list constraints

**Rationale**:
- Qwen2.5-72B-Instruct-AWQ supports structured output formats
- JSON format enables deterministic parsing (QR-002 requirement)
- Including valid category/subcategory list in prompt reduces hallucination
- Few-shot examples improve Russian banking domain understanding

**Alternatives Considered**:
- **Free-form text output**: Rejected - requires complex parsing, prone to format variations
- **Multiple sequential API calls (category, then subcategory)**: Rejected - doubles latency, exceeds 2s budget
- **Fine-tuned model**: Rejected - out of scope for hackathon timeline, Scibox models are fixed

**Implementation Approach**:
```python
system_prompt = """Ты эксперт по банковским продуктам ВТБ Беларусь.
Твоя задача: классифицировать запросы клиентов по категориям и подкатегориям.

Доступные категории и подкатегории:
{category_list}

Ответь ТОЛЬКО в формате JSON:
{
  "category": "название категории",
  "subcategory": "название подкатегории",
  "confidence": 0.0-1.0
}"""

few_shot_examples = [
    {"inquiry": "Как открыть счет?", "category": "Счета и вклады", "subcategory": "Открытие счета"},
    {"inquiry": "Процентная ставка по кредиту", "category": "Кредиты", "subcategory": "Условия кредитования"}
]
```

### 2. FAQ Category Extraction

**Decision**: Parse Excel FAQ database on module initialization, cache category/subcategory hierarchy in memory

**Rationale**:
- FAQ file is stable during hackathon (Assumption in spec)
- ~50-100 categories expected, minimal memory footprint (<1MB)
- Eliminates file I/O on each classification request (performance optimization)
- Enables validation of LLM output against known categories

**Alternatives Considered**:
- **Load FAQ on each request**: Rejected - adds 50-100ms file I/O per request, violates <2s budget
- **Database storage**: Rejected - adds complexity, categories rarely change, overkill for MVP

**Implementation Approach**:
```python
from openpyxl import load_workbook

def parse_faq_categories(faq_path: str) -> dict[str, list[str]]:
    """Extract category → [subcategories] mapping from FAQ Excel"""
    workbook = load_workbook(faq_path, read_only=True)
    sheet = workbook.active

    categories = {}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        category, subcategory = row[0], row[1]  # Adjust column indices based on FAQ structure
        if category not in categories:
            categories[category] = []
        if subcategory not in categories[category]:
            categories[category].append(subcategory)

    return categories
```

### 3. Response Time Optimization

**Decision**: Implement timeout controls, connection pooling, and async API calls for batch processing

**Rationale**:
- Scibox API typically responds in 800ms-1.5s for classification tasks (verified in test_scibox_api.py)
- Timeout set to 1.8s allows 200ms overhead for parsing/validation (total <2s)
- Connection reuse reduces TCP handshake overhead (saves 50-100ms per request)
- Async processing for batch enables parallel API calls (User Story 3)

**Alternatives Considered**:
- **Caching**: Rejected for MVP - requires cache invalidation logic, determinism issues (QR-002)
- **Model quantization**: Rejected - Scibox models are fixed, no control over server-side optimization
- **Prompt length reduction**: Considered but risky - may reduce accuracy below 70% threshold

**Implementation Approach**:
```python
from openai import OpenAI
import asyncio

client = OpenAI(
    api_key=os.getenv("SCIBOX_API_KEY"),
    base_url="https://llm.t1v.scibox.tech/v1",
    timeout=1.8  # 1.8s API timeout + 0.2s overhead = <2s total
)

async def classify_batch(inquiries: list[str]) -> list[ClassificationResult]:
    """Parallel classification for batch processing"""
    tasks = [classify_single(inq) for inq in inquiries]
    return await asyncio.gather(*tasks)
```

### 4. Confidence Score Calculation

**Decision**: Use LLM's internal confidence if available, otherwise calculate based on prompt similarity to examples

**Rationale**:
- Qwen models may return token probabilities or confidence scores
- Fallback: cosine similarity between inquiry and known category keywords
- QR-003 requires confidence correlation with accuracy

**Alternatives Considered**:
- **Fixed confidence (always 1.0)**: Rejected - violates QR-003, no utility for operators
- **Ensemble voting (multiple LLM calls)**: Rejected - exceeds time budget, increases cost

**Implementation Approach**:
```python
def extract_confidence(llm_response: dict) -> float:
    """Extract or calculate confidence score 0.0-1.0"""
    # Try to extract from LLM response first
    if "confidence" in llm_response:
        return float(llm_response["confidence"])

    # Fallback: keyword-based confidence
    # (Implementation would compare inquiry tokens to category keywords)
    return 0.7  # Default moderate confidence
```

### 5. Input Validation Strategy

**Decision**: Implement Pydantic models for request/response validation with Cyrillic character detection

**Rationale**:
- Pydantic provides automatic validation (FR-009: non-empty, Cyrillic check)
- Type hints improve code quality and IDE support
- FastAPI integration path for future API endpoint (Checkpoint 3)

**Alternatives Considered**:
- **Manual validation**: Rejected - error-prone, verbose, no type safety
- **JSON Schema**: Rejected - less Pythonic, no integration with type system

**Implementation Approach**:
```python
from pydantic import BaseModel, field_validator
import re

class ClassificationRequest(BaseModel):
    text: str

    @field_validator('text')
    def validate_text(cls, v):
        if not v or len(v.strip()) < 5:
            raise ValueError("Inquiry text must be at least 5 characters")
        if len(v) > 5000:
            raise ValueError("Inquiry text must not exceed 5000 characters")
        if not re.search(r'[а-яА-ЯёЁ]', v):
            raise ValueError("Inquiry must contain at least one Cyrillic character")
        return v.strip()

class ClassificationResult(BaseModel):
    inquiry: str
    category: str
    subcategory: str
    confidence: float
    processing_time_ms: int
```

### 6. Logging and Observability

**Decision**: Use Python's `logging` module with structured JSON output for classification events

**Rationale**:
- FR-008 requires logging of timestamp, inquiry, category, subcategory, confidence, processing time
- JSON format enables log aggregation and analysis for accuracy monitoring
- Standard library avoids external dependencies (Principle V: Deployment Simplicity)

**Alternatives Considered**:
- **Print statements**: Rejected - unstructured, no log levels, not production-ready
- **Third-party logging (structlog, loguru)**: Rejected - unnecessary dependency for MVP

**Implementation Approach**:
```python
import logging
import json
import time

logger = logging.getLogger("classification")

def log_classification(inquiry: str, result: ClassificationResult):
    logger.info(json.dumps({
        "timestamp": time.time(),
        "inquiry": inquiry[:100],  # Truncate for privacy
        "category": result.category,
        "subcategory": result.subcategory,
        "confidence": result.confidence,
        "processing_time_ms": result.processing_time_ms
    }))
```

### 7. Testing Strategy

**Decision**: Three-layer testing - unit (mocked LLM), integration (testcontainers + real Scibox API), validation (ground truth dataset)

**Rationale**:
- Principle III mandates integration tests with testcontainers
- Unit tests enable fast iteration without API calls
- Validation tests verify 70% accuracy requirement (QR-001)

**Testing Layers**:

1. **Unit Tests** (`tests/unit/`)
   - Mock Scibox API responses
   - Test prompt construction logic
   - Test FAQ parsing
   - Test input validation
   - Fast execution (<5s total)

2. **Integration Tests** (`tests/integration/`)
   - Use testcontainers for SQLite database (if logging persistence added)
   - Real Scibox API calls (requires valid API key in test env)
   - Verify end-to-end classification flow
   - Moderate execution time (<30s)

3. **Validation Tests** (`data/validation/`)
   - Run classifier against validation_dataset.json with ground truth labels
   - Calculate accuracy: (correct / total) * 100
   - Generate validation_results.json report
   - Must achieve ≥70% to pass quality gate

**Example Integration Test**:
```python
import pytest
from testcontainers.core.container import DockerContainer
from src.classification.classifier import classify

def test_classification_integration():
    """Integration test with real Scibox API"""
    inquiry = "Как открыть счет?"
    result = classify(inquiry)

    assert result.category in ["Счета и вклады", "Кредиты", "Карты"]  # Valid categories
    assert result.subcategory  # Non-empty
    assert 0.0 <= result.confidence <= 1.0
    assert result.processing_time_ms < 2000  # <2s requirement
```

## Best Practices

### Python Async/Await for Batch Processing

**Guidance**: Use `asyncio` for concurrent API calls in batch classification (User Story 3)

**Benefits**:
- Single-threaded concurrency (no GIL issues)
- Efficient I/O-bound task handling (API calls)
- Native Python 3.11+ support

**Example**:
```python
async def classify_batch_async(inquiries: list[str]) -> list[ClassificationResult]:
    tasks = [classify_async(inq) for inq in inquiries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
```

### Error Handling Patterns

**Guidance**: Wrap Scibox API calls in try/except with specific error messages (FR-010)

**Error Categories**:
- **API Unavailable**: `requests.ConnectionError` → "Classification service unavailable. Please retry."
- **API Timeout**: `requests.Timeout` → "Classification timed out. Please retry with shorter inquiry."
- **Invalid Response**: `json.JSONDecodeError` → "Classification service returned invalid data. Please contact support."
- **Rate Limit**: HTTP 429 → "Too many requests. Please wait and retry."

**Example**:
```python
def classify_with_error_handling(inquiry: str) -> ClassificationResult:
    try:
        return classify(inquiry)
    except requests.ConnectionError:
        raise ClassificationError("Classification service unavailable. Please retry.")
    except requests.Timeout:
        raise ClassificationError("Classification timed out. Please retry.")
    except json.JSONDecodeError:
        raise ClassificationError("Invalid response from classification service.")
```

### Deterministic Results (QR-002)

**Guidance**: Set `temperature=0` in Scibox API calls for deterministic output

**Configuration**:
```python
response = client.chat.completions.create(
    model="Qwen2.5-72B-Instruct-AWQ",
    messages=[...],
    temperature=0.0,  # Deterministic mode
    max_tokens=150,   # Sufficient for JSON response
)
```

## Performance Benchmarks

### Expected Latencies (based on test_scibox_api.py results)

| Operation | Expected Time | Budget |
|-----------|--------------|--------|
| Scibox API call | 800-1500ms | 1800ms (with timeout) |
| FAQ parsing (cached) | 0ms | N/A |
| Input validation | 1-5ms | 50ms |
| JSON parsing | 1-5ms | 50ms |
| Logging | 1-10ms | 100ms |
| **Total** | **~1000-1700ms** | **<2000ms** |

### Optimization Targets

- **P50 latency**: <1200ms (40% margin from 2s limit)
- **P95 latency**: <1800ms (10% margin from 2s limit)
- **P99 latency**: <2000ms (hard limit, may timeout occasionally)

## Dependencies

### Production Dependencies

```
openai>=1.0.0           # Scibox API client
python-dotenv>=1.0.0    # Environment variable management
pydantic>=2.0.0         # Data validation
openpyxl>=3.1.0         # Excel FAQ parsing
```

### Development/Testing Dependencies

```
pytest>=7.4.0                    # Test framework
pytest-asyncio>=0.21.0           # Async test support
testcontainers>=3.7.0            # Integration test containers
pytest-cov>=4.1.0                # Code coverage reporting
```

## FAQ Database Structure Assumptions

Based on Constitution Principle VI and spec assumptions:

**Expected Excel Structure**:
```
Column A: Category (e.g., "Счета и вклады")
Column B: Subcategory (e.g., "Открытие счета")
Column C: FAQ Question
Column D: FAQ Answer
```

**Validation**:
- First row is header (skip in parsing)
- Categories and subcategories are in Russian Cyrillic
- No empty category/subcategory cells
- Total unique categories: ~5-15 (estimated)
- Total unique subcategories per category: ~5-10 (estimated)

**Fallback**: If structure differs, parser will be adjusted during implementation based on actual FAQ file inspection.

## Validation Dataset Format

**Expected JSON Structure** (`data/validation/validation_dataset.json`):
```json
[
  {
    "inquiry": "Как открыть счет?",
    "expected_category": "Счета и вклады",
    "expected_subcategory": "Открытие счета"
  },
  {
    "inquiry": "Какая процентная ставка по ипотеке?",
    "expected_category": "Кредиты",
    "expected_subcategory": "Ипотека"
  }
]
```

**Accuracy Calculation**:
```python
correct = sum(1 for result in results
              if result.category == expected_category
              and result.subcategory == expected_subcategory)
accuracy = (correct / total) * 100
```

## Risks and Mitigations

### Risk 1: Scibox API Rate Limiting

**Impact**: Could block validation testing or demo
**Probability**: Medium (unknown rate limits)
**Mitigation**:
- Implement exponential backoff retry logic
- Cache FAQ categories to minimize API calls
- Test rate limits early in development

### Risk 2: Classification Accuracy Below 70%

**Impact**: Fails quality gate (QR-001), loses 30 hackathon points
**Probability**: Medium (depends on prompt quality)
**Mitigation**:
- Iterate on prompt engineering with validation dataset
- Add more few-shot examples if accuracy low
- Ensure FAQ categories are correctly extracted

### Risk 3: Response Time Exceeds 2 Seconds

**Impact**: Fails performance requirement (PR-001)
**Probability**: Low (current Scibox latency ~1s)
**Mitigation**:
- Set aggressive 1.8s timeout
- Optimize prompt length (fewer tokens = faster)
- Monitor P95/P99 latencies during testing

### Risk 4: FAQ Database Structure Unknown

**Impact**: Parser fails, blocks classification
**Probability**: Low (FAQ file exists in repo)
**Mitigation**:
- Inspect FAQ file early in Phase 1
- Build flexible parser with column detection
- Document actual structure in data-model.md

## Next Steps (Phase 1)

1. Inspect actual FAQ file structure and document in data-model.md
2. Define precise data models (Pydantic classes) for Classification Request/Result
3. Generate OpenAPI contract for classification endpoint
4. Create quickstart.md with setup and usage examples
5. Re-validate Constitution compliance post-design
