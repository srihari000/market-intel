from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    OPENAI_API_KEY: str
    OPENAI_ANALYZER_MODEL: str = "gpt-4o"
    OPENAI_JUDGE_MODEL: str = "gpt-4o-mini"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:5173"
    # LangSmith tracing (optional — tracing disabled if not set)
    LANGSMITH_TRACING: str = "false"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "market-intel"

    class Config:
        env_file = ".env"


settings = Settings()
