# Quickstart: Classification Module

**Feature**: Classification Module
**Date**: 2025-10-14
**Purpose**: Get started with the Classification Module quickly - setup, usage examples, and testing

## Prerequisites

- Python 3.11 or higher
- Scibox API key (stored in `.env` file)
- FAQ database file: `docs/smart_support_vtb_belarus_faq_final.xlsx`

## Installation

### 1. Install Dependencies

```bash
# Install production dependencies
pip install openai>=1.0.0 python-dotenv>=1.0.0 pydantic>=2.0.0 openpyxl>=3.1.0

# Install development/testing dependencies
pip install pytest>=7.4.0 pytest-asyncio>=0.21.0 testcontainers>=3.7.0 pytest-cov>=4.1.0
```

Or use `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in project root:

```bash
# .env
SCIBOX_API_KEY=your_api_key_here
```

**Important**: The `.env` file is gitignored to prevent credential leaks.

### 3. Verify Setup

Run the Scibox API test to ensure connectivity:

```bash
python test_scibox_api.py
```

Expected output:
```
✅ All tests passed! SciBox API integration is working correctly.
```

## Usage

### Option 1: Python Module

```python
from src.classification.classifier import classify

# Classify a single inquiry
inquiry = "Как открыть счет в ВТБ?"
result = classify(inquiry)

print(f"Category: {result.category}")
print(f"Subcategory: {result.subcategory}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Processing time: {result.processing_time_ms}ms")
```

**Expected Output**:
```
Category: Новые клиенты
Subcategory: Регистрация и онбординг
Confidence: 0.92
Processing time: 1247ms
```

### Option 2: CLI Interface

```bash
# Single inquiry
python -m src.cli.classify "Как открыть счет в ВТБ?"

# Batch inquiries from file
python -m src.cli.classify --batch inquiries.txt

# Validation mode
python -m src.cli.classify --validate data/validation/validation_dataset.json
```

### Option 3: API Endpoint (Future)

```bash
# Start API server (once implemented)
uvicorn src.api.main:app --reload

# Make classification request
curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Как открыть счет в ВТБ?"}'
```

## Basic Examples

### Example 1: Single Classification

```python
from src.classification.classifier import classify

# New customer inquiry
inquiry = "Как открыть счет в ВТБ?"
result = classify(inquiry)

assert result.category == "Новые клиенты"
assert result.subcategory == "Регистрация и онбординг"
assert result.confidence > 0.7
assert result.processing_time_ms < 2000
```

### Example 2: Batch Classification

```python
from src.classification.classifier import classify_batch
import asyncio

inquiries = [
    "Как открыть счет?",
    "Какая процентная ставка по кредиту?",
    "Забыл пароль от мобильного приложения"
]

results = asyncio.run(classify_batch(inquiries))

for result in results:
    print(f"{result.inquiry[:30]}... → {result.category} / {result.subcategory}")
```

**Expected Output**:
```
Как открыть счет?... → Новые клиенты / Регистрация и онбординг
Какая процентная ставка по ... → Продукты - Кредиты / Потребительские - На всё про всё
Забыл пароль от мобильного... → Техническая поддержка / Проблемы и решения
```

### Example 3: Validation Testing

```python
from src.classification.validator import run_validation

# Run validation against ground truth dataset
validation_result = run_validation("data/validation/validation_dataset.json")

print(f"Accuracy: {validation_result.accuracy_percentage:.1f}%")
print(f"Correct: {validation_result.correct_classifications}/{validation_result.total_inquiries}")
print(f"Mean processing time: {validation_result.processing_time_stats.mean_ms}ms")

# Check quality gate (≥70% required)
assert validation_result.accuracy_percentage >= 70.0, "Failed quality gate!"
```

## Testing

### Unit Tests

Run unit tests with mocked LLM responses:

```bash
pytest tests/unit/ -v
```

Expected categories tested:
- Input validation
- FAQ parsing
- Prompt construction
- Confidence calculation

### Integration Tests

Run integration tests with real Scibox API:

```bash
# Requires SCIBOX_API_KEY in environment
pytest tests/integration/ -v
```

These tests verify:
- End-to-end classification with real API
- Response time requirements (<2s)
- Category/subcategory validity
- Error handling (timeouts, API failures)

### Validation Tests

Run validation against test dataset:

```bash
python -m src.cli.classify --validate data/validation/validation_dataset.json
```

**Quality Gate**: Must achieve ≥70% accuracy

## Project Structure

```
src/
├── classification/
│   ├── classifier.py        # Main classification logic
│   ├── prompt_builder.py    # LLM prompt construction
│   ├── faq_parser.py        # FAQ Excel parsing
│   ├── models.py            # Pydantic data models
│   └── client.py            # Scibox API client
├── utils/
│   ├── logging.py           # Structured logging
│   └── validation.py        # Input validation
└── cli/
    └── classify.py          # CLI interface

tests/
├── unit/                    # Unit tests (mocked)
├── integration/             # Integration tests (real API)
└── e2e/                     # E2E tests (deferred to UI phase)

data/
├── validation/
│   └── validation_dataset.json    # Ground truth test cases
└── results/
    └── validation_results.json    # Accuracy metrics

docs/
└── smart_support_vtb_belarus_faq_final.xlsx  # FAQ database

specs/001-classification-module-that/
├── spec.md                  # Feature specification
├── plan.md                  # Implementation plan
├── research.md              # Technical research
├── data-model.md            # Data structures
├── quickstart.md            # This file
└── contracts/
    └── classification-api.yaml   # OpenAPI specification
