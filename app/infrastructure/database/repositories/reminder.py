from psycopg import AsyncConnection


async def set_reminder(
    conn: AsyncConnection,
    user_id: int,
    time_str: str
) -> None:
    await conn.execute(
        """
        INSERT INTO reminders (user_id, time_str, enabled)
        VALUES (%s, %s, TRUE)
        ON CONFLICT (user_id)
        DO UPDATE SET time_str = EXCLUDED.time_str, enabled = TRUE
        """,
        (user_id, time_str),
    )


async def disable_reminder(
    conn: AsyncConnection,
    user_id: int
) -> bool:
    row = await conn.execute(
        """
        UPDATE reminders
        SET enabled = FALSE
        WHERE user_id = %s
        RETURNING user_id
        """,
        (user_id,),
    )
    result = await row.fetchone()
    return result is not None


async def get_reminder(
    conn: AsyncConnection,
    user_id: int
) -> dict | None:
    row = await conn.execute(
        """
        SELECT user_id, time_str, enabled
        FROM reminders
        WHERE user_id = %s
        """,
        (user_id,),
    )
    result = await row.fetchone()
    if not result:
        return None
    return {
        "user_id": result[0],
        "time_str": result[1],
        "enabled": result[2],
    }


async def get_enabled_reminders(
    conn: AsyncConnection
) -> list[dict]:
    rows = await conn.execute(
        """
        SELECT user_id, time_str
        FROM reminders
        WHERE enabled = TRUE
        """
    )
    result = await rows.fetchall()
    return [{"user_id": r[0], "time_str": r[1]} for r in result]
