import asyncio
import logging
import sys

import psycopg
from app.bot.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL = """
CREATE TABLE IF NOT EXISTS reminders (
    user_id    BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    time_str   VARCHAR(5) NOT NULL,
    enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
"""


async def create_reminders_table():
    config = load_config()
    conninfo = (
        f"host={config.db.host} port={config.db.port} "
        f"dbname={config.db.name} user={config.db.user} "
        f"password={config.db.password}"
    )
    async with await psycopg.AsyncConnection.connect(conninfo) as conn:
        await conn.execute(SQL)
        await conn.commit()
        logger.info("Reminders table created")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_reminders_table())
