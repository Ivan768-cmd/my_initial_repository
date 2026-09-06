import uuid
from typing import Any

import aiohttp

from app.bot.config import Config


async def create_sbp_payment(
    config: Config,
    user_id: int,
    amount_rub: int,
    description: str,
    return_url: str,
) -> dict[str, Any]:
    if not config.bot.yookassa_shop_id or not config.bot.yookassa_secret_key:
        raise RuntimeError("YooKassa keys are not configured")

    payload = {
        "amount": {
            "value": f"{amount_rub:.2f}",
            "currency": "RUB",
        },
        "capture": True,
        "description": description,
        "payment_method_data": {"type": "sbp"},
        "confirmation": {
            "type": "redirect",
            "return_url": return_url,
        },
        "metadata": {
            "user_id": str(user_id),
            "purpose": "subscription",
        },
    }

    auth = aiohttp.BasicAuth(
        config.bot.yookassa_shop_id,
        config.bot.yookassa_secret_key,
    )
    headers = {
        "Content-Type": "application/json",
        "Idempotence-Key": str(uuid.uuid4()),
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.yookassa.ru/v3/payments",
            json=payload,
            headers=headers,
            auth=auth,
        ) as response:
            data = await response.json()
            if response.status >= 400:
                raise RuntimeError(str(data))
            return data


async def get_payment(config: Config, payment_id: str) -> dict[str, Any]:
    auth = aiohttp.BasicAuth(
        config.bot.yookassa_shop_id,
        config.bot.yookassa_secret_key,
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.yookassa.ru/v3/payments/{payment_id}",
            auth=auth,
        ) as response:
            data = await response.json()
            if response.status >= 400:
                raise RuntimeError(str(data))
            return data
