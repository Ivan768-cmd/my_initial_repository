from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from psycopg_pool import AsyncConnectionPool


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.pool = pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.pool.connection() as connection:
            async with connection.transaction():
                data["conn"] = connection
                return await handler(event, data)
