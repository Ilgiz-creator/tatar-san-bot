import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from bot.config import SETTINGS
from bot.handlers import commands, messages, callbacks
from bot.services import storage


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting bot with DB at %s", SETTINGS.db_path)

    storage.init_db()

    application = ApplicationBuilder().token(SETTINGS.telegram_token).build()

    application.add_handler(CommandHandler("start", commands.start))
    application.add_handler(CommandHandler("help", commands.help_command))
    application.add_handler(CommandHandler("about", commands.about_command))
    application.add_handler(CommandHandler("reset", commands.reset_command))

    application.add_handler(CallbackQueryHandler(callbacks.handle_paraphrase_callback))

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            messages.handle_text_message,
        )
    )

    logger.info("Bot is running. Waiting for updates...")
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
