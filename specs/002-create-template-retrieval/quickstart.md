# Quickstart Guide: Template Retrieval Module

**Feature**: Template Retrieval Module
**Target Audience**: Developers implementing the retrieval system
**Prerequisites**: Classification Module complete, Python 3.11+, Scibox API access

## Overview

This quickstart guide walks you through implementing the Template Retrieval Module from scratch, including:
1. Embedding precomputation on startup
2. Real-time template retrieval with cosine similarity ranking
3. Integration with Classification Module
4. Validation testing against ground truth dataset

**Time Estimate**: 8-12 hours for experienced Python developer

---

## Setup (30 minutes)

### 1. Environment Configuration

Ensure `.env` file includes embeddings API configuration (extends Classification Module config):

```bash
# Existing Classification Module config
SCIBOX_API_KEY=your_api_key_here
FAQ_PATH=docs/smart_support_vtb_belarus_faq_final.xlsx

# New Retrieval Module config
EMBEDDING_MODEL=bge-m3
EMBEDDING_CACHE_PATH=data/cache/embeddings.db  # Optional SQLite persistence
RETRIEVAL_TOP_K=5
RETRIEVAL_TIMEOUT_SECONDS=2.0
```

### 2. Install Dependencies

Add to `requirements.txt`:

```txt
# Existing dependencies
openai>=1.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
openpyxl>=3.1.0

# New dependencies for Retrieval Module
numpy>=1.24.0        # Vector operations
backoff>=2.2.0       # Retry logic for API calls
```

Install:
```bash
pip install -r requirements.txt
```

### 3. Verify FAQ Database

Ensure FAQ database is accessible:
```bash
python -c "from src.classification.faq_parser import parse_faq; templates = parse_faq('docs/smart_support_vtb_belarus_faq_final.xlsx'); print(f'Loaded {len(templates)} templates')"
```

Expected output: `Loaded 187 templates` (or similar count)

---

## Implementation Roadmap

### Phase 1: Embeddings Infrastructure (3-4 hours)

#### 1.1 Create Embeddings Client (`src/retrieval/embeddings.py`)

**Purpose**: Wrapper for Scibox bge-m3 embeddings API with batching and retry

```python
from openai import OpenAI
import backoff
import numpy as np
from typing import List
import os

class EmbeddingsClient:
    def __init__(self, api_key: str = None, model: str = "bge-m3"):
        self.client = OpenAI(
            api_key=api_key or os.getenv("SCIBOX_API_KEY"),
            base_url="https://llm.t1v.scibox.tech/v1"
        )
        self.model = model

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def embed(self, text: str) -> np.ndarray:
        """Embed single text (for runtime query embedding)."""
        response = self.client.embeddings.create(
            model=self.model,
            input=[text]
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple texts (for precomputation batching)."""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [np.array(emb.embedding, dtype=np.float32) for emb in response.data]
```

**Test**:
```python
client = EmbeddingsClient()
embedding = client.embed("Как открыть счет?")
print(f"Embedding shape: {embedding.shape}")  # Should be (768,)
print(f"Embedding dtype: {embedding.dtype}")  # Should be float32
```

#### 1.2 Create Embedding Cache (`src/retrieval/cache.py`)

**Purpose**: In-memory storage for precomputed template embeddings

```python
from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime

class TemplateMetadata:
    def __init__(self, template_id: str, category: str, subcategory: str,
                 question: str, answer: str):
        self.template_id = template_id
        self.category = category
        self.subcategory = subcategory
        self.question = question
        self.answer = answer

class EmbeddingCache:
    def __init__(self):
        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, TemplateMetadata] = {}
        self.precompute_time: Optional[float] = None

    def add(self, template_id: str, embedding: np.ndarray, metadata: TemplateMetadata):
        """Add template embedding to cache."""
        # Normalize embedding for faster cosine similarity
        normalized = embedding / np.linalg.norm(embedding)
        self.embeddings[template_id] = normalized
        self.metadata[template_id] = metadata

    def get_by_category(self, category: str, subcategory: str) -> List[Tuple[str, np.ndarray, TemplateMetadata]]:
        """Get all templates in a specific category/subcategory."""
        return [
            (tid, emb, self.metadata[tid])
            for tid, emb in self.embeddings.items()
            if self.metadata[tid].category == category
            and self.metadata[tid].subcategory == subcategory
        ]

    @property
    def is_ready(self) -> bool:
        """Check if cache has embeddings."""
        return len(self.embeddings) > 0

    @property
    def stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "total_templates": len(self.embeddings),
            "categories": len(set(m.category for m in self.metadata.values())),
            "precompute_time_seconds": self.precompute_time
        }
```

