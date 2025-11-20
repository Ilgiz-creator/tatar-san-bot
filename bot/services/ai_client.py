from typing import List, Dict

from openai import OpenAI

from bot.config import SETTINGS

# Клиент OpenAI. Ключ берём из настроек.
_client = OpenAI(api_key=SETTINGS.openai_api_key)


def build_chat_input(
    dialog_context: List[Dict[str, str]],
    user_message: str,
) -> list:
    """
    Собираем список сообщений для chat.completions:
    - системное сообщение с ролью бота,
    - контекст диалога (предыдущие реплики),
    - текущий запрос пользователя.
    """
    messages = [
        {
            "role": "system",
            "content": SETTINGS.system_prompt,
        }
    ]
    for msg in dialog_context:
        messages.append(
            {
                "role": msg["role"],
                "content": msg["content"],
            }
        )
    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )
    return messages


def generate_answer(
    dialog_context: List[Dict[str, str]],
    user_message: str,
) -> str:
    """
    Основная функция: отправляем контекст + запрос в модель и
    возвращаем текст её ответа.
    """
    messages = build_chat_input(dialog_context, user_message)

    resp = _client.chat.completions.create(
        model=SETTINGS.chat_model,  # например, gpt-4.1-mini или gpt-4o-mini
        messages=messages,
    )

    # Берём текст первого ответа
    return resp.choices[0].message.content.strip()


def paraphrase_message(
    original_text: str,
    reason: str = "profanity",
) -> str:
    """
    Перефразирование сообщения, чтобы убрать мат/токсичность, но
    сохранить смысл и язык.
    """
    prompt = (
        "Перефразируй сообщение пользователя так, чтобы оно не содержало мата, "
        "оскорблений, дискриминации или призывов к насилию. "
        "Сохрани исходный смысл и язык сообщения. "
        "Верни только новый вариант сообщения, без пояснений.\n\n"
        f"Исходное сообщение: «{original_text}»"
    )

    resp = _client.chat.completions.create(
        model=SETTINGS.chat_model,
        messages=[
            {
                "role": "system",
                "content": "Ты помощник по перефразированию сообщений.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    return resp.choices[0].message.content.strip()
