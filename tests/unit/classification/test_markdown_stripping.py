"""
Unit Tests for Markdown Code Block Stripping

Tests the strip_markdown_code_blocks() function that removes markdown
formatting from LLM JSON responses.

Following TDD approach - these tests will FAIL until implementation is complete.
"""

import pytest


# Import will fail until function is implemented
try:
    from src.classification.classifier import strip_markdown_code_blocks
except (ImportError, AttributeError):
    # Define placeholder for TDD - tests should fail until real implementation
    def strip_markdown_code_blocks(text: str) -> str:
        raise NotImplementedError("strip_markdown_code_blocks not yet implemented")


class TestMarkdownStripping:
    """Test suite for markdown code block stripping functionality."""

    # T001: Test markdown-wrapped JSON with language specifier
    def test_strip_json_code_block(self):
        """Test stripping ```json code block markers."""
        input_text = """```json
{
  "category": "Продукты - Карты",
  "subcategory": "Карты рассрочки - КСТАТИ",
  "confidence": 0.97
}
```"""
        expected = """{
  "category": "Продукты - Карты",
  "subcategory": "Карты рассрочки - КСТАТИ",
  "confidence": 0.97
}"""
        result = strip_markdown_code_blocks(input_text)
        assert result == expected, f"Expected cleaned JSON, got: {result}"

    # T002: Test generic code block (no language specifier)
    def test_strip_generic_code_block(self):
        """Test stripping generic ``` code block markers."""
        input_text = """```
{
  "category": "Продукты - Вклады",
  "subcategory": "Рублевые - Великий путь",
  "confidence": 0.95
}
```"""
        expected = """{
  "category": "Продукты - Вклады",
  "subcategory": "Рублевые - Великий путь",
  "confidence": 0.95
}"""
        result = strip_markdown_code_blocks(input_text)
        assert result == expected, f"Expected cleaned JSON, got: {result}"

    # T003: Test leading/trailing whitespace handling
    def test_strip_with_whitespace(self):
        """Test that leading/trailing whitespace is properly handled."""
        input_text = """

  ```json
  {
    "category": "Продукты - Карты",
    "subcategory": "Дебетовые карты",
    "confidence": 0.89
  }
  ```

"""
        expected = """{
    "category": "Продукты - Карты",
    "subcategory": "Дебетовые карты",
    "confidence": 0.89
  }"""
        result = strip_markdown_code_blocks(input_text)
        assert result == expected, f"Expected cleaned JSON with proper whitespace, got: {result}"

    # T004: Test backward compatibility (unwrapped JSON)
    def test_no_stripping_needed(self):
        """Test that unwrapped JSON passes through unchanged (backward compat)."""
        input_text = """{
  "category": "Продукты - Кредиты",
  "subcategory": "Потребительские кредиты",
  "confidence": 0.92
}"""
        result = strip_markdown_code_blocks(input_text)
        assert result == input_text, f"Expected unchanged JSON, got: {result}"

    # T005: Test incomplete markers (edge case)
    def test_incomplete_markers(self):
        """Test handling of incomplete code block markers."""
        # Only opening marker, no closing
        input_text = """```json
{
  "category": "Продукты - Вклады",
  "confidence": 0.85
}"""
        expected = """{
  "category": "Продукты - Вклады",
  "confidence": 0.85
}"""
        result = strip_markdown_code_blocks(input_text)
        assert result == expected, f"Expected markers stripped even if incomplete, got: {result}"

        # Only closing marker, no opening
        input_text2 = """{
  "category": "Продукты - Карты",
  "confidence": 0.90
}
```"""
        expected2 = """{
  "category": "Продукты - Карты",
  "confidence": 0.90
}"""
        result2 = strip_markdown_code_blocks(input_text2)
        assert result2 == expected2, f"Expected closing marker stripped, got: {result2}"

    # T013 (US2): Test uppercase language specifier
    def test_uppercase_specifier(self):
        """Test handling of uppercase language specifier (```JSON)."""
        input_text = """```JSON
{
  "category": "Продукты - Вклады",
  "confidence": 0.88
}
```"""
        # Should treat as generic ``` since we don't special-case uppercase
        expected = """{
  "category": "Продукты - Вклады",
  "confidence": 0.88
}"""
        result = strip_markdown_code_blocks(input_text)
        assert result == expected, f"Expected cleaned JSON, got: {result}"

    # T014 (US2): Test newlines within code block
    def test_newlines_preserved(self):
        """Test that newlines within JSON content are preserved."""
        input_text = """```json
{

  "category": "Продукты - Вклады",

  "confidence": 0.91
}
```"""
        # Newlines within JSON should be preserved
        result = strip_markdown_code_blocks(input_text)
        assert "{" in result
        assert "}" in result
        assert "category" in result
        # Verify it's valid structure that can be parsed
        import json
        json.loads(result)  # Should not raise

    # T015 (US2): Test multiple whitespace variations
    def test_whitespace_variations(self):
        """Test various whitespace patterns around markers."""
        test_cases = [
            ("```json\n{}\n```", "{}"),  # Minimal
            ("```json  \n{}\n  ```", "{}"),  # Trailing spaces
            ("\t```json\n{}\n```\t", "{}"),  # Tabs
            ("  \n  ```json\n{}\n```  \n  ", "{}"),  # Multiple newlines/spaces
        ]

        for input_text, expected_content in test_cases:
            result = strip_markdown_code_blocks(input_text)
            assert expected_content in result, f"Failed for input: {repr(input_text)}"

    # T022 (US3): Test error log content verification
    def test_error_handling_preserves_content(self):
        """Test that stripping preserves content for error logging."""
        # Invalid JSON wrapped in markdown
        input_text = """```json
{
  "category": "Продукты"
  # Missing closing brace and comma
```"""
        result = strip_markdown_code_blocks(input_text)

        # Result should still contain the invalid JSON for error logging
        assert "category" in result
        assert "Продукты" in result
        # Markers should be gone
        assert "```" not in result