#### 1.3 Implement Precomputation (`src/retrieval/embeddings.py`)

**Purpose**: Load FAQ templates and precompute embeddings on startup

```python
import asyncio
from src.classification.faq_parser import parse_faq
from src.retrieval.cache import EmbeddingCache, TemplateMetadata
import time

async def precompute_embeddings(
    faq_path: str,
    embeddings_client: EmbeddingsClient,
    batch_size: int = 20
) -> EmbeddingCache:
    """
    Precompute embeddings for all FAQ templates.

    Args:
        faq_path: Path to FAQ Excel database
        embeddings_client: Embeddings API client
        batch_size: Number of templates per API batch

    Returns:
        EmbeddingCache with precomputed embeddings
    """
    start_time = time.time()
    cache = EmbeddingCache()

    # Load templates from FAQ
    templates = parse_faq(faq_path)
    print(f"Loaded {len(templates)} templates from FAQ database")

    # Batch templates for efficient API calls
    batches = [templates[i:i+batch_size] for i in range(0, len(templates), batch_size)]

    failed_count = 0
    for batch in batches:
        try:
            # Combine question + answer for embedding
            texts = [f"{t['question']} {t['answer']}" for t in batch]

            # Call embeddings API
            embeddings = embeddings_client.embed_batch(texts)

            # Add to cache
            for template, embedding in zip(batch, embeddings):
                metadata = TemplateMetadata(
                    template_id=template['id'],
                    category=template['category'],
                    subcategory=template['subcategory'],
                    question=template['question'],
                    answer=template['answer']
                )
                cache.add(template['id'], embedding, metadata)

            print(f"Embedded batch: {len(batch)} templates")

        except Exception as e:
            print(f"Failed to embed batch: {e}")
            failed_count += len(batch)

    elapsed = time.time() - start_time
    cache.precompute_time = elapsed

    print(f"\nPrecomputation complete:")
    print(f"  - Total: {len(templates)} templates")
    print(f"  - Succeeded: {len(cache.embeddings)} templates")
    print(f"  - Failed: {failed_count} templates")
    print(f"  - Time: {elapsed:.1f} seconds")

    return cache
```

**Test**:
```python
import asyncio

async def test_precompute():
    client = EmbeddingsClient()
    cache = await precompute_embeddings(
        faq_path="docs/smart_support_vtb_belarus_faq_final.xlsx",
        embeddings_client=client,
        batch_size=20
    )
    print(cache.stats)

asyncio.run(test_precompute())
```

Expected: ~187 templates embedded in <60 seconds

---

### Phase 2: Retrieval Logic (2-3 hours)

#### 2.1 Implement Cosine Similarity Ranking (`src/retrieval/ranker.py`)

**Purpose**: Rank templates by semantic similarity

```python
import numpy as np
from typing import List
from src.retrieval.models import RetrievalResult

def cosine_similarity_batch(query_embedding: np.ndarray, template_embeddings: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between query and multiple templates.

    Args:
        query_embedding: Shape (768,) - normalized query vector
        template_embeddings: Shape (N, 768) - normalized template vectors

    Returns:
        similarities: Shape (N,) - cosine similarity scores
    """
    # Normalize query (if not already normalized)
    query_norm = query_embedding / np.linalg.norm(query_embedding)

    # Dot product = cosine similarity (when normalized)
    similarities = np.dot(template_embeddings, query_norm)
    return similarities

def rank_templates(
    query_embedding: np.ndarray,
    candidates: List[Tuple[str, np.ndarray, TemplateMetadata]],
    top_k: int = 5
) -> List[RetrievalResult]:
    """
    Rank templates by cosine similarity.

    Args:
        query_embedding: Query embedding vector
        candidates: List of (template_id, embedding, metadata) tuples
        top_k: Number of results to return

    Returns:
        Top-K ranked templates
    """
    if not candidates:
        return []

    # Extract embeddings and IDs
    template_ids = [c[0] for c in candidates]
    template_embeddings = np.array([c[1] for c in candidates])
    template_metadata = [c[2] for c in candidates]

    # Compute similarities
    similarities = cosine_similarity_batch(query_embedding, template_embeddings)

    # Sort by similarity descending
    ranked_indices = np.argsort(similarities)[::-1][:top_k]

    # Build results
    results = []
    for rank, idx in enumerate(ranked_indices, start=1):
        metadata = template_metadata[idx]
        similarity = float(similarities[idx])

        results.append(RetrievalResult(
            template_id=template_ids[idx],
            template_question=metadata.question,
            template_answer=metadata.answer,
            category=metadata.category,
            subcategory=metadata.subcategory,
            similarity_score=similarity,
            combined_score=similarity,  # Pure similarity for MVP
            rank=rank
        ))

    return results
```

