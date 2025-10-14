"""
Embeddings API client for Template Retrieval Module.

Provides OpenAI-compatible wrapper for Scibox bge-m3 embeddings API with:
- Single and batch embedding support
- Exponential backoff retry logic
- Error wrapping for API failures
- Async precomputation for FAQ templates
"""

import os
import time
import logging
from typing import List, Optional

import backoff
import numpy as np
from openai import OpenAI, OpenAIError

from src.retrieval.cache import EmbeddingCache, TemplateMetadata

logger = logging.getLogger(__name__)

# BGE-M3 model produces 1024-dimensional embeddings
EMBEDDING_DIM = 1024


class EmbeddingsError(Exception):
    """Base exception for embeddings API errors."""
    pass


class EmbeddingsClient:
    """
    OpenAI-compatible client for Scibox bge-m3 embeddings API.

    Features:
    - Automatic retry with exponential backoff (max 3 attempts)
    - Single and batch embedding support
    - Error wrapping for better diagnostics
    - Returns numpy arrays (float32) for efficient computation

    Example:
        >>> client = EmbeddingsClient()
        >>> embedding = client.embed("Как открыть счет?")
        >>> print(embedding.shape)
        (1024,)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "bge-m3",
        base_url: str = "https://llm.t1v.scibox.tech/v1"
    ):
        """
        Initialize embeddings client.

        Args:
            api_key: Scibox API key (defaults to SCIBOX_API_KEY env var)
            model: Embedding model name (default: bge-m3 for Russian language)
            base_url: Scibox API base URL

        Raises:
            ValueError: If API key not provided and not in environment
        """
        self.api_key = api_key or os.getenv("SCIBOX_API_KEY")
        if not self.api_key:
            raise ValueError(
                "SCIBOX_API_KEY must be provided or set in environment. "
                "Obtain from: https://llm.t1v.scibox.tech/"
            )

        self.model = model
        self.base_url = base_url

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as e:
            raise EmbeddingsError(f"Failed to initialize OpenAI client: {e}") from e

        logger.info(f"Initialized EmbeddingsClient (model={model}, base_url={base_url})")

    @backoff.on_exception(
        backoff.expo,
        (OpenAIError, Exception),
        max_tries=3,
        max_time=30,
        on_backoff=lambda details: logger.warning(
            f"Embedding API retry {details['tries']} "
            f"after {details['wait']:.1f}s: {details['exception']}"
        )
    )
    def embed(self, text: str) -> np.ndarray:
        """
        Embed single text (for runtime query embedding).

        Uses exponential backoff retry (max 3 attempts):
        - 1st retry: ~2s delay
        - 2nd retry: ~4s delay
        - 3rd retry: ~8s delay

        Args:
            text: Input text to embed (customer inquiry, template, etc.)

        Returns:
            Embedding vector as numpy array (shape: (1024,), dtype: float32)

        Raises:
            EmbeddingsError: If API call fails after all retries

        Example:
            >>> client = EmbeddingsClient()
            >>> embedding = client.embed("Как открыть накопительный счет?")
            >>> embedding.shape
            (1024,)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=[text]
            )

            if not response.data or len(response.data) == 0:
                raise EmbeddingsError("API returned empty response")

            embedding = np.array(response.data[0].embedding, dtype=np.float32)

            # Validate embedding shape (bge-m3 produces 1024-dimensional embeddings)
            if embedding.shape != (EMBEDDING_DIM,):
                raise EmbeddingsError(
                    f"Unexpected embedding shape: {embedding.shape}, expected ({EMBEDDING_DIM},)"
                )

            return embedding

        except OpenAIError as e:
            raise EmbeddingsError(f"Scibox API error: {e}") from e
        except Exception as e:
            raise EmbeddingsError(f"Embedding failed: {e}") from e

    @backoff.on_exception(
        backoff.expo,
        (OpenAIError, Exception),
        max_tries=3,
        max_time=30,
        on_backoff=lambda details: logger.warning(
            f"Batch embedding API retry {details['tries']} "
            f"after {details['wait']:.1f}s: {details['exception']}"
        )
    )
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed multiple texts in a single API call (for precomputation batching).

        More efficient than calling embed() repeatedly. Recommended batch size: 20-50 texts.

        Uses exponential backoff retry (max 3 attempts):
        - 1st retry: ~2s delay
        - 2nd retry: ~4s delay
        - 3rd retry: ~8s delay

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors as numpy arrays (each shape: (1024,), dtype: float32)

        Raises:
            EmbeddingsError: If API call fails after all retries
            ValueError: If texts list is empty

        Example:
            >>> client = EmbeddingsClient()
            >>> texts = ["Как открыть счет?", "Какой процент по вкладу?"]
            >>> embeddings = client.embed_batch(texts)
            >>> len(embeddings)
            2
            >>> embeddings[0].shape
            (1024,)
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty strings
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("No valid non-empty texts provided")

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=valid_texts
            )

            if not response.data or len(response.data) == 0:
                raise EmbeddingsError("API returned empty response")

            if len(response.data) != len(valid_texts):
                raise EmbeddingsError(
                    f"API returned {len(response.data)} embeddings, expected {len(valid_texts)}"
                )

            embeddings = []
            for i, emb_data in enumerate(response.data):
                embedding = np.array(emb_data.embedding, dtype=np.float32)

                # Validate embedding shape
                if embedding.shape != (EMBEDDING_DIM,):
                    raise EmbeddingsError(
                        f"Unexpected embedding shape at index {i}: {embedding.shape}, expected ({EMBEDDING_DIM},)"
                    )

                embeddings.append(embedding)

            return embeddings

        except OpenAIError as e:
            raise EmbeddingsError(f"Scibox API error: {e}") from e
        except Exception as e:
            raise EmbeddingsError(f"Batch embedding failed: {e}") from e


