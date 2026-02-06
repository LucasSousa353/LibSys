from datetime import datetime, timezone
from typing import Annotated, Iterable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis
import jwt
from jwt.exceptions import InvalidTokenError
import structlog

from app.core.base import get_db
from app.core.cache.redis import get_redis
from app.core.config import settings
from app.domains.users.models import User
from app.domains.users.schemas import UserRole

logger = structlog.get_logger()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

_ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}

_TOKEN_BLACKLIST_PREFIX = "token:blacklist:"


async def is_token_blacklisted(token: str, redis: Redis) -> bool:
    """Verifica se o token foi revogado (logout)."""
    return await redis.exists(f"{_TOKEN_BLACKLIST_PREFIX}{token}") > 0


async def blacklist_token(token: str, ttl_seconds: int, redis: Redis) -> None:
    """Adiciona token à blacklist com TTL igual ao tempo restante de expiração."""
    await redis.setex(f"{_TOKEN_BLACKLIST_PREFIX}{token}", ttl_seconds, "1")


_PASSWORD_RESET_ALLOWED_PATHS = {"/users/me/reset-password", "/logout"}


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    Valida o token JWT e retorna o usuário associado.

    Verificações adicionais:
    - Compara ``iat`` do token com ``password_reset_at`` do usuário para
      invalidar tokens emitidos antes de um reset de senha.
    - Bloqueia usuários com ``must_reset_password=True`` em todas as rotas
      exceto a própria rota de reset de senha.

    Raises:
        HTTPException: Se o token for inválido ou o usuário não existir
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    algorithm = settings.ALGORITHM.upper()
    if algorithm not in _ALLOWED_JWT_ALGORITHMS:
        logger.error("Unsafe JWT algorithm configured", algorithm=algorithm)
        raise credentials_exception

    # Verificar se o token foi revogado (logout)
    if await is_token_blacklisted(token, redis):
        logger.warning("Blacklisted token used")
        raise credentials_exception

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[algorithm]
        )
        email: str | None = payload.get("sub")
        if email is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
    except InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        raise credentials_exception

    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("User not found from token", email=email)
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )

    # --- invalida tokens emitidos antes do ultimo reset de senha ----
    token_iat = payload.get("iat")
    if user.password_reset_at and token_iat is not None:
        iat_dt = datetime.fromtimestamp(token_iat, tz=timezone.utc)
        reset_at = user.password_reset_at
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        if iat_dt < reset_at:
            logger.warning(
                "Token issued before password reset",
                email=email,
                iat=iat_dt.isoformat(),
                reset_at=reset_at.isoformat(),
            )
            raise credentials_exception

    # --- bloqueia usuários que devem redefinir a senha ----
    if user.must_reset_password:
        request_path = request.url.path.rstrip("/")
        if request_path not in _PASSWORD_RESET_ALLOWED_PATHS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="É necessário redefinir a senha antes de continuar",
            )

    return user


def is_staff(user: User) -> bool:
    return user.role in {UserRole.ADMIN.value, UserRole.LIBRARIAN.value}


def require_roles(allowed_roles: Iterable[str]):
    allowed_set = {str(role).strip().lower() for role in allowed_roles}

    async def _require_roles(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        role_value = getattr(current_user.role, "value", current_user.role)
        normalized_role = str(role_value).strip().lower()
        if normalized_role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso nao autorizado para este recurso",
            )
        return current_user

    return _require_roles
