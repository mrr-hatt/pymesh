"""
Pytest configuration and global fixtures.
"""

import pytest
import pytest_asyncio
from pymesh.controller.api import db_manager
from pymesh.storage.models import Base


@pytest_asyncio.fixture(autouse=True)
async def init_test_database():
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
