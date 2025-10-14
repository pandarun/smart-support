# Data Model: Template Retrieval Module

**Feature**: Template Retrieval Module
**Date**: 2025-10-14
**Purpose**: Define data structures and relationships for embeddings-based template retrieval

## Overview

This data model describes the entities, value objects, and data flows for the Template Retrieval Module. All models use Pydantic for validation and type safety, ensuring compatibility with the Classification Module's data structures.

## Core Entities

### 1. Template

**Purpose**: Represents a single FAQ template with precomputed embedding

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `str` | Required, unique | Template identifier (e.g., "tmpl_savings_001") |
| `category` | `str` | Required, matches FAQ structure | Top-level category (e.g., "Счета и вклады") |
| `subcategory` | `str` | Required, matches FAQ structure | Second-level classification (e.g., "Открытие счета") |
| `question` | `str` | Required, min 10 chars | Template question text in Russian |
| `answer` | `str` | Required, min 20 chars | Template answer text in Russian |
| `embedding` | `np.ndarray` | Optional, shape (768,) | Precomputed bge-m3 embedding vector |
| `embedding_text` | `str` | Computed | Combined text used for embedding: `f"{question} {answer}"` |
| `success_rate` | `float` | Optional, 0.0-1.0, default 0.5 | Historical operator selection rate (future enhancement) |
| `usage_count` | `int` | Optional, >= 0, default 0 | Number of times template selected by operators |
| `created_at` | `datetime` | Auto-set | Template creation timestamp |
| `updated_at` | `datetime` | Auto-update | Last template modification timestamp |

**Relationships**:
- Belongs to one Category and one Subcategory (from FAQ database)
- Has one precomputed embedding vector (generated on startup)
- Can appear in multiple RetrievalResults (one-to-many)

**Validation Rules**:
- `question` and `answer` must contain at least one Cyrillic character (Russian language validation)
- `category` and `subcategory` must exist in FAQ database structure
- `embedding` shape must be (768,) if present (bge-m3 dimension)
- `success_rate` must be in range [0.0, 1.0]

**State Transitions**:
```
Created (no embedding) → Embedding Pending → Embedded (ready for retrieval)
                                ↓
                        Embedding Failed (logged, excluded from retrieval)
```

---

### 2. RetrievalResult

**Purpose**: Represents a single retrieved template with relevance scores

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `template_id` | `str` | Required | Reference to Template.id |
| `template_question` | `str` | Required | Template question text (denormalized for UI) |
| `template_answer` | `str` | Required | Template answer text (denormalized for UI) |
| `category` | `str` | Required | Template category (denormalized) |
| `subcategory` | `str` | Required | Template subcategory (denormalized) |
| `similarity_score` | `float` | Required, 0.0-1.0 | Cosine similarity between query and template embeddings |
| `combined_score` | `float` | Required, 0.0-1.0 | Final ranking score (similarity or weighted with historical) |
| `rank` | `int` | Required, >= 1 | Position in ranked results (1 = best match) |
| `confidence_level` | `str` | Computed | "high" (>0.7), "medium" (0.5-0.7), "low" (<0.5) |

**Relationships**:
- References one Template (many-to-one)
- Part of one RetrievalResponse (many-to-one)

**Validation Rules**:
- `similarity_score` and `combined_score` must be in range [0.0, 1.0]
- `rank` must be positive integer
- `confidence_level` is auto-computed from `combined_score`

**Computed Fields**:
```python
@property
def confidence_level(self) -> str:
    if self.combined_score >= 0.7:
        return "high"
    elif self.combined_score >= 0.5:
        return "medium"
    else:
        return "low"
```

---

### 3. RetrievalRequest

**Purpose**: Input model for template retrieval endpoint/function

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `query` | `str` | Required, min 5 chars | Customer inquiry text in Russian |
| `category` | `str` | Required | Classified category from Classification Module |
| `subcategory` | `str` | Required | Classified subcategory from Classification Module |
| `classification_confidence` | `float` | Optional, 0.0-1.0 | Classification confidence score (informational) |
| `top_k` | `int` | Optional, 1-10, default 5 | Number of templates to return |
| `use_historical_weighting` | `bool` | Optional, default False | Enable weighted scoring with historical success rates |

**Validation Rules**:
- `query` must contain at least one Cyrillic character
- `query` length between 5 and 5000 characters
- `category` and `subcategory` must exist in FAQ database
- `top_k` clamped to range [1, 10]

