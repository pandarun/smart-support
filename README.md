# Smart Support - Classification Module

AI-powered customer inquiry classification system for VTB Belarus banking support.

## Overview

The Classification Module automatically analyzes Russian banking customer inquiries and assigns them to appropriate product categories and subcategories. Built for the Minsk Hackathon, it achieves ≥70% accuracy with <2 second response time using Scibox Qwen2.5-72B-Instruct-AWQ LLM.

### Key Features

- **Single Inquiry Classification**: Classify customer inquiries instantly with category, subcategory, and confidence scores
- **Batch Processing**: Process multiple inquiries in parallel with efficient async operations
- **Validation Testing**: Measure classification accuracy against ground truth datasets
- **Quality Gates**: Automatic ≥70% accuracy requirement enforcement
- **Performance**: <2 second response time (95th percentile)
- **CLI Interface**: Easy-to-use command-line interface for all operations

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Scibox API key ([Get one here](https://llm.t1v.scibox.tech/))
- FAQ database file: `docs/smart_support_vtb_belarus_faq_final.xlsx`

### Installation

```bash
# Clone repository
git clone <repository-url>
cd smart-support

# Install dependencies
pip install -r requirements.txt

# For development (testing)
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env and set SCIBOX_API_KEY=your_key_here
```

### Usage

#### Single Inquiry Classification

```bash
python -m src.cli.classify "Как открыть счет в ВТБ?"
```

Output:
```
======================================================================
CLASSIFICATION RESULT
======================================================================
Inquiry: Как открыть счет в ВТБ?...
Category: Новые клиенты
Subcategory: Регистрация и онбординг
Confidence: 0.92
Processing Time: 1247ms
Timestamp: 2025-10-14T10:30:45Z
======================================================================
```

#### Batch Classification

```bash
# Create file with inquiries (one per line)
cat > inquiries.txt << 'END'
Как открыть счет?
Какая процентная ставка по вкладу?
Забыл пароль от мобильного приложения
END

# Process batch
python -m src.cli.classify --batch inquiries.txt
```

#### Validation Testing

```bash
# Run validation against test dataset
python -m src.cli.classify --validate data/validation/validation_dataset.json
```

Output:
```
======================================================================
VALIDATION REPORT
======================================================================
Total Inquiries: 10
Correct Classifications: 8
Accuracy: 80.0%

Per-Category Accuracy:
  ✓ Новые клиенты: 100.0% (2/2)
  ✓ Продукты - Вклады: 75.0% (3/4)
  ✓ Техническая поддержка: 100.0% (1/1)

Processing Time Statistics:
  Min: 892ms
  Max: 1654ms
  Mean: 1203ms
  P95: 1587ms
======================================================================

✅ PASSED: Accuracy 80.0% meets ≥70% requirement
```

## FAQ Categories

The system recognizes 6 main categories with 35 subcategories:

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
   - Потребительские кредиты
   - Онлайн/Экспресс кредиты

5. **Техническая поддержка** (1 subcategory)
   - Проблемы и решения

6. **Частные клиенты** (4 subcategories)
   - Банковские карточки, Вклады, Кредиты, Онлайн-сервисы

## Testing

### Run Unit Tests

```bash
# Fast mocked tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ -v --cov=src --cov-report=term-missing
```

### Run Integration Tests

```bash
# Requires SCIBOX_API_KEY in environment
export SCIBOX_API_KEY=your_key_here
pytest tests/integration/ -v -m integration
```

### Run All Tests

```bash
pytest tests/ -v --cov=src --cov-report=html
```

## Project Structure

```
smart-support/
├── src/
│   ├── classification/
│   │   ├── classifier.py       # Core classification logic
│   │   ├── prompt_builder.py   # LLM prompt construction
│   │   ├── faq_parser.py       # FAQ Excel parsing
│   │   ├── client.py           # Scibox API client
│   │   ├── models.py           # Pydantic data models
│   │   └── validator.py        # Validation & accuracy
│   ├── utils/
│   │   ├── logging.py          # Structured logging
│   │   └── validation.py       # Input validation
│   └── cli/
│       └── classify.py         # CLI interface
├── tests/
│   ├── unit/                   # Unit tests (mocked)
│   ├── integration/            # Integration tests (real API)
│   └── e2e/                    # E2E tests (future)
├── data/
│   ├── validation/             # Validation datasets
│   └── results/                # Validation results
├── docs/
│   └── smart_support_vtb_belarus_faq_final.xlsx
├── specs/001-classification-module-that/
│   ├── spec.md                 # Feature specification
│   ├── plan.md                 # Implementation plan
│   ├── tasks.md                # Task breakdown
│   └── quickstart.md           # Quick start guide
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── .env.example                # Environment template
├── pytest.ini                  # Pytest configuration
└── README.md                   # This file
```

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `SCIBOX_API_KEY` | Yes | Scibox API authentication key | N/A |
| `FAQ_PATH` | No | Path to FAQ Excel file | `docs/smart_support_vtb_belarus_faq_final.xlsx` |
| `LOG_LEVEL` | No | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `API_TIMEOUT` | No | Scibox API timeout in seconds | `1.8` |

### CLI Options

```bash
# General options
--verbose           Enable verbose output
--log-level LEVEL   Set logging level (DEBUG, INFO, WARNING, ERROR)

# Modes (mutually exclusive)
<inquiry>           Classify single inquiry (default mode)
--batch FILE        Batch mode: classify inquiries from file
--validate DATASET  Validation mode: test accuracy against dataset
```

## Architecture

### Components

1. **Classifier**: Core classification orchestration with input validation, API calls, and result formatting
2. **Prompt Builder**: Constructs LLM prompts with few-shot examples and category constraints
3. **FAQ Parser**: Extracts category hierarchy from Excel file with in-memory caching
4. **Scibox Client**: OpenAI-compatible API wrapper with timeout and error handling
5. **Validator**: Accuracy testing with per-category breakdown and performance metrics
6. **CLI**: User-friendly command-line interface for all operations

### Data Flow

```
User Input → Validation → Prompt Builder → Scibox API → JSON Parser → Result Validation → Output
                                                ↓
                                        FAQ Categories (cached)
```

### Performance Optimizations

- FAQ categories loaded once on module import (cached in memory)
- Async/await for parallel batch processing
- Connection pooling for API requests
- Aggressive timeout (1.8s) to meet <2s requirement

## Hackathon Evaluation

### Scoring Criteria

- **Classification Quality (30 points)**: 10 points per correctly classified validation inquiry
- **Recommendation Relevance (30 points)**: Future ranking module integration
- **UI/UX (20 points)**: CLI interface quality and response speed
- **Presentation (20 points)**: Demo quality and business logic depth

### Checkpoints

- **Checkpoint 1**: ✅ Scibox integration, classification, FAQ import, validation
- **Checkpoint 2**: Ranking module integration, UI development
- **Checkpoint 3**: Full operator interface, quality evaluation

## Troubleshooting

### "Classification service unavailable"

**Cause**: Scibox API connection failed

**Solution**:
1. Check internet connectivity
2. Verify `SCIBOX_API_KEY` is correct in `.env`
3. Test API: `python test_scibox_api.py`
4. Check Scibox status: https://llm.t1v.scibox.tech/

### "Inquiry must contain at least one Cyrillic character"

**Cause**: Input validation failed - no Russian text detected

**Solution**: Ensure inquiry contains Russian (Cyrillic) characters
- Valid: "Как открыть счет?"
- Invalid: "How to open account?"

### Classification timeout (>2 seconds)

**Cause**: Scibox API slow response or network latency

**Solution**:
1. Check network: `ping llm.t1v.scibox.tech`
2. Reduce inquiry length if very long (>1000 words)
3. Retry request (transient network issues)

### Low accuracy on validation dataset (<70%)

**Cause**: Prompt engineering issues or FAQ mismatch

**Solution**:
1. Review misclassified inquiries: `python -m src.cli.classify --validate --verbose`
2. Check FAQ categories match validation expectations
3. Adjust few-shot examples in `prompt_builder.py`

## Development

### Running in Development Mode

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run with verbose logging
python -m src.cli.classify --verbose --log-level DEBUG "Test inquiry"

# Watch tests
pytest-watch tests/unit/
```

### Adding New Categories

1. Update FAQ Excel file: `docs/smart_support_vtb_belarus_faq_final.xlsx`
2. Restart application (FAQ parser reloads on init)
3. Update validation dataset: `data/validation/validation_dataset.json`
4. Run validation to verify: `python -m src.cli.classify --validate data/validation/validation_dataset.json`

## License

Proprietary - Minsk Hackathon 2025

## Support

- **Specification**: [specs/001-classification-module-that/spec.md](specs/001-classification-module-that/spec.md)
- **Technical Plan**: [specs/001-classification-module-that/plan.md](specs/001-classification-module-that/plan.md)
- **Quick Start**: [specs/001-classification-module-that/quickstart.md](specs/001-classification-module-that/quickstart.md)
- **Constitution**: [.specify/memory/constitution.md](.specify/memory/constitution.md)

## Contributors

Smart Support Team - Minsk Hackathon 2025
