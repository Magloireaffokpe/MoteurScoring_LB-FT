from pydantic import BaseModel
from uuid import UUID


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: str


class UserMe(BaseModel):
    id: UUID
    login: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
