from flask import Flask, request
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from bot import BOT_TOKEN, init_db, start, button_callback, handle_text, save_file

app = Flask(__name__)

# Initialize DB
init_db()

# Build Telegram app
tg_app = ApplicationBuilder().token(BOT_TOKEN).build()
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CallbackQueryHandler(button_callback))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
tg_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, save_file))

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    asyncio.run(tg_app.process_update(update))
    return "OK"
