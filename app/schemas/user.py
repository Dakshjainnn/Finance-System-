from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole

    model_config = {"from_attributes": True}


class UserRoleUpdate(BaseModel):
    role: UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

