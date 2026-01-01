from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import sqlite3, re

# ================== SOZLAMALAR ==================
API_TOKEN = "8518580630:AAEHPhMnqs2TKgotmyoCUaeSFAm1TG0_VRk"
ADMIN_ID = 7009490051

MAIN_CHANNEL = "@TezOL_Rasmiy"
TOP_CHANNEL = "@TezOL_TopDokonlar"

bot = Bot(API_TOKEN)
dp = Dispatcher(bot)

# ================== DATABASE ==================
conn = sqlite3.connect("tezol.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS shops (user_id INTEGER PRIMARY KEY, name TEXT)")
cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    shop TEXT,
    created_at TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS force_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT UNIQUE
)
""")
cur.execute("INSERT OR IGNORE INTO force_channels(channel) VALUES (?)", (MAIN_CHANNEL,))
cur.execute("INSERT OR IGNORE INTO force_channels(channel) VALUES (?)", (TOP_CHANNEL,))
conn.commit()

# ================== STATE ==================
state = {}
temp = {}

# ================== HELPERS ==================
async def check_sub(uid):
    cur.execute("SELECT channel FROM force_channels")
    for (ch,) in cur.fetchall():
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status == "left":
                return False
        except:
            return False
    return True

def has_shop(uid):
    cur.execute("SELECT name FROM shops WHERE user_id=?", (uid,))
    return cur.fetchone()

def user_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if not has_shop(uid):
        kb.add("🏪 Do‘kon qo‘shish")
    else:
        kb.add("➕ Mahsulot qo‘shish")
        kb.add("🏆 TOP-10 do‘konlar")
    if uid == ADMIN_ID:
        kb.add("🧑‍💼 Admin panel")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Kanal qo‘shish", "➖ Kanal o‘chirish")
    kb.add("📢 Xabar yuborish", "👥 Foydalanuvchilar")
    kb.add("⬅️ Orqaga")
    return kb

# ================== START ==================
@dp.message_handler(commands=["start"])
async def start(msg):
    uid = msg.from_user.id
    cur.execute("INSERT OR IGNORE INTO users VALUES (?)", (uid,))
    conn.commit()

    if not await check_sub(uid):
        kb = types.InlineKeyboardMarkup()
        cur.execute("SELECT channel FROM force_channels")
        for (ch,) in cur.fetchall():
            kb.add(types.InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}"))
        kb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        await msg.answer(
            "♻️ *TezOL — isrofga qarshi platforma*\n\n"
            "Davom etish uchun kanallarga obuna bo‘ling 👇",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return

    await msg.answer(
        "♻️ *TezOL — isrofga qarshi platforma*\n\n"
        "Ortib qolgan yoki muddati yaqin mahsulotlarni\n"
        "*arzon narxda tez soting!*",
        reply_markup=user_menu(uid),
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "check")
async def check(cb):
    if await check_sub(cb.from_user.id):
        await cb.message.edit_text("✅ Obuna tasdiqlandi.\n/start yuboring")
    else:
        await cb.answer("❌ Hali obuna yo‘q", show_alert=True)

# ================== ADMIN ==================
@dp.message_handler(commands=["admin"])
@dp.message_handler(text="🧑‍💼 Admin panel")
async def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    await msg.answer("🧑‍💼 ADMIN PANEL", reply_markup=admin_menu())

# ================== TEXT FLOW ==================
@dp.message_handler(content_types=types.ContentType.TEXT)
async def text_flow(msg):
    uid, t = msg.from_user.id, msg.text

    # ----- ADMIN -----
    if uid == ADMIN_ID:
        if t == "⬅️ Orqaga":
            await msg.answer("🔙 Asosiy menyu", reply_markup=user_menu(uid)); return
        if t == "👥 Foydalanuvchilar":
            cur.execute("SELECT COUNT(*) FROM users")
            await msg.answer(f"👥 Jami foydalanuvchilar: {cur.fetchone()[0]}"); return
        if t == "➕ Kanal qo‘shish":
            state[uid] = "add_channel"
            await msg.answer("➕ Kanal username yuboring (@ bilan):"); return
        if t == "➖ Kanal o‘chirish":
            state[uid] = "del_channel"
            await msg.answer("🗑 O‘chirish uchun kanal username yuboring:"); return
        if t == "📢 Xabar yuborish":
            state[uid] = "broadcast"
            await msg.answer("📢 Yuboriladigan xabarni yozing:"); return
        if state.get(uid) == "add_channel":
            cur.execute("INSERT OR IGNORE INTO force_channels VALUES (NULL,?)", (t,))
            conn.commit(); state.pop(uid)
            await msg.answer("✅ Kanal qo‘shildi", reply_markup=admin_menu()); return
        if state.get(uid) == "del_channel":
            cur.execute("DELETE FROM force_channels WHERE channel=?", (t,))
            conn.commit(); state.pop(uid)
            await msg.answer("❌ Kanal o‘chirildi", reply_markup=admin_menu()); return
        if state.get(uid) == "broadcast":
            cur.execute("SELECT user_id FROM users")
            for (u,) in cur.fetchall():
                try: await bot.send_message(u, t)
                except: pass
            state.pop(uid)
            await msg.answer("✅ Xabar yuborildi", reply_markup=admin_menu()); return

    # ----- USER -----
    if t == "🏆 TOP-10 do‘konlar":
        await msg.answer(f"🏆 TOP-10 do‘konlar shu kanalda:\n👉 {TOP_CHANNEL}")
        return

    if t == "🏪 Do‘kon qo‘shish":
        state[uid] = "shop"
        await msg.answer("🏪 Do‘kon nomini kiriting:")
        return

    if state.get(uid) == "shop":
        cur.execute("INSERT INTO shops VALUES (?,?)", (uid, t))
        conn.commit(); state.pop(uid)
        await msg.answer("✅ Do‘kon qo‘shildi", reply_markup=user_menu(uid))
        return

    if t == "➕ Mahsulot qo‘shish":
        if not has_shop(uid):
            await msg.answer("❗ Avval do‘kon qo‘shing", reply_markup=user_menu(uid))
            return
        temp[uid] = {}
        state[uid] = "name"
        await msg.answer("📦 Mahsulot nomi:")
        return

    if state.get(uid) == "name":
        temp[uid]["name"] = t; state[uid] = "qty"
        await msg.answer("📦 Hajmi yoki soni:")
        return

    if state.get(uid) == "qty":
        temp[uid]["qty"] = t; state[uid] = "old"
        await msg.answer("💰 Asl narx:")
        return

    if state.get(uid) == "old":
        temp[uid]["old"] = t; state[uid] = "new"
        await msg.answer("🔥 Chegirma narx:")
        return

    if state.get(uid) == "new":
        temp[uid]["new"] = t; state[uid] = "exp"
        await msg.answer("⏳ Muddati:")
        return

    if state.get(uid) == "exp":
        temp[uid]["exp"] = t; state[uid] = "phone"
        await msg.answer("📞 Telefon raqam:")
        return

    if state.get(uid) == "phone":
        if not re.match(r"^\+?\d{9,13}$", t):
            await msg.answer("❌ Telefon noto‘g‘ri, qayta kiriting:")
            return
        temp[uid]["phone"] = t; state[uid] = "address"
        await msg.answer("📍 Manzil:")
        return

    if state.get(uid) == "address":
        temp[uid]["address"] = t; state[uid] = "desc"
        await msg.answer("📝 Qisqa tavsif:")
        return

    if state.get(uid) == "desc":
        temp[uid]["desc"] = t; state[uid] = "photo"
        await msg.answer("📸 Mahsulot rasmini yuboring:")
        return

# ================== PHOTO ==================
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def photo(msg):
    uid = msg.from_user.id
    if state.get(uid) != "photo":
        return

    shop_row = has_shop(uid)
    if not shop_row:
        await msg.answer("❗ Avval do‘kon qo‘shing", reply_markup=user_menu(uid))
        state.pop(uid, None); temp.pop(uid, None)
        return

    shop = shop_row[0]
    p = temp[uid]

    caption = (
        f"♻️ ORTGAN MAHSULOT\n\n"
        f"🏪 {shop}\n"
        f"📦 {p['name']}\n"
        f"📦 Hajmi/Soni: {p['qty']}\n"
        f"💰 Asl: {p['old']}\n"
        f"🔥 Chegirma: {p['new']}\n"
        f"⏳ {p['exp']}\n"
        f"📞 {p['phone']}\n"
        f"📍 {p['address']}\n\n"
        f"*{p['desc']}*"
    )

    try:
        await bot.send_photo(
            MAIN_CHANNEL,
            msg.photo[-1].file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    except:
        await msg.answer(
            "⚠️ Mahsulot kanalga yuborilmadi.\n"
            "Bot kanalga admin qilinganini tekshiring."
        )

    cur.execute(
        "INSERT INTO products (user_id, shop, created_at) VALUES (?,?,?)",
        (uid, shop, datetime.now().isoformat())
    )
    conn.commit()

    state.pop(uid, None)
    temp.pop(uid, None)

    await msg.answer("✅ Mahsulot muvaffaqiyatli joylandi!", reply_markup=user_menu(uid))

# ================== TOP-10 ==================
async def post_top():
    since = (datetime.now() - timedelta(days=3)).isoformat()
    cur.execute("""
    SELECT shop, COUNT(*) FROM products
    WHERE created_at>=?
    GROUP BY shop
    ORDER BY COUNT(*) DESC
    LIMIT 10
    """, (since,))
    rows = cur.fetchall()
    if not rows:
        return

    text = "🏆 *SO‘NGGI 3 KUN TOP-10 DO‘KONLAR*\n\n"
    for i, (s, c) in enumerate(rows, 1):
        text += f"{i}. {s} — {c} ta mahsulot\n"

    await bot.send_message(TOP_CHANNEL, text, parse_mode="Markdown")

# ================== STARTUP ==================
async def on_startup(dp):
    await bot.set_my_commands(
        [BotCommand("start", "Boshlash")],
        scope=BotCommandScopeDefault()
    )
    await bot.set_my_commands(
        [BotCommand("start", "Boshlash"), BotCommand("admin", "Admin panel")],
        scope=BotCommandScopeChat(chat_id=ADMIN_ID)
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(post_top, "interval", days=3)
    scheduler.start()

# ================== RUN ==================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
