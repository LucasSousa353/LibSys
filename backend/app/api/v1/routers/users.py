from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.base import get_db
from app.core.cache.redis import get_redis
from app.core.config import settings
from app.domains.auth.dependencies import get_current_user
from app.domains.loans.models import LoanStatus
from app.domains.loans.schemas import LoanResponse
from app.domains.loans.services import LoanService
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserResponse
from app.domains.users.services import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    service = UserService(db=db)
    try:
        new_user = await service.create_user(user)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db=db)
    users = await service.list_users(skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db=db)
    try:
        user = await service.get_user_by_id(user_id)
        return user
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{user_id}/loans", response_model=List[LoanResponse])
async def list_user_loans(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    status: Optional[LoanStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    user_service = UserService(db=db)
    try:
        await user_service.get_user_by_id(user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    loan_service = LoanService(db=db, redis=redis)
    return await loan_service.list_loans(
        user_id=user_id, status=status, skip=skip, limit=limit
    )
