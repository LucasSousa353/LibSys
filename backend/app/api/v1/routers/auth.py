from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import structlog

from app.core.base import get_db
from app.core.config import settings
from app.domains.auth.security import create_access_token, verify_password
from app.domains.users.models import User
from app.domains.auth.schemas import TokenResponse

router = APIRouter(tags=["Auth"])
logger = structlog.get_logger()


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Endpoint de autenticação que retorna um token JWT.

    - **username**: email do usuário
    - **password**: senha do usuário
    """
    # 1. Buscar usuário pelo email (form_data.username no OAuth2 é o campo de login)
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # 2. Validar senha
    if not user or not verify_password(form_data.password, user.hashed_password):
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

    # 3. Gerar Token JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )

    logger.info("User authenticated successfully", email=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "must_reset_password": user.must_reset_password,
    }
