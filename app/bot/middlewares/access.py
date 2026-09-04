from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject, PreCheckoutQuery
from psycopg import AsyncConnection

from app.bot.config import Config
from app.infrastructure.database.repositories.access import has_active_premium


ALLOWED_COMMANDS = {"/start", "/pay", "/help", "/subscription"}


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        config: Config = data["config"]
        conn: AsyncConnection | None = data.get("conn")

        user = None
        if isinstance(event, (Message, CallbackQuery, PreCheckoutQuery)):
            user = event.from_user

        if user is None:
            return await handler(event, data)

        if user.id in config.bot.admin_ids:
            return await handler(event, data)

        if isinstance(event, PreCheckoutQuery):
            return await handler(event, data)

        if isinstance(event, Message) and event.successful_payment:
            return await handler(event, data)

        if isinstance(event, Message) and event.text:
            command = event.text.split()[0].split("@")[0]
            if command in ALLOWED_COMMANDS:
                return await handler(event, data)

        if conn is not None and await has_active_premium(conn, user.id):
            return await handler(event, data)

        text = (
            "Доступ к боту открывается после оплаты подписки.\n\n"
            "Оформить: /pay"
        )

        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer("Сначала оплати подписку: /pay", show_alert=True)

        return None
