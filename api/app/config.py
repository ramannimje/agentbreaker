from pydantic import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://agentbreaker:agentbreaker_dev_password@localhost:5432/agentbreaker"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
