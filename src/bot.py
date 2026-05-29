import asyncio
import logging
import re
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.ai_generator import generate_application_draft
from src.config import TELEGRAM_TOKEN, is_user_allowed
from src.database import get_recent_applications, get_stats, init_db, log_application
from src.email_sender import get_pdf_attachments, send_email_with_retry

logger = logging.getLogger(__name__)

# State constants
(
    CHOOSING_CATEGORY,
    ENTERING_DESCRIPTION,
    ENTERING_EMAIL,
    CONFIRMING_APPLICATION,
    EDITING_BODY,
) = range(5)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def is_valid_email(email: str) -> bool:
    """Validate email address format."""
    return bool(EMAIL_REGEX.match(email))

async def check_whitelist(update: Update) -> bool:
    """Verify if the user is authorized to use the bot."""
    user = update.effective_user
    if not user:
        return False
    if not is_user_allowed(user.id):
        logger.warning(f"Unauthorized access attempt by user ID {user.id} (@{user.username})")
        msg = "Entschuldigung, Sie sind nicht autorisiert, diesen Bot zu nutzen."
        if update.message:
            await update.message.reply_text(msg)
        elif update.callback_query:
            await update.callback_query.answer("Nicht autorisiert.", show_alert=True)
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the application flow and ask for the job category."""
    if not await check_whitelist(update):
        return ConversationHandler.END

    context.user_data.clear()
    logger.info(f"User {update.effective_user.id} started a new application flow.")

    keyboard = [
        [
            InlineKeyboardButton("🍳 Küche (Kitchen)", callback_data="cat_Kitchen"),
            InlineKeyboardButton("☕ Café (Cafe)", callback_data="cat_Cafe"),
            InlineKeyboardButton("📦 Lager (Warehouse)", callback_data="cat_Warehouse"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Hallo Leni! Bitte wähle eine Kategorie für deine Bewerbung aus:",
        reply_markup=reply_markup
    )
    return CHOOSING_CATEGORY

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle category selection inline keyboard."""
    if not await check_whitelist(update):
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()

    category = query.data.split("_")[1]
    context.user_data["category"] = category

    logger.info(f"User selected category: {category}")

    await query.edit_message_text(
        text=(
            f"Ausgewählte Kategorie: <b>{category}</b>\n\n"
            "Bitte füge jetzt die Stellenbeschreibung (Job Description) ein:"
        ),
        parse_mode="HTML"
    )
    return ENTERING_DESCRIPTION

async def description_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receipt of the job description."""
    if not await check_whitelist(update):
        return ConversationHandler.END

    description = update.message.text.strip()
    context.user_data["job_description"] = description

    logger.info("Job description received from user.")

    await update.message.reply_text(
        "Bitte gib jetzt die E-Mail-Adresse des Arbeitgebers/Recruiters an:"
    )
    return ENTERING_EMAIL

async def email_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receipt of the recruiter's email address."""
    if not await check_whitelist(update):
        return ConversationHandler.END

    email = update.message.text.strip()
    if not is_valid_email(email):
        await update.message.reply_text(
            "Dies ist keine gültige E-Mail-Adresse. Bitte gib eine gültige E-Mail-Adresse ein:"
        )
        return ENTERING_EMAIL

    context.user_data["recipient_email"] = email
    category = context.user_data["category"]
    job_description = context.user_data["job_description"]

    logger.info(f"Valid email received: {email}. Triggering GPT-4o draft generation...")

    # Notify user we are generating
    status_msg = await update.message.reply_text(
        "Generiere deutschen Bewerbungsentwurf mit GPT-4o..."
    )

    try:
        subject, body = await asyncio.to_thread(
            generate_application_draft, category, job_description
        )
        context.user_data["subject"] = subject
        context.user_data["body"] = body

        # Gather attachments
        attachments = get_pdf_attachments(category)
        context.user_data["attachments"] = [str(p) for p in attachments]

        # Remove the status message
        await status_msg.delete()

        # Send preview
        await send_draft_preview(update, context)
        return CONFIRMING_APPLICATION

    except Exception as e:
        logger.error(f"Draft generation failed: {e}")
        await status_msg.delete()
        await update.message.reply_text(
            "Die KI-Generierung ist fehlgeschlagen. Bitte versuche es erneut mit /start."
        )
        return ConversationHandler.END

