from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from psycopg import AsyncConnection

from app.bot.config import Config
from app.bot.services.yookassa import create_sbp_payment, get_payment
from app.infrastructure.database.repositories.transaction import ensure_user
from app.infrastructure.database.repositories.access import (
    has_active_premium,
    get_premium_until,
    grant_premium_days,
    get_user_subscriptions,
)

router = Router(name="pay")

SUB_PRICE_RUB = 369
SUB_DAYS = 30


def _pay_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Карта в Telegram", callback_data="pay_card")],
            [InlineKeyboardButton(text="🏦 СБП", callback_data="pay_sbp")],
        ]
    )


@router.message(Command("pay"))
async def process_pay_command(
    message: Message,
    conn: AsyncConnection,
    config: Config,
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

    await message.answer(
        f"Подписка на {SUB_DAYS} дней — <b>{SUB_PRICE_RUB} ₽</b>\n\n"
        "Выбери способ оплаты:",
        reply_markup=_pay_keyboard(),
    )


@router.callback_query(F.data == "pay_card")
async def process_pay_card(
    callback: CallbackQuery,
    config: Config,
    bot: Bot,
) -> None:
    if not config.bot.provider_token:
        await callback.answer("Оплата картой пока не настроена", show_alert=True)
        return

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Подписка на бота",
        description=f"Доступ ко всем функциям на {SUB_DAYS} дней",
        payload=f"sub_{SUB_DAYS}d",
        provider_token=config.bot.provider_token,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка", amount=SUB_PRICE_RUB * 100)],
    )
    await callback.answer()


@router.callback_query(F.data == "pay_sbp")
async def process_pay_sbp(
    callback: CallbackQuery,
    conn: AsyncConnection,
    config: Config,
    bot: Bot,
) -> None:
    if not config.bot.yookassa_shop_id or not config.bot.yookassa_secret_key:
        await callback.answer("СБП пока не настроена", show_alert=True)
        return

    await ensure_user(
        conn,
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    me = await bot.me()
    return_url = f"https://t.me/{me.username}"

    try:
        payment = await create_sbp_payment(
            config=config,
            user_id=callback.from_user.id,
            amount_rub=SUB_PRICE_RUB,
            description=f"Подписка на {SUB_DAYS} дней",
            return_url=return_url,
        )
    except Exception:
        await callback.message.answer("Не получилось создать платёж СБП. Попробуй позже.")
        await callback.answer()
        return

    payment_id = payment.get("id")
    confirmation = payment.get("confirmation") or {}
    url = confirmation.get("confirmation_url")

    if not payment_id or not url:
        await callback.message.answer("ЮKassa не вернула ссылку на оплату.")
        await callback.answer()
        return

    await conn.execute(
        """
        INSERT INTO payments (payment_id, user_id, status, amount)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (payment_id) DO NOTHING
        """,
        (payment_id, callback.from_user.id, payment.get("status", "pending"), SUB_PRICE_RUB),
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть СБП", url=url)],
            [InlineKeyboardButton(text="Я оплатил", callback_data=f"sbp_check:{payment_id}")],
        ]
    )
    await callback.message.answer(
        "Оплата через СБП.\n"
        "Нажми кнопку, оплати, затем вернись и нажми «Я оплатил».",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sbp_check:"))
async def process_sbp_check(
    callback: CallbackQuery,
    conn: AsyncConnection,
    config: Config,
) -> None:
    payment_id = callback.data.split(":", 1)[1]
    try:
        payment = await get_payment(config, payment_id)
    except Exception:
        await callback.answer("Не удалось проверить платёж", show_alert=True)
        return

    status = payment.get("status")
    await conn.execute(
        "UPDATE payments SET status = %s WHERE payment_id = %s",
        (status, payment_id),
    )

    if status == "succeeded":
        until = await grant_premium_days(
            conn,
            callback.from_user.id,
            SUB_DAYS,
            source="sbp",
        )
        await callback.message.answer(
            "Оплата СБП прошла успешно!\n"
            f"Подписка активна до <b>{until.strftime('%d.%m.%Y')}</b>."
        )
        await callback.answer()
        return

    if status in {"pending", "waiting_for_capture"}:
        await callback.answer("Платёж ещё не поступил. Подожди минуту и нажми снова.", show_alert=True)
        return

    await callback.answer(f"Статус платежа: {status}", show_alert=True)


@router.message(Command("subscription"))
async def process_subscription_command(
    message: Message,
    conn: AsyncConnection,
    config: Config,
) -> None:
    if message.from_user.id in config.bot.admin_ids:
        await message.answer("У администратора полный доступ без оплаты.")
        return

    from datetime import datetime
    until = await get_premium_until(conn, message.from_user.id)
    active = until is not None and until > datetime.now()

    if not active:
        await message.answer("Подписка не активна.\nОформить: /pay")
        return

    history = await get_user_subscriptions(conn, message.from_user.id)
    lines = [f"Подписка активна до <b>{until.strftime('%d.%m.%Y %H:%M')}</b>"]
    if history:
        lines.append("\n<b>История:</b>")
        for item in history[:5]:
            status = "✅" if item["is_active"] else "❌"
            lines.append(
                f"{status} {item['starts_at'].strftime('%d.%m.%Y')} — "
                f"{item['expires_at'].strftime('%d.%m.%Y')}"
            )
    await message.answer("\n".join(lines))


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
    until = await grant_premium_days(conn, message.from_user.id, SUB_DAYS, source="payment")
    await message.answer(
        "Оплата прошла успешно!\n\n"
        f"Подписка активна до <b>{until.strftime('%d.%m.%Y')}</b>."
    )
