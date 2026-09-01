from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from psycopg import AsyncConnection

from app.infrastructure.database.repositories.budget import (
    set_limit,
    get_all_limits,
)
from app.infrastructure.database.repositories.transaction import (
    get_category_spent,
    ensure_user,
)

router = Router(name="budget")


@router.message(Command("set_limit"))
async def process_set_limit_command(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Использование:\n"
            "<code>/set_limit Такси 3000</code>\n\n"
            "Устанавливает лимит на категорию."
        )
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
        first_name=message.from_user.first_name
    )

    await set_limit(conn, message.from_user.id, category, limit)

    await message.answer(
        f"Лимит для категории <b>{category.capitalize()}</b> "
        f"установлен: <b>{limit:,.0f} ₽</b>"
    )


@router.message(Command("limits"))
@router.message(F.text == "📋 Лимиты")
async def process_limits_command(message: Message, conn: AsyncConnection) -> None:
    limits = await get_all_limits(conn, message.from_user.id)

    if not limits:
        await message.answer(
            "Лимиты ещё не установлены.\n\n"
            "Чтобы установить, используй:\n"
            "<code>/set_limit Такси 3000</code>"
        )
        return

    lines = []
    for category, limit in sorted(limits.items()):
        spent = await get_category_spent(conn, message.from_user.id, category)
        remaining = limit - spent
        percent = min(100, int(spent / limit * 100)) if limit > 0 else 0

        status = "✅"
        if percent >= 100:
            status = "🚨"
        elif percent >= 80:
            status = "⚠️"

        lines.append(
            f"{status} <b>{category}</b>\n"
            f"   Потрачено: {spent:,.0f} из {limit:,.0f} ₽ ({percent}%)\n"
            f"   Осталось: {remaining:,.0f} ₽"
        )

    text = "<b>Твои лимиты:</b>\n\n" + "\n\n".join(lines)
    await message.answer(text)
