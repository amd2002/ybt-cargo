from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "YBT Cargo Manager"
    SECRET_KEY: str = "change-me"
    DEBUG: bool = False

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "ybt-cargo-pdfs"
    R2_PUBLIC_URL: str = ""

    RATE_SIERRA_LEONE: float = 280.0
    RATE_GUINEE: float = 340.0

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    class Config:
        env_file = ".env"

settings = Settings()
