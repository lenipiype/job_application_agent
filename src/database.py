import logging
import sqlite3
from pathlib import Path

from src.config import DB_PATH

logger = logging.getLogger(__name__)

def get_db_connection() -> sqlite3.Connection:
    """Connect to SQLite database and ensure directories exist."""
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initialize the SQLite database schema if not present."""
    logger.info("Initializing SQLite database...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                attachments TEXT,
                status TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info("Database initialized successfully.")

def log_application(
    category: str,
    recipient_email: str,
    subject: str,
    body: str,
    attachments: str,
    status: str
) -> None:
    """Insert a new job application log into the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO applications (category, recipient_email, subject, body, attachments, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (category, recipient_email, subject, body, attachments, status))
        conn.commit()
    logger.info(f"Logged application to {recipient_email} as {status}")

def get_recent_applications(limit: int = 10) -> list[dict]:
    """Retrieve the last N applications sent."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, recipient_email, subject, sent_at, status
            FROM applications
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_stats() -> dict[str, int]:
    """Get the total successful applications sent, grouped by category."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM applications
            WHERE status = 'SUCCESS'
            GROUP BY category
        """)
        rows = cursor.fetchall()

        stats = {"Kitchen": 0, "Cafe": 0, "Warehouse": 0}
        for row in rows:
            cat = row["category"]
            if cat in stats:
                stats[cat] = row["count"]
        return stats
