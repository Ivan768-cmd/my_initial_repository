from psycopg import AsyncConnection


async def get_all_user_ids(conn: AsyncConnection) -> list[int]:
    rows = await conn.execute("SELECT user_id FROM users")
    result = await rows.fetchall()
    return [int(r[0]) for r in result]
