"""
Authentication and token management for PyMesh controller.
"""

import secrets
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pymesh.storage.models import AuthToken


class AuthManager:
    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    async def create_token(
        session: AsyncSession,
        network_id: str = "default",
        description: str = "Join token",
        max_uses: Optional[int] = None,
    ) -> str:
        token_str = AuthManager.generate_token()
        token_obj = AuthToken(
            token=token_str,
            network_id=network_id,
            description=description,
            max_uses=max_uses,
        )
        session.add(token_obj)
        await session.commit()
        return token_str

    @staticmethod
    async def validate_token(session: AsyncSession, token_str: str) -> bool:
        stmt = select(AuthToken).where(AuthToken.token == token_str)
        result = await session.execute(stmt)
        token_obj = result.scalar_one_or_none()

        if not token_obj:
            return False

        if token_obj.max_uses is not None and token_obj.used_count >= token_obj.max_uses:
            return False

        token_obj.used_count += 1
        await session.commit()
        return True
