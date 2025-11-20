from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict


@dataclass
class UserState:
    user_id: int
    name: str
    created_at: str
    last_reset_at: str
    dialog_context: List[Dict[str, str]] = field(default_factory=list)
    requests_count: int = 0
    violations_count: int = 0
    mode: str = "default"


def reset_state(state: UserState) -> UserState:
    state.dialog_context = []
    state.last_reset_at = datetime.utcnow().isoformat()
    return state
