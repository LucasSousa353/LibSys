from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis

from app.core.base import get_db
from app.core.redis import get_redis
from app.loans.models import Loan, LoanStatus
from app.loans.schemas import LoanCreate, LoanResponse
from app.loans.services import LoanService
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/loans", tags=["Loans"])


def get_loan_service(
    db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)
) -> LoanService:
    return LoanService(db, redis)


@router.post(
    "/",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def create_loan(
    loan_in: LoanCreate, service: LoanService = Depends(get_loan_service)
):
    try:
        return await service.create_loan(loan_in)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loan_id}/return", status_code=status.HTTP_200_OK)
async def return_loan(loan_id: int, service: LoanService = Depends(get_loan_service)):
    try:
        return await service.return_loan(loan_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[LoanResponse])
async def list_loans(
    user_id: Optional[int] = None,
    status: Optional[LoanStatus] = None,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):

    query = select(Loan)
    if user_id:
        query = query.where(Loan.user_id == user_id)
    if status:
        query = query.where(Loan.status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