```

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `SCIBOX_API_KEY` | Yes | Scibox API authentication key | N/A |
| `FAQ_PATH` | No | Path to FAQ Excel file | `docs/smart_support_vtb_belarus_faq_final.xlsx` |
| `LOG_LEVEL` | No | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `API_TIMEOUT` | No | Scibox API timeout in seconds | `1.8` |

### FAQ Categories

The module recognizes 6 main categories:

1. **Новые клиенты** (2 subcategories)
   - Регистрация и онбординг
   - Первые шаги

2. **Продукты - Вклады** (9 subcategories)
   - Валютные (CNY, EUR, RUB, USD)
   - Рублевые (Великий путь, Мои условия, и др.)

3. **Продукты - Карты** (10 subcategories)
   - Дебетовые карты
   - Кредитные карты
   - Карты рассрочки

4. **Продукты - Кредиты** (9 subcategories)
   - Автокредиты
   - Потребительские
   - Онлайн кредиты
   - Экспресс-кредиты

5. **Техническая поддержка** (1 subcategory)
   - Проблемы и решения

6. **Частные клиенты** (4 subcategories)
   - Банковские карточки
   - Вклады и депозиты
   - Кредиты
   - Онлайн-сервисы

## Common Use Cases

### Use Case 1: Classify New Customer Inquiry

```python
from src.classification.classifier import classify

# Operator receives inquiry
inquiry = "Хочу открыть расчетный счет, какие документы нужны?"

# Classify to determine category
result = classify(inquiry)

# Display to operator
print(f"Категория: {result.category}")
print(f"Подкатегория: {result.subcategory}")
print(f"Уверенность: {result.confidence * 100:.0f}%")

# Low confidence warning
if result.confidence < 0.5:
    print("⚠️ Низкая уверенность - требуется ручная проверка")
```

### Use Case 2: Bulk Quality Assurance

```python
from src.classification.classifier import classify_batch
import asyncio

# Load recent inquiries from database/log
inquiries = load_recent_inquiries(limit=100)

# Classify in batch
results = asyncio.run(classify_batch(inquiries))

# Analyze distribution
category_counts = {}
for result in results:
    category_counts[result.category] = category_counts.get(result.category, 0) + 1

print("Category distribution:")
for category, count in sorted(category_counts.items()):
    print(f"  {category}: {count}")
```

### Use Case 3: Validation Before Deployment

```python
from src.classification.validator import run_validation

# Run validation
result = run_validation("data/validation/validation_dataset.json")

# Generate report
print("=" * 70)
print("VALIDATION REPORT")
print("=" * 70)
print(f"Total inquiries: {result.total_inquiries}")
print(f"Correct: {result.correct_classifications}")
print(f"Accuracy: {result.accuracy_percentage:.1f}%")
print()
print("Per-category accuracy:")
for category, stats in result.per_category_accuracy.items():
    print(f"  {category}: {stats.accuracy:.1f}% ({stats.correct}/{stats.total})")
print()
print(f"Performance:")
print(f"  Mean: {result.processing_time_stats.mean_ms}ms")
print(f"  P95: {result.processing_time_stats.p95_ms}ms")

# Quality gate check
if result.accuracy_percentage < 70.0:
    print()
    print("❌ FAILED: Accuracy below 70% threshold")
    exit(1)
else:
    print()
    print("✅ PASSED: Quality gate satisfied")
```

## Troubleshooting

### Issue: "Classification service unavailable"

**Cause**: Scibox API connection failed

**Solution**:
1. Check internet connectivity
2. Verify `SCIBOX_API_KEY` is set correctly in `.env`
3. Test API with `python test_scibox_api.py`
4. Check Scibox API status at https://llm.t1v.scibox.tech/

### Issue: "Inquiry must contain at least one Cyrillic character"

**Cause**: Input validation failed - no Russian text detected

**Solution**:
- Ensure inquiry contains Russian (Cyrillic) characters
- Example valid: "Как открыть счет?"
- Example invalid: "How to open account?"

### Issue: Classification timeout (>2 seconds)

**Cause**: Scibox API slow response or network latency

**Solution**:
1. Check network latency: `ping llm.t1v.scibox.tech`
2. Reduce prompt length if inquiry is very long (>1000 words)
3. Retry the request (transient network issues)

### Issue: Low accuracy on validation dataset (<70%)

**Cause**: Prompt engineering issues or FAQ mismatch

**Solution**:
1. Review misclassified inquiries: `python -m src.cli.classify --validate --verbose`
2. Check if FAQ categories match validation dataset expectations
3. Adjust few-shot examples in prompt_builder.py
4. Increase LLM temperature (currently 0 for determinism) cautiously

## Performance Expectations

### Latency Targets

| Metric | Target | Typical |
|--------|--------|---------|
| P50 (median) | <1200ms | ~1000ms |
| P95 | <1800ms | ~1500ms |
| P99 | <2000ms | ~1700ms |

### Accuracy Targets

| Dataset | Minimum | Target |
|---------|---------|--------|
| Validation | 70% | 80%+ |
| Production | 70% | 85%+ |

## Next Steps

1. **Implement Core Module** → Run `/speckit.tasks` to generate task list
2. **Unit Testing** → Write tests for each component
3. **Integration Testing** → Test with real Scibox API
4. **Validation** → Create validation dataset and achieve ≥70% accuracy
5. **Integration** → Connect to ranking module and operator UI (Checkpoint 2-3)

## Support

- **Spec**: [spec.md](./spec.md)
- **Technical Plan**: [plan.md](./plan.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contract**: [contracts/classification-api.yaml](./contracts/classification-api.yaml)
- **Constitution**: [../../.specify/memory/constitution.md](../../.specify/memory/constitution.md)
