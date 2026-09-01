from psycopg_pool import AsyncConnectionPool

from app.bot.config import Config


async def get_pg_pool(config: Config) -> AsyncConnectionPool:
    conninfo = (
        f"host={config.db.host} "
        f"port={config.db.port} "
        f"dbname={config.db.name} "
        f"user={config.db.user} "
        f"password={config.db.password}"
    )

    pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=10,
        open=False
    )
    await pool.open()
    return pool
