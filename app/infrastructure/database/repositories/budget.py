from psycopg import AsyncConnection


async def set_limit(
    conn: AsyncConnection,
    user_id: int,
    category: str,
    amount: float
) -> None:
    await conn.execute(
        """
        INSERT INTO limits (user_id, category, amount)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, category)
        DO UPDATE SET amount = EXCLUDED.amount
        """,
        (user_id, category.capitalize(), amount),
    )


async def get_limit(
    conn: AsyncConnection,
    user_id: int,
    category: str
) -> float | None:
    row = await conn.execute(
        """
        SELECT amount FROM limits
        WHERE user_id = %s AND LOWER(category) = LOWER(%s)
        """,
        (user_id, category),
    )
    result = await row.fetchone()
    return float(result[0]) if result else None


async def get_all_limits(
    conn: AsyncConnection,
    user_id: int
) -> dict[str, float]:
    rows = await conn.execute(
        """
        SELECT category, amount FROM limits
        WHERE user_id = %s
        ORDER BY category
        """,
        (user_id,),
    )
    result = await rows.fetchall()
    return {r[0]: float(r[1]) for r in result}
