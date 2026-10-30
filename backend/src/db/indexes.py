from src.db.mongo_db import get_db


async def create_indexes():
    """Create indexes for the users collection."""

    db = await get_db()
    await db.users.create_index("email", unique=True, name="idx_email")