**Alternative Constructor** (from ClassificationResult):
```python
@classmethod
def from_classification(
    cls,
    query: str,
    classification: ClassificationResult,
    top_k: int = 5
) -> "RetrievalRequest":
    return cls(
        query=query,
        category=classification.category,
        subcategory=classification.subcategory,
        classification_confidence=classification.confidence,
        top_k=top_k
    )
```

---

### 4. RetrievalResponse

**Purpose**: Output model for template retrieval endpoint/function

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `query` | `str` | Required | Original customer inquiry (echoed back) |
| `category` | `str` | Required | Category used for filtering (echoed back) |
| `subcategory` | `str` | Required | Subcategory used for filtering (echoed back) |
| `results` | `List[RetrievalResult]` | Required, max 10 items | Ranked template results |
| `total_candidates` | `int` | Required, >= 0 | Number of templates in category before ranking |
| `processing_time_ms` | `float` | Required, >= 0 | Time to embed query + rank templates (milliseconds) |
| `timestamp` | `datetime` | Auto-set | When retrieval completed |
| `warnings` | `List[str]` | Optional | Warnings (e.g., "Low confidence matches", "No templates in category") |

**Validation Rules**:
- `results` length must be <= `top_k` from request
- `results` must be sorted by `rank` ascending (1, 2, 3, ...)
- `processing_time_ms` should be < 1000ms (logged if exceeded)

**Computed Checks**:
```python
@validator('results')
def validate_ranking(cls, results):
    for i, result in enumerate(results):
        assert result.rank == i + 1, f"Result {i} has incorrect rank {result.rank}"
    return results
```

---

### 5. EmbeddingVector (Value Object)

**Purpose**: Wrapper for numpy embedding arrays with utility methods

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `vector` | `np.ndarray` | Required, shape (768,), dtype float32 | bge-m3 embedding vector |
| `is_normalized` | `bool` | Default False | Whether vector is L2-normalized |

**Methods**:
```python
def normalize(self) -> "EmbeddingVector":
    """Return L2-normalized copy of this vector."""
    norm = np.linalg.norm(self.vector)
    return EmbeddingVector(vector=self.vector / norm, is_normalized=True)

def cosine_similarity(self, other: "EmbeddingVector") -> float:
    """Compute cosine similarity with another embedding."""
    # Normalize both vectors if not already normalized
    v1 = self.normalize() if not self.is_normalized else self
    v2 = other.normalize() if not other.is_normalized else other
    return float(np.dot(v1.vector, v2.vector))
```

---

### 6. ValidationRecord

**Purpose**: Ground truth pairing for retrieval quality validation

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `str` | Required, unique | Validation record identifier (e.g., "val_001") |
| `query` | `str` | Required | Customer inquiry text to test |
| `category` | `str` | Required | Known correct category |
| `subcategory` | `str` | Required | Known correct subcategory |
| `correct_template_id` | `str` | Required | Ground truth template ID that should appear in top-K |
| `notes` | `str` | Optional | Human-readable explanation of what makes this template correct |

**Validation Rules**:
- `query` must be realistic customer inquiry (min 10 chars)
- `correct_template_id` must exist in FAQ database
- `category` and `subcategory` must match correct template's classification

---

### 7. ValidationResult

**Purpose**: Aggregate results from retrieval validation run

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `total_queries` | `int` | Required, > 0 | Number of validation queries tested |
| `top_1_correct` | `int` | Required, >= 0 | Queries where correct template ranked #1 |
| `top_3_correct` | `int` | Required, >= 0 | Queries where correct template in top-3 (quality gate) |
| `top_5_correct` | `int` | Required, >= 0 | Queries where correct template in top-5 |
| `top_3_accuracy` | `float` | Computed | Percentage: `top_3_correct / total_queries * 100` |
| `per_query_results` | `List[ValidationQueryResult]` | Required | Detailed results for each query |
| `avg_similarity_correct` | `float` | Computed | Average similarity score for correct templates |
| `avg_similarity_incorrect` | `float` | Computed | Average similarity score for top-ranked incorrect templates |
| `processing_time_stats` | `ProcessingTimeStats` | Required | Min/max/mean/p95 processing times |
| `timestamp` | `datetime` | Auto-set | When validation run completed |

**Quality Gate Check**:
```python
@property
def passes_quality_gate(self) -> bool:
    """Check if validation meets ≥80% top-3 accuracy requirement."""
    return self.top_3_accuracy >= 80.0
```