async def precompute_embeddings(
    faq_path: str,
    embeddings_client: EmbeddingsClient,
    batch_size: int = 20,
    storage_backend: Optional["StorageBackend"] = None
) -> EmbeddingCache:
    """
    Precompute embeddings for all FAQ templates (async for parallel batching).

    Loads templates from FAQ database, batches them for efficient API calls,
    embeds each batch, and stores normalized embeddings in cache. Optionally
    persists embeddings to storage backend for fast startup on future runs.

    Performance requirement: <60 seconds for 200 templates (PR-002)

    Args:
        faq_path: Path to FAQ Excel database
        embeddings_client: Initialized EmbeddingsClient instance
        batch_size: Number of templates per API batch (recommended: 20-50)
        storage_backend: Optional storage backend to persist embeddings.
                        If provided, embeddings will be stored for fast startup.

    Returns:
        EmbeddingCache with precomputed normalized embeddings

    Raises:
        ImportError: If FAQ parser module not available
        FileNotFoundError: If FAQ database file not found
        EmbeddingsError: If all batches fail to embed

    Example:
        >>> import asyncio
        >>> client = EmbeddingsClient()
        >>> # Without persistence (original behavior)
        >>> cache = asyncio.run(precompute_embeddings(
        ...     "docs/smart_support_vtb_belarus_faq_final.xlsx",
        ...     client,
        ...     batch_size=20
        ... ))
        >>> cache.stats
        {'total_templates': 187, 'categories': 6, 'precompute_time_seconds': 45.3}

        >>> # With persistence (new feature)
        >>> from src.retrieval.storage import create_storage_backend, StorageConfig
        >>> config = StorageConfig.from_env()
        >>> storage = create_storage_backend(config)
        >>> storage.connect()
        >>> storage.initialize_schema()
        >>> cache = asyncio.run(precompute_embeddings(
        ...     "docs/smart_support_vtb_belarus_faq_final.xlsx",
        ...     client,
        ...     batch_size=20,
        ...     storage_backend=storage
        ... ))
    """
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from src.retrieval.storage.base import StorageBackend

    start_time = time.time()
    cache = EmbeddingCache(storage_backend=None)  # Don't load from storage during precompute

    logger.info(f"Starting embedding precomputation (batch_size={batch_size})")

    # Import FAQ parser (from Classification Module)
    try:
        from src.classification.faq_parser import parse_faq
    except ImportError as e:
        raise ImportError(
            "FAQ parser not found. Ensure Classification Module is installed: "
            "src.classification.faq_parser.parse_faq"
        ) from e

    # Load templates from FAQ database
    try:
        templates = parse_faq(faq_path)
        logger.info(f"Loaded {len(templates)} templates from FAQ database")
    except FileNotFoundError:
        raise FileNotFoundError(f"FAQ database not found: {faq_path}")
    except Exception as e:
        raise EmbeddingsError(f"Failed to parse FAQ database: {e}") from e

    if not templates:
        raise EmbeddingsError("FAQ database is empty - no templates to embed")

    # Batch templates for efficient API calls
    batches = [templates[i:i + batch_size] for i in range(0, len(templates), batch_size)]
    logger.info(f"Split into {len(batches)} batches")

    failed_count = 0
    succeeded_count = 0

    for batch_idx, batch in enumerate(batches, start=1):
        try:
            # Combine question + answer for embedding (better semantic representation)
            texts = [f"{t['question']} {t['answer']}" for t in batch]

            # Call embeddings API
            logger.debug(f"Embedding batch {batch_idx}/{len(batches)} ({len(batch)} templates)")
            embeddings = embeddings_client.embed_batch(texts)

            # Add to cache with normalized embeddings
            for template, embedding in zip(batch, embeddings):
                metadata = TemplateMetadata(
                    template_id=template.get('id', f"tmpl_{template['category']}_{succeeded_count}"),
                    category=template['category'],
                    subcategory=template['subcategory'],
                    question=template['question'],
                    answer=template['answer']
                )
                cache.add(metadata.template_id, embedding, metadata)
                succeeded_count += 1

            # Store to persistent storage if backend provided
            if storage_backend is not None and storage_backend.is_connected():
                try:
                    # Get or create version for current model
                    version_id = storage_backend.get_or_create_version(
                        model_name=embeddings_client.model,
                        model_version="v1",  # Default version
                        embedding_dimension=EMBEDDING_DIM
                    )

                    # Import utilities for content hashing
                    from src.utils.hashing import compute_content_hash
                    from src.retrieval.storage.models import EmbeddingRecordCreate

                    # Store batch in storage
                    records_to_store = []
                    for template, embedding in zip(batch, embeddings):
                        template_id = template.get('id', f"tmpl_{template['category']}_{len(records_to_store)}")
                        content_hash = compute_content_hash(template['question'], template['answer'])

                        record = EmbeddingRecordCreate(
                            template_id=template_id,
                            version_id=version_id,
                            embedding_vector=embedding,
                            category=template['category'],
                            subcategory=template['subcategory'],
                            question_text=template['question'],
                            answer_text=template['answer'],
                            content_hash=content_hash,
                            success_rate=0.5,
                            usage_count=0
                        )
                        records_to_store.append(record)

                    storage_backend.store_embeddings_batch(records_to_store)
                    logger.debug(f"Stored batch {batch_idx} to persistent storage")

                except Exception as e:
                    logger.warning(f"Failed to store batch {batch_idx} to storage: {e}")

            logger.info(
                f"✓ Embedded batch {batch_idx}/{len(batches)}: "
                f"{len(batch)} templates ({succeeded_count}/{len(templates)} total)"
            )

        except EmbeddingsError as e:
            logger.error(f"✗ Failed to embed batch {batch_idx}/{len(batches)}: {e}")
            failed_count += len(batch)
            # Continue with remaining batches (partial failure is acceptable)
            continue
        except Exception as e:
            logger.error(f"✗ Unexpected error in batch {batch_idx}/{len(batches)}: {e}")
            failed_count += len(batch)
            continue

    elapsed = time.time() - start_time
    cache.precompute_time = elapsed

    # Log final statistics
    logger.info(f"\n{'='*60}")
    logger.info(f"Precomputation complete:")
    logger.info(f"  - Total: {len(templates)} templates")
    logger.info(f"  - Succeeded: {succeeded_count} templates ({succeeded_count/len(templates)*100:.1f}%)")
    logger.info(f"  - Failed: {failed_count} templates ({failed_count/len(templates)*100:.1f}%)")
    logger.info(f"  - Time: {elapsed:.1f} seconds")
    logger.info(f"  - Performance: {len(templates)/elapsed:.1f} templates/second")
    logger.info(f"{'='*60}\n")

    # Verify we have at least some embeddings
    if succeeded_count == 0:
        raise EmbeddingsError("All embedding batches failed - cache is empty")

    # Warn if performance requirement not met
    if elapsed > 60.0:
        logger.warning(
            f"Precomputation took {elapsed:.1f}s, exceeds 60s requirement (PR-002). "
            f"Consider increasing batch_size or checking network latency."
        )

    return cache
