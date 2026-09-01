from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from psycopg import AsyncConnection

from app.infrastructure.database.repositories.goal import (
    add_goal,
    get_user_goals,
    add_to_goal,
)
from app.infrastructure.database.repositories.transaction import ensure_user

router = Router(name="goals")


@router.message(Command("add_goal"))
async def process_add_goal_command(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Использование:\n"
            "<code>/add_goal Отпуск 120000</code>\n\n"
            "Создаёт новую финансовую цель."
        )
        return

    name = args[1]
    try:
        target = float(args[2].replace(",", "."))
    except ValueError:
        await message.answer("Сумма цели должна быть числом.")
        return

    if target <= 0:
        await message.answer("Сумма цели должна быть больше нуля.")
        return

    await ensure_user(
        conn,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    goal = await add_goal(conn, message.from_user.id, name, target)

    await message.answer(
        f"Цель <b>«{goal['name']}»</b> создана!\n"
        f"Нужно накопить: <b>{goal['target_amount']:,.0f} ₽</b>"
    )


@router.message(Command("goals"))
@router.message(F.text == "🎯 Цели")
async def process_goals_command(message: Message, conn: AsyncConnection) -> None:
    goals = await get_user_goals(conn, message.from_user.id)

    if not goals:
        await message.answer(
            "У тебя пока нет целей.\n\n"
            "Создай первую:\n"
            "<code>/add_goal Отпуск 120000</code>"
        )
        return

    lines = []
    for goal in goals:
        percent = min(100, int(goal["current_amount"] / goal["target_amount"] * 100)) if goal["target_amount"] > 0 else 0
        remaining = max(0, goal["target_amount"] - goal["current_amount"])

        filled = percent // 10
        bar = "█" * filled + "░" * (10 - filled)

        status = "✅" if percent >= 100 else "🎯"

        lines.append(
            f"{status} <b>{goal['name']}</b>\n"
            f"   {bar} {percent}%\n"
            f"   {goal['current_amount']:,.0f} / {goal['target_amount']:,.0f} ₽\n"
            f"   Осталось: {remaining:,.0f} ₽"
        )

    text = "<b>Твои цели:</b>\n\n" + "\n\n".join(lines)
    await message.answer(text)


@router.message(Command("save"))
async def process_save_command(message: Message, conn: AsyncConnection) -> None:
    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Использование:\n"
            "<code>/save Отпуск 5000</code>\n\n"
            "Откладывает указанную сумму в цель."
        )
        return

    goal_name = args[1]
    try:
        amount = float(args[2].replace(",", "."))
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return

    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return

    goal = await add_to_goal(conn, message.from_user.id, goal_name, amount)

    if goal is None:
        await message.answer(
            f"Цель «{goal_name}» не найдена.\n"
            "Посмотри список целей: /goals"
        )
        return

    percent = min(100, int(goal["current_amount"] / goal["target_amount"] * 100))
    remaining = max(0, goal["target_amount"] - goal["current_amount"])

    text = (
        f"В цель <b>«{goal['name']}»</b> добавлено <b>{amount:,.0f} ₽</b>\n\n"
        f"Сейчас: {goal['current_amount']:,.0f} / {goal['target_amount']:,.0f} ₽ ({percent}%)\n"
    )

    if remaining > 0:
        text += f"Осталось накопить: {remaining:,.0f} ₽"
    else:
        text += "🎉 Цель достигнута!"

    await message.answer(text)
