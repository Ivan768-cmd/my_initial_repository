from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject, PreCheckoutQuery, Update
from psycopg import AsyncConnection

from app.bot.config import Config
from app.infrastructure.database.repositories.access import has_active_premium


ALLOWED_COMMANDS = {"/start", "/pay", "/help", "/subscription", "/privacy"}


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        config: Config = data["config"]
        conn: AsyncConnection | None = data.get("conn")

        message: Message | None = None
        callback: CallbackQuery | None = None
        pre_checkout: PreCheckoutQuery | None = None

        if isinstance(event, Update):
            message = event.message
            callback = event.callback_query
            pre_checkout = event.pre_checkout_query
        elif isinstance(event, Message):
            message = event
        elif isinstance(event, CallbackQuery):
            callback = event
        elif isinstance(event, PreCheckoutQuery):
            pre_checkout = event

        user = None
        if message and message.from_user:
            user = message.from_user
        elif callback and callback.from_user:
            user = callback.from_user
        elif pre_checkout and pre_checkout.from_user:
            user = pre_checkout.from_user

        if user is None:
            return await handler(event, data)

        if user.id in config.bot.admin_ids:
            return await handler(event, data)

        if pre_checkout is not None:
            return await handler(event, data)

        if message and message.successful_payment:
            return await handler(event, data)

        if message and message.text:
            command = message.text.split()[0].split("@")[0]
            if command in ALLOWED_COMMANDS:
                return await handler(event, data)

        if callback and callback.data:
            if callback.data in {"pay_card", "pay_sbp"} or callback.data.startswith("sbp_check:"):
                return await handler(event, data)

        if conn is not None and await has_active_premium(conn, user.id):
            return await handler(event, data)

        text = (
            "Доступ к боту открывается после оплаты подписки.\n\n"
            "Оформить: /pay"
        )

        if message:
            await message.answer(text)
        elif callback:
            await callback.answer("Сначала оплати подписку: /pay", show_alert=True)

        return None