---

### 8. ValidationQueryResult (Nested Model)

**Purpose**: Detailed results for a single validation query

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `query_id` | `str` | Required | Reference to ValidationRecord.id |
| `query_text` | `str` | Required | Customer inquiry tested |
| `correct_template_id` | `str` | Required | Ground truth template ID |
| `retrieved_templates` | `List[str]` | Required | Template IDs retrieved (in rank order) |
| `correct_template_rank` | `int` | Optional | Rank of correct template (None if not retrieved) |
| `is_top_1` | `bool` | Computed | True if correct template ranked #1 |
| `is_top_3` | `bool` | Computed | True if correct template in top-3 |
| `is_top_5` | `bool` | Computed | True if correct template in top-5 |
| `similarity_scores` | `Dict[str, float]` | Required | Template ID -> similarity score mapping |

---

### 9. ProcessingTimeStats (Value Object)

**Purpose**: Statistical summary of processing times

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `min_ms` | `float` | Required, >= 0 | Minimum processing time (milliseconds) |
| `max_ms` | `float` | Required, >= 0 | Maximum processing time (milliseconds) |
| `mean_ms` | `float` | Required, >= 0 | Average processing time (milliseconds) |
| `p95_ms` | `float` | Required, >= 0 | 95th percentile processing time (milliseconds) |
| `sample_count` | `int` | Required, > 0 | Number of samples measured |

**Validation Rule**:
- `p95_ms` should be < 1000ms (performance requirement PR-001)

---

## Data Relationships

### Entity Relationship Diagram

```
┌─────────────────┐
│  FAQ Database   │ (Excel file)
│  (existing)     │
└────────┬────────┘
         │ parses
         ▼
┌─────────────────┐           ┌──────────────────┐
│    Template     │◄──────────│ EmbeddingVector  │
│  (with embedding)│  has one  └──────────────────┘
└────────┬────────┘
         │
         │ referenced by
         ▼
┌─────────────────┐           ┌──────────────────┐
│ RetrievalResult │◄──────────│ RetrievalResponse│
│  (single match) │  contains │  (top-K results) │
└─────────────────┘  multiple └──────────────────┘
         ▲
         │ includes
         │
┌─────────────────┐
│ ValidationQuery │
│     Result      │
└─────────────────┘
```

---

## Data Flows

### Flow 1: Embedding Precomputation (Startup)

```
1. Load FAQ templates from Excel (reuse Classification Module parser)
   ↓
2. For each template:
     a. Combine question + answer text
     b. Batch templates (20-50 per batch)
   ↓
3. Call Scibox embeddings API (bge-m3) in batches
   ↓
4. Store embeddings in in-memory cache:
     - Key: template_id
     - Value: (embedding_vector, template_metadata)
   ↓
5. Optional: Persist to SQLite for faster restarts
   ↓
6. Report readiness: {total_templates: X, embedded: Y, failed: Z}
```

**Error Handling**:
- API failures: Retry with exponential backoff (3 attempts)
- Persistent failures: Log template ID, mark as unavailable, continue with remaining templates
- Empty category: Warn but don't block startup

---

### Flow 2: Template Retrieval (Runtime)

```
1. Receive RetrievalRequest:
     - query (customer inquiry)
     - category, subcategory (from Classification Module)
     - top_k (default 5)
   ↓
2. Filter templates by category/subcategory:
     candidates = cache.get_by_category(category, subcategory)
   ↓
3. Embed query via Scibox embeddings API (bge-m3)
   ↓
4. Compute cosine similarity for each candidate:
     similarities = [cosine_sim(query_emb, template_emb) for template in candidates]
   ↓
5. Rank by similarity (or weighted score if historical enabled):
     ranked = sort(candidates, key=similarity, reverse=True)[:top_k]
   ↓
6. Return RetrievalResponse:
     - results: List[RetrievalResult] (top-K)
     - processing_time_ms: elapsed time
     - warnings: ["Low confidence"] if all scores < 0.5
```

**Performance Optimizations**:
- Pre-normalize template embeddings (once during precomputation)
- Use numpy vectorized operations (batch cosine similarity)
- Cache query embeddings (optional, if same query repeated)

---

### Flow 3: Validation Run (Testing)

