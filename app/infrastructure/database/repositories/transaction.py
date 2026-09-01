from datetime import datetime, timedelta
from collections import defaultdict

from psycopg import AsyncConnection


async def ensure_user(
    conn: AsyncConnection,
    user_id: int,
    username: str | None = None,
    first_name: str | None = None
) -> None:
    await conn.execute(
        """
        INSERT INTO users (user_id, username, first_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            username = COALESCE(EXCLUDED.username, users.username),
            first_name = COALESCE(EXCLUDED.first_name, users.first_name)
        """,
        (user_id, username, first_name)
    )


async def add_transaction(
    conn: AsyncConnection,
    user_id: int,
    amount: float,
    category: str,
    is_income: bool = False,
    comment: str | None = None
) -> dict:
    row = await conn.execute(
        """
        INSERT INTO transactions (user_id, amount, category, is_income, comment)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, user_id, amount, category, is_income, comment, created_at
        """,
        (user_id, amount, category, is_income, comment),
    )
    result = await row.fetchone()
    return {
        "id": result[0],
        "user_id": result[1],
        "amount": float(result[2]),
        "category": result[3],
        "is_income": result[4],
        "comment": result[5],
        "created_at": result[6],
    }


async def get_user_transactions(
    conn: AsyncConnection,
    user_id: int,
    limit: int = 50
) -> list[dict]:
    rows = await conn.execute(
        """
        SELECT id, user_id, amount, category, is_income, comment, created_at
        FROM transactions
        WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (user_id, limit),
    )
    result = await rows.fetchall()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "amount": float(r[2]),
            "category": r[3],
            "is_income": r[4],
            "comment": r[5],
            "created_at": r[6],
        }
        for r in result
    ]


async def get_user_balance(conn: AsyncConnection, user_id: int) -> float:
    row = await conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN is_income THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN NOT is_income THEN amount ELSE 0 END), 0)
        FROM transactions
        WHERE user_id = %s
        """,
        (user_id,),
    )
    result = await row.fetchone()
    return float(result[0])


async def delete_transaction_by_id(
    conn: AsyncConnection,
    user_id: int,
    tx_id: int
) -> dict | None:
    row = await conn.execute(
        """
        DELETE FROM transactions
        WHERE id = %s AND user_id = %s
        RETURNING id, user_id, amount, category, is_income, comment, created_at
        """,
        (tx_id, user_id),
    )
    result = await row.fetchone()
    if not result:
        return None
    return {
        "id": result[0],
        "user_id": result[1],
        "amount": float(result[2]),
        "category": result[3],
        "is_income": result[4],
        "comment": result[5],
        "created_at": result[6],
    }


async def delete_last_transaction(
    conn: AsyncConnection,
    user_id: int
) -> dict | None:
    row = await conn.execute(
        """
        DELETE FROM transactions
        WHERE id = (
            SELECT id FROM transactions
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        )
        RETURNING id, user_id, amount, category, is_income, comment, created_at
        """,
        (user_id,),
    )
    result = await row.fetchone()
    if not result:
        return None
    return {
        "id": result[0],
        "user_id": result[1],
        "amount": float(result[2]),
        "category": result[3],
        "is_income": result[4],
        "comment": result[5],
        "created_at": result[6],
    }


async def get_last_transaction(
    conn: AsyncConnection,
    user_id: int
) -> dict | None:
    row = await conn.execute(
        """
        SELECT id, user_id, amount, category, is_income, comment, created_at
        FROM transactions
        WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (user_id,),
    )
    result = await row.fetchone()
    if not result:
        return None
    return {
        "id": result[0],
        "user_id": result[1],
        "amount": float(result[2]),
        "category": result[3],
        "is_income": result[4],
        "comment": result[5],
        "created_at": result[6],
    }


async def edit_last_amount(
    conn: AsyncConnection,
    user_id: int,
    new_amount: float
) -> dict | None:
    last = await get_last_transaction(conn, user_id)
    if last is None:
        return None

    row = await conn.execute(
        """
        UPDATE transactions
        SET amount = %s
        WHERE id = %s AND user_id = %s
        RETURNING id, user_id, amount, category, is_income, comment, created_at
        """,
        (new_amount, last["id"], user_id),
    )
    result = await row.fetchone()
    if not result:
        return None
    return {
        "id": result[0],
        "user_id": result[1],
        "amount": float(result[2]),
        "category": result[3],
        "is_income": result[4],
        "comment": result[5],
        "created_at": result[6],
    }


async def edit_last_category(
    conn: AsyncConnection,
    user_id: int,
    new_category: str
) -> dict | None:
    last = await get_last_transaction(conn, user_id)
    if last is None:
        return None

    row = await conn.execute(
        """
        UPDATE transactions
        SET category = %s
        WHERE id = %s AND user_id = %s
        RETURNING id, user_id, amount, category, is_income, comment, created_at
        """,
        (new_category.capitalize(), last["id"], user_id),
    )
    result = await row.fetchone()
    if not result:
        return None
    return {
        "id": result[0],
        "user_id": result[1],
        "amount": float(result[2]),
        "category": result[3],
        "is_income": result[4],
        "comment": result[5],
        "created_at": result[6],
    }


async def get_stats_by_category(
    conn: AsyncConnection,
    user_id: int
) -> dict[str, dict[str, float]]:
    rows = await conn.execute(
        """
        SELECT
            category,
            COALESCE(SUM(CASE WHEN is_income THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN NOT is_income THEN amount ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE user_id = %s
        GROUP BY category
        ORDER BY category
        """,
        (user_id,),
    )
    result = await rows.fetchall()
    stats = {}
    for r in result:
        stats[r[0]] = {
            "income": float(r[1]),
            "expense": float(r[2]),
        }
    return stats


async def get_period_summary(
    conn: AsyncConnection,
    user_id: int,
    days: int
) -> dict:
    rows = await conn.execute(
        """
        SELECT
            category,
            is_income,
            amount,
            created_at
        FROM transactions
        WHERE user_id = %s
          AND created_at >= NOW() - (%s || ' days')::INTERVAL
        """,
        (user_id, str(days)),
    )
    result = await rows.fetchall()

    total_income = 0.0
    total_expense = 0.0
    by_category: dict[str, float] = defaultdict(float)

    for r in result:
        category, is_income, amount, _ = r
        amount = float(amount)
        if is_income:
            total_income += amount
        else:
            total_expense += amount
            by_category[category] += amount

    return {
        "income": total_income,
        "expense": total_expense,
        "balance": total_income - total_expense,
        "by_category": dict(by_category),
        "count": len(result),
    }


async def get_category_spent(
    conn: AsyncConnection,
    user_id: int,
    category: str
) -> float:
    row = await conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = %s
          AND NOT is_income
          AND LOWER(category) = LOWER(%s)
        """,
        (user_id, category),
    )
    result = await row.fetchone()
    return float(result[0])
