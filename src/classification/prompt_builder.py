"""
Classification Module - Prompt Builder

Constructs LLM prompts for classification tasks.
Implements few-shot learning with structured JSON output.

Constitution Compliance:
- Principle IV: API-First Integration (prompt engineering for Scibox LLM)
- QR-002: Deterministic results (structured JSON format)
"""

from collections import OrderedDict
from typing import Dict, List


class PromptBuilder:
    """
    Builds classification prompts for Scibox LLM.
    
    Uses system prompt with category list, few-shot examples,
    and JSON output format specification.
    """
    
    # Default confidences help few-shot examples stay realistic for each block
    CATEGORY_CONFIDENCE_DEFAULTS = {
        "Новые клиенты": 0.93,
        "Техническая поддержка": 0.95,
        "Продукты - Вклады": 0.96,
        "Продукты - Карты": 0.97,
        "Продукты - Кредиты": 0.97,
        "Частные клиенты": 0.92
    }

    # Map every subcategory to a representative inquiry and trigger keywords
    SUBCATEGORY_GUIDE = OrderedDict([
        ("Регистрация и онбординг", {
            "category": "Новые клиенты",
            "example_inquiry": "Как стать клиентом банка онлайн?",
            "keywords": ["регистрация", "новый клиент", "МСИ", "идентификация"]
        }),
        ("Первые шаги", {
            "category": "Новые клиенты",
            "example_inquiry": "Первый вход в Интернет-банк",
            "keywords": ["первый вход", "настроить", "мобильное приложение", "логин"]
        }),
        ("Проблемы и решения", {
            "category": "Техническая поддержка",
            "example_inquiry": "Не могу войти в Интернет-банк",
            "keywords": ["забыл пароль", "не могу войти", "ошибка", "сбросить доступ"]
        }),
        ("Дебетовые карты - MORE", {
            "category": "Продукты - Карты",
            "example_inquiry": "Как оформить карту MORE?",
            "keywords": ["карта more", "more", "преимущества", "лимиты"]
        }),
        ("Дебетовые карты - Форсаж", {
            "category": "Продукты - Карты",
            "example_inquiry": "Как получить карту Форсаж?",
            "keywords": ["форсаж", "мгновенного выпуска", "за сколько минут", "карта форсаж"]
        }),
        ("Дебетовые карты - Комплимент", {
            "category": "Продукты - Карты",
            "example_inquiry": "Кто может оформить карту Комплимент?",
            "keywords": ["комплимент", "премиальная карта", "льготы", "стоимость обслуживания"]
        }),
        ("Дебетовые карты - Signature", {
            "category": "Продукты - Карты",
            "example_inquiry": "Как получить премиальную карту Signature?",
            "keywords": ["signature", "премиальная карта", "привилегии", "требования"]
        }),
        ("Дебетовые карты - Infinite", {
            "category": "Продукты - Карты",
            "example_inquiry": "Как оформить карту Infinite?",
            "keywords": ["infinite", "пакет услуг", "требования к доходу", "привилегии"]
        }),
        ("Кредитные карты - PLAT/ON", {
            "category": "Продукты - Карты",
            "example_inquiry": "Где можно оформить карточку PLAT/ON?",
            "keywords": ["plat/on", "платон", "бонусный период", "кредитный лимит"]
        }),
        ("Кредитные карты - Портмоне 2.0", {
            "category": "Продукты - Карты",
            "example_inquiry": "Как оформить кредитную карту Портмоне 2.0?",
            "keywords": ["портмоне", "портмоне 2.0", "кредитная карта", "лимит портмоне"]
        }),
        ("Кредитные карты - Отличник", {
            "category": "Продукты - Карты",
            "example_inquiry": "Кто может оформить карту Отличник?",
            "keywords": ["отличник", "справка о доходах", "лимит", "процент на остаток"]
        }),
        ("Карты рассрочки - ЧЕРЕПАХА", {
            "category": "Продукты - Карты",
            "example_inquiry": "Где можно оформить карту ЧЕРЕПАХА?",
            "keywords": ["черепаха", "карта рассрочки", "магазины-партнеры", "кредитный лимит"]
        }),
        ("Карты рассрочки - КСТАТИ", {
            "category": "Продукты - Карты",
            "example_inquiry": "Как оформить карту КСТАТИ?",
            "keywords": ["кстати", "карта рассрочки", "преимущества", "лимиты"]
        }),
        ("Потребительские - На всё про всё", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "Как оформить кредит На всё про всё?",
            "keywords": ["на всё про всё", "потребительский кредит", "условия", "оформить"]
        }),
        ("Потребительские - Дальше - меньше", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "Что означает снижаемая ставка?",
            "keywords": ["дальше меньше", "снижаемая ставка", "лестничная ставка", "график погашения"]
        }),
        ("Потребительские - Легко платить", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "Что такое льготные месяцы?",
            "keywords": ["легко платить", "льготные месяцы", "пауза по платежам", "план выплат"]
        }),
        ("Потребительские - Всё только начинается", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "Кто может оформить этот кредит?",
            "keywords": ["всё только начинается", "молодежный кредит", "кто может оформить", "условия"]
        }),
        ("Потребительские - Старт", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "На какую сумму можно взять Старт?",
            "keywords": ["старт", "сумма кредита", "потребительский старт", "срок кредита"]
        }),
        ("Онлайн кредиты - Проще в онлайн", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "Как оформить онлайн кредит?",
            "keywords": ["проще в онлайн", "онлайн кредит", "без визита", "дистанционно"]
        }),
        ("Автокредиты - Автокредит без залога", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "На какие авто выдается кредит?",
            "keywords": ["автокредит", "без залога", "процент по авто", "транспорт"]
        }),
        ("Экспресс-кредиты - В магазинах-партнерах", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "В каких магазинах можно оформить?",
            "keywords": ["магазинах-партнерах", "экспресс кредит", "в магазине", "оформить на месте"]
        }),
        ("Экспресс-кредиты - На роднае", {
            "category": "Продукты - Кредиты",
            "example_inquiry": "Что такое кредит На роднае?",
            "keywords": ["на роднае", "экспресс-кредит", "магазины", "льготная ставка"]
        }),
        ("Рублевые - Мои условия", {
            "category": "Продукты - Вклады",
            "example_inquiry": "Как открыть вклад Мои условия?",
            "keywords": ["мои условия", "процентная ставка", "рублевый вклад", "пополнение"]
        }),
        ("Рублевые - Мои условия онлайн", {
            "category": "Продукты - Вклады",
            "example_inquiry": "Как открыть онлайн вклад?",
            "keywords": ["мои условия онлайн", "онлайн вклад", "через приложение", "интернет-банк"]
        }),
        ("Рублевые - Великий путь", {
            "category": "Продукты - Вклады",
            "example_inquiry": "Что особенного в этом вкладе?",
            "keywords": ["великий путь", "долгосрочный вклад", "премиальный", "доходность"]
        }),
        ("Рублевые - СуперСемь", {
            "category": "Продукты - Вклады",
            "example_inquiry": "На какой срок вклад СуперСемь?",
            "keywords": ["суперсемь", "ставка", "7%", "срок вклада"]
        }),
        ("Рублевые - Подушка безопасности", {
            "category": "Продукты - Вклады",
            "example_inquiry": "Как работает условный вклад?",
            "keywords": ["подушка безопасности", "условный вклад", "досрочное изъятие", "страховой"]
        }),
        ("Валютные - USD", {
            "category": "Продукты - Вклады",
            "example_inquiry": "Какая ставка по долларовому вкладу?",
            "keywords": ["долларовый вклад", "usd", "ставка в долларах", "минимальная сумма usd"]
        }),
        ("Валютные - EUR", {
            "category": "Продукты - Вклады",
            "example_inquiry": "Есть ли вклады в евро?",
            "keywords": ["вклад в евро", "eur", "ставка в евро", "условия по евро"]
        }),
        ("Валютные - RUB", {
            "category": "Продукты - Вклады",
            "example_inquiry": "Можно ли открыть рублевый вклад?",
            "keywords": ["вклад в рублях", "российских рублях", "rub", "открыть вклад rub"]
        }),
        ("Валютные - CNY", {
            "category": "Продукты - Вклады",
            "example_inquiry": "Принимаются ли юани на вклад?",
            "keywords": ["вклад в юанях", "cny", "китайская валюта", "доходность юани"]
        }),
        ("Кредиты", {
            "category": "Частные клиенты",
            "example_inquiry": "Почему банк может отказать в выдаче кредита, и что такое ПДН?",
            "keywords": ["отказ в кредите", "ПДН", "справка о доходах", "самозанятый"]
        }),
        ("Банковские карточки", {
            "category": "Частные клиенты",
            "example_inquiry": "Как узнать текущий платеж по кредитной карточке?",
            "keywords": ["кредитная карточка", "текущий платеж", "лимит пополнения", "получить карточку"]
        }),
        ("Вклады и депозиты", {
            "category": "Частные клиенты",
            "example_inquiry": "Могу ли я оформить онлайн-вклад в вашем банке?",
            "keywords": ["онлайн-вклад", "досрочное закрытие", "регламент размещения", "оформить депозит без офиса"]
        }),
        ("Онлайн-сервисы", {
            "category": "Частные клиенты",
            "example_inquiry": "Почему не получается войти под логином и паролем из старого ДБО?",
            "keywords": ["интернет-банк", "логин и пароль", "старое ДБО", "история платежей"]
        })
    ])

    FEW_SHOT_EXAMPLES = []
    for subcategory, meta in SUBCATEGORY_GUIDE.items():
        FEW_SHOT_EXAMPLES.append(
            {
                "inquiry": meta["example_inquiry"],
                "category": meta["category"],
                "subcategory": subcategory,
                "confidence": CATEGORY_CONFIDENCE_DEFAULTS.get(meta["category"], 0.9)
            }
        )
    
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
        keyword_map = self._format_keyword_map()
        sample_snippets = "\n\n".join(
            f'Запрос: "{example["inquiry"]}"\nОтвет: {{"category": "{example["category"]}", "subcategory": "{example["subcategory"]}", "confidence": {example["confidence"]}}}'
            for example in self.FEW_SHOT_EXAMPLES
        )

        system_prompt = f"""Ты эксперт по банковским продуктам ВТБ Беларусь.
Твоя задача: классифицировать запросы клиентов по категориям и подкатегориям.

ДОСТУПНЫЕ КАТЕГОРИИ И ПОДКАТЕГОРИИ:
{category_list}

КЛЮЧЕВЫЕ ПОДСКАЗКИ ПО ПОДКАТЕГОРИЯМ:
{keyword_map}

ИНСТРУКЦИИ:
1. Внимательно прочитай запрос клиента
2. Определи, к какой категории и подкатегории он относится
3. Выбери ТОЛЬКО из списка доступных категорий выше
4. Оцени уверенность в классификации (0.0 до 1.0)
5. Ответь СТРОГО в формате JSON

АЛГОРИТМ СОВПАДЕНИЯ:
1. Найди точные или близкие совпадения с ключевыми подсказками (названия продуктов, аббревиатуры, частые словосочетания) и выбери соответствующую подкатегорию.
2. Если запрос почти дословно совпадает с шаблонным вопросом FAQ, используй ту же категорию и подкатегорию.
3. Если явных совпадений нет, примени правила ниже и выбери наиболее подходящую пару категория/подкатегория.

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
   - Конкретный продукт (Великий путь, СуперСемь, Подушка безопасности, Мои условия онлайн) → "Продукты - Вклады" → название продукта
   - Валюта указана (доллары, евро, юани, рубли) → "Продукты - Вклады" → соответствующая валюта
   - Слова "онлайн", "через приложение", "через интернет-банк" → "Продукты - Вклады" → "Рублевые - Мои условия онлайн"
   - Общий вопрос про ставки/проценты БЕЗ упоминания конкретного продукта → "Продукты - Вклады" → "Рублевые - Мои условия"
   - Примеры: "Какая процентная ставка?", "Какие проценты?", "Сколько начисляют?" → "Рублевые - Мои условия"
   - ВАЖНО: "Великий путь", "СуперСемь", "Подушка безопасности" используй ТОЛЬКО при явном упоминании названия
   - Вопросы про досрочное закрытие, регламент, оформление без посещения офиса → "Частные клиенты" → "Вклады и депозиты"

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

ДИЗАМБИГАЦИЯ БЛИЗКИХ ПОДКАТЕГОРИЙ:
- "Рублевые - Мои условия онлайн" выбирай при словах "онлайн", "через приложение", "интернет-банк". Без этих маркеров про ставки → "Рублевые - Мои условия".
- Общие вопросы про пополнение, досрочное закрытие или регламенты без названия продукта → "Частные клиенты" → "Вклады и депозиты".
- Первый вход и настройка приложений → "Новые клиенты" → "Первые шаги"; регистрация и идентификация через МСИ → "Регистрация и онбординг".
- "Онлайн кредиты - Проще в онлайн" реагирует на "онлайн кредит", "без визита", "проще в онлайн"; без явного названия и про политику банка → "Частные клиенты" → "Кредиты".
- Ошибки доступа, заблокированные пароли и технические сбои → "Техническая поддержка" → "Проблемы и решения"; навигация и функционал без сбоев → "Частные клиенты" → "Онлайн-сервисы".

ФОРМАТ ОТВЕТА (JSON):
{{
  "category": "название категории из списка",
  "subcategory": "название подкатегории из списка",
  "confidence": 0.95
}}

ПРИМЕРЫ:
{sample_snippets}
... и другие примеры по всем подкатегориям.

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

    def _format_keyword_map(self) -> str:
        """
        Format keyword hints grouped per category for inclusion in the prompt.
        """
        lines = []
        keyword_order = [
            "Новые клиенты",
            "Техническая поддержка",
            "Продукты - Вклады",
            "Продукты - Карты",
            "Продукты - Кредиты",
            "Частные клиенты"
        ]

        for category in keyword_order:
            scoped_subcats = [
                (subcategory, meta)
                for subcategory, meta in self.SUBCATEGORY_GUIDE.items()
                if meta["category"] == category
            ]
            if not scoped_subcats:
                continue
            lines.append(f"\n{category}")
            for subcategory, meta in scoped_subcats:
                keywords = ", ".join(meta["keywords"])
                lines.append(f"  - {subcategory}: {keywords}")

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
