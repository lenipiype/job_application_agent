import logging
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

logger = logging.getLogger(__name__)

POSITIONS = {
    "Kitchen": "documents/Kitchen",
    "Cafe": "documents/Cafe",
    "Warehouse": "documents/Warehouse",
}

def get_pdf_attachments(category: str) -> list[Path]:
    """Scan the position's directory and return all PDF file paths."""
    if category not in POSITIONS:
        logger.warning(f"Unknown position category: {category}")
        return []

    folder = Path(POSITIONS[category])
    if not folder.exists():
        logger.warning(f"Category folder does not exist: {folder}")
        return []

    return [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]

def send_email_with_retry(
    to_email: str,
    subject: str,
    body: str,
    attachments: list[Path]
) -> None:
    """Send an email via SMTP with attachments. Retries up to 3 times with exponential backoff."""
    sender_email = os.getenv("EMAIL_ADDRESS")
    smtp_login = os.getenv("SMTP_LOGIN")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")

    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except (TypeError, ValueError):
        smtp_port = 587

    if not sender_email or not smtp_login or not smtp_password:
        raise ValueError("Missing email SMTP credentials in environment variables.")

    # Create the email message
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # Attach all PDFs
    for path in attachments:
        if not path.exists():
            logger.warning(f"Attachment file not found: {path}")
            continue
        try:
            with open(path, "rb") as f:
                file_data = f.read()
                file_name = path.name
                msg.add_attachment(
                    file_data,
                    maintype="application",
                    subtype="pdf",
                    filename=file_name
                )
            logger.info(f"Successfully attached file: {file_name}")
        except Exception as e:
            logger.error(f"Failed to attach {path}: {e}")
            raise

    # Exponential backoff parameters
    max_attempts = 3
    delay = 2  # start at 2s
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                f"Attempting to send email to {to_email} "
                f"(Attempt {attempt}/{max_attempts})..."
            )

            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(smtp_login, smtp_password)
                smtp.send_message(msg)

            logger.info(f"Email sent successfully to {to_email} on attempt {attempt}.")
            return
        except Exception as e:
            logger.warning(f"Email sending attempt {attempt} failed: {e}")
            last_exception = e
            if attempt < max_attempts:
                logger.info(f"Waiting {delay} seconds before retrying...")
                time.sleep(delay)
                delay *= 2

    # If we reached here, all attempts failed
    logger.error(f"Failed to send email to {to_email} after {max_attempts} attempts.")
    raise last_exception or RuntimeError("SMTP send failed.")
