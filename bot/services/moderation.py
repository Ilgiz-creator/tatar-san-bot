from dataclasses import dataclass
from typing import Dict, Any

from profanityfilter import ProfanityFilter
from openai import OpenAI

from bot.config import SETTINGS

# Наш дополнительный список матерных/оскорбительных слов
_EXTRA_WORDS = {
    # Русский мат/токсик
    "блядь",
    "блять",
    "бля",
    "хуй",
    "хер",
    "пизда",
    "сука",
    "ублюдок",
    "мразь",
    "говно",
    "ебать",
    "ебаный",
    "пидор",
    "пидарас",
    "мудак",
    "хуесос",
    "уебок",
    "уёбок",
    # Английский
    "fuck",
    "fucking",
    "motherfucker",
    "bitch",
    "bastard",
    "asshole",
    "dick",
    "cunt",
    "shit",
    "bullshit",
}

# Библиотека сама знает англ. список, мы добавляем свои слова
_pf = ProfanityFilter(extra_censor_list=list(_EXTRA_WORDS))

_openai_client = OpenAI(api_key=SETTINGS.openai_api_key)


@dataclass
class ModerationResult:
    blocked: bool
    source: str  # 'local' | 'openai' | 'none'
    categories: Dict[str, Any]


def contains_local_profanity(text: str) -> bool:
    """
    Быстрый локальный чек на мат/брань.

    Делаем двойную защиту:
    1) Явно ищем наши слова-подстроки в тексте (lowercase).
    2) Потом даём поработать библиотеке profanityfilter.
    """
    try:
        low = text.lower()
        for bad in _EXTRA_WORDS:
            if bad in low:
                return True

        return _pf.is_profane(text)
    except Exception:
        # Если что-то пошло не так — не валим бота
        return False


def censor_local(text: str) -> str:
    """
    Локальное «замыливание» текста, если понадобится.
    """
    try:
        return _pf.censor(text)
    except Exception:
        return text


def check_openai_moderation(text: str) -> ModerationResult:
    """
    Проверка через OpenAI Moderation API.
    Если что-то ломается — считаем, что текст "чистый",
    чтобы не блокировать пользователя из-за проблем сервиса.
    """
    try:
        resp = _openai_client.moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
        result = resp.results[0]
        categories = dict(result.categories)
        blocked = bool(result.flagged)
        return ModerationResult(
            blocked=blocked,
            source="openai" if blocked else "none",
            categories=categories,
        )
    except Exception:
        return ModerationResult(blocked=False, source="none", categories={})
