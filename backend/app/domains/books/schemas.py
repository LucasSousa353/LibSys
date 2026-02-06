from pydantic import BaseModel, ConfigDict, Field, field_validator

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, description="Título do livro")
    author: str = Field(..., min_length=1, description="Autor do livro")
    isbn: str = Field(..., description="ISBN único")
    total_copies: int = Field(default=1, ge=1, description="Quantidade total adquirida")

    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_and_validate_text(cls, value: str) -> str:
        if value is None:
            raise ValueError("Campo obrigatório")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Campo não pode ser vazio")
        return cleaned

class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, description="Título do livro")
    author: str | None = Field(None, min_length=1, description="Autor do livro")
    total_copies: int | None = Field(None, ge=1, description="Quantidade total adquirida")

    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_and_validate_text(cls, value):
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Campo não pode ser vazio")
        return cleaned


class BookResponse(BookBase):
    id: int
    available_copies: int

    model_config = ConfigDict(from_attributes=True)
