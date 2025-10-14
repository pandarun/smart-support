"""
Integration test fixtures for Template Retrieval Module.

Provides reusable fixtures for integration testing:
- EmbeddingCache with sample templates
- Scibox embeddings API client (can be mocked for offline testing)
- Mock template data covering main categories
- FAQ parser mocking
"""

import os
import pytest
import numpy as np
from unittest.mock import Mock, patch
from typing import List, Dict

from src.retrieval.embeddings import EmbeddingsClient, precompute_embeddings
from src.retrieval.cache import EmbeddingCache, TemplateMetadata
from src.retrieval.retriever import TemplateRetriever


# ============================================================================
# Sample Template Data
# ============================================================================


@pytest.fixture
def sample_templates() -> List[Dict[str, str]]:
    """
    Sample FAQ templates for testing (10 templates across 3 categories).

    Covers main categories:
    - Счета и вклады (3 templates)
    - Кредиты (3 templates)
    - Карты (4 templates)

    Returns:
        List of template dictionaries with id, category, subcategory, question, answer
    """
    return [
        # Счета и вклады
        {
            "id": "tmpl_savings_001",
            "category": "Счета и вклады",
            "subcategory": "Открытие счета",
            "question": "Как открыть накопительный счет?",
            "answer": "Для открытия накопительного счета вам необходимо посетить отделение банка с паспортом или использовать мобильное приложение."
        },
        {
            "id": "tmpl_savings_002",
            "category": "Счета и вклады",
            "subcategory": "Открытие счета",
            "question": "Какие документы нужны для открытия счета?",
            "answer": "Для открытия счета необходим паспорт гражданина Беларуси. Для юридических лиц требуется полный пакет учредительных документов."
        },
        {
            "id": "tmpl_savings_003",
            "category": "Счета и вклады",
            "subcategory": "Процентные ставки",
            "question": "Какой процент по вкладу для пенсионеров?",
            "answer": "Процентная ставка по вкладу для пенсионеров составляет 8% годовых при размещении от 500 рублей на срок от 6 месяцев."
        },

        # Кредиты
        {
            "id": "tmpl_credit_001",
            "category": "Кредиты",
            "subcategory": "Потребительский кредит",
            "question": "Как оформить потребительский кредит?",
            "answer": "Для оформления потребительского кредита необходимо заполнить заявку онлайн или посетить отделение банка с паспортом и справкой о доходах."
        },
        {
            "id": "tmpl_credit_002",
            "category": "Кредиты",
            "subcategory": "Потребительский кредит",
            "question": "Какая максимальная сумма потребительского кредита?",
            "answer": "Максимальная сумма потребительского кредита составляет 50 000 рублей на срок до 5 лет."
        },
        {
            "id": "tmpl_credit_003",
            "category": "Кредиты",
            "subcategory": "Ипотека",
            "question": "Какие условия ипотеки для молодых семей?",
            "answer": "Для молодых семей действует льготная ставка 9% годовых при первоначальном взносе от 15% и сроке кредитования до 30 лет."
        },

        # Карты
        {
            "id": "tmpl_card_001",
            "category": "Карты",
            "subcategory": "Дебетовые карты",
            "question": "Как заказать дебетовую карту?",
            "answer": "Дебетовую карту можно заказать онлайн в мобильном приложении или в любом отделении банка. Карта будет готова через 3-5 рабочих дней."
        },
        {
            "id": "tmpl_card_002",
            "category": "Карты",
            "subcategory": "Дебетовые карты",
            "question": "Какой кэшбэк по дебетовой карте?",
            "answer": "По дебетовой карте Premium кэшбэк составляет до 5% в выбранных категориях и 1% на все остальные покупки."
        },
        {
            "id": "tmpl_card_003",
            "category": "Карты",
            "subcategory": "Кредитные карты",
            "question": "Какая процентная ставка по кредитной карте?",
            "answer": "Процентная ставка по кредитной карте составляет от 18% годовых с льготным периодом 60 дней."
        },
        {
            "id": "tmpl_card_004",
            "category": "Карты",
            "subcategory": "Блокировка карты",
            "question": "Как заблокировать карту при утере?",
            "answer": "Для блокировки карты позвоните в контакт-центр банка по номеру 123 или заблокируйте карту в мобильном приложении."
        },
    ]


# ============================================================================
# Embedding Cache Fixtures
# ============================================================================


