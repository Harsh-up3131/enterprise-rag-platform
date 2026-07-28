from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    organization_name: str  # POC: signup always creates a new org (the user becomes owner)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    organization_id: str
    user_id: str
