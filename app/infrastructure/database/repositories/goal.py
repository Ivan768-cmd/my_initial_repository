from psycopg import AsyncConnection


async def add_goal(
    conn: AsyncConnection,
    user_id: int,
    name: str,
    target_amount: float
) -> dict:
    row = await conn.execute(
        """
        INSERT INTO goals (user_id, name, target_amount, current_amount)
        VALUES (%s, %s, %s, 0)
        ON CONFLICT (user_id, name)
        DO UPDATE SET target_amount = EXCLUDED.target_amount
        RETURNING id, user_id, name, target_amount, current_amount, created_at
        """,
        (user_id, name, target_amount),
    )
    result = await row.fetchone()
    return {
        "id": result[0],
        "user_id": result[1],
        "name": result[2],
        "target_amount": float(result[3]),
        "current_amount": float(result[4]),
        "created_at": result[5],
    }


async def get_user_goals(
    conn: AsyncConnection,
    user_id: int
) -> list[dict]:
    rows = await conn.execute(
        """
        SELECT id, user_id, name, target_amount, current_amount, created_at
        FROM goals
        WHERE user_id = %s
        ORDER BY created_at
        """,
        (user_id,),
    )
    result = await rows.fetchall()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "name": r[2],
            "target_amount": float(r[3]),
            "current_amount": float(r[4]),
            "created_at": r[5],
        }
        for r in result
    ]


async def add_to_goal(
    conn: AsyncConnection,
    user_id: int,
    goal_name: str,
    amount: float
) -> dict | None:
    row = await conn.execute(
        """
        UPDATE goals
        SET current_amount = current_amount + %s
        WHERE user_id = %s AND LOWER(name) = LOWER(%s)
        RETURNING id, user_id, name, target_amount, current_amount, created_at
        """,
        (amount, user_id, goal_name),
    )
    result = await row.fetchone()
    if not result:
        return None
    return {
        "id": result[0],
        "user_id": result[1],
        "name": result[2],
        "target_amount": float(result[3]),
        "current_amount": float(result[4]),
        "created_at": result[5],
    }
