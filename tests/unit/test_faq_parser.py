"""
Unit Tests for FAQ Parser

Tests FAQ Excel parsing and category validation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.classification.faq_parser import FAQParser


@pytest.fixture
def faq_file_path():
    """Get FAQ file path (skip if not exists)."""
    faq_path = Path("docs/smart_support_vtb_belarus_faq_final.xlsx")
    if not faq_path.exists():
        pytest.skip("FAQ file not found")
    return str(faq_path)


@pytest.mark.unit
def test_faq_parser_initialization(faq_file_path):
    """Test FAQ parser initializes with valid file."""
    parser = FAQParser(faq_file_path)
    
    assert parser.faq_path.exists()
    assert parser.get_category_count() > 0
    assert parser.get_subcategory_count() > 0


@pytest.mark.unit
def test_faq_parser_file_not_found():
    """Test FAQ parser raises error for missing file."""
    with pytest.raises(FileNotFoundError):
        FAQParser("nonexistent_file.xlsx")


@pytest.mark.unit
def test_get_categories(faq_file_path):
    """Test getting list of categories."""
    parser = FAQParser(faq_file_path)
    
    categories = parser.get_categories()
    
    assert isinstance(categories, list)
    assert len(categories) > 0
    
    # Categories should be unique and sorted
    assert len(categories) == len(set(categories))
    assert categories == sorted(categories)


@pytest.mark.unit
def test_get_subcategories(faq_file_path):
    """Test getting subcategories for a category."""
    parser = FAQParser(faq_file_path)
    
    categories = parser.get_categories()
    category = categories[0]
    
    subcategories = parser.get_subcategories(category)
    
    assert isinstance(subcategories, list)
    assert len(subcategories) > 0


@pytest.mark.unit
def test_get_subcategories_invalid_category(faq_file_path):
    """Test getting subcategories for invalid category returns empty list."""
    parser = FAQParser(faq_file_path)
    
    subcategories = parser.get_subcategories("NonexistentCategory")
    
    assert subcategories == []


@pytest.mark.unit
def test_get_all_categories_dict(faq_file_path):
    """Test getting complete category dictionary."""
    parser = FAQParser(faq_file_path)
    
    categories_dict = parser.get_all_categories_dict()
    
    assert isinstance(categories_dict, dict)
    assert len(categories_dict) > 0
    
    # Each category should have subcategories
    for category, subcategories in categories_dict.items():
        assert isinstance(subcategories, list)
        assert len(subcategories) > 0


@pytest.mark.unit
def test_is_valid_category(faq_file_path):
    """Test category validation."""
    parser = FAQParser(faq_file_path)
    
    categories = parser.get_categories()
    valid_category = categories[0]
    
    assert parser.is_valid_category(valid_category) is True
    assert parser.is_valid_category("InvalidCategory") is False


@pytest.mark.unit
def test_is_valid_subcategory(faq_file_path):
    """Test subcategory validation."""
    parser = FAQParser(faq_file_path)
    
    categories = parser.get_categories()
    category = categories[0]
    subcategories = parser.get_subcategories(category)
    valid_subcategory = subcategories[0]
    
    assert parser.is_valid_subcategory(category, valid_subcategory) is True
    assert parser.is_valid_subcategory(category, "InvalidSubcategory") is False
    assert parser.is_valid_subcategory("InvalidCategory", valid_subcategory) is False


@pytest.mark.unit
def test_format_for_prompt(faq_file_path):
    """Test formatting categories for LLM prompt."""
    parser = FAQParser(faq_file_path)
    
    formatted = parser.format_for_prompt()
    
    assert isinstance(formatted, str)
    assert len(formatted) > 0
    
    # Should contain category names
    categories = parser.get_categories()
    for category in categories[:3]:  # Check first 3
        assert category in formatted


@pytest.mark.unit
def test_category_count_matches_dict(faq_file_path):
    """Test category count matches dictionary size."""
    parser = FAQParser(faq_file_path)
    
    category_count = parser.get_category_count()
    categories_dict = parser.get_all_categories_dict()
    
    assert category_count == len(categories_dict)


@pytest.mark.unit
def test_subcategory_count_matches_sum(faq_file_path):
    """Test subcategory count matches sum of all subcategories."""
    parser = FAQParser(faq_file_path)
    
    subcategory_count = parser.get_subcategory_count()
    categories_dict = parser.get_all_categories_dict()
    
    expected_count = sum(len(subcats) for subcats in categories_dict.values())
    
    assert subcategory_count == expected_count


@pytest.mark.unit
@patch('src.classification.faq_parser.openpyxl.load_workbook')
def test_faq_parser_handles_empty_file(mock_load_workbook):
    """Test FAQ parser handles empty Excel file."""
    # Mock empty workbook
    mock_workbook = MagicMock()
    mock_sheet = MagicMock()
    mock_sheet.iter_rows.return_value = []
    mock_workbook.active = mock_sheet
    mock_load_workbook.return_value = mock_workbook
    
    with pytest.raises(ValueError, match="No categories found"):
        parser = FAQParser("dummy.xlsx")
