import sqlite3
from contextlib import closing
from typing import List, Dict, Any
import os

DB_PATH = os.getenv("DB_PATH", "history.db")

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
