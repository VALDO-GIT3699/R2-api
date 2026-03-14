from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AppleLoginRequest(BaseModel):
    identity_token: str
    email: EmailStr | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
