from pydantic import BaseModel

from app.domains.users.schemas import UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: UserRole
    must_reset_password: bool