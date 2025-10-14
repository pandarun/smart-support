# Research: Template Retrieval Module

**Feature**: Template Retrieval Module
**Date**: 2025-10-14
**Purpose**: Resolve technical decisions and validate approach before implementation

## Overview

This research phase validates the hybrid embeddings-based retrieval architecture, evaluates vector similarity approaches, and confirms integration patterns with the Classification Module. All decisions prioritize meeting hackathon requirements: <1s retrieval latency, ≥80% top-3 accuracy, and seamless integration for Checkpoint 2 demo.

## Research Topics

### 1. Embedding Storage Strategy

**Decision**: In-memory dictionary with optional SQLite persistence

**Rationale**:
- **Performance**: In-memory storage enables <1s retrieval (numpy cosine similarity on ~100-200 768-dim vectors takes ~5-10ms)
- **Memory footprint**: ~100MB for 200 templates × 768 dimensions × 8 bytes/float64 = manageable for deployment container
- **Startup time**: Precomputing 200 embeddings via Scibox API takes ~30-45s (within 60s requirement)
- **Persistence**: Optional SQLite backup enables faster restarts during development/testing (skip re-calling Scibox API)

**Alternatives considered**:
- **Vector database (Pinecone, Weaviate, Milvus)**: Rejected due to deployment complexity (violates Constitution Principle V: Deployment Simplicity) and overkill for 100-200 vectors
- **Redis with RediSearch**: Rejected due to additional service dependency and hackathon time constraints
- **File-based pickle storage**: Considered but SQLite provides better queryability for debugging and template metadata storage

**Implementation approach**:
```python
# In-memory cache structure
class EmbeddingCache:
    def __init__(self):
        self.embeddings: Dict[str, np.ndarray] = {}  # template_id -> embedding vector
        self.metadata: Dict[str, TemplateMetadata] = {}  # template_id -> metadata

    def add(self, template_id: str, embedding: np.ndarray, metadata: TemplateMetadata):
        self.embeddings[template_id] = embedding
        self.metadata[template_id] = metadata

    def get_by_category(self, category: str, subcategory: str) -> List[Tuple[str, np.ndarray]]:
        return [(tid, emb) for tid, emb in self.embeddings.items()
                if self.metadata[tid].category == category
                and self.metadata[tid].subcategory == subcategory]
```

---

### 2. Cosine Similarity Computation

**Decision**: Numpy vectorized operations with manual cosine similarity implementation

**Rationale**:
- **Performance**: Numpy dot product + norm calculation is highly optimized (leverages BLAS)
- **Simplicity**: No additional dependencies beyond numpy (already standard for Python ML)
- **Control**: Manual implementation allows optimization (e.g., pre-normalizing embeddings to avoid repeated norm calculations)
- **Latency**: Cosine similarity for 1 query vs 50 templates (filtered by category) takes <5ms on typical hardware

**Alternatives considered**:
- **scipy.spatial.distance.cosine**: Rejected because it computes distance (1 - similarity) and requires per-pair calculation (slower for batch)
- **sklearn.metrics.pairwise.cosine_similarity**: Considered but adds heavyweight dependency for simple operation
- **faiss library**: Rejected due to compilation complexity and overkill for small dataset

**Implementation approach**:
```python
def cosine_similarity(query_embedding: np.ndarray, template_embeddings: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between query and multiple templates.

    Args:
        query_embedding: Shape (768,) - single query vector
        template_embeddings: Shape (N, 768) - N template vectors

    Returns:
        similarities: Shape (N,) - similarity scores for each template
    """
    # Pre-normalize embeddings for efficiency
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    template_norms = template_embeddings / np.linalg.norm(template_embeddings, axis=1, keepdims=True)

    # Vectorized dot product = cosine similarity (when normalized)
    similarities = np.dot(template_norms, query_norm)
    return similarities
```

---

### 3. Embeddings API Integration Pattern

**Decision**: OpenAI-compatible client with batch embedding support and retry logic

**Rationale**:
- **Consistency**: Reuses existing Scibox API client pattern from Classification Module
- **Efficiency**: Batch embedding requests reduce API call overhead during precomputation (20-50 templates per batch)
- **Reliability**: Exponential backoff retry handles transient API failures during startup
- **Rate limiting**: Built-in client retry honors Scibox rate limits