```
1. Load validation dataset: List[ValidationRecord]
   ↓
2. For each validation query:
     a. Call retrieve_templates(query, category, subcategory, top_k=5)
     b. Check if correct_template_id in retrieved results
     c. Record rank of correct template (if found)
     d. Record similarity scores
     e. Track processing time
   ↓
3. Aggregate statistics:
     - top_1_correct, top_3_correct, top_5_correct counts
     - Calculate top_3_accuracy (quality gate: ≥80%)
     - Compute avg_similarity for correct vs incorrect
     - Calculate processing time stats (min/max/mean/p95)
   ↓
4. Generate ValidationResult report
   ↓
5. Save to data/results/retrieval_validation_results.json
   ↓
6. Display pass/fail status (color-coded if terminal supports)
```

---

## Storage Strategy

### In-Memory Cache (Primary)

**Structure**:
```python
{
    "embeddings": {
        "tmpl_001": np.array([0.12, -0.34, ...], dtype=float32),  # 768 dims
        "tmpl_002": np.array([...]),
        ...
    },
    "metadata": {
        "tmpl_001": {
            "category": "Счета и вклады",
            "subcategory": "Открытие счета",
            "question": "Как открыть счет?",
            "answer": "...",
            "success_rate": 0.85,
            "usage_count": 42
        },
        ...
    }
}
```

**Memory Footprint Estimate**:
- 200 templates × 768 dimensions × 4 bytes (float32) = ~600 KB (embeddings)
- 200 templates × ~1 KB (metadata JSON) = ~200 KB
- **Total: ~1 MB** (negligible, easily scales to 1000+ templates)

### SQLite Cache (Optional Persistence)

**Table: `template_embeddings`**
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `template_id` | TEXT | PRIMARY KEY | Template identifier |
| `embedding_blob` | BLOB | NOT NULL | Serialized numpy array (pickle or msgpack) |
| `embedding_hash` | TEXT | NOT NULL | SHA256 hash of embedding text (for cache invalidation) |
| `created_at` | TIMESTAMP | NOT NULL | When embedding was computed |

**Usage**:
- Load from SQLite on startup (skip Scibox API call if embeddings up-to-date)
- Invalidate cache if FAQ database modified (check embedding_hash)

---

## Pydantic Model Examples

### Template Model
```python
from pydantic import BaseModel, Field, validator
import numpy as np
from datetime import datetime

class Template(BaseModel):
    id: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    subcategory: str = Field(..., min_length=1)
    question: str = Field(..., min_length=10)
    answer: str = Field(..., min_length=20)
    embedding: Optional[np.ndarray] = None
    success_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    usage_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def embedding_text(self) -> str:
        return f"{self.question} {self.answer}"

    @validator('embedding')
    def validate_embedding_shape(cls, v):
        if v is not None:
            assert v.shape == (768,), f"Embedding must be 768-dimensional, got {v.shape}"
        return v

    class Config:
        arbitrary_types_allowed = True  # Allow numpy arrays
```

### RetrievalRequest Model
```python
class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=5000)
    category: str = Field(..., min_length=1)
    subcategory: str = Field(..., min_length=1)
    classification_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: int = Field(default=5, ge=1, le=10)
    use_historical_weighting: bool = False

    @classmethod
    def from_classification(
        cls,
        query: str,
        classification: "ClassificationResult",  # From Classification Module
        top_k: int = 5
    ) -> "RetrievalRequest":
        return cls(
            query=query,
            category=classification.category,
            subcategory=classification.subcategory,
            classification_confidence=classification.confidence,
            top_k=top_k
        )
```

---

## Migration from Classification Module

### Shared Models (Reuse)
- `FAQCategory` (from Classification Module FAQ parser)
- `ClassificationResult` (input to retrieval)

### New Models (This Module)
- `Template` (extends FAQ template with embeddings)
- `RetrievalRequest`, `RetrievalResponse`, `RetrievalResult`
- `ValidationRecord`, `ValidationResult`, `ValidationQueryResult`
- `EmbeddingVector`, `ProcessingTimeStats`

---

## Summary

**Total Models**: 9 core entities + 2 value objects + 2 shared from Classification Module

**Storage**: In-memory primary, SQLite optional (~1 MB for 200 templates)

**Key Design Decisions**:
- Pydantic for all models (type safety, validation)
- Numpy arrays for embeddings (performance, compatibility)
- Denormalized fields in RetrievalResult (avoid lookups in UI layer)
- Optional SQLite persistence (developer convenience, not required for production)

All models validated against spec requirements - ready for contract generation (Phase 1).
