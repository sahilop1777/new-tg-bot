import os
import sqlite3
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL")
BOT_USERNAME = os.getenv("BOT_USERNAME")

# ================= DATABASE =================
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referrer_id INTEGER,
    points INTEGER DEFAULT 0,
    coupon TEXT
)
""")
conn.commit()

# ================= HELPERS =================
async def is_user_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot = context.bot

    if not await is_user_joined(bot, user.id):
        keyboard = [[
            InlineKeyboardButton(
                "✅ Join Channel",
                url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
            )
        ]]
        await update.message.reply_text(
            "❗ You must join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0])
        except:
            pass

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, referrer_id) VALUES (?, ?)",
            (user.id, referrer_id)
        )
        conn.commit()

        if referrer_id and referrer_id != user.id:
            cursor.execute(
                "UPDATE users SET points = points + 1 WHERE user_id=?",
                (referrer_id,)
            )
            conn.commit()

    await update.message.reply_text(
        "🎉 Welcome!\n\n/mypoints – Check points\n/referral – Get referral link"
    )

# ================= MY POINTS =================
async def mypoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT points, coupon FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    if not data:
        await update.message.reply_text("❌ User not found.")
        return

    points, coupon = data

    if points >= 3 and not coupon:
        coupon = "CPN-" + ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )
        cursor.execute(
            "UPDATE users SET coupon=? WHERE user_id=?",
            (coupon, user_id)
        )
        conn.commit()
        await update.message.reply_text(
            f"🎉 Congratulations!\n⭐ Points: {points}\n🎟 Coupon: {coupon}"
        )
    else:
        msg = f"⭐ Your Points: {points}"
        if coupon:
            msg += f"\n🎟 Coupon: {coupon}"
        await update.message.reply_text(msg)

# ================= REFERRAL =================
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    await update.message.reply_text(
        f"🔗 Your Referral Link:\n\n{link}"
    )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mypoints", mypoints))
    app.add_handler(CommandHandler("referral", referral))

    app.run_polling()

if __name__ == "__main__":
    main()
