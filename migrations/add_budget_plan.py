import asyncio
import logging
import sys

import psycopg
from app.bot.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL = """
CREATE TABLE IF NOT EXISTS monthly_plans (
    user_id        BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    income         NUMERIC(12, 2) NOT NULL,
    updated_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS budget_items (
    id             SERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category       VARCHAR(100) NOT NULL,
    amount         NUMERIC(12, 2) NOT NULL,
    UNIQUE(user_id, category)
);
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
        logger.info("Budget plan tables created")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate())
