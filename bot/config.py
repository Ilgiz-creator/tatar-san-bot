import os
import sys
from dataclasses import dataclass


@dataclass
class Settings:
    telegram_token: str
    openai_api_key: str
    db_path: str = "bot.db"
    chat_model: str = "gpt-4.1-mini"
    system_prompt: str = (
        "Ты — дружелюбный и полезный ассистент в Telegram-боте, "
        "созданном в рамках хакатона TATAR SAN командой «Инь Ян». "
        "Отвечай вежливо, по делу и на том языке, на котором задают вопрос. "
        "Если вопрос неясен — запроси уточнение. "
        "Избегай токсичности, оскорблений и запрещённого контента."
    )


def load_settings() -> Settings:
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    db_path = os.getenv("DB_PATH", "bot.db")

    missing = []
    if not tg_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not openai_key:
        missing.append("OPENAI_API_KEY")

    if missing:
        sys.stderr.write(
            f"ERROR: Missing environment variables: {', '.join(missing)}\n"
        )
        sys.exit(1)

    return Settings(
        telegram_token=tg_token,
        openai_api_key=openai_key,
        db_path=db_path,
    )


SETTINGS = load_settings()
