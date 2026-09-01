import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from psycopg import AsyncConnection

from app.infrastructure.database.repositories.reminder import (
    set_reminder,
    disable_reminder,
    get_reminder,
)
from app.infrastructure.database.repositories.transaction import ensure_user

router = Router(name="reminders")


@router.message(Command("remind"))
async def process_remind_command(message: Message, conn: AsyncConnection) -> None:
    """
    /remind on 21:00  — включить
    /remind off       — выключить
    /remind           — статус
    """
    args = message.text.split()

    await ensure_user(
        conn,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    # /remind  → статус
    if len(args) == 1:
        reminder = await get_reminder(conn, message.from_user.id)
        if reminder and reminder["enabled"]:
            await message.answer(
                f"Напоминание включено на <b>{reminder['time_str']}</b>\n"
                "Выключить: <code>/remind off</code>"
            )
        else:
            await message.answer(
                "Напоминание выключено.\n"
                "Включить: <code>/remind on 21:00</code>"
            )
        return

    action = args[1].lower()

    # /remind off
    if action == "off":
        disabled = await disable_reminder(conn, message.from_user.id)
        if disabled:
            await message.answer("Напоминание выключено.")
        else:
            await message.answer("У тебя не было активного напоминания.")
        return

    # /remind on 21:00
    if action == "on":
        if len(args) < 3:
            await message.answer(
                "Укажи время:\n"
                "<code>/remind on 21:00</code>"
            )
            return

        time_str = args[2]
        if not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", time_str):
            await message.answer(
                "Неверный формат времени. Используй ЧЧ:ММ\n"
                "Пример: <code>/remind on 21:00</code>"
            )
            return

        # Нормализуем до HH:MM
        h, m = time_str.split(":")
        time_str = f"{int(h):02d}:{m}"

        await set_reminder(conn, message.from_user.id, time_str)
        await message.answer(
            f"Напоминание включено на <b>{time_str}</b> каждый день.\n"
            "Выключить: <code>/remind off</code>"
        )
        return

    await message.answer(
        "Использование:\n"
        "• <code>/remind on 21:00</code> — включить\n"
        "• <code>/remind off</code> — выключить\n"
        "• <code>/remind</code> — статус"
    )
