import sqlite3
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
TOKEN = "YOUR_BOT_TOKEN_HERE"
CHANNEL_USERNAME = "@channelforsellings"
BOT_USERNAME = "mybitiokbot"
ADMIN_ID = 123456789  # <-- PUT YOUR TELEGRAM USER ID

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
        return member.status in ("member", "administrator", "creator")
    except:
        return False

# ================= KEYBOARDS =================
def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("🔄 Verify", callback_data="verify")]
    ])

def main_menu_keyboard(is_admin=False):
    buttons = [
        [InlineKeyboardButton("⭐ My Points", callback_data="mypoints")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="referral")],
        [InlineKeyboardButton("🎟 My Coupon", callback_data="mycoupon")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(buttons)

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 View Users", callback_data="admin_users")],
        [InlineKeyboardButton("🎟 Add Coupon", callback_data="admin_coupon")],
        [InlineKeyboardButton("🔄 Reset Points", callback_data="admin_reset")],
        [InlineKeyboardButton("⬅ Back", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❗ Join our channel to continue.",
        reply_markup=join_keyboard()
    )

# ================= VERIFY =================
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    bot = context.bot

    if not await is_user_joined(bot, user.id):
        await query.answer(
            "❌ You have not joined the channel",
            show_alert=True
        )
        return

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not cursor.fetchone():
        referrer_id = None
        if context.args:
            try:
                referrer_id = int(context.args[0])
            except:
                pass

        cursor.execute(
            "INSERT INTO users (user_id, referrer_id) VALUES (?,?)",
            (user.id, referrer_id)
        )
        conn.commit()

        if referrer_id and referrer_id != user.id:
            cursor.execute(
                "UPDATE users SET points = points + 1 WHERE user_id=?",
                (referrer_id,)
            )
            conn.commit()

    await query.message.edit_text(
        "🏠 *Main Menu*",
        reply_markup=main_menu_keyboard(user.id == ADMIN_ID),
        parse_mode="Markdown"
    )

# ================= USER BUTTONS =================
async def mypoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("SELECT points FROM users WHERE user_id=?", (query.from_user.id,))
    points = cursor.fetchone()[0]

    await query.message.edit_text(
        f"⭐ Your Points: {points}",
        reply_markup=main_menu_keyboard(query.from_user.id == ADMIN_ID)
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    link = f"https://t.me/{BOT_USERNAME}?start={query.from_user.id}"
    await query.message.edit_text(
        f"🔗 Your Referral Link:\n\n{link}",
        reply_markup=main_menu_keyboard(query.from_user.id == ADMIN_ID)
    )

async def mycoupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("SELECT points, coupon FROM users WHERE user_id=?", (query.from_user.id,))
    points, coupon = cursor.fetchone()

    if points >= 3 and not coupon:
        coupon = "CPN-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        cursor.execute(
            "UPDATE users SET coupon=? WHERE user_id=?",
            (coupon, query.from_user.id)
        )
        conn.commit()

    msg = f"🎟 Coupon: {coupon}" if coupon else "❌ No coupon yet"
    await query.message.edit_text(msg, reply_markup=main_menu_keyboard(query.from_user.id == ADMIN_ID))

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    await query.message.edit_text(
        "👑 *Admin Panel*",
        reply_markup=admin_keyboard(),
        parse_mode="Markdown"
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    await query.message.edit_text(
        f"📊 Total Users: {count}",
        reply_markup=admin_keyboard()
    )

async def admin_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("UPDATE users SET points=0, coupon=NULL")
    conn.commit()

    await query.message.edit_text(
        "🔄 All user points reset",
        reply_markup=admin_keyboard()
    )

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text(
        "🏠 Main Menu",
        reply_markup=main_menu_keyboard(query.from_user.id == ADMIN_ID)
    )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
    app.add_handler(CallbackQueryHandler(mypoints, pattern="mypoints"))
    app.add_handler(CallbackQueryHandler(referral, pattern="referral"))
    app.add_handler(CallbackQueryHandler(mycoupon, pattern="mycoupon"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern="admin_users"))
    app.add_handler(CallbackQueryHandler(admin_reset, pattern="admin_reset"))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))

    app.run_polling()

if __name__ == "__main__":
    main()
