import sqlite3
from contextlib import closing
from typing import List, Dict, Any
import os

DB_PATH = os.getenv("DB_PATH", "data/history.db")

# Ensure the messages table exists
with sqlite3.connect(DB_PATH) as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            role TEXT,
            username TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Track last imported message per channel
    conn.execute('''
        CREATE TABLE IF NOT EXISTS import_state (
            channel_id INTEGER PRIMARY KEY,
            last_message_id INTEGER
        )
    ''')

def add_message(channel_id: int, role: str, username: str, content: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (channel_id, role, username, content) VALUES (?, ?, ?, ?)",
            (channel_id, role, username, content)
        )
        conn.commit()

def get_history(channel_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT role, username, content FROM messages WHERE channel_id = ? ORDER BY id DESC LIMIT ?",
            (channel_id, limit)
        )
        rows = cursor.fetchall()
        # Reverse to get chronological order
        return [
            {"role": row[0], "username": row[1], "content": row[2]} for row in reversed(rows)
        ]

def search_history(channel_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT role, username, content FROM messages
            WHERE channel_id = ? AND content LIKE ?
            ORDER BY id DESC LIMIT ?
            """,
            (channel_id, f"%{query}%", limit)
        )
        rows = cursor.fetchall()
        return [
            {"role": row[0], "username": row[1], "content": row[2]} for row in rows
        ]

def get_last_imported_message_id(channel_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT last_message_id FROM import_state WHERE channel_id = ?",
            (channel_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

def set_last_imported_message_id(channel_id: int, message_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO import_state (channel_id, last_message_id) VALUES (?, ?)",
            (channel_id, message_id)
        )
        conn.commit()

def get_messages_after_user_last(channel_id: int, username: str) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        # Find the last message id sent by the user in this channel
        cursor = conn.execute(
            """
            SELECT id FROM messages
            WHERE channel_id = ? AND username = ?
            ORDER BY id DESC LIMIT 1
            """,
            (channel_id, username)
        )
        row = cursor.fetchone()
        if not row:
            return []
        last_user_id = row[0]
        # Get all messages after that id
        cursor = conn.execute(
            """
            SELECT role, username, content FROM messages
            WHERE channel_id = ? AND id > ?
            ORDER BY id ASC
            """,
            (channel_id, last_user_id)
        )
        rows = cursor.fetchall()
        return [
            {"role": r[0], "username": r[1], "content": r[2]} for r in rows
        ]

def message_count(channel_id: int, days: int | str) -> int:
    """
    Returns the number of messages sent in the given channel in the last `days` days, or all time if days == 'all'.
    """
    with sqlite3.connect(DB_PATH) as conn:
        if days == 'all':
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE channel_id = ?",
                (channel_id,)
            )
        else:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM messages
                WHERE channel_id = ? AND timestamp >= datetime('now', ?)
                """,
                (channel_id, f'-{days} days')
            )
        row = cursor.fetchone()
        return row[0] if row else 0
