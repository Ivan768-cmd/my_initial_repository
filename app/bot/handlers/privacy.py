from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="privacy")

PRIVACY_TEXT = (
    "<b>Политика конфиденциальности</b>\n\n"
    "Бот сохраняет только данные, нужные для работы:\n"
    "• Telegram ID, имя и username\n"
    "• записи о доходах и расходах, которые вы сами отправили\n"
    "• лимиты, цели, бюджет и напоминания\n"
    "• сведения об оплате подписки\n\n"
    "Данные хранятся на сервере в базе PostgreSQL.\n"
    "Мы не продаём их и не передаём третьим лицам, кроме платёжной системы "
    "ЮKassa — только в рамках оплаты.\n\n"
    "Удалить свои данные можно командой /reset_data.\n"
    "По вопросам: <a href=\"https://t.me/dafar_21\">написать администратору</a>."
)


@router.message(Command("privacy"))
async def process_privacy_command(message: Message) -> None:
    await message.answer(PRIVACY_TEXT)
