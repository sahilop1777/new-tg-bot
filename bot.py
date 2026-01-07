import sqlite3
import random
import string
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
TOKEN = "8078328136:AAHceSLv2HmSxtnxKWmab0MmGzmf7Cd5lSo"
CHANNEL_USERNAME = "@channelforsellings"
BOT_USERNAME = "newfinal00bot"
ADMIN_ID = 6416481890

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referrer_id INTEGER,
    points INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY,
    value INTEGER,
    used INTEGER DEFAULT 0
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

def gen_coupon():
    return "CPN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ================= KEYBOARDS =================
def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("🔄 Verify", callback_data="verify")]
    ])

def main_menu(is_admin=False):
    kb = [
        [InlineKeyboardButton("⭐ My Points", callback_data="mypoints")],
        [InlineKeyboardButton("🎟 My Coupon", callback_data="mycoupon")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="referral")]
    ]
    if is_admin:
        kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add ₹500 Coupon", callback_data="add500")],
        [InlineKeyboardButton("➕ Add ₹1000 Coupon", callback_data="add1000")],
        [InlineKeyboardButton("📊 View Users", callback_data="admin_users")],
        [InlineKeyboardButton("🔄 Reset Points", callback_data="reset")],
        [InlineKeyboardButton("⬅ Back", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❗ Join channel then verify",
        reply_markup=join_keyboard()
    )

# ================= VERIFY =================
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user = q.from_user
    bot = context.bot

    if not await is_user_joined(bot, user.id):
        await q.answer("❌ You have not joined channel", show_alert=True)
        return

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    if not cursor.fetchone():
        ref = int(context.args[0]) if context.args else None
        cursor.execute("INSERT INTO users (user_id, referrer_id) VALUES (?,?)", (user.id, ref))
        if ref and ref != user.id:
            cursor.execute("UPDATE users SET points = points + 1 WHERE user_id=?", (ref,))
        conn.commit()

    await q.message.edit_text(
        "🏠 Main Menu",
        reply_markup=main_menu(user.id == ADMIN_ID)
    )

# ================= USER =================
async def mypoints(update, context):
    q = update.callback_query
    await q.answer()
    cursor.execute("SELECT points FROM users WHERE user_id=?", (q.from_user.id,))
    p = cursor.fetchone()[0]
    await q.message.edit_text(f"⭐ Points: {p}", reply_markup=main_menu(q.from_user.id == ADMIN_ID))

async def referral(update, context):
    q = update.callback_query
    await q.answer()
    link = f"https://t.me/{BOT_USERNAME}?start={q.from_user.id}"
    await q.message.edit_text(f"🔗 Your link:\n{link}", reply_markup=main_menu(q.from_user.id == ADMIN_ID))

async def mycoupon(update, context):
    q = update.callback_query
    await q.answer()

    cursor.execute("SELECT points FROM users WHERE user_id=?", (q.from_user.id,))
    points = cursor.fetchone()[0]

    need = 500 if points >= 3 and points < 5 else 1000 if points >= 5 else None
    if not need:
        await q.message.edit_text("❌ Not enough points", reply_markup=main_menu())
        return

    cursor.execute("SELECT code FROM coupons WHERE value=? AND used=0 LIMIT 1", (need,))
    row = cursor.fetchone()
    if not row:
        await q.message.edit_text("❌ Coupon not available", reply_markup=main_menu())
        return

    code = row[0]
    cursor.execute("UPDATE coupons SET used=1 WHERE code=?", (code,))
    conn.commit()

    await q.message.edit_text(
        f"🎟 Coupon ₹{need}\nCode: `{code}`",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ================= ADMIN =================
async def admin(update, context):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        return
    await q.message.edit_text("👑 Admin Panel", reply_markup=admin_menu())

async def add_coupon(update, context, value):
    code = gen_coupon()
    cursor.execute("INSERT INTO coupons VALUES (?,?,0)", (code, value))
    conn.commit()
    await update.callback_query.answer(f"Coupon ₹{value} added")

async def add500(update, context):
    await add_coupon(update, context, 500)

async def add1000(update, context):
    await add_coupon(update, context, 1000)

async def admin_users(update, context):
    q = update.callback_query
    await q.answer()
    cursor.execute("SELECT COUNT(*) FROM users")
    await q.message.edit_text(f"👥 Users: {cursor.fetchone()[0]}", reply_markup=admin_menu())

async def reset(update, context):
    q = update.callback_query
    await q.answer()
    cursor.execute("UPDATE users SET points=0")
    cursor.execute("UPDATE coupons SET used=0")
    conn.commit()
    await q.message.edit_text("🔄 Reset done", reply_markup=admin_menu())

async def back(update, context):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("🏠 Main Menu", reply_markup=main_menu(q.from_user.id == ADMIN_ID))

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify, "^verify$"))
    app.add_handler(CallbackQueryHandler(mypoints, "^mypoints$"))
    app.add_handler(CallbackQueryHandler(referral, "^referral$"))
    app.add_handler(CallbackQueryHandler(mycoupon, "^mycoupon$"))
    app.add_handler(CallbackQueryHandler(admin, "^admin$"))
    app.add_handler(CallbackQueryHandler(add500, "^add500$"))
    app.add_handler(CallbackQueryHandler(add1000, "^add1000$"))
    app.add_handler(CallbackQueryHandler(admin_users, "^admin_users$"))
    app.add_handler(CallbackQueryHandler(reset, "^reset$"))
    app.add_handler(CallbackQueryHandler(back, "^back$"))

    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
