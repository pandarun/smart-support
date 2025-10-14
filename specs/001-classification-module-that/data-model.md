# Data Model: Classification Module

**Feature**: Classification Module
**Date**: 2025-10-14
**Purpose**: Define data structures, entities, and their relationships for classification implementation

## Overview

This document defines the data model for the Classification Module, including input/output structures, FAQ category hierarchy, and validation dataset format.

## Core Entities

### 1. Inquiry

**Description**: Customer question or request text in Russian, the primary input to the classification system.

**Attributes**:
- `text` (string, required): The inquiry text from the customer
  - Minimum length: 5 characters
  - Maximum length: 5000 characters
  - Must contain at least one Cyrillic character
  - Whitespace trimmed automatically

**Validation Rules**:
- Non-empty after trimming whitespace
- Contains at least one Cyrillic character (regex: `[а-яА-ЯёЁ]`)
- Length between 5 and 5000 characters inclusive

**Example**:
```json
{
  "text": "Как открыть счет в ВТБ?"
}
```

### 2. Category

**Description**: Top-level product classification from VTB Belarus FAQ structure.

**Attributes**:
- `name` (string, required): Category name in Russian
- `subcategories` (list[string], required): List of valid subcategories under this category

**Valid Categories** (extracted from `docs/smart_support_vtb_belarus_faq_final.xlsx`):

| Category | Subcategory Count | Description |
|----------|------------------|-------------|
| Новые клиенты | 2 | New customer onboarding |
| Продукты - Вклады | 9 | Deposit products |
| Продукты - Карты | 10 | Card products (debit, credit, installment) |
| Продукты - Кредиты | 9 | Loan products (auto, consumer, express) |
| Техническая поддержка | 1 | Technical support issues |
| Частные клиенты | 4 | Private client services |

**Total**: 6 categories, 35 subcategories

### 3. Subcategory

**Description**: Second-level classification under a category from VTB Belarus FAQ structure.

**Attributes**:
- `name` (string, required): Subcategory name in Russian
- `parent_category` (string, required): Parent category name

**Complete Hierarchy**:

```
Новые клиенты
├── Первые шаги
└── Регистрация и онбординг

Продукты - Вклады
├── Валютные - CNY
├── Валютные - EUR
├── Валютные - RUB
├── Валютные - USD
├── Рублевые - Великий путь
├── Рублевые - Мои условия
├── Рублевые - Мои условия онлайн
├── Рублевые - Подушка безопасности
└── Рублевые - СуперСемь

Продукты - Карты
├── Дебетовые карты - Infinite
├── Дебетовые карты - MORE
├── Дебетовые карты - Signature
├── Дебетовые карты - Комплимент
├── Дебетовые карты - Форсаж
├── Карты рассрочки - КСТАТИ
├── Карты рассрочки - ЧЕРЕПАХА
├── Кредитные карты - PLAT/ON
├── Кредитные карты - Отличник
└── Кредитные карты - Портмоне 2.0

Продукты - Кредиты
├── Автокредиты - Автокредит без залога
├── Онлайн кредиты - Проще в онлайн
├── Потребительские - Всё только начинается
├── Потребительские - Дальше - меньше
├── Потребительские - Легко платить
├── Потребительские - На всё про всё
├── Потребительские - Старт
├── Экспресс-кредиты - В магазинах-партнерах
└── Экспресс-кредиты - На роднае

Техническая поддержка
└── Проблемы и решения

Частные клиенты
├── Банковские карточки
├── Вклады и депозиты
├── Кредиты
└── Онлайн-сервисы
```

### 4. Classification Result

**Description**: Output containing predicted category, subcategory, confidence score, and processing metadata.

**Attributes**:
- `inquiry` (string, required): Original inquiry text (for traceability)
- `category` (string, required): Predicted top-level category
- `subcategory` (string, required): Predicted subcategory
- `confidence` (float, required): Confidence score between 0.0 and 1.0
- `processing_time_ms` (integer, required): Time taken to classify in milliseconds
- `timestamp` (datetime, optional): When classification was performed

**Validation Rules**:
- `category` must be one of the 6 valid categories
- `subcategory` must be valid under the predicted category
- `confidence` must be between 0.0 and 1.0 inclusive
- `processing_time_ms` must be positive integer

**Example**:
```json
{
  "inquiry": "Как открыть счет в ВТБ?",
  "category": "Новые клиенты",
  "subcategory": "Регистрация и онбординг",
  "confidence": 0.92,
  "processing_time_ms": 1247,
  "timestamp": "2025-10-14T10:30:45Z"
}
```

### 5. Validation Record

**Description**: Ground truth pairing of inquiry text with correct category and subcategory for accuracy testing.

**Attributes**:
- `id` (integer, required): Unique identifier for the test case
- `inquiry` (string, required): Test inquiry text
- `expected_category` (string, required): Ground truth category
- `expected_subcategory` (string, required): Ground truth subcategory
- `notes` (string, optional): Additional context about the test case

**Example**:
```json
{
  "id": 1,
  "inquiry": "Как открыть счет в ВТБ?",
  "expected_category": "Новые клиенты",
  "expected_subcategory": "Регистрация и онбординг",
  "notes": "Clear account opening question"
}
```

