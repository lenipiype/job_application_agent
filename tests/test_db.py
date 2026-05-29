import os
import tempfile

import pytest

from src import database


@pytest.fixture(autouse=True)
def setup_temp_db(monkeypatch):
    """Fixture to set up a temporary isolated SQLite database for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name

    # Patch DB_PATH to use our temporary file
    monkeypatch.setattr(database, "DB_PATH", temp_db_path)

    # Initialize schema
    database.init_db()

    yield temp_db_path

    # Cleanup after test runs
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except Exception:
            pass

def test_init_db():
    """Verify table creation works and table structure is present."""
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='applications'")
        row = cursor.fetchone()
        assert row is not None
        assert row["name"] == "applications"

def test_log_and_get_recent():
    """Test inserting an application log and retrieving it."""
    database.log_application(
        category="Kitchen",
        recipient_email="recruiter@kfc.at",
        subject="Bewerbung als Küchenhilfe",
        body="Sehr geehrte Damen und Herren...",
        attachments="cv.pdf,experience.pdf",
        status="SUCCESS"
    )

    recent = database.get_recent_applications(5)
    assert len(recent) == 1
    assert recent[0]["category"] == "Kitchen"
    assert recent[0]["recipient_email"] == "recruiter@kfc.at"
    assert recent[0]["subject"] == "Bewerbung als Küchenhilfe"
    assert recent[0]["status"] == "SUCCESS"

def test_get_stats():
    """Test stats computation counts only SUCCESS applications correctly.

    The counts should be grouped by category.
    """
    database.log_application("Kitchen", "k1@test.com", "Subj", "Body", "cv.pdf", "SUCCESS")
    database.log_application("Kitchen", "k2@test.com", "Subj", "Body", "cv.pdf", "SUCCESS")
    database.log_application("Cafe", "c1@test.com", "Subj", "Body", "cv.pdf", "SUCCESS")
    # FAILED should be omitted from success stats
    database.log_application(
        "Warehouse", "w1@test.com", "Subj", "Body", "cv.pdf", "FAILED"
    )

    stats = database.get_stats()
    assert stats["Kitchen"] == 2
    assert stats["Cafe"] == 1
    assert stats["Warehouse"] == 0
