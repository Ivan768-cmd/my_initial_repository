import re
from dataclasses import dataclass


@dataclass
class ParsedTransaction:
    amount: float
    category: str
    is_income: bool = False
    comment: str | None = None


INCOME_KEYWORDS = {
    "зарплата", "зарп", "зп", "доход", "подработка",
    "аванс", "премия", "перевод", "кэшбек", "кэшбэк",
    "возврат", "дивиденды", "проценты"
}


def parse_transaction(text: str) -> ParsedTransaction | None:
    """
    Поддерживает форматы:
    - Такси 450
    - 450 такси
    - такси -450
    - 450р продукты
    - Кофе 280 #работа
    - Магнит продукты 1200
    - Зарплата 85000
    """
    original = text.strip()
    if not original:
        return None

    comment = None
    comment_match = re.search(r"#(\w+)", original)
    if comment_match:
        comment = comment_match.group(1)
        original = original.replace(comment_match.group(0), "").strip()

    amount_match = re.search(
        r"(-?\s*\d+[.,]?\d*)\s*(?:р|руб|₽)?",
        original,
        re.IGNORECASE
    )
    if not amount_match:
        return None

    amount_str = amount_match.group(1).replace(" ", "").replace(",", ".")
    try:
        amount = abs(float(amount_str))
    except ValueError:
        return None

    if amount <= 0:
        return None

    category_part = (
        original[:amount_match.start()] + original[amount_match.end():]
    ).strip()

    category_part = re.sub(r"[+\-–—]", " ", category_part)
    category_part = re.sub(r"\s+", " ", category_part).strip()

    category = category_part if category_part else "Без категории"
    category = category.capitalize()

    is_income = any(
        keyword in category.lower() for keyword in INCOME_KEYWORDS
    )

    if is_income:
        category = "Доход"

    return ParsedTransaction(
        amount=amount,
        category=category,
        is_income=is_income,
        comment=comment
    )
