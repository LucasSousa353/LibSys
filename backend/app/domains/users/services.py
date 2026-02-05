from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.users.models import User
from app.domains.users.schemas import UserCreate
from app.domains.auth.security import get_password_hash


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_in: UserCreate) -> User:
        """
        Cria um novo usuário no sistema.
        
        Args:
            user_in: Dados do usuário a ser criado
            
        Returns:
            User: Usuário criado
            
        Raises:
            ValueError: Se email já está registrado
        """
        # Verifica email duplicado
        query = select(User).where(User.email == user_in.email)
        result = await self.db.execute(query)
        if result.scalar_one_or_none():
            raise ValueError("Email já registrado")

        # Hash da senha
        hashed = get_password_hash(user_in.password)
        
        # Persiste no banco
        new_user = User(
            name=user_in.name,
            email=user_in.email,
            hashed_password=hashed
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        return new_user

    async def list_users(self, skip: int = 0, limit: int = 10) -> List[User]:
        """
        Lista usuários com paginação.
        
        Args:
            skip: Número de registros a pular (paginação)
            limit: Número máximo de registros a retornar
            
        Returns:
            List[User]: Lista de usuários
        """
        query = select(User).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all() # type: ignore

    async def get_user_by_id(self, user_id: int) -> User:
        """
        Busca um usuário pelo ID.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            User: Usuário encontrado
            
        Raises:
            LookupError: Se usuário não for encontrado
        """
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise LookupError("Usuário não localizado")
            
        return user

    async def get_user_by_email(self, email: str) -> User:
        """
        Busca um usuário pelo email.
        
        Args:
            email: Email do usuário
            
        Returns:
            User: Usuário encontrado
            
        Raises:
            LookupError: Se usuário não for encontrado
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise LookupError("Usuário não encontrado")
            
        return user
