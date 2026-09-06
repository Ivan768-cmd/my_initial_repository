from datetime import datetime

from psycopg import AsyncConnection


async def set_limit(conn: AsyncConnection, user_id: int, category: str, amount: float) -> None:
    await conn.execute(
        """
        INSERT INTO limits (user_id, category, amount)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, category)
        DO UPDATE SET amount = EXCLUDED.amount
        """,
        (user_id, category.capitalize(), amount),
    )


async def get_limit(conn: AsyncConnection, user_id: int, category: str) -> float | None:
    row = await conn.execute(
        """
        SELECT amount FROM limits
        WHERE user_id = %s AND LOWER(category) = LOWER(%s)
        """,
        (user_id, category),
    )
    result = await row.fetchone()
    return float(result[0]) if result else None


async def get_all_limits(conn: AsyncConnection, user_id: int) -> dict[str, float]:
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


async def set_monthly_income(conn: AsyncConnection, user_id: int, income: float) -> None:
    await conn.execute(
        """
        INSERT INTO monthly_plans (user_id, income, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (user_id)
        DO UPDATE SET income = EXCLUDED.income, updated_at = NOW()
        """,
        (user_id, income),
    )


async def get_monthly_income(conn: AsyncConnection, user_id: int) -> float | None:
    row = await conn.execute(
        "SELECT income FROM monthly_plans WHERE user_id = %s",
        (user_id,),
    )
    result = await row.fetchone()
    return float(result[0]) if result else None


async def set_budget_item(conn: AsyncConnection, user_id: int, category: str, amount: float) -> None:
    await conn.execute(
        """
        INSERT INTO budget_items (user_id, category, amount)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, category)
        DO UPDATE SET amount = EXCLUDED.amount
        """,
        (user_id, category.capitalize(), amount),
    )


async def get_budget_items(conn: AsyncConnection, user_id: int) -> dict[str, float]:
    rows = await conn.execute(
        """
        SELECT category, amount
        FROM budget_items
        WHERE user_id = %s
        ORDER BY amount DESC
        """,
        (user_id,),
    )
    result = await rows.fetchall()
    return {r[0]: float(r[1]) for r in result}


async def get_month_spent_by_category(conn: AsyncConnection, user_id: int) -> dict[str, float]:
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = await conn.execute(
        """
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = %s
          AND NOT is_income
          AND created_at >= %s
        GROUP BY category
        """,
        (user_id, month_start),
    )
    result = await rows.fetchall()
    return {r[0]: float(r[1]) for r in result}


async def get_last_month_expense_share(conn: AsyncConnection, user_id: int) -> dict[str, float]:
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = await conn.execute(
        """
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = %s
          AND NOT is_income
          AND created_at >= %s - INTERVAL '30 days'
          AND created_at < %s
        GROUP BY category
        """,
        (user_id, month_start, month_start),
    )
    result = await rows.fetchall()
    total = sum(float(r[1]) for r in result)
    if total <= 0:
        return {}
    return {r[0]: float(r[1]) / total for r in result}
