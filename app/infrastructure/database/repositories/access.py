from datetime import datetime, timedelta

from psycopg import AsyncConnection


async def get_premium_until(conn: AsyncConnection, user_id: int) -> datetime | None:
    row = await conn.execute(
        "SELECT premium_until FROM users WHERE user_id = %s",
        (user_id,),
    )
    result = await row.fetchone()
    if not result:
        return None
    return result[0]


async def has_active_premium(conn: AsyncConnection, user_id: int) -> bool:
    premium_until = await get_premium_until(conn, user_id)
    if premium_until is None:
        return False
    return premium_until > datetime.now()


async def grant_premium_days(
    conn: AsyncConnection,
    user_id: int,
    days: int = 30
) -> datetime:
    current = await get_premium_until(conn, user_id)
    now = datetime.now()
    start = current if current and current > now else now
    new_until = start + timedelta(days=days)

    await conn.execute(
        """
        UPDATE users
        SET premium_until = %s
        WHERE user_id = %s
        """,
        (new_until, user_id),
    )
    return new_until
