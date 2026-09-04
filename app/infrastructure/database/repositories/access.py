from datetime import datetime, timedelta

from psycopg import AsyncConnection


async def get_premium_until(conn: AsyncConnection, user_id: int) -> datetime | None:
    row = await conn.execute(
        """
        SELECT MAX(expires_at)
        FROM premium_subscriptions
        WHERE user_id = %s
          AND is_active = TRUE
        """,
        (user_id,),
    )
    result = await row.fetchone()
    if not result or result[0] is None:
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
    days: int = 30,
    source: str = "payment"
) -> datetime:
    current = await get_premium_until(conn, user_id)
    now = datetime.now()
    start = current if current and current > now else now
    new_until = start + timedelta(days=days)

    await conn.execute(
        """
        INSERT INTO premium_subscriptions (user_id, starts_at, expires_at, is_active, source)
        VALUES (%s, %s, %s, TRUE, %s)
        """,
        (user_id, start, new_until, source),
    )
    return new_until


async def get_user_subscriptions(
    conn: AsyncConnection,
    user_id: int
) -> list[dict]:
    rows = await conn.execute(
        """
        SELECT id, starts_at, expires_at, is_active, source, created_at
        FROM premium_subscriptions
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    result = await rows.fetchall()
    return [
        {
            "id": r[0],
            "starts_at": r[1],
            "expires_at": r[2],
            "is_active": r[3],
            "source": r[4],
            "created_at": r[5],
        }
        for r in result
    ]