**Alternatives considered**:
- **Sequential embedding requests**: Rejected due to startup time (200 sequential requests × 200ms = 40s baseline, plus overhead)
- **Custom HTTP client with requests library**: Rejected to maintain consistency with Classification Module's openai client

**Implementation approach**:
```python
from openai import OpenAI
import backoff

class EmbeddingsClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://llm.t1v.scibox.tech/v1"
        )

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def embed_batch(self, texts: List[str], model: str = "bge-m3") -> List[np.ndarray]:
        """Embed multiple texts in a single API call."""
        response = self.client.embeddings.create(
            model=model,
            input=texts
        )
        return [np.array(emb.embedding) for emb in response.data]
```

---

### 4. Template Ranking Algorithm

**Decision**: Pure cosine similarity for MVP, with optional weighted scoring for future enhancement

**Rationale**:
- **MVP simplicity**: Cosine similarity alone achieves high accuracy on semantic search benchmarks (bge-m3 model SOTA performance)
- **Testability**: Pure similarity scoring is deterministic and easy to validate
- **Future enhancement**: Historical success rate weighting (FR-018 SHOULD) can be added later without architecture changes

**Alternatives considered**:
- **BM25 + embeddings hybrid**: Rejected due to complexity and time constraints (requires tokenization, TF-IDF calculation)
- **LLM reranking**: Rejected due to latency impact (would require additional Scibox API call, exceeding 1s budget)
- **Learning-to-rank model**: Rejected due to training data requirements and deployment complexity

**Implementation approach**:
```python
def rank_templates(
    query_embedding: np.ndarray,
    templates: List[Template],
    top_k: int = 5,
    use_historical: bool = False
) -> List[RetrievalResult]:
    """
    Rank templates by similarity (with optional historical weighting).

    Args:
        query_embedding: Query vector
        templates: Filtered templates (by category/subcategory)
        top_k: Number of results to return
        use_historical: Enable weighted scoring (0.7*similarity + 0.3*usage_rate)

    Returns:
        Top-K ranked templates with scores
    """
    template_embeddings = np.array([t.embedding for t in templates])
    similarities = cosine_similarity(query_embedding, template_embeddings)

    if use_historical:
        historical_scores = np.array([t.success_rate for t in templates])
        combined_scores = 0.7 * similarities + 0.3 * historical_scores
    else:
        combined_scores = similarities

    # Sort by score descending
    ranked_indices = np.argsort(combined_scores)[::-1][:top_k]

    return [
        RetrievalResult(
            template=templates[idx],
            similarity_score=similarities[idx],
            combined_score=combined_scores[idx],
            rank=rank + 1
        )
        for rank, idx in enumerate(ranked_indices)
    ]
```

---

### 5. Integration with Classification Module

**Decision**: Accept ClassificationResult Pydantic model as input, filter templates by category/subcategory before retrieval

**Rationale**:
- **Type safety**: Pydantic models provide validation and IDE autocomplete
- **Performance**: Category/subcategory filtering reduces search space from 200 templates to ~10-30 (typical subcategory size)
- **Modularity**: Retrieval Module remains testable independently (can mock ClassificationResult for testing)

**Alternatives considered**:
- **Direct function call chaining**: Rejected to maintain module independence (violates Constitution Principle I)
- **Message queue integration**: Rejected as overkill for synchronous workflow

**Implementation approach**:
```python
from src.classification.models import ClassificationResult

def retrieve_templates(
    query: str,
    classification: ClassificationResult,
    top_k: int = 5
) -> List[RetrievalResult]:
    """
    Retrieve relevant templates given query and classification.

    Args:
        query: Customer inquiry text
        classification: Output from Classification Module
        top_k: Number of templates to return

    Returns:
        Ranked templates with similarity scores
    """
    # 1. Filter templates by category/subcategory
    filtered_templates = cache.get_by_category(
        classification.category,
        classification.subcategory
    )

    # 2. Embed query
    query_embedding = embeddings_client.embed(query)

    # 3. Rank and return top-K
    return rank_templates(query_embedding, filtered_templates, top_k)
```

---

### 6. Validation Dataset Structure

