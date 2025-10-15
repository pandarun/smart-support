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
    # Expanded to cover all categories and edge cases
    FEW_SHOT_EXAMPLES = [
        # 1. Новые клиенты
        {
            "inquiry": "Как открыть счет в банке?",
            "category": "Новые клиенты",
            "subcategory": "Регистрация и онбординг",
            "confidence": 0.95
        },
        # 2. Техническая поддержка
        {
            "inquiry": "Забыл пароль от мобильного приложения, как восстановить?",
            "category": "Техническая поддержка",
            "subcategory": "Проблемы и решения",
            "confidence": 0.95
        },
        # 3. Продукты - Вклады (specific product)
        {
            "inquiry": "Как открыть вклад Великий путь?",
            "category": "Продукты - Вклады",
            "subcategory": "Рублевые - Великий путь",
            "confidence": 0.98
        },
        # 4. Продукты - Вклады (generic ruble deposit)
        {
            "inquiry": "Какая процентная ставка по рублевому вкладу?",
            "category": "Продукты - Вклады",
            "subcategory": "Рублевые - Мои условия",
            "confidence": 0.90
        },
        # 5. Продукты - Вклады (currency specific)
        {
            "inquiry": "Какая процентная ставка по вкладу в долларах?",
            "category": "Продукты - Вклады",
            "subcategory": "Валютные - USD",
            "confidence": 0.95
        },
        # 6. Продукты - Карты (specific card mentioned)
        {
            "inquiry": "Как оформить карту MORE?",
            "category": "Продукты - Карты",
            "subcategory": "Дебетовые карты - MORE",
            "confidence": 0.98
        },
        # 7. Продукты - Карты (credit card with name)
        {
            "inquiry": "Условия по кредитной карте Портмоне 2.0",
            "category": "Продукты - Карты",
            "subcategory": "Кредитные карты - Портмоне 2.0",
            "confidence": 0.97
        },
        # 8. Продукты - Кредиты (specific loan product)
        {
            "inquiry": "Условия потребительского кредита На всё про всё",
            "category": "Продукты - Кредиты",
            "subcategory": "Потребительские - На всё про всё",
            "confidence": 0.97
        },
        # 9. Продукты - Кредиты (auto loan)
        {
            "inquiry": "Какая процентная ставка по автокредиту?",
            "category": "Продукты - Кредиты",
            "subcategory": "Автокредиты - Автокредит без залога",
            "confidence": 0.93
        },
        # 10. Частные клиенты - generic card question (no specific product)
        {
            "inquiry": "Как узнать текущий платеж по кредитной карточке?",
            "category": "Частные клиенты",
            "subcategory": "Банковские карточки",
            "confidence": 0.92
        },
        # 11. Частные клиенты - generic credit question (policy/process)
        {
            "inquiry": "Почему банк может отказать в выдаче кредита?",
            "category": "Частные клиенты",
            "subcategory": "Кредиты",
            "confidence": 0.94
        },
        # 12. Частные клиенты - generic deposit question (policy/process)
        {
            "inquiry": "Обязательно ли приходить в офис банка для открытия депозита?",
            "category": "Частные клиенты",
            "subcategory": "Вклады и депозиты",
            "confidence": 0.93
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

ПРАВИЛА КЛАССИФИКАЦИИ:

A. КОГДА ИСПОЛЬЗОВАТЬ "Продукты - [Тип]" (продуктовые категории):
   Выбирай эти категории, если запрос:
   - Упоминает КОНКРЕТНОЕ название продукта (MORE, Форсаж, Портмоне 2.0, Великий путь, На всё про всё, и т.д.)
   - Спрашивает про условия, ставки, преимущества конкретного продукта
   - Просит оформить конкретный продукт

B. КОГДА ИСПОЛЬЗОВАТЬ "Частные клиенты" (общие категории):
   Выбирай эти категории, если запрос:
   - НЕ упоминает конкретное название продукта
   - Спрашивает про общие правила, политики, процедуры банка
   - Касается общих вопросов по типу продукта (например, "как узнать платеж по кредитной карточке")

СПЕЦИАЛЬНЫЕ ПРАВИЛА ПО ТИПАМ ПРОДУКТОВ:

1. ВКЛАДЫ:
   - Конкретный продукт (Великий путь, СуперСемь и т.д.) → "Продукты - Вклады" → название продукта
   - Валюта указана (доллары, евро, юани, рубли) → "Продукты - Вклады" → соответствующая валюта
   - Общий вопрос про рублевые вклады БЕЗ названия → "Продукты - Вклады" → "Рублевые - Мои условия"
   - Общие правила открытия депозитов, процедуры → "Частные клиенты" → "Вклады и депозиты"

2. КАРТЫ:
   - Упоминается название (MORE, Форсаж, Комплимент, PLAT/ON, Портмоне 2.0, ЧЕРЕПАХА, и т.д.) → "Продукты - Карты" → конкретная карта
   - Общий вопрос про карточки БЕЗ названия → "Частные клиенты" → "Банковские карточки"

3. КРЕДИТЫ:
   - Упоминается название (На всё про всё, Дальше - меньше, Автокредит, и т.д.) → "Продукты - Кредиты" → конкретный кредит
   - Упоминается тип (автокредит, потребительский, экспресс) → "Продукты - Кредиты" → соответствующий тип
   - Общие вопросы про кредиты, отказы, политики → "Частные клиенты" → "Кредиты"

4. ДРУГИЕ КАТЕГОРИИ:
   - Регистрация, открытие счета → "Новые клиенты"
   - Технические проблемы, пароли → "Техническая поддержка"
   - Настройка онлайн-банкинга → "Частные клиенты" → "Онлайн-сервисы"

ФОРМАТ ОТВЕТА (JSON):
{{
  "category": "название категории из списка",
  "subcategory": "название подкатегории из списка",
  "confidence": 0.95
}}

ПРИМЕРЫ:

Запрос: "{self.FEW_SHOT_EXAMPLES[0]['inquiry']}"
Ответ: {{"category": "{self.FEW_SHOT_EXAMPLES[0]['category']}", "subcategory": "{self.FEW_SHOT_EXAMPLES[0]['subcategory']}", "confidence": {self.FEW_SHOT_EXAMPLES[0]['confidence']}}}

Запрос: "{self.FEW_SHOT_EXAMPLES[5]['inquiry']}"
Ответ: {{"category": "{self.FEW_SHOT_EXAMPLES[5]['category']}", "subcategory": "{self.FEW_SHOT_EXAMPLES[5]['subcategory']}", "confidence": {self.FEW_SHOT_EXAMPLES[5]['confidence']}}}

Запрос: "{self.FEW_SHOT_EXAMPLES[9]['inquiry']}"
Ответ: {{"category": "{self.FEW_SHOT_EXAMPLES[9]['category']}", "subcategory": "{self.FEW_SHOT_EXAMPLES[9]['subcategory']}", "confidence": {self.FEW_SHOT_EXAMPLES[9]['confidence']}}}

Запрос: "{self.FEW_SHOT_EXAMPLES[7]['inquiry']}"
Ответ: {{"category": "{self.FEW_SHOT_EXAMPLES[7]['category']}", "subcategory": "{self.FEW_SHOT_EXAMPLES[7]['subcategory']}", "confidence": {self.FEW_SHOT_EXAMPLES[7]['confidence']}}}

Запрос: "{self.FEW_SHOT_EXAMPLES[10]['inquiry']}"
Ответ: {{"category": "{self.FEW_SHOT_EXAMPLES[10]['category']}", "subcategory": "{self.FEW_SHOT_EXAMPLES[10]['subcategory']}", "confidence": {self.FEW_SHOT_EXAMPLES[10]['confidence']}}}

ВАЖНО:
- Используй ТОЛЬКО категории и подкатегории из списка выше
- Ответ должен быть валидным JSON
- Уверенность (confidence) должна быть от 0.0 до 1.0
- Не добавляй дополнительные поля в JSON"""
        
        return system_prompt
    
    def _format_categories(self) -> str:
        """
        Format categories for inclusion in prompt.
        Groups product categories together, then general customer categories.

        Returns:
            Formatted string with categories and subcategories
        """
        lines = []

        # Define category ordering for better logical grouping
        category_order = [
            "Новые клиенты",
            "Продукты - Вклады",
            "Продукты - Карты",
            "Продукты - Кредиты",
            "Частные клиенты",
            "Техническая поддержка"
        ]

        # Add helpful descriptions for major categories
        category_descriptions = {
            "Продукты - Вклады": "  [Конкретные вклады с названиями или валютой]",
            "Продукты - Карты": "  [Конкретные карты с названиями]",
            "Продукты - Кредиты": "  [Конкретные кредиты с названиями]",
            "Частные клиенты": "  [Общие вопросы БЕЗ названия продукта]"
        }

        # Group by ordered categories
        for category in category_order:
            if category in self.categories:
                # Add category with optional description
                category_line = f"\n{category}"
                if category in category_descriptions:
                    category_line += f"\n{category_descriptions[category]}"
                lines.append(category_line)

                # Add subcategories
                for subcategory in sorted(self.categories[category]):
                    lines.append(f"  - {subcategory}")

        # Add any categories not in the predefined order (for completeness)
        for category, subcategories in sorted(self.categories.items()):
            if category not in category_order:
                lines.append(f"\n{category}:")
                for subcategory in sorted(subcategories):
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
