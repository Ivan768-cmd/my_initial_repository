import asyncio
import logging

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from psycopg import AsyncConnection

from app.bot.config import Config
from app.infrastructure.database.repositories.user import get_all_user_ids

router = Router(name="broadcast")
logger = logging.getLogger(__name__)


@router.message(Command("broadcast"))
async def process_broadcast(
    message: Message,
    conn: AsyncConnection,
    config: Config,
    bot: Bot,
) -> None:
    if message.from_user.id not in config.bot.admin_ids:
        await message.answer("Команда только для администратора.")
        return

    text = message.text.split(maxsplit=1)
    if len(text) < 2 or not text[1].strip():
        await message.answer(
            "Использование:\n"
            "<code>/broadcast Текст сообщения code>"
        )
        return

    body = text[1].strip()
    user_ids = await get_all_user_ids(conn)

    if not user_ids:
        await message.answer("Пользователей пока нет.")
        return

    await message.answer(f"Начинаю рассылку для {len(user_ids)} пользователей...")

    ok = 0
    fail = 0

    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=body)
            ok += 1
        except Exception as e:
            fail += 1
            logger.warning("Broadcast failed for %s: %s", user_id, e)
        await asyncio.sleep(0.05)

    await message.answer(
        "Рассылка завершена.\n"
        f"Успешно: <b>{ok}</b>\n"
        f"Не доставлено: <b>{fail}</b>"
    )
