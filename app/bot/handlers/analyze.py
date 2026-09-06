from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from psycopg import AsyncConnection

from app.bot.services.ai_analyzer import (
    build_period_report,
    build_month_forecast,
    build_habits_report,
)

router = Router(name="analyze")


@router.message(Command("analyze"))
async def process_analyze_command(message: Message, conn: AsyncConnection) -> None:
    week = await build_period_report(
        conn,
        message.from_user.id,
        days=7,
        title="AI-анализ за 7 дней",
    )
    await message.answer(week)


@router.message(Command("month"))
async def process_month_command(message: Message, conn: AsyncConnection) -> None:
    report = await build_period_report(
        conn,
        message.from_user.id,
        days=30,
        title="Разбор за 30 дней",
    )
    forecast = await build_month_forecast(conn, message.from_user.id)
    await message.answer(report)
    await message.answer(forecast)


@router.message(Command("habits"))
async def process_habits_command(message: Message, conn: AsyncConnection) -> None:
    text = await build_habits_report(conn, message.from_user.id)
    await message.answer(text)
