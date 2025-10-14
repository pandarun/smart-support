"""
Integration Test Fixtures

Provides fixtures for integration testing with real dependencies.

Constitution Compliance:
- Principle III: Integration tests with testcontainers (mandated)
"""

import os
import pytest
from pathlib import Path

from src.classification.faq_parser import FAQParser, get_faq_parser
from src.classification.client import SciboxClient, get_scibox_client
from src.classification.classifier import Classifier


@pytest.fixture(scope="session")
def faq_file_path():
    """Get path to FAQ file."""
    faq_path = Path("docs/smart_support_vtb_belarus_faq_final.xlsx")
    if not faq_path.exists():
        pytest.skip(f"FAQ file not found: {faq_path}")
    return str(faq_path)


@pytest.fixture(scope="session")
def faq_parser(faq_file_path):
    """Create FAQ parser instance for testing."""
    return FAQParser(faq_file_path)


@pytest.fixture(scope="session")
def scibox_api_key():
    """Get Scibox API key from environment."""
    api_key = os.getenv("SCIBOX_API_KEY")
    if not api_key:
        pytest.skip("SCIBOX_API_KEY environment variable not set")
    return api_key


@pytest.fixture(scope="session")
def scibox_client(scibox_api_key):
    """Create Scibox client instance for testing."""
    return SciboxClient(api_key=scibox_api_key, timeout=2.0)


@pytest.fixture(scope="function")
def classifier(faq_parser, scibox_client):
    """Create classifier instance for testing."""
    return Classifier(faq_parser=faq_parser, scibox_client=scibox_client)


@pytest.fixture
def sample_inquiries():
    """Sample inquiries for testing."""
    return [
        "Как открыть счет в банке?",
        "Какая процентная ставка по вкладу в долларах?",
        "Забыл пароль от мобильного приложения",
        "Условия по кредитной карте Портмоне 2.0",
        "Как получить дебетовую карту?"
    ]


@pytest.fixture
def sample_validation_records():
    """Sample validation records with ground truth."""
    return [
        {
            "inquiry": "Как открыть счет?",
            "expected_category": "Новые клиенты",
            "expected_subcategory": "Регистрация и онбординг"
        },
        {
            "inquiry": "Какая процентная ставка по ипотеке?",
            "expected_category": "Продукты - Кредиты",
            "expected_subcategory": "Ипотека"
        },
        {
            "inquiry": "Забыл пароль от приложения",
            "expected_category": "Техническая поддержка",
            "expected_subcategory": "Проблемы и решения"
        }
    ]
