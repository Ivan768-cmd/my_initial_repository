import asyncio
import logging
import sys

import psycopg
from app.bot.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL = """
ALTER TABLE users
ADD COLUMN IF NOT EXISTS premium_until TIMESTAMP;
"""


async def migrate():
    config = load_config()
    conninfo = (
        f"host={config.db.host} port={config.db.port} "
        f"dbname={config.db.name} user={config.db.user} "
        f"password={config.db.password}"
    )
    async with await psycopg.AsyncConnection.connect(conninfo) as conn:
        await conn.execute(SQL)
        await conn.commit()
        logger.info("premium_until column added")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate())
