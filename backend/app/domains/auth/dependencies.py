from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import jwt
from jwt.exceptions import InvalidTokenError
import structlog

from app.core.base import get_db
from app.core.config import settings
from app.domains.users.models import User

logger = structlog.get_logger()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Valida o token JWT e retorna o usuário associado.
    
    Raises:
        HTTPException: Se o token for inválido ou o usuário não existir
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
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

    return user
