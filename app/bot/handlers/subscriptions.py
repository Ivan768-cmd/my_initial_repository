from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from psycopg import AsyncConnection

from app.infrastructure.database.repositories.subscription import (
    add_subscription,
    get_user_subscriptions,
    get_subscriptions_total,
    delete_subscription,
)
from app.infrastructure.database.repositories.transaction import ensure_user

router = Router(name="subscriptions")


@router.message(Command("add_sub"))
async def process_add_sub_command(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Использование:\n"
            "<code>/add_sub Netflix 799</code>\n\n"
            "Добавляет ежемесячную подписку."
        )
        return

    name = args[1]
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
        first_name=message.from_user.first_name
    )

    sub = await add_subscription(conn, message.from_user.id, name, amount)
    total = await get_subscriptions_total(conn, message.from_user.id)

    await message.answer(
        f"Подписка <b>{sub['name']}</b> добавлена: <b>{sub['amount']:,.0f} ₽/мес</b>\n\n"
        f"Всего на подписки: <b>{total:,.0f} ₽</b> в месяц"
    )


@router.message(Command("subs"))
async def process_subs_command(message: Message, conn: AsyncConnection) -> None:
    subs = await get_user_subscriptions(conn, message.from_user.id)

    if not subs:
        await message.answer(
            "Подписок пока нет.\n\n"
            "Добавить:\n"
            "<code>/add_sub Netflix 799</code>"
        )
        return

    lines = []
    for s in subs:
        lines.append(f"• <b>{s['name']}</b> — {s['amount']:,.0f} ₽/мес")

    total = await get_subscriptions_total(conn, message.from_user.id)

    text = (
        "<b>Твои подписки:</b>\n\n"
        + "\n".join(lines)
        + f"\n\n<b>Итого:</b> {total:,.0f} ₽ в месяц"
    )
    await message.answer(text)


@router.message(Command("del_sub"))
async def process_del_sub_command(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "<code>/del_sub Netflix</code>"
        )
        return

    name = args[1].strip()
    deleted = await delete_subscription(conn, message.from_user.id, name)

    if not deleted:
        await message.answer(f"Подписка «{name}» не найдена.")
        return

    total = await get_subscriptions_total(conn, message.from_user.id)
    await message.answer(
        f"Подписка <b>{name}</b> удалена.\n"
        f"Теперь на подписки: <b>{total:,.0f} ₽</b> в месяц"
    )
