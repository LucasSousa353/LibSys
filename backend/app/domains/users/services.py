from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.models import User
from app.domains.users.schemas import UserCreate
from app.domains.users.repository import UserRepository
from app.domains.auth.security import get_password_hash
from app.core.messages import ErrorMessages
from app.core.reports.pdf import PdfTableBuilder


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = UserRepository(db)

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
        existing_user = await self.repository.find_by_email(user_in.email)
        if existing_user:
            raise ValueError(ErrorMessages.USER_EMAIL_ALREADY_EXISTS)

        # Hash da senha
        hashed = get_password_hash(user_in.password)

        # Persiste no banco
        new_user = User(name=user_in.name, email=user_in.email, hashed_password=hashed)
        new_user = await self.repository.create(new_user)

        # Commit da transação
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
        return await self.repository.find_all(skip=skip, limit=limit)

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
        user = await self.repository.find_by_id(user_id)

        if not user:
            raise LookupError(ErrorMessages.USER_NOT_FOUND)

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
        user = await self.repository.find_by_email(email)

        if not user:
            raise LookupError(ErrorMessages.USER_NOT_FOUND)

        return user

    async def export_users_pdf_file(
        self, file_path: str, batch_size: int = 1000
    ) -> None:
        """Exporta usuarios em PDF direto para arquivo."""
        headers = [
            "ID",
            "Name",
            "Email",
            "Created At",
        ]
        pdf = PdfTableBuilder("Users Export", headers, orientation="L")

        skip = 0
        while True:
            users = await self.repository.find_all(skip=skip, limit=batch_size)
            if not users:
                break

            for user in users:
                created_at = user.created_at.isoformat() if user.created_at else ""
                pdf.add_row(
                    [
                        str(user.id),
                        user.name,
                        user.email,
                        created_at,
                    ]
                )

            skip += batch_size

        pdf.output_to_file(file_path)
