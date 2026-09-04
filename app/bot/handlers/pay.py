from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    LabeledPrice,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from psycopg import AsyncConnection

from app.bot.config import Config
from app.infrastructure.database.repositories.transaction import ensure_user
from app.infrastructure.database.repositories.access import (
    has_active_premium,
    get_premium_until,
    grant_premium_days,
)

router = Router(name="pay")

SUB_PRICE_RUB = 199
SUB_DAYS = 30


@router.message(Command("pay"))
async def process_pay_command(
    message: Message,
    conn: AsyncConnection,
    config: Config,
    bot: Bot,
) -> None:
    await ensure_user(
        conn,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if message.from_user.id in config.bot.admin_ids:
        await message.answer("У администратора полный доступ без оплаты.")
        return

    if await has_active_premium(conn, message.from_user.id):
        until = await get_premium_until(conn, message.from_user.id)
        until_str = until.strftime("%d.%m.%Y") if until else "—"
        await message.answer(f"Подписка уже активна до <b>{until_str}</b>.")
        return

    if not config.bot.provider_token:
        await message.answer(
            "Оплата пока подключается.\n"
            "Когда ЮKassa будет готова, здесь появится кнопка оплаты.\n\n"
            f"Планируемая цена: <b>{SUB_PRICE_RUB} ₽</b> за {SUB_DAYS} дней."
        )
        return

    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Подписка на бота",
        description=f"Доступ ко всем функциям на {SUB_DAYS} дней",
        payload=f"sub_{SUB_DAYS}d",
        provider_token=config.bot.provider_token,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка", amount=SUB_PRICE_RUB * 100)],
    )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
    conn: AsyncConnection,
) -> None:
    await ensure_user(
        conn,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    until = await grant_premium_days(conn, message.from_user.id, SUB_DAYS)
    await message.answer(
        "Оплата прошла успешно!\n\n"
        f"Подписка активна до <b>{until.strftime('%d.%m.%Y')}</b>.\n"
        "Можешь пользоваться ботом."
    )
