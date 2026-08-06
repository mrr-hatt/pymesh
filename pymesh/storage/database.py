"""
Async SQLAlchemy database manager supporting SQLite and PostgreSQL.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .models import Base


class DatabaseManager:
    def __init__(self, db_url: str = "sqlite+aiosqlite:///./pymesh_controller.db"):
        self.db_url = db_url
        self.engine = create_async_engine(
            self.db_url,
            echo=False,
            future=True,
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def init_db(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session_maker() as session:
            yield session
