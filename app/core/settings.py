import os


def _split_origins(value: str) -> list[str]:
    if not value:
        return []
    if value.strip() == "*":
        return ["*"]
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./r2.db")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "8"))
    allowed_origins: list[str] = _split_origins(os.getenv("ALLOWED_ORIGINS", "*"))
    apple_audience: str = os.getenv("APPLE_AUDIENCE", "")
    email_check_deliverability: bool = _to_bool(
        os.getenv("EMAIL_CHECK_DELIVERABILITY"),
        default=env.lower() == "production",
    )


settings = Settings()
