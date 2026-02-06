from typing import List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserRole
from app.domains.users.repository import UserRepository
from app.domains.auth.security import get_password_hash
from app.core.messages import ErrorMessages
from app.core.reports.pdf import PdfTableBuilder
from app.domains.audit.services import AuditLogService


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = UserRepository(db)

    async def create_user(
        self, user_in: UserCreate, actor_user_id: int | None = None
    ) -> User:
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
        new_user = User(
            name=user_in.name,
            email=user_in.email,
            hashed_password=hashed,
            role=UserRole.USER.value,
            must_reset_password=False,
            password_reset_at=None,
            is_active=True,
        )
        new_user = await self.repository.create(new_user)
        await self.db.flush()

        audit_service = AuditLogService(self.db)
        await audit_service.log_event(
            action="user_created",
            entity_type="user",
            entity_id=new_user.id,
            actor_user_id=actor_user_id,
            level="info",
            message="User created",
            metadata={"email": new_user.email},
        )

        # Commit da transação
        await self.db.commit()
        await self.db.refresh(new_user)

        return new_user

    async def update_user_status(
        self, user_id: int, is_active: bool, actor_user_id: int | None = None
    ) -> User:
        """Ativa ou inativa um usuario."""
        user = await self.get_user_by_id(user_id)
        user.is_active = is_active
        await self.repository.update(user)

        audit_service = AuditLogService(self.db)
        await audit_service.log_event(
            action="user_activated" if is_active else "user_deactivated",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=actor_user_id,
            level="info" if is_active else "warning",
            message="User status updated",
            metadata={"is_active": is_active},
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def require_password_reset(
        self, user_id: int, actor_user_id: int | None = None
    ) -> User:
        """Marca o usuario para reset obrigatorio de senha."""
        user = await self.get_user_by_id(user_id)
        user.must_reset_password = True
        user.password_reset_at = datetime.now(timezone.utc)
        await self.repository.update(user)

        audit_service = AuditLogService(self.db)
        await audit_service.log_event(
            action="password_reset_requested",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=actor_user_id,
            level="warning",
            message="Password reset requested",
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def reset_password(
        self, user_id: int, new_password: str, actor_user_id: int | None = None
    ) -> User:
        """Atualiza a senha e remove o reset obrigatorio."""
        user = await self.get_user_by_id(user_id)
        user.hashed_password = get_password_hash(new_password)
        user.must_reset_password = False
        user.password_reset_at = datetime.now(timezone.utc)
        await self.repository.update(user)

        audit_service = AuditLogService(self.db)
        await audit_service.log_event(
            action="password_reset",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=actor_user_id,
            level="info",
            message="Password reset completed",
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

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

    async def lookup_users(self, query_text: str, skip: int = 0, limit: int = 10) -> List[User]:
        """
        Busca usuários por nome ou email com paginação.

        Args:
            query_text: Texto de busca
            skip: Número de registros a pular (paginação)
            limit: Número máximo de registros a retornar

        Returns:
            List[User]: Lista de usuários
        """
        return await self.repository.find_lookup(query_text, skip=skip, limit=limit)

    async def lookup_users_by_ids(self, user_ids: List[int]) -> List[User]:
        """Busca usuarios por IDs com retorno limitado ao essencial."""
        return await self.repository.find_by_ids(user_ids)

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