@pytest.fixture
def empty_cache() -> EmbeddingCache:
    """
    Empty embedding cache for testing.

    Returns:
        Empty EmbeddingCache instance
    """
    return EmbeddingCache()


@pytest.fixture
def populated_cache(sample_templates) -> EmbeddingCache:
    """
    Embedding cache populated with sample templates and random embeddings.

    Note: Uses random embeddings for testing (not real Scibox embeddings).
    Suitable for offline testing and unit tests.

    Returns:
        EmbeddingCache with 10 sample templates
    """
    cache = EmbeddingCache()

    for template in sample_templates:
        # Generate random 768-dimensional embedding (normalized)
        embedding = np.random.randn(768).astype(np.float32)

        metadata = TemplateMetadata(
            template_id=template["id"],
            category=template["category"],
            subcategory=template["subcategory"],
            question=template["question"],
            answer=template["answer"]
        )

        cache.add(template["id"], embedding, metadata)

    cache.precompute_time = 5.0  # Mock precomputation time

    return cache


# ============================================================================
# Embeddings Client Fixtures
# ============================================================================


@pytest.fixture
def embeddings_client_real() -> EmbeddingsClient:
    """
    Real Scibox embeddings API client.

    Requires SCIBOX_API_KEY environment variable.
    Use for integration tests with real API (online testing).

    Returns:
        EmbeddingsClient configured for Scibox API

    Raises:
        pytest.skip: If SCIBOX_API_KEY not set
    """
    api_key = os.getenv("SCIBOX_API_KEY")
    if not api_key:
        pytest.skip("SCIBOX_API_KEY not set - skipping integration test with real API")

    return EmbeddingsClient(api_key=api_key)


@pytest.fixture
def embeddings_client_mock() -> Mock:
    """
    Mocked embeddings client for offline testing.

    Returns random 768-dimensional embeddings for any input.
    Use for integration tests without API dependency.

    Returns:
        Mock object with embed() and embed_batch() methods
    """
    mock_client = Mock(spec=EmbeddingsClient)

    # Mock embed() to return random 768-dim vector
    mock_client.embed = Mock(
        return_value=np.random.randn(768).astype(np.float32)
    )

    # Mock embed_batch() to return list of random vectors
    def mock_embed_batch(texts):
        return [np.random.randn(768).astype(np.float32) for _ in texts]

    mock_client.embed_batch = Mock(side_effect=mock_embed_batch)

    return mock_client


# ============================================================================
# Retriever Fixtures
# ============================================================================


@pytest.fixture
def retriever_with_mock_client(populated_cache, embeddings_client_mock) -> TemplateRetriever:
    """
    Template retriever with mocked embeddings client (offline testing).

    Uses populated cache with random embeddings and mocked client.
    Suitable for integration tests without API dependency.

    Returns:
        TemplateRetriever instance ready for testing
    """
    return TemplateRetriever(
        embeddings_client=embeddings_client_mock,
        cache=populated_cache
    )


@pytest.fixture
async def retriever_with_real_client(embeddings_client_real) -> TemplateRetriever:
    """
    Template retriever with real Scibox embeddings (online testing).

    Precomputes embeddings for sample templates using real API.
    Requires SCIBOX_API_KEY environment variable.

    Returns:
        TemplateRetriever instance with real embeddings

    Raises:
        pytest.skip: If SCIBOX_API_KEY not set
    """
    # Create temporary FAQ file with sample templates (or use real FAQ)
    faq_path = os.getenv("FAQ_PATH")
    if not faq_path or not os.path.exists(faq_path):
        pytest.skip("FAQ_PATH not set or file not found - skipping integration test with real FAQ")

    # Precompute embeddings
    cache = await precompute_embeddings(
        faq_path=faq_path,
        embeddings_client=embeddings_client_real,
        batch_size=20
    )

    return TemplateRetriever(
        embeddings_client=embeddings_client_real,
        cache=cache
    )


# ============================================================================
# FAQ Parser Mocking
# ============================================================================


@pytest.fixture
def mock_faq_parser(sample_templates):
    """
    Mock FAQ parser that returns sample templates.

    Use with patch() to replace real FAQ parser in integration tests.

    Example:
        >>> with patch('src.classification.faq_parser.parse_faq', mock_faq_parser):
        ...     templates = parse_faq("any_path.xlsx")
        ...     # Returns sample_templates

    Returns:
        Mock function that returns sample templates
    """
    def _parse_faq(faq_path: str) -> List[Dict[str, str]]:
        """Mock parse_faq function."""
        return sample_templates

    return _parse_faq
