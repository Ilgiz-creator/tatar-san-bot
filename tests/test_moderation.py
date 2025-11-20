from bot.services import moderation


def test_moderation_clean_text():
    text = "Привет, как дела?"
    assert moderation.contains_local_profanity(text) is False


def test_moderation_profanity_text():
    text = "ты блядь"
    assert moderation.contains_local_profanity(text) is True
