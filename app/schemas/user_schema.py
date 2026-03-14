import re

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.settings import settings

NICKNAME_REGEX = re.compile(r"^[a-z0-9_]{3,24}$")


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=3, max_length=24)

    @field_validator("email")
    @classmethod
    def validate_real_email(cls, value: EmailStr) -> EmailStr:
        try:
            validated = validate_email(
                str(value).strip(),
                check_deliverability=settings.email_check_deliverability,
            )
            return validated.normalized
        except EmailNotValidError as exc:
            raise ValueError("Correo invalido o no entregable") from exc
        except Exception as exc:
            # Fail closed: if deliverability can't be verified, reject registration.
            raise ValueError("Correo invalido o no verificable") from exc

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not NICKNAME_REGEX.fullmatch(normalized):
            raise ValueError(
                "Nickname invalido. Usa 3-24 caracteres: minusculas, numeros o guion bajo"
            )
        return normalized


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nickname: str
    is_email_verified: bool
