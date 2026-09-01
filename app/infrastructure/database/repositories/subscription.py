from psycopg import AsyncConnection


async def add_subscription(
    conn: AsyncConnection,
    user_id: int,
    name: str,
    amount: float
) -> dict:
    row = await conn.execute(
        """
        INSERT INTO subscriptions (user_id, name, amount)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, name)
        DO UPDATE SET amount = EXCLUDED.amount
        RETURNING id, user_id, name, amount, created_at
        """,
        (user_id, name, amount),
    )
    result = await row.fetchone()
    return {
        "id": result[0],
        "user_id": result[1],
        "name": result[2],
        "amount": float(result[3]),
        "created_at": result[4],
    }


async def get_user_subscriptions(
    conn: AsyncConnection,
    user_id: int
) -> list[dict]:
    rows = await conn.execute(
        """
        SELECT id, user_id, name, amount, created_at
        FROM subscriptions
        WHERE user_id = %s
        ORDER BY name
        """,
        (user_id,),
    )
    result = await rows.fetchall()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "name": r[2],
            "amount": float(r[3]),
            "created_at": r[4],
        }
        for r in result
    ]


async def get_subscriptions_total(
    conn: AsyncConnection,
    user_id: int
) -> float:
    row = await conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM subscriptions
        WHERE user_id = %s
        """,
        (user_id,),
    )
    result = await row.fetchone()
    return float(result[0])


async def delete_subscription(
    conn: AsyncConnection,
    user_id: int,
    name: str
) -> bool:
    row = await conn.execute(
        """
        DELETE FROM subscriptions
        WHERE user_id = %s AND LOWER(name) = LOWER(%s)
        RETURNING id
        """,
        (user_id, name),
    )
    result = await row.fetchone()
    return result is not None