### 6. Validation Result

**Description**: Aggregated accuracy metrics from validation dataset testing.

**Attributes**:
- `total_inquiries` (integer, required): Total test cases processed
- `correct_classifications` (integer, required): Number of correct predictions (both category and subcategory match)
- `accuracy_percentage` (float, required): Overall accuracy (correct / total) × 100
- `per_category_accuracy` (dict, required): Accuracy breakdown by category
- `processing_time_stats` (dict, required): Latency statistics (min, max, mean, p95)
- `timestamp` (datetime, required): When validation was run

**Example**:
```json
{
  "total_inquiries": 10,
  "correct_classifications": 8,
  "accuracy_percentage": 80.0,
  "per_category_accuracy": {
    "Новые клиенты": {"total": 3, "correct": 3, "accuracy": 100.0},
    "Продукты - Карты": {"total": 4, "correct": 3, "accuracy": 75.0},
    "Техническая поддержка": {"total": 3, "correct": 2, "accuracy": 66.7}
  },
  "processing_time_stats": {
    "min_ms": 892,
    "max_ms": 1654,
    "mean_ms": 1203,
    "p95_ms": 1587
  },
  "timestamp": "2025-10-14T10:35:12Z"
}
```

## Data Structures (Pydantic Models)

### ClassificationRequest

```python
from pydantic import BaseModel, field_validator
import re

class ClassificationRequest(BaseModel):
    """Request payload for classification endpoint"""
    text: str

    @field_validator('text')
    def validate_text(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("Inquiry text must be at least 5 characters")
        if len(v) > 5000:
            raise ValueError("Inquiry text must not exceed 5000 characters")
        if not re.search(r'[а-яА-ЯёЁ]', v):
            raise ValueError("Inquiry must contain at least one Cyrillic character")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"text": "Как открыть счет в ВТБ?"}
            ]
        }
    }
```

### ClassificationResult

```python
from pydantic import BaseModel, Field
from datetime import datetime

class ClassificationResult(BaseModel):
    """Response payload for classification endpoint"""
    inquiry: str
    category: str
    subcategory: str
    confidence: float = Field(ge=0.0, le=1.0)
    processing_time_ms: int = Field(gt=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "inquiry": "Как открыть счет в ВТБ?",
                    "category": "Новые клиенты",
                    "subcategory": "Регистрация и онбординг",
                    "confidence": 0.92,
                    "processing_time_ms": 1247,
                    "timestamp": "2025-10-14T10:30:45Z"
                }
            ]
        }
    }
```

### BatchClassificationRequest

```python
from pydantic import BaseModel, Field

class BatchClassificationRequest(BaseModel):
    """Request payload for batch classification (User Story 3)"""
    inquiries: list[str] = Field(min_length=1, max_length=100)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "inquiries": [
                        "Как открыть счет?",
                        "Какая процентная ставка по кредиту?",
                        "Забыл пароль от мобильного приложения"
                    ]
                }
            ]
        }
    }
```

### BatchClassificationResult

```python
from pydantic import BaseModel

class BatchClassificationResult(BaseModel):
    """Response payload for batch classification"""
    results: list[ClassificationResult]
    total_processing_time_ms: int
```

### ValidationRecord

```python
from pydantic import BaseModel

class ValidationRecord(BaseModel):
    """Single validation test case"""
    id: int
    inquiry: str
    expected_category: str
    expected_subcategory: str
    notes: str | None = None
```

### ValidationResult

```python
from pydantic import BaseModel, Field
from datetime import datetime

class CategoryAccuracy(BaseModel):
    total: int
    correct: int
    accuracy: float

class ProcessingTimeStats(BaseModel):
    min_ms: int
    max_ms: int
    mean_ms: int
    p95_ms: int

class ValidationResult(BaseModel):
    """Aggregated validation metrics"""
    total_inquiries: int
    correct_classifications: int
    accuracy_percentage: float = Field(ge=0.0, le=100.0)
    per_category_accuracy: dict[str, CategoryAccuracy]
    processing_time_stats: ProcessingTimeStats
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

## FAQ Database Schema

**File**: `docs/smart_support_vtb_belarus_faq_final.xlsx`

**Structure**:

| Column | Field Name | Type | Description |
|--------|-----------|------|-------------|
| A | Основная категория | string | Top-level category |
| B | Подкатегория | string | Second-level subcategory |
| C | Пример вопроса | string | Example customer question |
| D | Приоритет | string | Priority level (высокий, средний, низкий) |
| E | Целевая аудитория | string | Target audience |
| F | Шаблонный ответ | string | Template response text |

**Usage**:
- Row 1 is header (skip in parsing)
- Extract columns A and B for category/subcategory mapping
- Total rows: ~50-100 FAQ entries
- Unique categories: 6
- Unique subcategories: 35

**Parsing Example**:
```python
from openpyxl import load_workbook
from collections import defaultdict

