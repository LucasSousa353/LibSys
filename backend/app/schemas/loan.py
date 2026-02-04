from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.loan import LoanStatus

class LoanBase(BaseModel):
    book_id: int
    user_id: int

class LoanCreate(LoanBase):
    pass

class LoanResponse(LoanBase):
    id: int
    loan_date: datetime
    expected_return_date: datetime
    return_date: Optional[datetime] = None
    status: LoanStatus

    model_config = ConfigDict(from_attributes=True)