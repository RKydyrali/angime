from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Core ---
    POSTGRES_URL: str = "postgresql+asyncpg://angime:angime@localhost:5432/angime"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    APP_BASE_URL: str = "http://localhost:8000"   # внешний URL вебхука

    # --- AI (OpenRouter) ---
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_AUDIO_MODEL: str = "openai/gpt-audio-mini"

    # --- Telegram (уведомления + админ) ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""

    # --- Админка ---
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    # --- Meta Cloud API ---
    META_GRAPH_VERSION: str = "v21.0"

    # --- Подписки ---
    DEFAULT_SUBSCRIPTION_PRICE: int = 20000
    DEFAULT_SUBSCRIPTION_PLAN: str = "monthly"

    # --- Напоминания ---
    REMINDER_CHECK_SECONDS: int = 60

    # --- Опционально ---
    SENTRY_DSN: str = ""
    RATE_LIMIT_PER_SENDER: int = 60
    RATE_LIMIT_WINDOW: int = 60
    DEBOUNCE_SECONDS: float = 2.5
    DEBOUNCE_MAX_SECONDS: float = 8.0

    model_config = {"env_file": ".env", "extra": "ignore"}


config = Settings()
