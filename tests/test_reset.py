from bot.services.state import UserState, reset_state


def test_reset_clears_dialog_and_updates_time():
    state = UserState(
        user_id=123,
        name="Test",
        created_at="2025-01-01T00:00:00",
        last_reset_at="2025-01-01T00:00:00",
        dialog_context=[
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте"},
        ],
        requests_count=5,
        violations_count=1,
    )

    old_reset = state.last_reset_at
    new_state = reset_state(state)

    assert new_state.dialog_context == []
    assert new_state.last_reset_at != old_reset