def parse_faq_categories(faq_path: str) -> dict[str, list[str]]:
    wb = load_workbook(faq_path, read_only=True)
    sheet = wb.active

    categories = defaultdict(set)
    for row in sheet.iter_rows(min_row=2, values_only=True):
        category = row[0]  # Column A
        subcategory = row[1]  # Column B
        if category and subcategory:
            categories[category].add(subcategory)

    # Convert sets to sorted lists
    return {cat: sorted(subcats) for cat, subcats in categories.items()}
```

## Validation Dataset Schema

**File**: `data/validation/validation_dataset.json`

**Format**: JSON array of validation records

```json
[
  {
    "id": 1,
    "inquiry": "Как открыть счет в ВТБ?",
    "expected_category": "Новые клиенты",
    "expected_subcategory": "Регистрация и онбординг",
    "notes": "Clear new account inquiry"
  },
  {
    "id": 2,
    "inquiry": "Какая процентная ставка по ипотеке?",
    "expected_category": "Продукты - Кредиты",
    "expected_subcategory": "Автокредиты - Автокредит без залога",
    "notes": "Mortgage/loan rate question"
  },
  {
    "id": 3,
    "inquiry": "Забыл пароль от мобильного приложения",
    "expected_category": "Техническая поддержка",
    "expected_subcategory": "Проблемы и решения",
    "notes": "Technical support password reset"
  }
]
```

**Creation**: This file will be provided by hackathon organizers or created manually from FAQ examples.

## Validation Results Schema

**File**: `data/results/validation_results.json`

**Format**: JSON object with aggregated metrics

```json
{
  "total_inquiries": 10,
  "correct_classifications": 8,
  "accuracy_percentage": 80.0,
  "per_category_accuracy": {
    "Новые клиенты": {
      "total": 3,
      "correct": 3,
      "accuracy": 100.0
    },
    "Продукты - Карты": {
      "total": 4,
      "correct": 3,
      "accuracy": 75.0
    },
    "Техническая поддержка": {
      "total": 3,
      "correct": 2,
      "accuracy": 66.7
    }
  },
  "processing_time_stats": {
    "min_ms": 892,
    "max_ms": 1654,
    "mean_ms": 1203,
    "p95_ms": 1587
  },
  "timestamp": "2025-10-14T10:35:12Z"
}
```

## Error Handling Models

### ClassificationError

```python
from pydantic import BaseModel

class ClassificationError(BaseModel):
    """Error response for classification failures"""
    error: str
    error_type: str  # "validation", "api_error", "timeout", "unknown"
    details: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "Classification service unavailable",
                    "error_type": "api_error",
                    "details": "Connection timeout to Scibox API"
                }
            ]
        }
    }
```

## State Transitions

### Classification Workflow State Machine

```
┌─────────────────┐
│  Request        │
│  Received       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Validating     │
│  Input          │
└────┬─────┬──────┘
     │     │
     │     └───────────────┐
     │                     │ (invalid)
     │                     ▼
     │             ┌───────────────┐
     │             │  Return Error │
     │             └───────────────┘
     │
     ▼ (valid)
┌─────────────────┐
│  Calling LLM    │
│  API            │
└────┬─────┬──────┘
     │     │
     │     └───────────────┐
     │                     │ (timeout/error)
     │                     ▼
     │             ┌───────────────┐
     │             │  Return Error │
     │             └───────────────┘
     │
     ▼ (success)
┌─────────────────┐
│  Parsing LLM    │
│  Response       │
└────┬─────┬──────┘
     │     │
     │     └───────────────┐
     │                     │ (invalid JSON)
     │                     ▼
     │             ┌───────────────┐
     │             │  Return Error │
     │             └───────────────┘
     │
     ▼ (valid)
┌─────────────────┐
│  Validating     │
│  Category       │
└────┬─────┬──────┘
     │     │
     │     └───────────────┐
     │                     │ (unknown category)
     │                     ▼
     │             ┌───────────────┐
     │             │  Return Error │
     │             └───────────────┘
     │
     ▼ (valid)
┌─────────────────┐
│  Logging &      │
│  Return Result  │
└─────────────────┘
```

## Data Relationships

```
ValidationRecord
    ├── inquiry: string
    ├── expected_category: string ──┐
    └── expected_subcategory: string│
                                     │
                                     ▼
                              FAQ Database
                                     │
                                     ├── Category (6 total)
                                     │     └── Subcategory (35 total)
                                     │
                                     ▼
                           Classification Result
                                     │
                                     ├── category: string
                                     ├── subcategory: string
                                     ├── confidence: float
                                     └── processing_time_ms: int
                                     │
                                     ▼
                           Validation Result
                                     │
                                     ├── accuracy_percentage: float
                                     └── per_category_accuracy: dict
```

## Summary

**Total Data Models**: 12
- 6 core entities (Inquiry, Category, Subcategory, ClassificationResult, ValidationRecord, ValidationResult)
- 5 API payloads (ClassificationRequest, BatchClassificationRequest, BatchClassificationResult, ClassificationError)
- 3 helper types (CategoryAccuracy, ProcessingTimeStats)

**FAQ Hierarchy**: 6 categories → 35 subcategories
**Validation Format**: JSON array of ground truth test cases
**Result Format**: JSON object with accuracy metrics and latency stats
