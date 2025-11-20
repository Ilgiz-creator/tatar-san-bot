import logging
from typing import Dict
from uuid import uuid4

from telegram import Update
from telegram.ext import ContextTypes

from bot.services import storage, ai_client

logger = logging.getLogger(__name__)

PENDING_PARAPHRASES: Dict[str, Dict] = {}


def create_paraphrase_session(user_id: int, original: str, paraphrased: str) -> str:
    token = str(uuid4())
    PENDING_PARAPHRASES[token] = {
        "user_id": user_id,
        "original": original,
        "paraphrased": paraphrased,
    }
    return token


async def handle_paraphrase_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("PARAPHRASE_"):
        return

    try:
        action, token = data.split(":", maxsplit=1)
    except ValueError:
        return

    session = PENDING_PARAPHRASES.get(token)
    if not session:
        await query.edit_message_text(
            "Сессия перефразирования уже недоступна. Попробуйте сформулировать запрос заново."
        )
        return

    user_id = query.from_user.id
    if session["user_id"] != user_id:
        await query.edit_message_text("Эта сессия перефразирования не для вас.")
        return

    if action == "PARAPHRASE_ACCEPT":
        paraphrased = session["paraphrased"]
        PENDING_PARAPHRASES.pop(token, None)

        dialog = storage.get_last_messages(user_id, limit=20)
        answer = ai_client.generate_answer(dialog, paraphrased)

        storage.add_message(user_id, "user", paraphrased)
        storage.add_message(user_id, "assistant", answer)
        storage.increment_requests(user_id, 1)

        await query.edit_message_text(
            text=(
                "Отправляю перефразированный запрос и отвечаю на него:\n\n"
                f"«{paraphrased}»\n\n"
                f"Ответ:\n{answer}"
            )
        )
    elif action == "PARAPHRASE_REJECT":
        PENDING_PARAPHRASES.pop(token, None)
        await query.edit_message_text(
            "Окей, не буду отправлять этот вариант 😊\n"
            "Ты можешь сам отредактировать свой запрос и прислать его заново — "
            "я снова помогу с проверкой и ответом."
        )
