import os
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

# Get your bot token from Railway Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Basic start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is alive 🚀")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in Railway Variables!")

    # Build the bot application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add /start command handler
    app.add_handler(CommandHandler("start", start))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
