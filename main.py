import logging
import threading

from flask import Flask, jsonify

from src.bot import setup_bot_application
from src.config import PORT

logger = logging.getLogger(__name__)

# Flask web application for health check endpoints
web_app = Flask(__name__)

@web_app.route("/health", methods=["GET"])
def health():
    """Health check endpoint required by deployment platforms."""
    return jsonify({"status": "ok"}), 200

@web_app.route("/", methods=["GET"])
def home():
    """Default route."""
    return "Job Application Bot is running.", 200

def run_web():
    """Run Flask server in a separate background thread."""
    try:
        logger.info(f"Starting Flask server on port {PORT}...")
        web_app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        logger.critical(f"Flask server failed to start: {e}")

def main():
    """Main entrypoint starting the health check and polling the Telegram bot."""
    # Start web thread for health checks
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    # Initialize and run bot polling
    logger.info("Starting Telegram bot polling...")
    try:
        bot_app = setup_bot_application()
        bot_app.run_polling(
            drop_pending_updates=True
        )
    except Exception as e:
        logger.critical(f"Telegram bot polling encountered a critical error: {e}")

if __name__ == "__main__":
    main()
