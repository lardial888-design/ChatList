import sqlite3
from typing import Any, Dict, List, Optional


DB_PATH = "chatlist.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                prompt TEXT NOT NULL,
                tags TEXT
            );

            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                api_url TEXT NOT NULL,
                api_key_env TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER NOT NULL,
                model_id INTEGER NOT NULL,
                response_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id),
                FOREIGN KEY (model_id) REFERENCES models(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT
            );
            """
        )


def add_prompt(created_at: str, prompt: str, tags: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO prompts (created_at, prompt, tags) VALUES (?, ?, ?)",
            (created_at, prompt, tags),
        )
        return int(cur.lastrowid)


def list_prompts(limit: int = 100) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, created_at, prompt, tags FROM prompts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def add_model(name: str, api_url: str, api_key_env: str, is_active: int = 1) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO models (name, api_url, api_key_env, is_active) VALUES (?, ?, ?, ?)",
            (name, api_url, api_key_env, is_active),
        )
        return int(cur.lastrowid)


def list_models() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, api_url, api_key_env, is_active FROM models ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def update_model(
    model_id: int, name: str, api_url: str, api_key_env: str, is_active: int
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE models
            SET name = ?, api_url = ?, api_key_env = ?, is_active = ?
            WHERE id = ?
            """,
            (name, api_url, api_key_env, is_active, model_id),
        )


def delete_model(model_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM models WHERE id = ?", (model_id,))


def list_active_models() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, api_url, api_key_env, is_active FROM models WHERE is_active = 1"
        ).fetchall()
    return [dict(row) for row in rows]


def add_result(
    prompt_id: int, model_id: int, response_text: str, created_at: str
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO results (prompt_id, model_id, response_text, created_at) VALUES (?, ?, ?, ?)",
            (prompt_id, model_id, response_text, created_at),
        )
        return int(cur.lastrowid)


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def get_setting(key: str) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    if not row:
        return None
    return row["value"]
