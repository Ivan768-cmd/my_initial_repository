from collections import defaultdict
from datetime import datetime, timedelta

from psycopg import AsyncConnection


async def _fetch_transactions(
    conn: AsyncConnection,
    user_id: int,
    start: datetime,
    end: datetime,
) -> list[dict]:
    rows = await conn.execute(
        """
        SELECT amount, category, is_income, comment, created_at
        FROM transactions
        WHERE user_id = %s
          AND created_at >= %s
          AND created_at < %s
        ORDER BY created_at
        """,
        (user_id, start, end),
    )
    result = await rows.fetchall()
    return [
        {
            "amount": float(r[0]),
            "category": r[1],
            "is_income": r[2],
            "comment": r[3],
            "created_at": r[4],
        }
        for r in result
    ]


async def _fetch_subs_total(conn: AsyncConnection, user_id: int) -> float:
    row = await conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM subscriptions
        WHERE user_id = %s
        """,
        (user_id,),
    )
    result = await row.fetchone()
    return float(result[0]) if result else 0.0


def _summarize(transactions: list[dict]) -> dict:
    income = 0.0
    expense = 0.0
    by_category: dict[str, float] = defaultdict(float)
    small_counts: dict[str, int] = defaultdict(int)

    for t in transactions:
        if t["is_income"]:
            income += t["amount"]
        else:
            expense += t["amount"]
            by_category[t["category"]] += t["amount"]
            if t["amount"] <= 300:
                small_counts[t["category"]] += 1

    return {
        "income": income,
        "expense": expense,
        "balance": income - expense,
        "by_category": dict(by_category),
        "small_counts": dict(small_counts),
        "count": len(transactions),
    }


def _percent(part: float, whole: float) -> int:
    if whole <= 0:
        return 0
    return int(round(part / whole * 100))


def _progress_compare(current: float, previous: float) -> str:
    if previous <= 0:
        return "нет данных за прошлый период"
    diff = current - previous
    pct = abs(diff) / previous * 100
    if diff > 0:
        return f"больше на {diff:,.0f} ₽ ({pct:.0f}%)"
    if diff < 0:
        return f"меньше на {abs(diff):,.0f} ₽ ({pct:.0f}%)"
    return "без изменений"


async def build_period_report(
    conn: AsyncConnection,
    user_id: int,
    days: int,
    title: str,
) -> str:
    now = datetime.now()
    start = now - timedelta(days=days)
    prev_start = start - timedelta(days=days)

    current_tx = await _fetch_transactions(conn, user_id, start, now)
    prev_tx = await _fetch_transactions(conn, user_id, prev_start, start)

    current = _summarize(current_tx)
    previous = _summarize(prev_tx)
    subs_total = await _fetch_subs_total(conn, user_id)

    if current["count"] == 0:
        return f"{title}\n\nЗа этот период записей нет."

    lines = [f"<b>{title}</b>\n"]
    lines.append(f"Доходы: <b>+{current['income']:,.0f} ₽</b>")
    lines.append(f"Расходы: <b>−{current['expense']:,.0f} ₽</b>")
    lines.append(f"Итого: <b>{current['balance']:,.0f} ₽</b>")

    if current["by_category"]:
        lines.append("\n<b>Структура расходов:</b>")
        items = sorted(current["by_category"].items(), key=lambda x: -x[1])
        for category, amount in items[:8]:
            pct = _percent(amount, current["expense"])
            lines.append(f"• {category}: {amount:,.0f} ₽ ({pct}%)")

    lines.append("\n<b>Сравнение с прошлым периодом:</b>")
    lines.append(f"Расходы: {_progress_compare(current['expense'], previous['expense'])}")
    lines.append(f"Доходы: {_progress_compare(current['income'], previous['income'])}")

    leaks = []
    for category, count in current["small_counts"].items():
        if count >= 4:
            amount = current["by_category"].get(category, 0)
            leaks.append(f"• {category}: {count} мелких трат на {amount:,.0f} ₽")

    if subs_total > 0:
        leaks.append(f"• Подписки: {subs_total:,.0f} ₽ в месяц")

    lines.append("\n<b>Возможные утечки:</b>")
    if leaks:
        lines.extend(leaks)
    else:
        lines.append("Явных мелких утечек не видно.")

    lines.append("\n<b>Рекомендации:</b>")
    if current["expense"] > current["income"] and current["income"] > 0:
        lines.append("• Расходы выше доходов — стоит урезать 1–2 крупные категории.")
    if leaks:
        lines.append("• Проверь регулярные мелкие траты: их легко не заметить.")
    if subs_total > 0 and current["expense"] > 0 and subs_total / current["expense"] > 0.15:
        lines.append("• Подписки занимают заметную долю бюджета. Какие из них реально нужны?")
    if current["expense"] <= current["income"]:
        lines.append("• Запас есть. Можно заранее откладывать фиксированную сумму в цель.")
    lines.append("• Это не инвестиционный совет, только разбор твоих трат.")

    return "\n".join(lines)


async def build_month_forecast(conn: AsyncConnection, user_id: int) -> str:
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)

    days_passed = max((now - month_start).days, 1)
    days_in_month = (next_month - month_start).days
    days_left = max(days_in_month - days_passed, 0)

    tx = await _fetch_transactions(conn, user_id, month_start, now)
    summary = _summarize(tx)

    if summary["count"] == 0:
        return "За этот месяц записей пока нет. Прогноз появится после первых трат."

    daily_expense = summary["expense"] / days_passed
    daily_income = summary["income"] / days_passed
    forecast_expense = daily_expense * days_in_month
    forecast_income = daily_income * days_in_month
    forecast_left = forecast_income - forecast_expense

    text = (
        "<b>Прогноз до конца месяца</b>\n\n"
        f"Прошло дней: {days_passed} из {days_in_month}\n"
        f"Уже потрачено: {summary['expense']:,.0f} ₽\n"
        f"Уже получено: {summary['income']:,.0f} ₽\n\n"
        f"Средний расход в день: {daily_expense:,.0f} ₽\n"
        f"Прогноз расходов за месяц: <b>{forecast_expense:,.0f} ₽</b>\n"
        f"Прогноз доходов за месяц: <b>{forecast_income:,.0f} ₽</b>\n"
        f"Ожидаемый остаток: <b>{forecast_left:,.0f} ₽</b>\n"
    )

    if days_left == 0:
        text += "\nМесяц уже заканчивается."
    elif forecast_left < 0:
        text += "\nЕсли темп сохранится, к концу месяца будет минус. Имеет смысл снизить дневные траты."
    else:
        text += f"\nЕсли тратить не больше {daily_expense:,.0f} ₽ в день, запас должен остаться."

    return text


async def build_habits_report(conn: AsyncConnection, user_id: int) -> str:
    now = datetime.now()
    start = now - timedelta(days=30)
    tx = await _fetch_transactions(conn, user_id, start, now)
    expenses = [t for t in tx if not t["is_income"]]

    if not expenses:
        return "За 30 дней расходов нет — анализировать привычки пока нечего."

    weekend = defaultdict(float)
    weekday = defaultdict(float)
    total_weekend = 0.0
    total_weekday = 0.0

    for t in expenses:
        if t["created_at"].weekday() >= 5:
            weekend[t["category"]] += t["amount"]
            total_weekend += t["amount"]
        else:
            weekday[t["category"]] += t["amount"]
            total_weekday += t["amount"]

    lines = ["<b>Привычки за 30 дней</b>\n"]
    lines.append(f"Будни: {total_weekday:,.0f} ₽")
    lines.append(f"Выходные: {total_weekend:,.0f} ₽")

    insights = []
    categories = set(weekend) | set(weekday)
    for category in categories:
        w = weekend.get(category, 0.0)
        d = weekday.get(category, 0.0)
        if d > 0 and w > d * 1.3:
            pct = int((w / d - 1) * 100)
            insights.append(
                f"• На «{category}» в выходные уходит на {pct}% больше, чем в будни."
            )
        elif w > 0 and d > w * 1.3:
            pct = int((d / w - 1) * 100)
            insights.append(
                f"• На «{category}» в будни уходит на {pct}% больше, чем в выходные."
            )

    if total_weekday > 0 and total_weekend > total_weekday * 0.6:
        insights.append("• Выходные заметно разгоняют общие расходы.")

    lines.append("\n<b>Что видно:</b>")
    if insights:
        lines.extend(insights[:6])
    else:
        lines.append("Явных перекосов по дням недели пока нет.")

    return "\n".join(lines)
