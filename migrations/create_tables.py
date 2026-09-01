import asyncio
import logging
import sys

from psycopg_pool import AsyncConnectionPool

from app.bot.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id       BIGINT PRIMARY KEY,
    username      VARCHAR(255),
    first_name    VARCHAR(255),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    amount        NUMERIC(12, 2) NOT NULL,
    category      VARCHAR(100) NOT NULL,
    is_income     BOOLEAN NOT NULL DEFAULT FALSE,
    comment       VARCHAR(255),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS limits (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category      VARCHAR(100) NOT NULL,
    amount        NUMERIC(12, 2) NOT NULL,
    UNIQUE(user_id, category)
);

CREATE TABLE IF NOT EXISTS goals (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name          VARCHAR(100) NOT NULL,
    target_amount NUMERIC(12, 2) NOT NULL,
    current_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name          VARCHAR(100) NOT NULL,
    amount        NUMERIC(12, 2) NOT NULL,
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
"""


async def create_tables() -> None:
    config = load_config()

    conninfo = (
        f"host={config.db.host} "
        f"port={config.db.port} "
        f"dbname={config.db.name} "
        f"user={config.db.user} "
        f"password={config.db.password}"
    )

    pool = AsyncConnectionPool(conninfo=conninfo, min_size=1, max_size=5, open=False)
    await pool.open()

    try:
        async with pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(CREATE_TABLES_SQL)
                logger.info("Tables created successfully")
    finally:
        await pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_tables())
