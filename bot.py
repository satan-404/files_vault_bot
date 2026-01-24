
import os
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

# ---------- CONFIGURATION ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET_CHANNEL_ID = int(os.getenv("SECRET_CHANNEL_ID"))

FILE_STORE = {}

# ---------- COMMAND HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 FilesVault Bot ready")

# ---------- FILE HANDLER ----------
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    try:
        if msg.photo:
            file_id = msg.photo[-1].file_id
            code = f"ph_{file_id}"
            await context.bot.send_photo(chat_id=SECRET_CHANNEL_ID, photo=file_id)
        elif msg.video:
            file_id = msg.video.file_id
            code = f"vi_{file_id}"
            await context.bot.send_video(chat_id=SECRET_CHANNEL_ID, video=file_id)
        else:
            await msg.reply_text("❌ Unsupported file type")
            return

        FILE_STORE[code] = file_id
        await msg.reply_text(code)  # only reply with the code

    except Exception as e:
        await msg.reply_text("❌ Error forwarding file to secret channel")
        print("Error forwarding:", e)

# ---------- RESTORE HANDLER ----------
async def restore_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    match = re.search(r"(ph|vi)_[A-Za-z0-9_-]+", text)
    if not match:
        return

    code = match.group(0)
    file_id = FILE_STORE.get(code)

    if not file_id:
        await update.message.reply_text("❌ Code not found")
        return

    try:
        if code.startswith("ph_"):
            await update.message.reply_photo(file_id)
        else:
            await update.message.reply_video(file_id)
    except Exception as e:
        print("Restore error:", e)

# ---------- MAIN ----------
def main():
    request = HTTPXRequest(
        connect_timeout=20,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=60,
        http_version="1.1",
    )

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, save_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, restore_file))

    print("🤖 Bot running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
