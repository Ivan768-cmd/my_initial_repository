from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from app.bot.keyboards.reply import get_main_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def process_start_command(message: Message) -> None:
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Я бот для учёта расходов.\n"
        "Просто пиши сообщения вида:\n"
        "• <code>Такси 450</code>\n"
        "• <code>Продукты 3200</code>\n"
        "• <code>Зарплата 85000</code>\n\n"
        "Список всех команд — /help",
        reply_markup=get_main_keyboard()
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def process_help_command(message: Message) -> None:
    text = (
        "<b>Доступные команды:</b>\n\n"
        "/start — начать работу\n"
        "/help — список команд\n"
        "/balance — текущий баланс\n"
        "/history — последние операции\n"
        "/stats — статистика по категориям\n"
        "/today — сводка за сегодня\n"
        "/week — сводка за 7 дней\n"
        "/delete_last — удалить последнюю запись\n"
        "/edit_amount 500 — изменить сумму\n"
        "/edit_category Продукты — изменить категорию\n\n"
        "<b>Бюджет:</b>\n"
        "/set_limit Такси 3000 — установить лимит\n"
        "/limits — посмотреть лимиты\n\n"
        "<b>Цели:</b>\n"
        "/add_goal Отпуск 120000 — создать цель\n"
        "/goals — список целей\n"
        "/save Отпуск 5000 — отложить в цель\n\n"
        "<b>Подписки:</b>\n"
        "/add_sub Netflix 799 — добавить подписку\n"
        "/subs — список подписок\n"
        "/del_sub Netflix — удалить подписку\n\n"
        "<b>Настройки:</b>\n"
        "/settings — настройки\n"
        "/reset_data — удалить все данные\n\n"
        "<b>Как добавлять записи:</b>\n"
        "• <code>Такси 450</code>\n"
        "• <code>Кофе 280 #работа</code>\n"
        "• <code>Зарплата 85000</code>"
    )
    await message.answer(text)
