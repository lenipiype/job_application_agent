import smtplib
from unittest.mock import MagicMock, patch

import pytest

from src import email_sender


def test_get_pdf_attachments(tmp_path, monkeypatch):
    """Test that get_pdf_attachments retrieves only PDF files from the correct folder."""
    # Setup mock positions mapping to our temp directory folders
    mock_positions = {
        "Kitchen": str(tmp_path / "Kitchen"),
        "Cafe": str(tmp_path / "Cafe")
    }
    monkeypatch.setattr(email_sender, "POSITIONS", mock_positions)

    # Create category directories
    (tmp_path / "Kitchen").mkdir()
    (tmp_path / "Cafe").mkdir()

    # Populate Kitchen folder with some mock files
    (tmp_path / "Kitchen" / "Leni_cv.pdf").write_text("PDF content")
    (tmp_path / "Kitchen" / "Certificate.PDF").write_text("PDF content uppercase")
    (tmp_path / "Kitchen" / "notes.txt").write_text("Plain text")

    pdfs = email_sender.get_pdf_attachments("Kitchen")
    file_names = [p.name for p in pdfs]

    assert len(pdfs) == 2
    assert "Leni_cv.pdf" in file_names
    assert "Certificate.PDF" in file_names
    assert "notes.txt" not in file_names

@patch("smtplib.SMTP")
@patch("time.sleep")
def test_send_email_success(mock_sleep, mock_smtp_class, monkeypatch):
    """Verify that SMTP operations are executed on first success."""
    monkeypatch.setenv("EMAIL_ADDRESS", "sender@test.com")
    monkeypatch.setenv("SMTP_LOGIN", "login_user")
    monkeypatch.setenv("SMTP_PASSWORD", "pwd")

    mock_smtp = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp

    email_sender.send_email_with_retry("recipient@test.com", "Test Subject", "Test Body", [])

    assert mock_smtp_class.call_count == 1
    assert mock_smtp.starttls.call_count == 1
    assert mock_smtp.login.call_count == 1
    assert mock_smtp.send_message.call_count == 1
    assert mock_sleep.call_count == 0  # No retry sleeps needed

@patch("smtplib.SMTP")
@patch("time.sleep")
def test_send_email_retry_to_success(mock_sleep, mock_smtp_class, monkeypatch):
    """Verify SMTP retries up to 3 times and succeeds on the third attempt."""
    monkeypatch.setenv("EMAIL_ADDRESS", "sender@test.com")
    monkeypatch.setenv("SMTP_LOGIN", "login_user")
    monkeypatch.setenv("SMTP_PASSWORD", "pwd")

    mock_smtp = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp

    # Mock send_message to fail twice and succeed once
    mock_smtp.send_message.side_effect = [
        smtplib.SMTPConnectError(101, "Connection failed"),
        smtplib.SMTPConnectError(101, "Connection failed"),
        None
    ]

    email_sender.send_email_with_retry("recipient@test.com", "Test Subject", "Test Body", [])

    assert mock_smtp.send_message.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(2)
    mock_sleep.assert_any_call(4)

@patch("smtplib.SMTP")
@patch("time.sleep")
def test_send_email_fails_all_retries(mock_sleep, mock_smtp_class, monkeypatch):
    """Verify SMTP raises exception if all 3 attempts fail."""
    monkeypatch.setenv("EMAIL_ADDRESS", "sender@test.com")
    monkeypatch.setenv("SMTP_LOGIN", "login_user")
    monkeypatch.setenv("SMTP_PASSWORD", "pwd")

    mock_smtp = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp
    mock_smtp.send_message.side_effect = smtplib.SMTPException("Perm Error")

    with pytest.raises(smtplib.SMTPException, match="Perm Error"):
        email_sender.send_email_with_retry("recipient@test.com", "Test Subject", "Test Body", [])

    assert mock_smtp.send_message.call_count == 3
    assert mock_sleep.call_count == 2
