import os
import sqlite3
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")                 # Railway variable
CHANNEL_USERNAME = os.getenv("CHANNEL")    # example: @channelforsellings
BOT_USERNAME = os.getenv("BOT_USERNAME")   # without @

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

# ================= FUNCTIONS =================
def is_user_joined(bot, user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= START COMMAND =================
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    bot = context.bot

    # Force Join
    if not is_user_joined(bot, user.id):
        keyboard = [
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
        ]
        update.message.reply_text(
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

    update.message.reply_text(
        "🎉 Welcome!\n\n"
        "📌 Commands:\n"
        "/mypoints – Check points\n"
        "/referral – Get referral link"
    )

# ================= MY POINTS =================
def mypoints(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cursor.execute("SELECT points, coupon FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    if not data:
        update.message.reply_text("❌ User not found.")
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
        update.message.reply_text(
            f"🎉 Congratulations!\n\n"
            f"⭐ Points: {points}\n"
            f"🎟 Coupon Code: {coupon}"
        )
    else:
        msg = f"⭐ Your Points: {points}"
        if coupon:
            msg += f"\n🎟 Coupon: {coupon}"
        update.message.reply_text(msg)

# ================= REFERRAL =================
def referral(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    update.message.reply_text(
        "🔗 Your Referral Link:\n\n"
        f"{link}\n\n"
        "Invite friends and earn points!"
    )

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("mypoints", mypoints))
    dp.add_handler(CommandHandler("referral", referral))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
