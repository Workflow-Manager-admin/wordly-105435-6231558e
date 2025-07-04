import sqlite3
from typing import List, Dict, Any, Optional

DB_PATH = "leaderboard.db"


def _get_connection():
    """Returns a SQLite connection and ensures table exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            solved INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


# PUBLIC_INTERFACE
def save_completed_game(user_id: str, username: str, attempts: int, solved: bool):
    """
    Saves a new completed game to the leaderboard DB.
    """
    conn = _get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO leaderboard (user_id, username, attempts, solved)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, attempts, int(solved)),
        )
    conn.close()


# PUBLIC_INTERFACE
def get_leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieve top leaderboard entries, ranked by fewest attempts, ties resolved by earliest completion.
    """
    conn = _get_connection()
    cur = conn.execute(
        """
        SELECT username, attempts, timestamp
        FROM leaderboard
        WHERE solved=1
        ORDER BY attempts ASC, timestamp ASC
        LIMIT ?
        """,
        (limit,),
    )
    entries = [
        {
            "rank": idx + 1,
            "username": row["username"],
            "attempts": row["attempts"],
            "timestamp": row["timestamp"]
        }
        for idx, row in enumerate(cur.fetchall())
    ]
    conn.close()
    return entries


# PUBLIC_INTERFACE
def get_user_best(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the user's best performance that is a solved entry. Returns None if N/A.
    """
    conn = _get_connection()
    cur = conn.execute(
        """
        SELECT username, attempts, timestamp
        FROM leaderboard
        WHERE user_id=? AND solved=1
        ORDER BY attempts ASC, timestamp ASC
        LIMIT 1
        """,
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(username=row["username"], attempts=row["attempts"], timestamp=row["timestamp"])
    return None
