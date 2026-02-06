from typing import Annotated, List, Optional
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.base import get_db
from app.core.cache.redis import get_redis
from app.core.config import settings
from app.domains.auth.dependencies import get_current_user
from app.domains.loans.models import LoanStatus
from app.domains.loans.schemas import LoanCreate, LoanResponse
from app.domains.loans.services import LoanService
from app.domains.users.models import User
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
    dependencies=[
        Depends(
            RateLimiter(
                times=settings.RATE_LIMIT_TIMES, seconds=settings.RATE_LIMIT_SECONDS
            )
        )
    ],
)
async def create_loan(
    loan_in: LoanCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: LoanService = Depends(get_loan_service),
):
    if loan_in.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode criar empréstimos para si mesmo",
        )
    try:
        return await service.create_loan(loan_in)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loan_id}/return", status_code=status.HTTP_200_OK)
async def return_loan(
    loan_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: LoanService = Depends(get_loan_service),
):
    try:
        return await service.return_loan(loan_id, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/", response_model=List[LoanResponse])
async def list_loans(
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: Optional[int] = None,
    status: Optional[LoanStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    service: LoanService = Depends(get_loan_service),
):
    effective_user_id = user_id if user_id == current_user.id else current_user.id
    return await service.list_loans(  # type: ignore
        user_id=effective_user_id, status=status, skip=skip, limit=limit
    )


@router.get("/export/csv")
async def export_loans_csv(
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    service: LoanService = Depends(get_loan_service),
):
    """
    Exporta dados de empréstimos em formato CSV com streaming.

    Parâmetros:
    - user_id: Filtro opcional por ID do usuário (padrão: usuário autenticado)
    - status: Filtro opcional por status (ACTIVE, RETURNED, OVERDUE)

    Retorna arquivo CSV com todos os empréstimos encontrados via streaming
    (baixa latência, sem risco de OOM).
    """

    effective_user_id = (
        current_user.id if not user_id or user_id != current_user.id else user_id
    )

    # Usar async generator para streaming
    csv_generator = service.export_loans_csv(user_id=effective_user_id, status=status)

    return StreamingResponse(
        csv_generator,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=emprestimos.csv"},
    )


@router.get("/export/pdf")
async def export_loans_pdf(
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: LoanService = Depends(get_loan_service),
):
    effective_user_id = (
        current_user.id if not user_id or user_id != current_user.id else user_id
    )
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_file.close()
    await service.export_loans_pdf_file(
        temp_file.name, user_id=effective_user_id, status=status
    )
    background_tasks.add_task(os.unlink, temp_file.name)
    return FileResponse(
        temp_file.name,
        media_type="application/pdf",
        filename="loans.pdf",
        background=background_tasks,
    )
