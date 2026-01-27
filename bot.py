import re
import uuid
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------- CONFIG ----------
BOT_TOKEN = "8224903873:AAFwdLzAvFpG2JW6w8DzOGr3H0zIXnvogLY"
SECRET_CHANNEL_ID = -1003509421903
FOOTER = "\n@magic_files_bot"
DB_FILE = "filesvault.db"

USER_CTX = {}

# ---------- DATABASE ----------
def db():
    return sqlite3.connect(DB_FILE)

def init_db():
    with db() as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            code TEXT PRIMARY KEY,
            file_id TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            code TEXT PRIMARY KEY,
            name TEXT,
            password TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS folder_files (
            folder_code TEXT,
            file_code TEXT
        )
        """)
        con.commit()

# ---------- HELPERS ----------
def get_folders():
    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT code, name, password FROM folders")
        rows = cur.fetchall()
        return {
            code: {"name": name, "password": password, "files": get_folder_files(code)}
            for code, name, password in rows
        }

def get_folder_files(folder_code):
    with db() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT file_code FROM folder_files WHERE folder_code=?",
            (folder_code,),
        )
        return [r[0] for r in cur.fetchall()]

def get_file(code):
    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT file_id FROM files WHERE code=?", (code,))
        row = cur.fetchone()
        return row[0] if row else None

def get_file_folder(code):
    with db() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT folder_code FROM folder_files WHERE file_code=?",
            (code,),
        )
        row = cur.fetchone()
        return row[0] if row else None

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USER_CTX.pop(update.message.from_user.id, None)
    kb = [
        [InlineKeyboardButton("📁 Create Folder", callback_data="create_folder")],
        [InlineKeyboardButton("📂 Folder List", callback_data="folder_list")],
    ]
    await update.message.reply_text(
        "📦 FilesVault Bot ready\n⚠️ Educational purposes only.",
        reply_markup=InlineKeyboardMarkup(kb),
    )

# ---------- CALLBACKS ----------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    FOLDERS = get_folders()

    if q.data == "create_folder":
        USER_CTX[uid] = {"step": "folder_name"}
        await q.message.reply_text("📁 Send folder name:")

    elif q.data == "folder_list":
        if not FOLDERS:
            await q.message.reply_text("❌ No folders found.")
            return
        kb = [
            [InlineKeyboardButton(v["name"], callback_data=f"folder_{k}")]
            for k, v in FOLDERS.items()
        ]
        await q.message.reply_text("📂 Select folder:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("folder_"):
        code = q.data.replace("folder_", "")
        USER_CTX[uid] = {"step": "folder_menu", "folder": code}

        kb = [
            [InlineKeyboardButton("➕ Add File", callback_data=f"add_{code}")],
            [InlineKeyboardButton("📄 View Files", callback_data=f"view_{code}")],
            [InlineKeyboardButton("🗑 Delete Folder", callback_data=f"del_{code}")],
        ]
        await q.message.reply_text(
            f"📁 {FOLDERS[code]['name']}\nType `exit` to leave this folder",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif q.data.startswith("add_"):
        code = q.data.replace("add_", "")
        USER_CTX[uid] = {"step": "add_file", "folder": code}
        await q.message.reply_text("📤 Send file:")

    elif q.data.startswith(("view_", "del_")):
        action, code = q.data.split("_", 1)
        folder = FOLDERS.get(code)

        if folder["password"]:
            USER_CTX[uid] = {
                "step": "check_password",
                "folder": code,
                "action": action,
                "tries": 0
            }
            await q.message.reply_text("🔒 Enter folder password:")
        else:
            await handle_folder_action(update, context, action, code)

# ---------- PASSWORD ----------
async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    ctx = USER_CTX.get(uid)
    pwd = update.message.text.strip()
    FOLDERS = get_folders()
    folder = FOLDERS.get(ctx["folder"])
    ctx["tries"] += 1

    if pwd == folder["password"]:
        action = ctx["action"]
        folder_code = ctx["folder"]
        file_code = ctx.get("file")
        USER_CTX.pop(uid)

        if action == "restore":
            fid = get_file(file_code)
            if fid:
                if file_code.startswith("ph_"):
                    await update.message.reply_photo(fid)
                else:
                    await update.message.reply_video(fid)
            else:
                await update.message.reply_text("❌ Code not found")
        else:
            await handle_folder_action(update, context, action, folder_code)
        return

    if ctx["tries"] >= 3:
        USER_CTX.pop(uid)
        await update.message.reply_text("❌ Too many attempts. Exiting folder.")
    else:
        await update.message.reply_text("❌ Wrong password. Try again:")

# ---------- FOLDER ACTION ----------
async def handle_folder_action(update, context, action, code):
    FOLDERS = get_folders()
    folder = FOLDERS.get(code)

    if action == "view":
        if not folder["files"]:
            await update.message.reply_text("📭 Folder is empty.")
            return
        await update.message.reply_text(
            "📄 Files:\n" + "\n".join(folder["files"]) + FOOTER
        )

    elif action == "del":
        with db() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM folders WHERE code=?", (code,))
            cur.execute("DELETE FROM folder_files WHERE folder_code=?", (code,))
            con.commit()
        await update.message.reply_text("🗑 Folder deleted.")

# ---------- TEXT ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()
    ctx = USER_CTX.get(uid)

    if ctx and ctx.get("step") in ("folder_menu", "add_file") and text.lower() == "exit":
        USER_CTX.pop(uid)
        await update.message.reply_text("✅ Exited folder.")
        return

    if ctx and ctx["step"] == "folder_name":
        ctx["name"] = text
        ctx["step"] = "folder_password"
        await update.message.reply_text("🔒 Password or `none`:")
        return

    if ctx and ctx["step"] == "folder_password":
        code = f"fo_{uuid.uuid4().hex[:8]}"
        pwd = None if text.lower() == "none" else text
        with db() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO folders VALUES (?, ?, ?)",
                (code, ctx["name"], pwd),
            )
            con.commit()
        USER_CTX[uid] = {"step": "add_file", "folder": code}
        await update.message.reply_text("📤 Folder ready. Send file:")
        return

    if ctx and ctx["step"] == "check_password":
        await handle_password(update, context)
        return

    await restore_file(update, context)

# ---------- FILE SAVE ----------
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    ctx = USER_CTX.get(uid)

    if update.message.photo:
        fid = update.message.photo[-1].file_id
        code = f"ph_{fid}"
    elif update.message.video:
        fid = update.message.video.file_id
        code = f"vi_{fid}"
    else:
        return

    await context.bot.copy_message(
        chat_id=SECRET_CHANNEL_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id,
    )

    with db() as con:
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO files VALUES (?, ?)", (code, fid))
        if ctx and ctx.get("step") == "add_file":
            cur.execute(
                "INSERT INTO folder_files VALUES (?, ?)",
                (ctx["folder"], code),
            )
        con.commit()

    USER_CTX.pop(uid, None)
    await update.message.reply_text(f"✅ Saved\n🔑 {code}{FOOTER}")

# ---------- RESTORE ----------
async def restore_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.message.from_user.id
    codes = re.findall(r"(?:ph|vi)_[A-Za-z0-9_-]+", text)

    for code in codes:
        folder_code = get_file_folder(code)
        if folder_code:
            with db() as con:
                cur = con.cursor()
                cur.execute("SELECT password FROM folders WHERE code=?", (folder_code,))
                pwd = cur.fetchone()[0]
            if pwd:
                USER_CTX[uid] = {
                    "step": "check_password",
                    "folder": folder_code,
                    "action": "restore",
                    "file": code,
                    "tries": 0
                }
                await update.message.reply_text("🔒 Enter folder password:")
                return

        fid = get_file(code)
        if not fid:
            await update.message.reply_text(f"❌ Code not found: {code}")
            continue

        if code.startswith("ph_"):
            await update.message.reply_photo(fid)
        else:
            await update.message.reply_video(fid)

# ---------- MAIN ----------
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, save_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 FilesVault Bot running (SQLite)...")
    app.run_polling()

if __name__ == "__main__":
    main()
