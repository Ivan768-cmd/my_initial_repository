import logging
import sys
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.config import load_config
from app.bot.middlewares.database import DatabaseMiddleware
from app.bot.middlewares.access import AccessMiddleware
from app.infrastructure.database.connection import get_pg_pool
from app.infrastructure.redis.storage import get_redis_storage
from app.bot.services.reminder_service import send_daily_reminders

from app.bot.handlers.start import router as start_router
from app.bot.handlers.pay import router as pay_router
from app.bot.handlers.reports import router as reports_router
from app.bot.handlers.budget import router as budget_router
from app.bot.handlers.goals import router as goals_router
from app.bot.handlers.subscriptions import router as subscriptions_router
from app.bot.handlers.settings import router as settings_router
from app.bot.handlers.reminders import router as reminders_router
from app.bot.handlers.expenses import router as expenses_router
from app.bot.handlers.analyze import router as analyze_router
from app.bot.handlers.privacy import router as privacy_router

from app.bot.handlers.broadcast import router as broadcast_router

logger = logging.getLogger(__name__)


async def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = load_config()

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = get_redis_storage(config)
    dp = Dispatcher(storage=storage)
    dp.workflow_data.update(config=config)

    db_pool = await get_pg_pool(config)
    dp.update.middleware(DatabaseMiddleware(db_pool))
    dp.update.middleware(AccessMiddleware())

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_daily_reminders,
        trigger="cron",
        minute="*",
        kwargs={"bot": bot, "pool": db_pool},
    )
    scheduler.start()

    dp.include_router(start_router)
    dp.include_router(broadcast_router)
    dp.include_router(privacy_router)
    dp.include_router(pay_router)
    dp.include_router(reports_router)
    dp.include_router(budget_router)
    dp.include_router(goals_router)
    dp.include_router(subscriptions_router)
    dp.include_router(settings_router)
    dp.include_router(reminders_router)
    dp.include_router(expenses_router)
    dp.include_router(analyze_router)

    logger.info("Starting bot...")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await db_pool.close()
        await storage.close()
        await bot.session.close()
        logger.info("Bot stopped")
