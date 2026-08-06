"""
Schema initialization and migration utilities for PyMesh database.
"""

from .database import DatabaseManager


async def run_migrations(db_url: str = "sqlite+aiosqlite:///./pymesh_controller.db") -> None:
    db = DatabaseManager(db_url)
    await db.init_db()
