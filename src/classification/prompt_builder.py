"""
Classification Module - Prompt Builder

Constructs LLM prompts for classification tasks.
Implements few-shot learning with structured JSON output.

Constitution Compliance:
- Principle IV: API-First Integration (prompt engineering for Scibox LLM)
- QR-002: Deterministic results (structured JSON format)
"""

from typing import Dict, List


class PromptBuilder:
    """
    Builds classification prompts for Scibox LLM.
    
    Uses system prompt with category list, few-shot examples,
    and JSON output format specification.
    """
    
    # Few-shot examples for Russian banking inquiries
    FEW_SHOT_EXAMPLES = [
        {
            "inquiry": "Как открыть счет в банке?",
            "category": "Новые клиенты",
            "subcategory": "Регистрация и онбординг",
            "confidence": 0.95
        },
        {
            "inquiry": "Какая процентная ставка?",
            "category": "Продукты - Вклады",
            "subcategory": "Рублевые - Мои условия",
            "confidence": 0.90
        },
        {
            "inquiry": "Какая процентная ставка по вкладу в долларах?",
            "category": "Продукты - Вклады",
            "subcategory": "Валютные (USD)",
            "confidence": 0.92
        },
        {
            "inquiry": "Забыл пароль от мобильного приложения, как восстановить?",
            "category": "Техническая поддержка",
            "subcategory": "Проблемы и решения",
            "confidence": 0.88
        }
    ]
    
    def __init__(self, categories: Dict[str, List[str]]):
        """
        Initialize prompt builder with FAQ categories.
        
        Args:
            categories: Dictionary mapping categories to subcategories
        """
        self.categories = categories
        self._system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """
        Build system prompt with category list and instructions.
        
        Returns:
            System prompt string
        """
        # Format categories for prompt
        category_list = self._format_categories()
        
        system_prompt = f"""Ты эксперт по банковским продуктам ВТБ Беларусь.
Твоя задача: классифицировать запросы клиентов по категориям и подкатегориям.

ДОСТУПНЫЕ КАТЕГОРИИ И ПОДКАТЕГОРИИ:
{category_list}

ИНСТРУКЦИИ:
1. Внимательно прочитай запрос клиента
2. Определи, к какой категории и подкатегории он относится
3. Выбери ТОЛЬКО из списка доступных категорий выше
4. Оцени уверенность в классификации (0.0 до 1.0)
5. Ответь СТРОГО в формате JSON

ВАЖНЫЕ ПРАВИЛА ДЛЯ ВКЛАДОВ:
- Если запрос про КОНКРЕТНЫЙ продукт (например, "Великий путь", "Максимум"), выбери эту подкатегорию
- Если запрос ОБЩИЙ про рублевые вклады без указания продукта → используй "Рублевые - Мои условия"
- Если запрос про валютные вклады (доллары, евро, юани) → выбери соответствующую валюту
- Если клиент спрашивает про "свой вклад", "мой вклад", "мои условия" → используй "Рублевые - Мои условия"

ФОРМАТ ОТВЕТА (JSON):
{{
  "category": "название категории из списка",
  "subcategory": "название подкатегории из списка",
  "confidence": 0.95
}}

ПРИМЕРЫ:

Запрос: "{self.FEW_SHOT_EXAMPLES[0]['inquiry']}"
Ответ: {{"category": "{self.FEW_SHOT_EXAMPLES[0]['category']}", "subcategory": "{self.FEW_SHOT_EXAMPLES[0]['subcategory']}", "confidence": {self.FEW_SHOT_EXAMPLES[0]['confidence']}}}

Запрос: "{self.FEW_SHOT_EXAMPLES[1]['inquiry']}"
Ответ: {{"category": "{self.FEW_SHOT_EXAMPLES[1]['category']}", "subcategory": "{self.FEW_SHOT_EXAMPLES[1]['subcategory']}", "confidence": {self.FEW_SHOT_EXAMPLES[1]['confidence']}}}

Запрос: "{self.FEW_SHOT_EXAMPLES[2]['inquiry']}"
Ответ: {{"category": "{self.FEW_SHOT_EXAMPLES[2]['category']}", "subcategory": "{self.FEW_SHOT_EXAMPLES[2]['subcategory']}", "confidence": {self.FEW_SHOT_EXAMPLES[2]['confidence']}}}

ВАЖНО:
- Используй ТОЛЬКО категории и подкатегории из списка выше
- Ответ должен быть валидным JSON
- Уверенность (confidence) должна быть от 0.0 до 1.0
- Не добавляй дополнительные поля в JSON"""
        
        return system_prompt
    
    def _format_categories(self) -> str:
        """
        Format categories for inclusion in prompt.
        
        Returns:
            Formatted string with categories and subcategories
        """
        lines = []
        for category, subcategories in sorted(self.categories.items()):
            lines.append(f"\n{category}:")
            for subcategory in subcategories:
                lines.append(f"  - {subcategory}")
        return "\n".join(lines)
    
    def build_classification_messages(self, inquiry: str) -> List[Dict[str, str]]:
        """
        Build messages for classification request.
        
        Args:
            inquiry: Customer inquiry text
            
        Returns:
            List of message dicts for OpenAI chat completion API
        """
        return [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": inquiry}
        ]
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for inspection/testing.
        
        Returns:
            System prompt string
        """
        return self._system_prompt
    
    def get_category_count(self) -> int:
        """Get number of categories in prompt."""
        return len(self.categories)
    
    def get_subcategory_count(self) -> int:
        """Get total number of subcategories in prompt."""
        return sum(len(subcats) for subcats in self.categories.values())
