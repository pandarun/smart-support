"""
Integration Tests for Markdown Parsing in Classification

Tests the full classification flow with markdown-wrapped JSON responses.
These tests mock the Scibox API to return markdown-formatted responses
and verify end-to-end parsing works correctly.
"""

import pytest
from unittest.mock import Mock, patch

from src.classification.classifier import Classifier, ClassificationError


class TestMarkdownParsingIntegration:
    """Integration tests for classification with markdown-wrapped responses."""

    @pytest.fixture
    def mock_faq_parser(self):
        """Mock FAQ parser with test categories."""
        parser = Mock()
        parser.get_all_categories_dict.return_value = {
            "Продукты - Карты": ["Дебетовые карты", "Карты рассрочки - КСТАТИ"],
            "Продукты - Вклады": ["Рублевые - Великий путь", "Рублевые - Подушка безопасности"]
        }
        parser.get_category_count.return_value = 2
        parser.get_subcategory_count.return_value = 4
        parser.is_valid_category.return_value = True
        parser.is_valid_subcategory.return_value = True
        return parser

    # T009: Integration test for markdown-wrapped JSON
    @patch('src.classification.classifier.get_faq_parser')
    @patch('src.classification.classifier.get_scibox_client')
    def test_classification_with_markdown_wrapped_json(self, mock_get_client, mock_get_parser):
        """Test full classification flow with markdown-wrapped JSON response."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.get_all_categories_dict.return_value = {
            "Продукты - Карты": ["Дебетовые карты"]
        }
        mock_parser.get_category_count.return_value = 1
        mock_parser.get_subcategory_count.return_value = 1
        mock_parser.is_valid_category.return_value = True
        mock_parser.is_valid_subcategory.return_value = True
        mock_get_parser.return_value = mock_parser

        # Mock Scibox client to return markdown-wrapped JSON
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = """```json
{
  "category": "Продукты - Карты",
  "subcategory": "Дебетовые карты",
  "confidence": 0.95
}
```"""
        mock_client.chat_completion.return_value = mock_completion
        mock_get_client.return_value = mock_client

        # Create classifier and run classification
        classifier = Classifier()
        result = classifier.classify("Как получить дебетовую карту?")

        # Verify result
        assert result.category == "Продукты - Карты"
        assert result.subcategory == "Дебетовые карты"
        assert result.confidence == 0.95
        assert result.processing_time_ms >= 1  # Should be > 0 with real time

    # T010: Integration test for backward compatibility
    @patch('src.classification.classifier.get_faq_parser')
    @patch('src.classification.classifier.get_scibox_client')
    def test_classification_with_unwrapped_json(self, mock_get_client, mock_get_parser):
        """Test backward compatibility with unwrapped JSON response."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.get_all_categories_dict.return_value = {
            "Продукты - Вклады": ["Рублевые - Великий путь"]
        }
        mock_parser.get_category_count.return_value = 1
        mock_parser.get_subcategory_count.return_value = 1
        mock_parser.is_valid_category.return_value = True
        mock_parser.is_valid_subcategory.return_value = True
        mock_get_parser.return_value = mock_parser

        # Mock Scibox client to return plain JSON (no markdown)
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = """{
  "category": "Продукты - Вклады",
  "subcategory": "Рублевые - Великий путь",
  "confidence": 0.92
}"""
        mock_client.chat_completion.return_value = mock_completion
        mock_get_client.return_value = mock_client

        # Create classifier and run classification
        classifier = Classifier()
        result = classifier.classify("Какая доходность у вклада?")

        # Verify result (should work exactly as before)
        assert result.category == "Продукты - Вклады"
        assert result.subcategory == "Рублевые - Великий путь"
        assert result.confidence == 0.92

    # T011: Integration test for error handling
    @patch('src.classification.classifier.get_faq_parser')
    @patch('src.classification.classifier.get_scibox_client')
    def test_classification_with_malformed_json(self, mock_get_client, mock_get_parser):
        """Test error handling with malformed JSON (even after markdown stripping)."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.get_all_categories_dict.return_value = {
            "Продукты - Карты": ["Дебетовые карты"]
        }
        mock_parser.get_category_count.return_value = 1
        mock_parser.get_subcategory_count.return_value = 1
        mock_get_parser.return_value = mock_parser

        # Mock Scibox client to return invalid JSON wrapped in markdown
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = """```json
{
  "category": "Продукты - Карты"
  # Missing closing brace and fields
```"""
        mock_client.chat_completion.return_value = mock_completion
        mock_get_client.return_value = mock_client

        # Create classifier and verify error handling
        classifier = Classifier()
        with pytest.raises(ClassificationError, match="Classification service returned invalid data"):
            classifier.classify("Тестовый запрос")

    # T020 (US3): Test markdown-wrapped invalid JSON
    @patch('src.classification.classifier.get_faq_parser')
    @patch('src.classification.classifier.get_scibox_client')
    def test_markdown_wrapped_invalid_json_error_logging(self, mock_get_client, mock_get_parser):
        """Test that markdown-wrapped invalid JSON produces proper error logs."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.get_all_categories_dict.return_value = {"Test": ["Test"]}
        mock_parser.get_category_count.return_value = 1
        mock_parser.get_subcategory_count.return_value = 1
        mock_get_parser.return_value = mock_parser

        # Mock invalid JSON response
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = """```json
{
  "invalid": "json",
  "missing": "fields"
}
```"""
        mock_client.chat_completion.return_value = mock_completion
        mock_get_client.return_value = mock_client

        classifier = Classifier()
        with pytest.raises(ClassificationError):
            classifier.classify("Test")

    # T021 (US3): Test non-JSON content wrapped in markdown
    @patch('src.classification.classifier.get_faq_parser')
    @patch('src.classification.classifier.get_scibox_client')
    def test_non_json_content_wrapped_in_markdown(self, mock_get_client, mock_get_parser):
        """Test error handling for non-JSON content in markdown blocks."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.get_all_categories_dict.return_value = {"Test": ["Test"]}
        mock_parser.get_category_count.return_value = 1
        mock_parser.get_subcategory_count.return_value = 1
        mock_get_parser.return_value = mock_parser

        # Mock non-JSON response
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = """```json
This is not JSON at all, just plain text.
```"""
        mock_client.chat_completion.return_value = mock_completion
        mock_get_client.return_value = mock_client

        classifier = Classifier()
        with pytest.raises(ClassificationError):
            classifier.classify("Test")


class TestGenericCodeBlockFormats:
    """Test various markdown format variations."""

    @patch('src.classification.classifier.get_faq_parser')
    @patch('src.classification.classifier.get_scibox_client')
    def test_generic_code_block_without_language(self, mock_get_client, mock_get_parser):
        """Test generic code block (no 'json' specifier)."""
        mock_parser = Mock()
        mock_parser.get_all_categories_dict.return_value = {"Test": ["Subtest"]}
        mock_parser.get_category_count.return_value = 1
        mock_parser.get_subcategory_count.return_value = 1
        mock_parser.is_valid_category.return_value = True
        mock_parser.is_valid_subcategory.return_value = True
        mock_get_parser.return_value = mock_parser

        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        # Generic code block (no 'json')
        mock_completion.choices[0].message.content = """```
{
  "category": "Test",
  "subcategory": "Subtest",
  "confidence": 0.88
}
```"""
        mock_client.chat_completion.return_value = mock_completion
        mock_get_client.return_value = mock_client

        classifier = Classifier()
        result = classifier.classify("Тестовый запрос")
        assert result.category == "Test"
        assert result.confidence == 0.88
