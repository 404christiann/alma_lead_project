from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    RESEND_API_KEY: str
    ATTORNEY_EMAIL: str
    RESEND_FROM_EMAIL: str
    MINIO_ENDPOINT_URL: str
    MINIO_PUBLIC_URL: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "resumes"
    PRESIGNED_URL_TTL_SECONDS: int = 3600
    CORS_ORIGINS: list[str]
    MAX_FILE_BYTES: int = 10_485_760


@lru_cache
def get_settings() -> Settings:
    return Settings()
