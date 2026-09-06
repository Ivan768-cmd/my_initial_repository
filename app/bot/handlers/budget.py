from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from psycopg import AsyncConnection

from app.infrastructure.database.repositories.budget import (
    set_limit,
    get_all_limits,
    set_monthly_income,
    get_monthly_income,
    set_budget_item,
    get_budget_items,
    get_month_spent_by_category,
    get_last_month_expense_share,
)
from app.infrastructure.database.repositories.transaction import (
    get_category_spent,
    ensure_user,
)

router = Router(name="budget")

DEFAULT_PLAN = {
    "Продукты": 0.30,
    "Транспорт": 0.15,
    "Кафе": 0.10,
    "Подписки": 0.10,
    "Другое": 0.35,
}


def _bar(percent: int) -> str:
    filled = min(10, max(0, percent // 10))
    return "█" * filled + "░" * (10 - filled)


@router.message(Command("set_income"))
async def process_set_income(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование:\n<code>/set_income 80000</code>")
        return

    try:
        income = float(args[1].replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return

    if income <= 0:
        await message.answer("Доход должен быть больше нуля.")
        return

    await ensure_user(
        conn,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await set_monthly_income(conn, message.from_user.id, income)

    shares = await get_last_month_expense_share(conn, message.from_user.id)
    plan = shares if shares else DEFAULT_PLAN

    lines = [f"Доход на месяц: <b>{income:,.0f} ₽</b>\n", "<b>Предлагаю распределение:</b>"]
    for category, share in sorted(plan.items(), key=lambda x: -x[1]):
        amount = round(income * share)
        await set_budget_item(conn, message.from_user.id, category, amount)
        lines.append(f"• {category}: {amount:,.0f} ₽ ({int(share * 100)}%)")

    lines.append("\nИзменить категорию: <code>/plan Такси 5000</code>")
    lines.append("Смотреть прогресс: /budget")
    await message.answer("\n".join(lines))


@router.message(Command("plan"))
async def process_plan(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Использование:\n<code>/plan Продукты 25000</code>")
        return

    category = args[1]
    try:
        amount = float(args[2].replace(",", "."))
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return

    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return

    await ensure_user(
        conn,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await set_budget_item(conn, message.from_user.id, category, amount)
    await message.answer(
        f"В бюджете «<b>{category.capitalize()}</b>»: <b>{amount:,.0f} ₽</b>\n"
        "Смотреть прогресс: /budget"
    )


@router.message(Command("budget"))
@router.message(F.text == "📋 Лимиты")
async def process_budget(message: Message, conn: AsyncConnection) -> None:
    income = await get_monthly_income(conn, message.from_user.id)
    items = await get_budget_items(conn, message.from_user.id)

    if income is None and not items:
        await message.answer(
            "Бюджет ещё не задан.\n\n"
            "Сначала укажи доход:\n"
            "<code>/set_income 80000</code>"
        )
        return

    spent_map = await get_month_spent_by_category(conn, message.from_user.id)
    lines = ["<b>Бюджет на месяц</b>\n"]
    if income is not None:
        lines.append(f"Доход: <b>{income:,.0f} ₽</b>\n")

    if not items:
        lines.append("Категории не заданы. Используй /set_income или /plan")
        await message.answer("\n".join(lines))
        return

    total_plan = 0.0
    total_spent = 0.0
    for category, planned in items.items():
        spent = spent_map.get(category, 0.0)
        percent = min(100, int(spent / planned * 100)) if planned > 0 else 0
        status = "🚨" if percent >= 100 else ("⚠️" if percent >= 80 else "✅")
        lines.append(
            f"{status} <b>{category}</b>\n"
            f"   {_bar(percent)} {percent}%\n"
            f"   {spent:,.0f} / {planned:,.0f} ₽"
        )
        total_plan += planned
        total_spent += spent

    lines.append(f"\nВсего по плану: {total_spent:,.0f} / {total_plan:,.0f} ₽")
    await message.answer("\n".join(lines))


@router.message(Command("set_limit"))
async def process_set_limit_command(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Использование:\n<code>/set_limit Такси 3000</code>")
        return

    category = args[1]
    try:
        limit = float(args[2].replace(",", "."))
    except ValueError:
        await message.answer("Сумма лимита должна быть числом.")
        return

    if limit <= 0:
        await message.answer("Лимит должен быть больше нуля.")
        return

    await ensure_user(
        conn,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await set_limit(conn, message.from_user.id, category, limit)
    await message.answer(
        f"Лимит для <b>{category.capitalize()}</b>: <b>{limit:,.0f} ₽</b>"
    )


@router.message(Command("limits"))
async def process_limits_command(message: Message, conn: AsyncConnection) -> None:
    limits = await get_all_limits(conn, message.from_user.id)
    if not limits:
        await message.answer("Лимиты не установлены.\n<code>/set_limit Такси 3000</code>")
        return

    lines = ["<b>Лимиты:</b>\n"]
    for category, limit in sorted(limits.items()):
        spent = await get_category_spent(conn, message.from_user.id, category)
        percent = min(100, int(spent / limit * 100)) if limit > 0 else 0
        lines.append(f"{category}: {spent:,.0f} / {limit:,.0f} ₽ ({percent}%)")
    await message.answer("\n".join(lines))
