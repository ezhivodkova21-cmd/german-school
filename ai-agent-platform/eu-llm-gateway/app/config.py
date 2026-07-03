from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gateway_shared_secret: str = "dev-secret-change-me"

    anthropic_api_key: str = ""
    anthropic_default_model: str = "claude-sonnet-5"

    openai_api_key: str = ""
    openai_default_model: str = "gpt-4.1"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
