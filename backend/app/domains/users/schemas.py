from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator


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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
