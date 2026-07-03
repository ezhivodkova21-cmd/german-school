from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./app.db"
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    eu_gateway_url: str = "http://localhost:8100"
    gateway_shared_secret: str = "dev-secret-change-me"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
