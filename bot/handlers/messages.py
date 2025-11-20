import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from bot.services import storage, moderation, ai_client
from bot.handlers.callbacks import create_paraphrase_session
from bot.handlers import commands

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000
MAX_VIOLATIONS_BEFORE_MUTE = 3


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    user = update.effective_user
    if not user:
        return

    user_id = user.id
    username = user.username
    first_name = user.first_name
    text = message.text or ""
    normalized_text = text.strip().lower()

    # --- ОБРАБОТКА КНОПОК REPLY-КЛАВИАТУРЫ ---
    if text == "ℹ️ Помощь":
        await commands.help_command(update, context)
        return

    if text == "🧹 Сбросить контекст":
        await commands.reset_command(update, context)
        return

    if text == "💬 Задать вопрос":
        await message.reply_text(
            "Напиши свой вопрос ниже — я постараюсь помочь 🙂"
        )
        return
    # -----------------------------------------

    logger.info(
        "INCOMING_MESSAGE user_id=%s username=%s text=%r",
        user_id,
        username,
        text,
    )

    # Регистрируем / обновляем пользователя
    user_row = storage.get_or_create_user(user_id, username, first_name)

    # --- ПОВЕДЕНИЕ, ЕСЛИ ПОЛЬЗОВАТЕЛЬ В МЬЮТЕ ---
    if user_row.get("is_muted"):
        # Снятие бана по слову "пожалуйста" (регистр не важен, одно слово)
        if normalized_text == "пожалуйста":
            storage.set_muted(user_id, False)
            await message.reply_text(
                "Спасибо за вежливость 🙂 Я снял ограничение, можем продолжать общение."
            )
        else:
            await message.reply_text(
                "Вы несколько раз отправили сообщения с ненормативной лексикой или нарушающие правила. "
                "Временно не могу отвечать.\n\n"
                "Чтобы снять ограничение, напишите одним словом: «пожалуйста»."
            )
        return
    # -------------------------------------------

    # Ограничение длины
    if len(text) > MAX_MESSAGE_LENGTH:
        await message.reply_text(
            f"Сообщение слишком длинное (> {MAX_MESSAGE_LENGTH} символов). "
            "Пожалуйста, сократите его и отправьте снова."
        )
        return

    # Показываем, что бот "печатает"
    await context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.TYPING,
    )

    # -------- ЛОКАЛЬНЫЙ ФИЛЬТР МАТА --------
    if moderation.contains_local_profanity(text):
        new_count = storage.increment_violations(user_id, 1)
        logger.info(
            "LOCAL_PROFANITY_DETECTED user_id=%s violations=%s text=%r",
            user_id,
            new_count,
            text,
        )

        if new_count >= MAX_VIOLATIONS_BEFORE_MUTE:
            storage.set_muted(user_id, True)
            await message.reply_text(
                "Вы несколько раз отправили сообщения с ненормативной лексикой. "
                "Временно не могу отвечать.\n\n"
                "Чтобы снять ограничение, напишите одним словом: «пожалуйста»."
            )
            return

        # Пытаемся перефразировать через OpenAI
        try:
            paraphrased = ai_client.paraphrase_message(text, reason="profanity")
        except Exception as e:
            logger.exception(
                "PARAPHRASE_ERROR_LOCAL user_id=%s error=%s", user_id, e
            )
            await message.reply_text(
                "Сообщение содержит ненормативную лексику, и у меня сейчас "
                "не получилось предложить корректный вариант формулировки.\n\n"
                "Пожалуйста, перефразируй его более нейтрально и отправь ещё раз 🙂"
            )
            return

        token = create_paraphrase_session(user_id, text, paraphrased)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Отправить этот вариант",
                        callback_data=f"PARAPHRASE_ACCEPT:{token}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "❌ Не отправлять",
                        callback_data=f"PARAPHRASE_REJECT:{token}",
                    ),
                ],
            ]
        )

        reply_text = (
            "Похоже, в сообщении есть ненормативная лексика, мы не можем отвечать на подобные сообщения.\n\n"
            "Предлагаю перефразировать так:\n"
            f"«{paraphrased}»\n\n"
            "Отправить этот вариант?"
        )
        await message.reply_text(reply_text, reply_markup=keyboard)
        return

    # -------- MODERATION OPENAI --------
    mod_result = moderation.check_openai_moderation(text)
    if mod_result.blocked:
        new_count = storage.increment_violations(user_id, 1)
        logger.info(
            "OPENAI_MODERATION_BLOCKED user_id=%s violations=%s categories=%s text=%r",
            user_id,
            new_count,
            mod_result.categories,
            text,
        )

        if new_count >= MAX_VIOLATIONS_BEFORE_MUTE:
            storage.set_muted(user_id, True)
            await message.reply_text(
                "Вы несколько раз отправили сообщения, нарушающие правила. "
                "Временно не могу отвечать.\n\n"
                "Чтобы снять ограничение, напишите одним словом: «пожалуйста»."
            )
            return

        try:
            paraphrased = ai_client.paraphrase_message(text, reason="moderation")
        except Exception as e:
            logger.exception(
                "PARAPHRASE_ERROR_OPENAI user_id=%s error=%s", user_id, e
            )
            await message.reply_text(
                "Сообщение нарушает правила, и у меня сейчас не получилось "
                "предложить безопасный вариант формулировки.\n\n"
                "Пожалуйста, перепиши его более корректно и отправь ещё раз 🙂"
            )
            return

        token = create_paraphrase_session(user_id, text, paraphrased)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Отправить этот вариант",
                        callback_data=f"PARAPHRASE_ACCEPT:{token}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "❌ Не отправлять",
                        callback_data=f"PARAPHRASE_REJECT:{token}",
                    ),
                ],
            ]
        )

        reply_text = (
            "Я не могу обработать это сообщение, потому что оно нарушает правила использования.\n\n"
            "Предлагаю перефразировать так:\n"
            f"«{paraphrased}»\n\n"
            "Отправить этот вариант?"
        )
        await message.reply_text(reply_text, reply_markup=keyboard)
        return

    # -------- ЗАПРОС К AI-МОДЕЛИ --------
    dialog = storage.get_last_messages(user_id, limit=20)

    try:
        answer = ai_client.generate_answer(dialog, text)
    except Exception as e:
        logger.exception("AI_ERROR user_id=%s error=%s", user_id, e)
        await message.reply_text(
            "Сейчас у меня не получилось получить ответ от модели 🤖\n"
            "Попробуй, пожалуйста, ещё раз чуть позже или переформулируй вопрос."
        )
        return

    if not answer or not answer.strip():
        logger.warning("EMPTY_AI_RESPONSE user_id=%s text=%r", user_id, text)
        await message.reply_text(
            "Модель вернула пустой ответ 😕\n"
            "Попробуй задать вопрос по-другому."
        )
        return

    logger.info(
        "AI_RESPONSE user_id=%s in_len=%d out_len=%d",
        user_id,
        len(text),
        len(answer),
    )

    storage.add_message(user_id, "user", text)
    storage.add_message(user_id, "assistant", answer)
    storage.increment_requests(user_id, 1)

    await message.reply_text(answer)
