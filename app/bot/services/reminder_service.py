import logging
from datetime import datetime

from aiogram import Bot
from psycopg_pool import AsyncConnectionPool

from app.infrastructure.database.repositories.reminder import get_enabled_reminders

logger = logging.getLogger(__name__)


async def send_daily_reminders(bot: Bot, pool: AsyncConnectionPool) -> None:
    """Проверяет текущее время и отправляет напоминания нужным пользователям."""
    now = datetime.now().strftime("%H:%M")

    try:
        async with pool.connection() as conn:
            reminders = await get_enabled_reminders(conn)

        for item in reminders:
            if item["time_str"] == now:
                try:
                    await bot.send_message(
                        chat_id=item["user_id"],
                        text=(
                            "📝 Напоминание\n\n"
                            "Не забудь записать расходы за сегодня.\n"
                            "Просто напиши, например: <code>Такси 300</code>"
                        )
                    )
                    logger.info("Reminder sent to user %s", item["user_id"])
                except Exception as e:
                    logger.warning("Failed to send reminder to %s: %s", item["user_id"], e)
    except Exception as e:
        logger.exception("Error in send_daily_reminders: %s", e)
