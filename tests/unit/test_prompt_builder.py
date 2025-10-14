"""
Unit Tests for Prompt Builder

Tests prompt construction and formatting.
"""

import pytest
from src.classification.prompt_builder import PromptBuilder


@pytest.fixture
def sample_categories():
    """Sample FAQ categories for testing."""
    return {
        "Новые клиенты": ["Регистрация и онбординг", "Первые шаги"],
        "Продукты - Вклады": ["Валютные (USD)", "Валютные (EUR)"],
        "Техническая поддержка": ["Проблемы и решения"]
    }


@pytest.fixture
def prompt_builder(sample_categories):
    """Create prompt builder instance."""
    return PromptBuilder(sample_categories)


@pytest.mark.unit
def test_prompt_builder_initialization(prompt_builder):
    """Test prompt builder initializes correctly."""
    assert prompt_builder.categories is not None
    assert prompt_builder.get_category_count() == 3
    assert prompt_builder.get_subcategory_count() == 5


@pytest.mark.unit
def test_system_prompt_structure(prompt_builder):
    """Test system prompt has correct structure."""
    system_prompt = prompt_builder.get_system_prompt()
    
    # Verify key sections present
    assert "эксперт по банковским продуктам" in system_prompt
    assert "JSON" in system_prompt
    assert "category" in system_prompt
    assert "subcategory" in system_prompt
    assert "confidence" in system_prompt
    
    # Verify few-shot examples are included
    assert "Как открыть счет" in system_prompt


@pytest.mark.unit
def test_categories_in_prompt(prompt_builder):
    """Test all categories are included in prompt."""
    system_prompt = prompt_builder.get_system_prompt()
    
    # All categories should be in prompt
    assert "Новые клиенты" in system_prompt
    assert "Продукты - Вклады" in system_prompt
    assert "Техническая поддержка" in system_prompt
    
    # All subcategories should be in prompt
    assert "Регистрация и онбординг" in system_prompt
    assert "Валютные (USD)" in system_prompt
    assert "Проблемы и решения" in system_prompt


@pytest.mark.unit
def test_few_shot_examples_in_prompt(prompt_builder):
    """Test few-shot examples are properly formatted."""
    system_prompt = prompt_builder.get_system_prompt()
    
    # Check for example inquiries
    for example in PromptBuilder.FEW_SHOT_EXAMPLES:
        assert example["inquiry"] in system_prompt
        assert example["category"] in system_prompt
        assert example["subcategory"] in system_prompt


@pytest.mark.unit
def test_build_classification_messages(prompt_builder):
    """Test message building for API call."""
    inquiry = "Как открыть счет?"
    
    messages = prompt_builder.build_classification_messages(inquiry)
    
    # Should return list with system and user messages
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == inquiry


@pytest.mark.unit
def test_json_format_in_prompt(prompt_builder):
    """Test JSON format specification is in prompt."""
    system_prompt = prompt_builder.get_system_prompt()
    
    # Verify JSON schema is specified
    assert '"category":' in system_prompt
    assert '"subcategory":' in system_prompt
    assert '"confidence":' in system_prompt
    
    # Verify JSON requirements
    assert "JSON" in system_prompt
    assert "{" in system_prompt
    assert "}" in system_prompt


@pytest.mark.unit
def test_prompt_includes_instructions(prompt_builder):
    """Test prompt includes clear instructions."""
    system_prompt = prompt_builder.get_system_prompt()
    
    # Should have clear instructions
    assert "классифицировать" in system_prompt.lower()
    assert "категори" in system_prompt.lower()
    assert "подкатегори" in system_prompt.lower()


@pytest.mark.unit
def test_category_format_for_prompt(prompt_builder, sample_categories):
    """Test category formatting utility."""
    formatted = prompt_builder._format_categories()
    
    # Should contain all categories
    for category in sample_categories.keys():
        assert category in formatted
    
    # Should be hierarchical
    assert ":" in formatted
    assert "-" in formatted or "•" in formatted or " " in formatted
