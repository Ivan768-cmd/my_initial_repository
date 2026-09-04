import asyncio
import logging
import sys

import psycopg
from app.bot.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL = """
CREATE TABLE IF NOT EXISTS premium_subscriptions (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    starts_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMP NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    source        VARCHAR(50) DEFAULT 'manual',
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_premium_user_id
ON premium_subscriptions(user_id);

CREATE INDEX IF NOT EXISTS idx_premium_expires
ON premium_subscriptions(expires_at);
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
        logger.info("premium_subscriptions table created")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate())
