from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from psycopg import AsyncConnection

from app.infrastructure.database.repositories.transaction import (
    get_user_balance,
    get_user_transactions,
    delete_last_transaction,
    get_stats_by_category,
    edit_last_amount,
    edit_last_category,
    get_period_summary,
)

router = Router(name="reports")


@router.message(Command("balance"))
@router.message(F.text == "💰 Баланс")
async def process_balance_command(message: Message, conn: AsyncConnection) -> None:
    balance = await get_user_balance(conn, message.from_user.id)
    await message.answer(f"Текущий баланс: <b>{balance:,.0f} ₽</b>")


@router.message(Command("history"))
@router.message(F.text == "📜 История")
async def process_history_command(message: Message, conn: AsyncConnection) -> None:
    transactions = await get_user_transactions(conn, message.from_user.id, limit=8)

    if not transactions:
        await message.answer("Пока нет ни одной записи.")
        return

    builder = InlineKeyboardBuilder()
    lines = []

    for t in transactions:
        sign = "🟢 +" if t["is_income"] else "🔴 −"
        comment = f" #{t['comment']}" if t["comment"] else ""
        date_str = t["created_at"].strftime("%d.%m %H:%M")

        lines.append(
            f"{sign}<b>{t['amount']:,.0f} ₽</b> — {t['category']}{comment}\n"
            f"   <i>{date_str}</i>"
        )

        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {t['category']} {t['amount']:,.0f}₽",
                callback_data=f"del_tx:{t['id']}"
            )
        )

    text = "<b>Последние операции:</b>\n\n" + "\n\n".join(lines)
    await message.answer(text, reply_markup=builder.as_markup())


@router.message(Command("delete_last"))
async def process_delete_last_command(message: Message, conn: AsyncConnection) -> None:
    deleted = await delete_last_transaction(conn, message.from_user.id)

    if deleted is None:
        await message.answer("Нечего удалять — записей нет.")
        return

    sign = "+" if deleted["is_income"] else "-"
    comment = f" #{deleted['comment']}" if deleted["comment"] else ""
    balance = await get_user_balance(conn, message.from_user.id)

    await message.answer(
        f"Удалена запись:\n"
        f"{sign}{deleted['amount']:,.0f} ₽ — {deleted['category']}{comment}\n\n"
        f"Текущий баланс: <b>{balance:,.0f} ₽</b>"
    )


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def process_stats_command(message: Message, conn: AsyncConnection) -> None:
    stats = await get_stats_by_category(conn, message.from_user.id)

    if not stats:
        await message.answer("Пока нет данных для статистики.")
        return

    lines = []
    total_expense = 0.0
    total_income = 0.0

    for category, data in sorted(stats.items()):
        expense = data["expense"]
        income = data["income"]
        total_expense += expense
        total_income += income

        if expense > 0 and income > 0:
            lines.append(f"• <b>{category}</b>: −{expense:,.0f} / +{income:,.0f} ₽")
        elif expense > 0:
            lines.append(f"• <b>{category}</b>: −{expense:,.0f} ₽")
        else:
            lines.append(f"• <b>{category}</b>: +{income:,.0f} ₽")

    text = (
        "<b>Статистика по категориям:</b>\n\n"
        + "\n".join(lines)
        + f"\n\n<b>Всего расходов:</b> {total_expense:,.0f} ₽"
        + f"\n<b>Всего доходов:</b> {total_income:,.0f} ₽"
    )
    await message.answer(text)


@router.message(Command("today"))
async def process_today_command(message: Message, conn: AsyncConnection) -> None:
    summary = await get_period_summary(conn, message.from_user.id, days=1)

    if summary["count"] == 0:
        await message.answer("За сегодня записей пока нет.")
        return

    lines = []
    for category, amount in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
        lines.append(f"• {category}: −{amount:,.0f} ₽")

    text = (
        "<b>Сводка за сегодня:</b>\n\n"
        f"Доходы: <b>+{summary['income']:,.0f} ₽</b>\n"
        f"Расходы: <b>−{summary['expense']:,.0f} ₽</b>\n"
        f"Итого: <b>{summary['balance']:,.0f} ₽</b>\n"
    )

    if lines:
        text += "\n<b>По категориям:</b>\n" + "\n".join(lines)

    await message.answer(text)


@router.message(Command("week"))
async def process_week_command(message: Message, conn: AsyncConnection) -> None:
    summary = await get_period_summary(conn, message.from_user.id, days=7)

    if summary["count"] == 0:
        await message.answer("За последние 7 дней записей пока нет.")
        return

    lines = []
    for category, amount in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
        lines.append(f"• {category}: −{amount:,.0f} ₽")

    text = (
        "<b>Сводка за 7 дней:</b>\n\n"
        f"Доходы: <b>+{summary['income']:,.0f} ₽</b>\n"
        f"Расходы: <b>−{summary['expense']:,.0f} ₽</b>\n"
        f"Итого: <b>{summary['balance']:,.0f} ₽</b>\n"
        f"Операций: {summary['count']}\n"
    )

    if lines:
        text += "\n<b>По категориям:</b>\n" + "\n".join(lines)

    await message.answer(text)


@router.message(Command("edit_amount"))
async def process_edit_amount_command(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "<code>/edit_amount 500</code>\n\n"
            "Изменяет сумму последней записи."
        )
        return

    try:
        new_amount = float(args[1].replace(",", "."))
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return

    if new_amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return

    updated = await edit_last_amount(conn, message.from_user.id, new_amount)

    if updated is None:
        await message.answer("Нет записей для редактирования.")
        return

    sign = "+" if updated["is_income"] else "-"
    balance = await get_user_balance(conn, message.from_user.id)

    await message.answer(
        f"Сумма изменена:\n"
        f"{sign}{updated['amount']:,.0f} ₽ — {updated['category']}\n\n"
        f"Текущий баланс: <b>{balance:,.0f} ₽</b>"
    )


@router.message(Command("edit_category"))
async def process_edit_category_command(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "<code>/edit_category Продукты</code>\n\n"
            "Изменяет категорию последней записи."
        )
        return

    new_category = args[1].strip()
    updated = await edit_last_category(conn, message.from_user.id, new_category)

    if updated is None:
        await message.answer("Нет записей для редактирования.")
        return

    sign = "+" if updated["is_income"] else "-"
    balance = await get_user_balance(conn, message.from_user.id)

    await message.answer(
        f"Категория изменена:\n"
        f"{sign}{updated['amount']:,.0f} ₽ — {updated['category']}\n\n"
        f"Текущий баланс: <b>{balance:,.0f} ₽</b>"
    )
