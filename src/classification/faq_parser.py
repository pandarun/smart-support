"""
Classification Module - FAQ Parser

Extracts category and subcategory hierarchy from VTB Belarus FAQ Excel file.
Implements caching for performance optimization.

Constitution Compliance:
- Principle VI: Knowledge Base Integration (FAQ parsing and validation)
- Performance: Load once on module import, cache in memory
"""

import os
from typing import Dict, List, Set
from pathlib import Path
import openpyxl
from collections import defaultdict


class FAQParser:
    """
    Parser for VTB Belarus FAQ Excel file.
    
    Extracts category/subcategory hierarchy and provides validation methods.
    """
    
    def __init__(self, faq_path: str):
        """
        Initialize FAQ parser.
        
        Args:
            faq_path: Path to FAQ Excel file
            
        Raises:
            FileNotFoundError: If FAQ file doesn't exist
            ValueError: If FAQ file format is invalid
        """
        self.faq_path = Path(faq_path)
        if not self.faq_path.exists():
            raise FileNotFoundError(f"FAQ file not found: {faq_path}")
        
        self._categories: Dict[str, List[str]] = {}
        self._load_categories()
    
    def _load_categories(self) -> None:
        """
        Load categories and subcategories from Excel file.
        
        Expected structure:
        - Column A (index 0): Category
        - Column B (index 1): Subcategory
        - First row is header (skipped)
        """
        try:
            workbook = openpyxl.load_workbook(self.faq_path, read_only=True, data_only=True)
            sheet = workbook.active
            
            categories_dict: Dict[str, Set[str]] = defaultdict(set)
            
            # Skip header row, iterate from row 2
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 2:
                    continue
                
                category = row[0]
                subcategory = row[1]
                
                # Skip empty cells
                if not category or not subcategory:
                    continue
                
                # Convert to string and strip whitespace
                category = str(category).strip()
                subcategory = str(subcategory).strip()
                
                if category and subcategory:
                    categories_dict[category].add(subcategory)
            
            workbook.close()
            
            # Convert sets to sorted lists for consistent ordering
            self._categories = {
                cat: sorted(list(subcats)) 
                for cat, subcats in sorted(categories_dict.items())
            }
            
            if not self._categories:
                raise ValueError("No categories found in FAQ file")
                
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to parse FAQ file: {str(e)}")
    
    def get_categories(self) -> List[str]:
        """
        Get list of all categories.
        
        Returns:
            Sorted list of category names
        """
        return sorted(list(self._categories.keys()))
    
    def get_subcategories(self, category: str) -> List[str]:
        """
        Get subcategories for a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of subcategory names, empty if category not found
        """
        return self._categories.get(category, [])
    
    def get_all_categories_dict(self) -> Dict[str, List[str]]:
        """
        Get complete category → subcategories mapping.
        
        Returns:
            Dictionary mapping categories to their subcategories
        """
        return self._categories.copy()
    
    def is_valid_category(self, category: str) -> bool:
        """
        Check if category exists in FAQ.
        
        Args:
            category: Category name to validate
            
        Returns:
            True if category exists, False otherwise
        """
        return category in self._categories
    
    def is_valid_subcategory(self, category: str, subcategory: str) -> bool:
        """
        Check if subcategory exists under given category.
        
        Args:
            category: Category name
            subcategory: Subcategory name to validate
            
        Returns:
            True if subcategory exists under category, False otherwise
        """
        if category not in self._categories:
            return False
        return subcategory in self._categories[category]
    
    def get_category_count(self) -> int:
        """Get total number of categories."""
        return len(self._categories)
    
    def get_subcategory_count(self) -> int:
        """Get total number of subcategories across all categories."""
        return sum(len(subcats) for subcats in self._categories.values())
    
    def format_for_prompt(self) -> str:
        """
        Format categories and subcategories for LLM prompt.
        
        Returns:
            Formatted string listing all categories and their subcategories
        """
        lines = []
        for category, subcategories in sorted(self._categories.items()):
            lines.append(f"\n{category}:")
            for subcategory in subcategories:
                lines.append(f"  - {subcategory}")
        return "\n".join(lines)


# Global FAQ parser instance (cached)
_faq_parser_instance: FAQParser = None


def get_faq_parser(faq_path: str = None) -> FAQParser:
    """
    Get cached FAQ parser instance.

    Args:
        faq_path: Path to FAQ file (optional, uses environment variable if not provided)

    Returns:
        Cached FAQParser instance

    Raises:
        ValueError: If FAQ path not provided and FAQ_PATH env var not set
    """
    global _faq_parser_instance

    if _faq_parser_instance is None:
        if faq_path is None:
            faq_path = os.getenv("FAQ_PATH", "docs/smart_support_vtb_belarus_faq_final.xlsx")

        if not faq_path:
            raise ValueError("FAQ path not provided and FAQ_PATH environment variable not set")

        _faq_parser_instance = FAQParser(faq_path)

    return _faq_parser_instance


def parse_faq(faq_path: str) -> List[Dict[str, str]]:
    """
    Parse FAQ Excel file and extract all templates.

    Reads the FAQ database and returns a list of templates with their
    categories, subcategories, questions, and answers.

    Args:
        faq_path: Path to FAQ Excel file

    Returns:
        List of template dictionaries with keys:
        - id: Unique template identifier (e.g., "tmpl_001")
        - category: Main category name
        - subcategory: Subcategory name
        - question: Example question text
        - answer: Template answer text

    Raises:
        FileNotFoundError: If FAQ file doesn't exist
        ValueError: If FAQ file format is invalid or empty

    Example:
        >>> templates = parse_faq("docs/faq.xlsx")
        >>> len(templates)
        187
        >>> templates[0]['category']
        'Счета и вклады'
    """
    import pandas as pd

    # Check if file exists
    faq_file = Path(faq_path)
    if not faq_file.exists():
        raise FileNotFoundError(f"FAQ file not found: {faq_path}")

    try:
        # Read Excel file
        df = pd.read_excel(faq_path)

        # Verify required columns exist
        required_columns = ['Основная категория', 'Подкатегория', 'Пример вопроса', 'Шаблонный ответ']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"FAQ file missing required columns: {missing_columns}")

        # Extract templates
        templates = []
        for idx, row in df.iterrows():
            # Skip rows with missing data
            if pd.isna(row['Основная категория']) or pd.isna(row['Подкатегория']):
                continue
            if pd.isna(row['Пример вопроса']) or pd.isna(row['Шаблонный ответ']):
                continue

            template = {
                'id': f"tmpl_{idx:03d}",
                'category': str(row['Основная категория']).strip(),
                'subcategory': str(row['Подкатегория']).strip(),
                'question': str(row['Пример вопроса']).strip(),
                'answer': str(row['Шаблонный ответ']).strip()
            }
            templates.append(template)

        if not templates:
            raise ValueError(f"No valid templates found in FAQ file: {faq_path}")

        return templates

    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise ValueError(f"Failed to parse FAQ file: {e}") from e
