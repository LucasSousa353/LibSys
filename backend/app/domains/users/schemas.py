from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator


class UserRole(str, Enum):
    ADMIN = "admin"
    LIBRARIAN = "librarian"
    USER = "user"


class UserBase(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr

    @field_validator("name", mode="before")
    @classmethod
    def strip_and_validate_name(cls, value: str) -> str:
        if value is None:
            raise ValueError("Campo obrigatório")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Nome não pode ser vazio")
        return cleaned


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Senha do usuário")


class UserResponse(UserBase):
    id: int
    role: UserRole
    password_reset_at: datetime | None = None
    must_reset_password: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLookupResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserPasswordResetRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Senha atual")
    new_password: str = Field(..., min_length=6, description="Nova senha")
