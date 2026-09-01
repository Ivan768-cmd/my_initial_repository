from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from psycopg import AsyncConnection

from app.bot.services.parser import parse_transaction
from app.bot.keyboards.inline import get_transaction_keyboard
from app.infrastructure.database.repositories.transaction import (
    ensure_user,
    add_transaction,
    get_user_balance,
    delete_last_transaction,
    delete_transaction_by_id,
    get_category_spent,
)
from app.infrastructure.database.repositories.budget import get_limit

router = Router(name="expenses")


@router.message(F.text)
async def process_transaction_message(
    message: Message,
    conn: AsyncConnection
) -> None:
    parsed = parse_transaction(message.text)

    if parsed is None:
        await message.answer(
            "Не понял сообщение.\n\n"
            "Напиши в формате:\n"
            "• <code>Такси 450</code>\n"
            "• <code>Продукты 3200</code>\n"
            "• <code>Кофе 280 #работа</code>"
        )
        return

    await ensure_user(
        conn,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    await add_transaction(
        conn,
        user_id=message.from_user.id,
        amount=parsed.amount,
        category=parsed.category,
        is_income=parsed.is_income,
        comment=parsed.comment
    )

    transaction_type = "Доход" if parsed.is_income else "Расход"
    comment_text = f"\nКомментарий: #{parsed.comment}" if parsed.comment else ""
    balance = await get_user_balance(conn, message.from_user.id)

    # Проверяем лимит (только для расходов)
    limit_warning = ""
    if not parsed.is_income:
        limit = await get_limit(conn, message.from_user.id, parsed.category)
        if limit is not None:
            spent = await get_category_spent(conn, message.from_user.id, parsed.category)
            percent = int(spent / limit * 100) if limit > 0 else 0
            remaining = limit - spent

            if percent >= 100:
                limit_warning = (
                    f"\n\n🚨 <b>Лимит превышен!</b>\n"
                    f"Категория «{parsed.category}»: "
                    f"потрачено {spent:,.0f} из {limit:,.0f} ₽"
                )
            elif percent >= 80:
                limit_warning = (
                    f"\n\n⚠️ <b>Внимание:</b> использовано {percent}% лимита\n"
                    f"Категория «{parsed.category}»: "
                    f"осталось {remaining:,.0f} ₽"
                )

    await message.answer(
        f"<b>{transaction_type} записан</b>\n\n"
        f"Категория: <b>{parsed.category}</b>\n"
        f"Сумма: <b>{parsed.amount:,.0f} ₽</b>"
        f"{comment_text}\n\n"
        f"Текущий баланс: <b>{balance:,.0f} ₽</b>"
        f"{limit_warning}",
        reply_markup=get_transaction_keyboard()
    )


@router.callback_query(F.data == "delete_last")
async def process_delete_last_callback(
    callback: CallbackQuery,
    conn: AsyncConnection
) -> None:
    deleted = await delete_last_transaction(conn, callback.from_user.id)

    if deleted is None:
        await callback.answer("Нечего удалять", show_alert=True)
        return

    sign = "+" if deleted["is_income"] else "-"
    comment = f" #{deleted['comment']}" if deleted["comment"] else ""
    balance = await get_user_balance(conn, callback.from_user.id)

    await callback.message.edit_text(
        f"Удалена запись:\n"
        f"{sign}{deleted['amount']:,.0f} ₽ — {deleted['category']}{comment}\n\n"
        f"Текущий баланс: <b>{balance:,.0f} ₽</b>"
    )
    await callback.answer()


@router.callback_query(F.data == "show_balance")
async def process_show_balance_callback(
    callback: CallbackQuery,
    conn: AsyncConnection
) -> None:
    balance = await get_user_balance(conn, callback.from_user.id)
    await callback.answer(
        f"Текущий баланс: {balance:,.0f} ₽",
        show_alert=True
    )


@router.callback_query(F.data.startswith("del_tx:"))
async def process_delete_tx_callback(
    callback: CallbackQuery,
    conn: AsyncConnection
) -> None:
    tx_id = int(callback.data.split(":")[1])
    deleted = await delete_transaction_by_id(conn, callback.from_user.id, tx_id)

    if deleted is None:
        await callback.answer("Запись уже удалена", show_alert=True)
        return

    sign = "+" if deleted["is_income"] else "-"
    comment = f" #{deleted['comment']}" if deleted["comment"] else ""
    balance = await get_user_balance(conn, callback.from_user.id)

    await callback.message.edit_text(
        f"Удалена запись:\n"
        f"{sign}{deleted['amount']:,.0f} ₽ — {deleted['category']}{comment}\n\n"
        f"Текущий баланс: <b>{balance:,.0f} ₽</b>"
    )
    await callback.answer()
