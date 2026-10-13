import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    bot_username: str = os.getenv("BOT_USERNAME", "").lstrip("@")
    admin_ids: set[int] = {
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.strip().isdigit()
    }
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_base_url: str | None = os.getenv("ANTHROPIC_BASE_URL") or None
    llm_model: str = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./coverbot.db")
    # Хранилище состояний диалогов (анкета, поиск). Пусто — в памяти, сбрасывается при рестарте
    redis_url: str | None = os.getenv("REDIS_URL") or None
    # Этап 1 — копим базу групп: поиск для продюсеров выключен, вместо него заглушка
    search_enabled: bool = os.getenv("SEARCH_ENABLED", "false").strip().lower() in ("1", "true", "yes")
    page_size: int = 5


settings = Settings()
