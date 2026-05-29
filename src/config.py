import logging
import os

from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

# Logger setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Essential Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_LOGIN = os.getenv("SMTP_LOGIN")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
DB_PATH = os.getenv("DB_PATH", "data/applications.db")
PORT = int(os.getenv("PORT", "10000"))

# Whitelist environment
ALLOWED_USER_IDS_STR = os.getenv("ALLOWED_USER_IDS", "")

def get_allowed_user_ids() -> list[int]:
    """Parse ALLOWED_USER_IDS into a list of integers."""
    if not ALLOWED_USER_IDS_STR:
        return []
    try:
        return [int(uid.strip()) for uid in ALLOWED_USER_IDS_STR.split(",") if uid.strip()]
    except ValueError as e:
        logger.error(f"Failed to parse ALLOWED_USER_IDS: {e}")
        return []

def is_user_allowed(user_id: int) -> bool:
    """Check if the Telegram user ID is whitelisted."""
    allowed_ids = get_allowed_user_ids()
    if not allowed_ids:
        logger.warning("No ALLOWED_USER_IDS configured. Permitting access to all users.")
        return True
    return user_id in allowed_ids