#### 2.2 Create Main Retrieval Function (`src/retrieval/retriever.py`)

**Purpose**: Orchestrate retrieval pipeline

```python
from src.retrieval.embeddings import EmbeddingsClient
from src.retrieval.cache import EmbeddingCache
from src.retrieval.ranker import rank_templates
from src.retrieval.models import RetrievalRequest, RetrievalResponse
from datetime import datetime
import time

class TemplateRetriever:
    def __init__(self, embeddings_client: EmbeddingsClient, cache: EmbeddingCache):
        self.embeddings_client = embeddings_client
        self.cache = cache

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """
        Retrieve top-K relevant templates.

        Args:
            request: RetrievalRequest with query and classification

        Returns:
            RetrievalResponse with ranked templates
        """
        start_time = time.time()

        # 1. Filter templates by category/subcategory
        candidates = self.cache.get_by_category(
            request.category,
            request.subcategory
        )

        # 2. Embed query
        query_embedding = self.embeddings_client.embed(request.query)

        # 3. Rank templates
        results = rank_templates(
            query_embedding,
            candidates,
            top_k=request.top_k
        )

        # 4. Generate warnings
        warnings = []
        if not candidates:
            warnings.append("No templates found in category")
        elif results and all(r.combined_score < 0.5 for r in results):
            warnings.append("Low confidence matches - all scores < 0.5")

        processing_time_ms = (time.time() - start_time) * 1000

        return RetrievalResponse(
            query=request.query,
            category=request.category,
            subcategory=request.subcategory,
            results=results,
            total_candidates=len(candidates),
            processing_time_ms=processing_time_ms,
            timestamp=datetime.now(),
            warnings=warnings
        )
```

**Test**:
```python
retriever = TemplateRetriever(embeddings_client, cache)

request = RetrievalRequest(
    query="Как открыть накопительный счет в мобильном приложении?",
    category="Счета и вклады",
    subcategory="Открытие счета",
    top_k=5
)

response = retriever.retrieve(request)
print(f"Found {len(response.results)} templates in {response.processing_time_ms:.1f}ms")
for result in response.results:
    print(f"  Rank {result.rank}: {result.template_question[:60]}... (score: {result.similarity_score:.3f})")
```

---

### Phase 3: Integration with Classification Module (1-2 hours)

#### 3.1 Create Integration Helper (`src/retrieval/integration.py`)

**Purpose**: Convenient integration with Classification Module

```python
from src.classification.classifier import classify_inquiry
from src.retrieval.retriever import TemplateRetriever
from src.retrieval.models import RetrievalRequest

def classify_and_retrieve(
    query: str,
    classifier,
    retriever: TemplateRetriever,
    top_k: int = 5
):
    """
    End-to-end pipeline: classify inquiry → retrieve templates.

    Args:
        query: Customer inquiry text
        classifier: Classification Module classifier instance
        retriever: Template Retriever instance
        top_k: Number of templates to return

    Returns:
        Tuple of (classification_result, retrieval_response)
    """
    # Step 1: Classify
    classification = classifier.classify(query)

    # Step 2: Retrieve
    retrieval_request = RetrievalRequest(
        query=query,
        category=classification.category,
        subcategory=classification.subcategory,
        classification_confidence=classification.confidence,
        top_k=top_k
    )
    retrieval = retriever.retrieve(retrieval_request)

    return classification, retrieval
```

