from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_

from app.domains.users.models import User


class UserRepository:
    """Repository para isolamento de queries de Users."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, user_id: int) -> Optional[User]:
        """Busca um usuário por ID."""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional[User]:
        """Busca um usuário por email."""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_all(self, skip: int = 0, limit: int = 10) -> List[User]:
        """
        Lista usuários com paginação.

        Args:
            skip: Número de registros a pular
            limit: Número máximo de registros a retornar

        Returns:
            List[User]: Lista de usuários encontrados
        """
        query = select(User).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore

    async def find_lookup(self, query_text: str, skip: int = 0, limit: int = 10) -> List[User]:
        """
        Busca usuários por nome ou email (parcial, case-insensitive).

        Args:
            query_text: Texto de busca
            skip: Número de registros a pular
            limit: Número máximo de registros a retornar

        Returns:
            List[User]: Lista de usuários encontrados
        """
        query = select(User).where(
            or_(
                User.name.ilike(f"%{query_text}%"),
                User.email.ilike(f"%{query_text}%"),
            )
        ).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore

    async def find_by_ids(self, user_ids: List[int]) -> List[User]:
        """Busca usuarios por uma lista de IDs."""
        if not user_ids:
            return []
        query = select(User).where(User.id.in_(user_ids))
        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore

    async def create(self, user: User) -> User:
        """Adiciona um novo usuário à sessão (sem commit)."""
        self.db.add(user)
        return user

    async def update(self, user: User) -> User:
        """Atualiza um usuário existente (sem commit)."""
        self.db.add(user)
        return user