async def send_draft_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and display the preview of the application draft."""
    subject = context.user_data["subject"]
    body = context.user_data["body"]
    attachments = context.user_data["attachments"]
    recipient = context.user_data["recipient_email"]

    attachment_names = [Path(p).name for p in attachments]

    preview = (
        f"📧 <b>Empfänger:</b> {recipient}\n\n"
        f"📝 <b>Betreff:</b> {subject}\n\n"
        f"💬 <b>Nachricht:</b>\n"
        f"----------------------------------------\n"
        f"{body}\n"
        f"----------------------------------------\n\n"
        f"📎 <b>Anhänge ({len(attachment_names)}):</b>\n"
        + (
            "\n".join(f"- {name}" for name in attachment_names)
            if attachment_names else "Keine PDFs gefunden!"
        )
        + "\n\nMöchtest du diese Bewerbung senden, bearbeiten oder abbrechen?"
    )

    keyboard = [
        [
            InlineKeyboardButton("🚀 Senden (Send)", callback_data="act_send"),
            InlineKeyboardButton("✍️ Bearbeiten (Edit)", callback_data="act_edit"),
            InlineKeyboardButton("❌ Abbrechen (Cancel)", callback_data="act_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Handle message vs callback queries
    if update.message:
        await update.message.reply_text(preview, reply_markup=reply_markup, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            preview, reply_markup=reply_markup, parse_mode="HTML"
        )

async def action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Send, Edit, or Cancel button selections."""
    if not await check_whitelist(update):
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "act_cancel":
        logger.info("User cancelled the application process.")
        await query.edit_message_text("Bewerbung abgebrochen. /start für einen neuen Versuch.")
        context.user_data.clear()
        return ConversationHandler.END

    elif action == "act_edit":
        logger.info("User requested to edit the draft.")
        await query.message.reply_text(
            "Bitte sende jetzt den neuen E-Mail-Text. Dieser ersetzt den aktuellen Entwurf."
        )
        return EDITING_BODY

    elif action == "act_send":
        logger.info("User approved. Sending application email...")
        status_msg = await query.message.reply_text(
            "Sende Bewerbungs-E-Mail über Brevo SMTP... (3 Versuche mit Backoff)"
        )

        recipient = context.user_data["recipient_email"]
        subject = context.user_data["subject"]
        body = context.user_data["body"]
        category = context.user_data["category"]
        attachments = [Path(p) for p in context.user_data["attachments"]]
        attachment_names_str = ",".join([p.name for p in attachments])

        try:
            # Send using async thread pool to prevent blocking the main bot thread
            await asyncio.to_thread(
                send_email_with_retry,
                recipient,
                subject,
                body,
                attachments
            )

            # Log to DB
            await asyncio.to_thread(
                log_application,
                category,
                recipient,
                subject,
                body,
                attachment_names_str,
                "SUCCESS"
            )

            await status_msg.delete()
            await query.message.reply_text("✅ Bewerbung wurde erfolgreich gesendet!")

        except Exception as e:
            logger.error(f"Email sending completely failed: {e}")

            # Log failure to DB
            await asyncio.to_thread(
                log_application,
                category,
                recipient,
                subject,
                body,
                attachment_names_str,
                "FAILED"
            )

            await status_msg.delete()
            await query.message.reply_text(
                f"❌ Fehler beim Senden: {e}\n\n"
                "Bewerbung fehlgeschlagen. Sende /start für einen neuen Versuch."
            )

        context.user_data.clear()
        return ConversationHandler.END

    return CONFIRMING_APPLICATION

async def edit_body_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receipt of the updated email body."""
    if not await check_whitelist(update):
        return ConversationHandler.END

    new_body = update.message.text.strip()
    context.user_data["body"] = new_body

    logger.info("User updated the email body draft.")

    await update.message.reply_text("Entwurf wurde aktualisiert. Hier ist die Vorschau:")
    await send_draft_preview(update, context)
    return CONFIRMING_APPLICATION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and reset the conversation flow."""
    if not await check_whitelist(update):
        return ConversationHandler.END

    logger.info("User triggered /cancel command.")
    context.user_data.clear()
    msg = "Vorgang abgebrochen. Senden Sie /start, um eine neue Bewerbung zu beginnen."

    if update.message:
        await update.message.reply_text(msg)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(msg)

    return ConversationHandler.END

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the last 10 sent applications from the database."""
    if not await check_whitelist(update):
        return

    logger.info(f"User {update.effective_user.id} requested history.")

    try:
        apps = await asyncio.to_thread(get_recent_applications, 10)
        if not apps:
            await update.message.reply_text("Keine Bewerbungen im Protokoll gefunden.")
            return

        msg = "<b>Letzte 10 Bewerbungen:</b>\n\n"
        for i, app in enumerate(apps, 1):
            status_emoji = "✅" if app["status"] == "SUCCESS" else "❌"
            msg += (
                f"{i}. {app['sent_at'][:16]} - <b>{app['category']}</b>\n"
                f"📧 An: {app['recipient_email']}\n"
                f"📝 Betreff: {app['subject']}\n"
                f"Status: {status_emoji} {app['status']}\n\n"
            )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        await update.message.reply_text("Fehler beim Abrufen des Bewerbungsverlaufs.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display overall application stats."""
    if not await check_whitelist(update):
        return

    logger.info(f"User {update.effective_user.id} requested stats.")

    try:
        data = await asyncio.to_thread(get_stats)
        total = sum(data.values())
        msg = (
            f"<b>Bewerbungsstatistiken (Erfolgreich gesendet):</b>\n\n"
            f"Gesamtzahl: {total}\n"
            f"🍳 Küche (Kitchen): {data.get('Kitchen', 0)}\n"
            f"☕ Café (Cafe): {data.get('Cafe', 0)}\n"
            f"📦 Lager (Warehouse): {data.get('Warehouse', 0)}"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        await update.message.reply_text("Fehler beim Abrufen der Statistiken.")

def setup_bot_application() -> Application:
    """Build and setup handlers for the telegram bot application."""
    if not TELEGRAM_TOKEN:
        raise ValueError("Missing TELEGRAM_TOKEN environment variable.")

    # Initialize SQLite database
    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Define conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_CATEGORY: [
                CallbackQueryHandler(category_callback, pattern="^cat_")
            ],
            ENTERING_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, description_received)
            ],
            ENTERING_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, email_received)
            ],
            CONFIRMING_APPLICATION: [
                CallbackQueryHandler(action_callback, pattern="^act_")
            ],
            EDITING_BODY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_body_received)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),  # Allow start to restart conversation at any state
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("cancel", cancel))

    return app
