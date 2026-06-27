from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    # --- OpenAI Direct (active) ---
    OPENAI_API_KEY: str
    OPENAI_ANALYZER_MODEL: str = "gpt-4o"
    OPENAI_JUDGE_MODEL: str = "gpt-4o-mini"

    # --- Azure OpenAI (uncomment to switch from direct OpenAI to Azure OpenAI) ---
    # AZURE_OPENAI_API_KEY: str
    # AZURE_OPENAI_ENDPOINT: str
    # AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    # AZURE_OPENAI_API_VERSION: str = "2024-02-01"

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
