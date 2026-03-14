import re

from pydantic import BaseModel, EmailStr, Field, field_validator

NICKNAME_REGEX = re.compile(r"^[a-z0-9_]{3,24}$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AppleLoginRequest(BaseModel):
    identity_token: str
    email: EmailStr | None = None
    nickname: str | None = Field(default=None, min_length=3, max_length=24)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if not NICKNAME_REGEX.fullmatch(normalized):
            raise ValueError(
                "Nickname invalido. Usa 3-24 caracteres: minusculas, numeros o guion bajo"
            )
        return normalized


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