**Decision**: JSON format matching Classification Module pattern, with query + ground truth template ID

**Rationale**:
- **Consistency**: Mirrors Classification Module validation dataset structure
- **Simplicity**: JSON is human-readable for manual dataset creation and review
- **Testability**: Easy to load and iterate in pytest validation tests

**Alternatives considered**:
- **CSV format**: Rejected due to difficulty handling multi-line text and nested metadata
- **Database storage**: Rejected as overkill for 10-20 validation records

**Dataset structure**:
```json
{
  "validation_queries": [
    {
      "id": "val_001",
      "query": "Как открыть накопительный счет в мобильном приложении?",
      "category": "Счета и вклады",
      "subcategory": "Открытие счета",
      "correct_template_id": "tmpl_savings_mobile_001",
      "notes": "Should match mobile app-specific savings account opening template"
    },
    {
      "id": "val_002",
      "query": "Какой процент по вкладу для пенсионеров?",
      "category": "Счета и вклады",
      "subcategory": "Процентные ставки",
      "correct_template_id": "tmpl_pensioner_deposit_rate_001",
      "notes": "Should prioritize pensioner-specific rate information"
    }
  ]
}
```

---

### 7. Concurrency Handling

**Decision**: Python asyncio for concurrent API calls during precomputation, threading for concurrent retrieval requests

**Rationale**:
- **Precomputation**: Async API calls maximize throughput during startup (parallel embedding requests to Scibox)
- **Retrieval**: Threading (or process workers via gunicorn) handles concurrent operator requests
- **Simplicity**: No need for complex distributed systems for 10 concurrent users requirement

**Alternatives considered**:
- **Multiprocessing**: Rejected due to pickling overhead for numpy arrays and unnecessary complexity
- **Celery task queue**: Rejected as overkill for synchronous retrieval workflow

**Implementation approach**:
```python
import asyncio

async def precompute_embeddings_async(templates: List[Template], batch_size: int = 20):
    """Precompute embeddings with batched async API calls."""
    tasks = []
    for i in range(0, len(templates), batch_size):
        batch = templates[i:i+batch_size]
        task = embed_batch_async(batch)
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    for batch, embeddings in zip(batched_templates, results):
        for template, embedding in zip(batch, embeddings):
            cache.add(template.id, embedding, template.metadata)
```

---

## Technology Stack Summary

| Component | Technology | Justification |
|-----------|------------|---------------|
| Embeddings API | Scibox bge-m3 via OpenAI client | Constitution mandated, OpenAI compatibility |
| Vector operations | numpy | Standard, performant, lightweight |
| Embedding storage | In-memory dict + optional SQLite | Fast retrieval, simple deployment |
| Similarity metric | Cosine similarity (manual) | Industry standard, efficient, deterministic |
| Concurrency | asyncio (precompute) + threading (retrieval) | Optimal for I/O-bound tasks |
| Data models | Pydantic | Type safety, validation, IDE support |
| Validation format | JSON | Human-readable, easy to create/review |

---

## Risk Mitigation

### Risk 1: Scibox API rate limits during precomputation
- **Mitigation**: Batch embedding requests (20-50 per batch), exponential backoff retry
- **Fallback**: Load precomputed embeddings from SQLite cache if available

### Risk 2: Embedding storage memory constraints
- **Mitigation**: Monitor memory usage, optimize by storing float32 instead of float64 (50% reduction)
- **Fallback**: Implement LRU cache for less-used categories if memory exceeds limits

### Risk 3: Retrieval latency exceeds 1 second under load
- **Mitigation**: Pre-normalize embeddings, use numpy vectorization, profile hot paths
- **Fallback**: Reduce top-k from 5 to 3 if latency critical

---

## Next Steps (Phase 1)

Based on research decisions:

1. **data-model.md**: Define Pydantic models for Template, RetrievalResult, EmbeddingCache, ValidationRecord
2. **contracts/retrieval-api.yaml**: OpenAPI spec for retrieval endpoint (input: query + classification, output: ranked templates)
3. **quickstart.md**: Developer guide for embedding precomputation, retrieval usage, and validation testing
4. **Update agent context**: Add numpy, asyncio patterns to Claude Code context

All research findings validated against spec requirements - ready for Phase 1 design.
