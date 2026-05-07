import os
import smtplib
import threading
import asyncio
from flask import Flask
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- WEB SERVER ----------------

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Job application bot is running."

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

POSITIONS = {
    "Kitchen": "documents/Kitchen",
    "Cafe": "documents/Cafe",
    "Warehouse": "documents/Warehouse",
}

CV_PROFILE = """
Leni Pazhayakariyil Iype is a Master student in Graz.
Experience: KFC kitchen work, catering service, supermarket/warehouse work.
Languages: English fluent, German A2 improving.
Availability: flexible for morning, afternoon, evening and weekend shifts.
"""


def get_files_for_position(position):
    folder = Path(POSITIONS[position])
    return list(folder.glob("*.pdf"))


def generate_application(position, job_description, recipient_email):
    files = get_files_for_position(position)
    file_names = [f.name for f in files]

    prompt = f"""
Write a professional German job application.

Candidate:
{CV_PROFILE}

Selected position type:
{position}

Job description:
{job_description}

Recipient email:
{recipient_email}

Attached documents:
{file_names}

Return exactly in this format:

SUBJECT:
...

EMAIL:
...

COVER_LETTER:
...
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content


def parse_subject_email(draft):
    subject = "Bewerbung um eine Teilzeitstelle"
    body = draft

    if "SUBJECT:" in draft and "EMAIL:" in draft:
        subject = draft.split("SUBJECT:", 1)[1].split("EMAIL:", 1)[0].strip()
        body = draft.split("EMAIL:", 1)[1]

        if "COVER_LETTER:" in body:
            body = body.split("COVER_LETTER:", 1)[0].strip()

    return subject, body


def send_application(to_email, subject, body, files):
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    for file_path in files:
        with open(file_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=file_path.name,
            )
    smtp_server = os.environ.get("SMTP_SERVER", "smtp-relay.brevo.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    
    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_LOGIN"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [["Kitchen", "Cafe", "Warehouse"]]

    await update.message.reply_text(
        "Welcome, Leni. Which position are you applying for?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )

    context.user_data["step"] = "position"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("step")

    if step == "position":
        if text not in POSITIONS:
            await update.message.reply_text("Please choose: Kitchen, Cafe, or Warehouse.")
            return

        context.user_data["position"] = text
        context.user_data["step"] = "job_description"

        await update.message.reply_text("Please send the job description.")
        return

    if step == "job_description":
        context.user_data["job_description"] = text
        context.user_data["step"] = "email"

        await update.message.reply_text("Please send the application email address.")
        return

    if step == "email":
        if "@" not in text:
            await update.message.reply_text("Please send a valid email address.")
            return

        context.user_data["recipient_email"] = text

        position = context.user_data["position"]
        job_description = context.user_data["job_description"]
        recipient_email = context.user_data["recipient_email"]

        draft = generate_application(position, job_description, recipient_email)
        files = get_files_for_position(position)

        context.user_data["draft"] = draft
        context.user_data["files"] = [str(f) for f in files]
        context.user_data["step"] = "approval"

        keyboard = [["APPROVE", "CANCEL"]]

        file_list = "\n".join([f.name for f in files])

        await update.message.reply_text(
            f"Application draft created:\n\n{draft}\n\n"
            f"Files to attach:\n{file_list}\n\n"
            "Approve or cancel?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        )
        return

    if step == "approval":
        if text == "APPROVE":
            try:
                draft = context.user_data["draft"]
                to_email = context.user_data["recipient_email"]
                files = [Path(f) for f in context.user_data["files"]]
        
                subject, body = parse_subject_email(draft)
                send_application(to_email, subject, body, files)
        
                context.user_data.clear()
                await update.message.reply_text("Application sent successfully. Back to start: send /start.")
                return
        
            except Exception as e:
                await update.message.reply_text(f"Sending failed: {e}")
                print("Sending failed:", e)
                return

        if text == "CANCEL":
            context.user_data.clear()
            await update.message.reply_text("Application cancelled. Back to start: send /start.")
            return

        await update.message.reply_text("Please choose APPROVE or CANCEL.")
        return

    await update.message.reply_text("Send /start to begin.")


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    main()
