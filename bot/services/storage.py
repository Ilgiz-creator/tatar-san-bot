import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

from bot.config import SETTINGS

_db_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(SETTINGS.db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    conn = _get_conn()
    with _db_lock:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_at TEXT,
                last_reset_at TEXT,
                total_requests INTEGER DEFAULT 0,
                violations_count INTEGER DEFAULT 0,
                is_muted INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )
        conn.commit()


def get_or_create_user(
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
) -> Dict[str, Any]:
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    with _db_lock:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE users
                SET username = ?, first_name = ?
                WHERE user_id = ?
                """,
                (username, first_name, user_id),
            )
            conn.commit()
            return dict(row)
        else:
            cur.execute(
                """
                INSERT INTO users (user_id, username, first_name, registered_at, last_reset_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, first_name, now, now),
            )
            conn.commit()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(cur.fetchone())


def increment_requests(user_id: int, delta: int = 1) -> None:
    conn = _get_conn()
    with _db_lock:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET total_requests = total_requests + ? WHERE user_id = ?",
            (delta, user_id),
        )
        conn.commit()


def increment_violations(user_id: int, delta: int = 1) -> int:
    conn = _get_conn()
    with _db_lock:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET violations_count = violations_count + ?
            WHERE user_id = ?
            """,
            (delta, user_id),
        )
        cur.execute(
            "SELECT violations_count FROM users WHERE user_id = ?", (user_id,)
        )
        row = cur.fetchone()
        conn.commit()
        return row["violations_count"] if row else 0


def set_muted(user_id: int, muted: bool) -> None:
    conn = _get_conn()
    with _db_lock:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET is_muted = ? WHERE user_id = ?",
            (1 if muted else 0, user_id),
        )
        conn.commit()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    with _db_lock:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def reset_dialog(user_id: int) -> None:
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    with _db_lock:
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        cur.execute(
            "UPDATE users SET last_reset_at = ? WHERE user_id = ?",
            (now, user_id),
        )
        conn.commit()


def add_message(user_id: int, role: str, content: str) -> None:
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    with _db_lock:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO messages (user_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role, content, now),
        )
        conn.commit()


def get_last_messages(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    conn = _get_conn()
    with _db_lock:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
        result = [dict(r) for r in rows]
        result.reverse()
        return result
