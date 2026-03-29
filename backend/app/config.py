from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    mineru_api_url: str = ""
    mineru_api_key: str = ""

    ai_api_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""
    ai_model: str = "deepseek-chat"

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 100

    class Config:
        env_file = ".env"

settings = Settings()
