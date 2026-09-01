from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from psycopg import AsyncConnection

router = Router(name="settings")


@router.message(Command("settings"))
async def process_settings_command(message: Message) -> None:
    text = (
        "<b>⚙️ Настройки</b>\n\n"
        "Валюта: <b>₽ (рубли)</b>\n"
        "Язык: <b>Русский</b>\n\n"
        "Пока доступно:\n"
        "• /reset_data — удалить все свои данные"
    )
    await message.answer(text)


@router.message(Command("reset_data"))
async def process_reset_data_command(message: Message) -> None:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить всё", callback_data="confirm_reset"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_reset"),
    )

    await message.answer(
        "⚠️ <b>Внимание!</b>\n\n"
        "Ты собираешься удалить <b>все</b> свои данные:\n"
        "• все транзакции\n"
        "• лимиты\n"
        "• цели\n"
        "• подписки\n\n"
        "Это действие нельзя отменить. Продолжить?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "cancel_reset")
async def process_cancel_reset(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Удаление отменено.")
    await callback.answer()


@router.callback_query(F.data == "confirm_reset")
async def process_confirm_reset(
    callback: CallbackQuery,
    conn: AsyncConnection
) -> None:
    user_id = callback.from_user.id

    await conn.execute("DELETE FROM transactions WHERE user_id = %s", (user_id,))
    await conn.execute("DELETE FROM limits WHERE user_id = %s", (user_id,))
    await conn.execute("DELETE FROM goals WHERE user_id = %s", (user_id,))
    await conn.execute("DELETE FROM subscriptions WHERE user_id = %s", (user_id,))
    await conn.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

    await callback.message.edit_text(
        "✅ Все твои данные удалены.\n"
        "Можешь начать заново — просто добавь первую запись."
    )
    await callback.answer()
