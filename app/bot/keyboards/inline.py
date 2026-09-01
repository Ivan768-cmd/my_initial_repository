from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_transaction_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data="delete_last"
        ),
        InlineKeyboardButton(
            text="💰 Баланс",
            callback_data="show_balance"
        )
    )

    return builder.as_markup()