**Test**:
```python
from src.classification.classifier import Classifier

# Initialize both modules
classifier = Classifier(api_key=os.getenv("SCIBOX_API_KEY"))
retriever = TemplateRetriever(embeddings_client, cache)

# Run full pipeline
query = "Как открыть накопительный счет в мобильном приложении?"
classification, retrieval = classify_and_retrieve(query, classifier, retriever)

print(f"Classification: {classification.category} > {classification.subcategory} ({classification.confidence:.2f})")
print(f"Retrieved {len(retrieval.results)} templates:")
for result in retrieval.results:
    print(f"  {result.rank}. {result.template_question[:60]}... ({result.similarity_score:.3f})")
```

---

### Phase 4: CLI Interface (1 hour)

#### 4.1 Create Retrieval CLI (`src/cli/retrieve.py`)

**Purpose**: Command-line interface for testing retrieval

```python
import argparse
import asyncio
from src.retrieval.embeddings import EmbeddingsClient, precompute_embeddings
from src.retrieval.retriever import TemplateRetriever
from src.retrieval.models import RetrievalRequest

async def main():
    parser = argparse.ArgumentParser(description="Template Retrieval CLI")
    parser.add_argument("query", help="Customer inquiry text")
    parser.add_argument("--category", required=True, help="Classified category")
    parser.add_argument("--subcategory", required=True, help="Classified subcategory")
    parser.add_argument("--top-k", type=int, default=5, help="Number of templates to return")
    args = parser.parse_args()

    # Initialize
    embeddings_client = EmbeddingsClient()
    cache = await precompute_embeddings("docs/smart_support_vtb_belarus_faq_final.xlsx", embeddings_client)
    retriever = TemplateRetriever(embeddings_client, cache)

    # Retrieve
    request = RetrievalRequest(
        query=args.query,
        category=args.category,
        subcategory=args.subcategory,
        top_k=args.top_k
    )
    response = retriever.retrieve(request)

    # Display
    print(f"\n=== Retrieval Results ===")
    print(f"Query: {args.query}")
    print(f"Category: {args.category} > {args.subcategory}")
    print(f"Processing time: {response.processing_time_ms:.1f}ms")
    print(f"Total candidates: {response.total_candidates}\n")

    for result in response.results:
        print(f"Rank {result.rank} (score: {result.similarity_score:.3f}, confidence: {result.confidence_level})")
        print(f"  Q: {result.template_question}")
        print(f"  A: {result.template_answer[:100]}...\n")

if __name__ == "__main__":
    asyncio.run(main())
```

**Usage**:
```bash
python -m src.cli.retrieve "Как открыть накопительный счет?" --category "Счета и вклады" --subcategory "Открытие счета"
```

---

### Phase 5: Validation Testing (2-3 hours)

#### 5.1 Create Validation Dataset (`data/validation/retrieval_validation_dataset.json`)

```json
{
  "validation_queries": [
    {
      "id": "val_001",
      "query": "Как открыть накопительный счет в мобильном приложении?",
      "category": "Счета и вклады",
      "subcategory": "Открытие счета",
      "correct_template_id": "tmpl_savings_mobile_001",
      "notes": "Should match mobile app-specific template"
    },
    {
      "id": "val_002",
      "query": "Какой процент по вкладу для пенсионеров?",
      "category": "Счета и вклады",
      "subcategory": "Процентные ставки",
      "correct_template_id": "tmpl_pensioner_rate_001",
      "notes": "Should prioritize pensioner-specific information"
    }
    // ... add 8+ more validation queries
  ]
}
```

#### 5.2 Implement Validation Runner (`src/retrieval/validator.py`)

