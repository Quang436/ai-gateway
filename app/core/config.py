from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "AI Gateway Service"
    APP_ENV: str = "development"
    PORT: int = 8000

    DATABASE_URL: str
    REDIS_URL: str

    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEFAULT_GATEWAY_API_KEY: str = "gw-test-secret-key-12345"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore")

settings = Settings()