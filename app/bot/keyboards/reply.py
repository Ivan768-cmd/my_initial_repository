from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💰 Баланс"),
        KeyboardButton(text="📊 Статистика")
    )
    builder.row(
        KeyboardButton(text="📜 История"),
        KeyboardButton(text="🎯 Цели")
    )
    builder.row(
        KeyboardButton(text="📋 Лимиты"),
        KeyboardButton(text="❓ Помощь")
    )

    return builder.as_markup(resize_keyboard=True)