```python
import json
from src.retrieval.models import ValidationRecord, ValidationResult, ValidationQueryResult
from src.retrieval.retriever import TemplateRetriever

def run_validation(
    dataset_path: str,
    retriever: TemplateRetriever,
    top_k: int = 5
) -> ValidationResult:
    """Run retrieval validation against test dataset."""

    # Load validation dataset
    with open(dataset_path) as f:
        dataset = json.load(f)

    queries = [ValidationRecord(**q) for q in dataset['validation_queries']]

    # Run retrieval for each query
    results = []
    processing_times = []

    for query_record in queries:
        request = RetrievalRequest(
            query=query_record.query,
            category=query_record.category,
            subcategory=query_record.subcategory,
            top_k=top_k
        )
        response = retriever.retrieve(request)
        processing_times.append(response.processing_time_ms)

        # Check if correct template in results
        retrieved_ids = [r.template_id for r in response.results]
        correct_rank = None
        if query_record.correct_template_id in retrieved_ids:
            correct_rank = retrieved_ids.index(query_record.correct_template_id) + 1

        results.append(ValidationQueryResult(
            query_id=query_record.id,
            query_text=query_record.query,
            correct_template_id=query_record.correct_template_id,
            retrieved_templates=retrieved_ids,
            correct_template_rank=correct_rank,
            is_top_1=(correct_rank == 1 if correct_rank else False),
            is_top_3=(correct_rank <= 3 if correct_rank else False),
            is_top_5=(correct_rank <= 5 if correct_rank else False),
            similarity_scores={r.template_id: r.similarity_score for r in response.results}
        ))

    # Calculate statistics
    top_1_correct = sum(1 for r in results if r.is_top_1)
    top_3_correct = sum(1 for r in results if r.is_top_3)
    top_5_correct = sum(1 for r in results if r.is_top_5)

    return ValidationResult(
        total_queries=len(queries),
        top_1_correct=top_1_correct,
        top_3_correct=top_3_correct,
        top_5_correct=top_5_correct,
        top_3_accuracy=(top_3_correct / len(queries)) * 100,
        per_query_results=results,
        processing_time_stats=calculate_stats(processing_times),
        timestamp=datetime.now()
    )
```

**Run Validation**:
```bash
python -m src.cli.retrieve --validate data/validation/retrieval_validation_dataset.json
```

---

## Common Patterns

### Pattern 1: Startup Initialization

```python
# In your application startup (main.py or __init__.py)
import asyncio
from src.retrieval.embeddings import EmbeddingsClient, precompute_embeddings
from src.retrieval.retriever import TemplateRetriever

async def initialize_retrieval():
    embeddings_client = EmbeddingsClient()
    cache = await precompute_embeddings(
        faq_path="docs/smart_support_vtb_belarus_faq_final.xlsx",
        embeddings_client=embeddings_client,
        batch_size=20
    )
    retriever = TemplateRetriever(embeddings_client, cache)
    return retriever

# Use in startup
retriever = asyncio.run(initialize_retrieval())
```

### Pattern 2: Error Handling

```python
try:
    response = retriever.retrieve(request)
    if response.warnings:
        print(f"Warnings: {', '.join(response.warnings)}")
    if not response.results:
        print("No templates found - escalate to manual search")
except Exception as e:
    print(f"Retrieval failed: {e}")
    # Fallback: return empty results or retry
```

### Pattern 3: Performance Monitoring

```python
# Log slow retrievals
if response.processing_time_ms > 1000:
    logger.warning(f"Slow retrieval: {response.processing_time_ms:.1f}ms for query '{request.query[:50]}'")
```

---

## Troubleshooting

### Issue: Precomputation takes >60 seconds
**Solution**: Increase batch size (try 30-50) or check network latency to Scibox API

### Issue: Low retrieval accuracy (<80%)
**Solution**:
1. Verify validation dataset has correct template IDs
2. Check that embeddings are normalized
3. Try embedding `question + answer` instead of just `question`

### Issue: High memory usage
**Solution**: Use float32 instead of float64 (50% memory reduction)

### Issue: Retrieval latency >1 second
**Solution**:
1. Pre-normalize embeddings during precomputation
2. Profile cosine similarity calculation
3. Reduce top_k or optimize numpy operations

---

## Next Steps

After completing this quickstart:

1. **Run validation**: Ensure ≥80% top-3 accuracy
2. **Integration test**: Verify full classification → retrieval pipeline
3. **Docker deployment**: Add retrieval service to docker-compose
4. **Generate tasks**: Run `/speckit.tasks` to create implementation task list

---

## Resources

- **Spec**: `specs/002-create-template-retrieval/spec.md`
- **Data Model**: `specs/002-create-template-retrieval/data-model.md`
- **API Contract**: `specs/002-create-template-retrieval/contracts/retrieval-api.yaml`
- **Research**: `specs/002-create-template-retrieval/research.md`

For questions or issues, refer to the spec or research documents.
