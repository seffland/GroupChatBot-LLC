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
    # Track TV show recommendations
    conn.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE
        )
    ''')
    # Track which users have watched which recommendations
    conn.execute('''
        CREATE TABLE IF NOT EXISTS recommendations_watched (
            recommendation_id INTEGER,
            username TEXT,
            PRIMARY KEY (recommendation_id, username),
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
        )
    ''')
    # Hall of Fame Quotes table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            message_id INTEGER,
            username TEXT,
            content TEXT,
            quoted_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Channel personalities table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS channel_personalities (
            channel_id INTEGER PRIMARY KEY,
            personality TEXT
        )
    ''')
    # Track user all-time high (ATH) events
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_ath (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            last_ath DATETIME
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
    If days == 0, returns the count for just today (EST), using the same logic as /funniest.
    If days == 'yesterday', returns the count for just yesterday (EST).
    """
    with sqlite3.connect(DB_PATH) as conn:
        if days == 'all':
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE channel_id = ?",
                (channel_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        elif days == 0:
            from datetime import datetime, time, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            today_start_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            today_start_utc = today_start_est.astimezone(timezone.utc)
            today_start_str = today_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM messages
                WHERE channel_id = ? AND timestamp >= ?
                """,
                (channel_id, today_start_str)
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        elif days == 'yesterday':
            from datetime import datetime, time, timedelta, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            yesterday_date = now_est.date() - timedelta(days=1)
            y_start_est = datetime.combine(yesterday_date, time(hour=0, minute=0), tzinfo=eastern)
            y_end_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            y_start_utc = y_start_est.astimezone(timezone.utc)
            y_end_utc = y_end_est.astimezone(timezone.utc)
            y_start_str = y_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            y_end_str = y_end_utc.strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM messages
                WHERE channel_id = ? AND timestamp >= ? AND timestamp < ?
                """,
                (channel_id, y_start_str, y_end_str)
            )
            row = cursor.fetchone()
            return row[0] if row else 0
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

def get_messages_for_timeframe(channel_id: int, timeframe: str) -> List[Dict[str, Any]]:
    """
    Returns all messages in the given channel for the specified timeframe.
    timeframe: 'today', 'yesterday', 'this_month', or 'all'
    """
    with sqlite3.connect(DB_PATH) as conn:
        if timeframe == 'all':
            cursor = conn.execute(
                "SELECT role, username, content FROM messages WHERE channel_id = ? ORDER BY id ASC",
                (channel_id,)
            )
        elif timeframe == 'today':
            from datetime import datetime, time, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            today_start_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            today_start_utc = today_start_est.astimezone(timezone.utc)
            today_start_str = today_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute(
                """
                SELECT role, username, content FROM messages
                WHERE channel_id = ? AND timestamp >= ?
                ORDER BY id ASC
                """,
                (channel_id, today_start_str)
            )
        elif timeframe == 'yesterday':
            from datetime import datetime, time, timedelta, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            yesterday_date = now_est.date() - timedelta(days=1)
            y_start_est = datetime.combine(yesterday_date, time(hour=0, minute=0), tzinfo=eastern)
            y_end_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            y_start_utc = y_start_est.astimezone(timezone.utc)
            y_end_utc = y_end_est.astimezone(timezone.utc)
            y_start_str = y_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            y_end_str = y_end_utc.strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute(
                """
                SELECT role, username, content FROM messages
                WHERE channel_id = ? AND timestamp >= ? AND timestamp < ?
                ORDER BY id ASC
                """,
                (channel_id, y_start_str, y_end_str)
            )
        elif timeframe == 'this_month':
            from datetime import datetime, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            month_start_est = now_est.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_start_utc = month_start_est.astimezone(timezone.utc)
            month_start_str = month_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute(
                """
                SELECT role, username, content FROM messages
                WHERE channel_id = ? AND timestamp >= ?
                ORDER BY id ASC
                """,
                (channel_id, month_start_str)
            )
        else:
            return []
        rows = cursor.fetchall()
        return [
            {"role": row[0], "username": row[1], "content": row[2]} for row in rows
        ]

def add_recommendation(title: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO recommendations (title) VALUES (?)",
            (title,)
        )
        conn.commit()

def mark_recommendation_watched(title: str, username: str):
    with sqlite3.connect(DB_PATH) as conn:
        # Get recommendation id
        cursor = conn.execute(
            "SELECT id FROM recommendations WHERE title = ?",
            (title,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Recommendation not found")
        rec_id = row[0]
        conn.execute(
            "INSERT OR IGNORE INTO recommendations_watched (recommendation_id, username) VALUES (?, ?)",
            (rec_id, username)
        )
        conn.commit()

def get_recommendations_with_watchers() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute('''
            SELECT r.title, GROUP_CONCAT(w.username) as watched_by
            FROM recommendations r
            LEFT JOIN recommendations_watched w ON r.id = w.recommendation_id
            GROUP BY r.id
        ''')
        return [
            {"title": row[0], "watched_by": row[1].split(",") if row[1] else []}
            for row in cursor.fetchall()
        ]

def add_quote(channel_id: int, message_id: int, username: str, content: str, quoted_by: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO quotes (channel_id, message_id, username, content, quoted_by) VALUES (?, ?, ?, ?, ?)",
            (channel_id, message_id, username, content, quoted_by)
        )
        conn.commit()

def get_quotes(channel_id: int = None, limit: int = 10):
    with sqlite3.connect(DB_PATH) as conn:
        if channel_id:
            cursor = conn.execute(
                "SELECT username, content, quoted_by, timestamp FROM quotes WHERE channel_id = ? ORDER BY id DESC LIMIT ?",
                (channel_id, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT username, content, quoted_by, timestamp FROM quotes ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        return [
            {"username": row[0], "content": row[1], "quoted_by": row[2], "timestamp": row[3]} for row in cursor.fetchall()
        ]

def set_channel_personality(channel_id: int, personality: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO channel_personalities (channel_id, personality) VALUES (?, ?)",
            (channel_id, personality)
        )
        conn.commit()

def get_channel_personality(channel_id: int) -> str | None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT personality FROM channel_personalities WHERE channel_id = ?",
            (channel_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

def get_user_ath(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT last_ath FROM user_ath WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

def set_user_ath(user_id: int, username: str, timestamp: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_ath (user_id, username, last_ath) VALUES (?, ?, ?)",
            (user_id, username, timestamp)
        )
        conn.commit()
