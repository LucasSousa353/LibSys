from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis
import structlog
from fastapi_limiter.depends import RateLimiter

from app.core.base import get_db
from app.core.cache.redis import get_redis
from app.core.config import settings
from app.core.messages import ErrorMessages
from app.domains.auth.security import create_access_token, verify_password
from app.domains.users.models import User
from app.domains.auth.schemas import TokenResponse
from app.domains.audit.services import AuditLogService

router = APIRouter(tags=["Auth"])
logger = structlog.get_logger()

_LOGIN_LOCKOUT_PREFIX = "login:lockout:"
_LOGIN_ATTEMPTS_PREFIX = "login:attempts:"


async def _check_lockout(email: str, redis: Redis) -> None:
    """Exceção 429 se a conta estiver bloqueada."""
    lockout_key = f"{_LOGIN_LOCKOUT_PREFIX}{email.lower()}"
    ttl = await redis.ttl(lockout_key)
    if ttl and ttl > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorMessages.USER_ACCOUNT_LOCKED.format(seconds=ttl),
        )


async def _record_failed_attempt(email: str, redis: Redis) -> None:
    """Incrementar contador de tentativas falhas; bloquear a conta quando o limite for atingido."""
    attempts_key = f"{_LOGIN_ATTEMPTS_PREFIX}{email.lower()}"
    lockout_key = f"{_LOGIN_LOCKOUT_PREFIX}{email.lower()}"

    count = await redis.incr(attempts_key)
    if count == 1:
        # First failure: set a sliding window equal to the lockout period
        await redis.expire(attempts_key, settings.LOGIN_LOCKOUT_SECONDS)

    if count >= settings.LOGIN_MAX_ATTEMPTS:
        await redis.setex(lockout_key, settings.LOGIN_LOCKOUT_SECONDS, "1")
        await redis.delete(attempts_key)
        logger.warning(
            "Account locked due to too many failed attempts",
            email=email,
            lockout_seconds=settings.LOGIN_LOCKOUT_SECONDS,
        )


async def _clear_failed_attempts(email: str, redis: Redis) -> None:
    """Reset the counter after a successful login."""
    await redis.delete(f"{_LOGIN_ATTEMPTS_PREFIX}{email.lower()}")


@router.post(
    "/token",
    response_model=TokenResponse,
    dependencies=[
        Depends(
            RateLimiter(
                times=settings.LOGIN_RATE_LIMIT_TIMES,
                seconds=settings.LOGIN_RATE_LIMIT_SECONDS,
            )
        )
    ],
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """
    Endpoint de autenticação que retorna um token JWT.

    - **username**: email do usuário
    - **password**: senha do usuário
    """
    # 1. Verificar lockout por email antes de qualquer operação
    await _check_lockout(form_data.username, redis)

    # 2. Buscar usuário pelo email (form_data.username no OAuth2 é o campo de login)
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # 3. Validar senha
    if not user or not verify_password(form_data.password, user.hashed_password):
        await _record_failed_attempt(form_data.username, redis)
        logger.warning("Failed login attempt", email=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )

    # 4. Gerar Token JWT
    await _clear_failed_attempts(user.email, redis)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )

    logger.info("User authenticated successfully", email=user.email)
    audit_service = AuditLogService(db)
    await audit_service.log_event(
        action="user_login",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        level="info",
        message="User login successful",
        metadata={"email": user.email},
    )
    await db.commit()
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "must_reset_password": user.must_reset_password,
    }
