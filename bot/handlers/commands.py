from typing import Optional

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services import storage

START_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["💬 Задать вопрос"],
        ["ℹ️ Помощь", "🧹 Сбросить контекст"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username: Optional[str] = user.username
    first_name: Optional[str] = user.first_name

    storage.get_or_create_user(user_id, username, first_name)

    text = (
        f"Привет, {first_name or 'друг'}! 👋\n\n"
        "Я — AI-бот, созданный в рамках хакатона TATAR SAN командой «Инь Ян».\n\n"
        "Могу:\n"
        "• отвечать на вопросы,\n"
        "• помогать с идеями и текстами,\n"
        "• вести диалог, запоминая контекст,\n"
        "• фильтровать нежелательный контент.\n\n"
        "Просто напиши свой вопрос или выбери кнопку ниже 👇"
    )

    await update.message.reply_text(text, reply_markup=START_KEYBOARD)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Что я умею:\n"
        "• Отвечать на вопросы (учёба, код, идеи, тексты).\n"
        "• Объяснять сложные темы простыми словами.\n"
        "• Продолжать разговор, опираясь на предыдущие сообщения.\n\n"
        "Команды:\n"
        "/start — начать заново\n"
        "/help — эта подсказка\n"
        "/about — о боте и команде\n"
        "/reset — сбросить контекст диалога"
    )
    await update.message.reply_text(text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Этот бот сделан в рамках хакатона TATAR SAN.\n"
        "Команда: «Инь Ян».\n\n"
        "Под капотом — Telegram Bot API + AI-модель (OpenAI) + фильтрация нежелательного контента.\n"
        "Репозиторий: (сюда можно вставить ссылку на GitHub)"
    )
    await update.message.reply_text(text)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    user_id = user.id

    storage.reset_dialog(user_id)

    text = (
        "Контекст нашего диалога очищен 🧹\n"
        "Можем начинать новый разговор — просто напиши сообщение."
    )
    await update.message.reply_text(text)
