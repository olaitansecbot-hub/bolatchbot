import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the /start command is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! I am @bolatchbot, your friendly helper. 🤖\n"
        "Send me any text and I will echo it back!\n"
        "Use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the /help command is issued."""
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "Just send me any text and I will repeat it."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the user message."""
    await update.message.reply_text(f"You said: {update.message.text}")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text("Sorry, I don't understand that command. Use /help to see available commands.")

# --- Main Function ---
def main():
    """Start the bot."""
    # Get the token from environment variable
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        logger.error("No token found! Please set the TELEGRAM_BOT_TOKEN environment variable.")
        return

    # Create the Application
    application = ApplicationBuilder().token(token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Register a handler for all text messages (excluding commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Register a handler for unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    # Run the bot with long polling
    logger.info("Starting bot with long polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
