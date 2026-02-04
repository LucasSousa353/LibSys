from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserBase(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Senha do usuário")


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
