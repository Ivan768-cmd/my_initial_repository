from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from psycopg import AsyncConnection

from app.bot.config import Config
from app.bot.keyboards.reply import get_main_keyboard
from app.infrastructure.database.repositories.transaction import ensure_user
from app.infrastructure.database.repositories.access import has_active_premium

router = Router(name="start")


@router.message(CommandStart())
async def process_start_command(
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

    is_admin = message.from_user.id in config.bot.admin_ids
    is_premium = await has_active_premium(conn, message.from_user.id)

    if is_admin or is_premium:
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
        return

    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Я бот для учёта расходов и доходов.\n\n"
        "Чтобы пользоваться ботом, нужна подписка.\n"
        "Стоимость: <b>369 ₽</b> за 30 дней.\n\n"
        "Оплатить: /pay"
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def process_help_command(
    message: Message,
    conn: AsyncConnection,
    config: Config,
) -> None:
    is_admin = message.from_user.id in config.bot.admin_ids
    is_premium = await has_active_premium(conn, message.from_user.id)

    if not (is_admin or is_premium):
        await message.answer(
            "Доступ откроется после оплаты подписки.\n\n"
            "Оплатить: /pay"
        )
        return

    text = (
        "<b>Доступные команды:</b>\n\n"
        "/start — начать работу\n"
        "/help — список команд\n"
        "/pay — подписка\n"
        "/privacy — политика конфиденциальности\n"
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
        "/limits — посмотреть лимиты\n"
        "/set_income 80000 — доход на месяц\n"
        "/budget — прогресс бюджета\n"
        "/plan Такси 5000 — категория в бюджете\n"
        "/unplan Такси — удалить категорию из бюджета\n\n"
        "<b>Анализ:</b>\n"
        "/analyze — разбор за 7 дней\n"
        "/month — разбор за 30 дней и прогноз\n"
        "/habits — привычки трат\n\n"
        "<b>Цели:</b>\n"
        "/add_goal Отпуск 120000 — создать цель\n"
        "/goals — список целей\n"
        "/save Отпуск 5000 — отложить в цель\n\n"
        "<b>Подписки:</b>\n"
        "/add_sub Netflix 799 — добавить подписку\n"
        "/subs — список подписок\n"
        "/del_sub Netflix — удалить подписку\n\n"
        "<b>Напоминания:</b>\n"
        "/remind on 21:00 — включить напоминание\n"
        "/remind off — выключить\n"
        "/remind — статус\n\n"
        "<b>Настройки:</b>\n"
        "/settings — настройки\n"
        "/reset_data — удалить все данные"
    )
    await message.answer(text)
