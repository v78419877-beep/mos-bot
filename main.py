import asyncio
import sqlite3
import random
import string
import os
import re
import json
from urllib.parse import quote
from urllib.request import urlopen
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = 7305320918
DATABASE_PATH = os.environ.get("DATABASE_PATH", "bot.db")
BOT_NAME = "Mos | Чат-менеджер"
SUPPORT_CHAT_LINK = "https://t.me/mospodd"
SUPPORT_CHANNEL_LINK = "https://t.me/moskanalp"
MODERATION_CHAT_ID = -1004438332613
SUPPORT_CHAT_ID = -1004438332613
TELETYPE_URL = "https://teletype.in/@sirenie3/Mos-command"

BOT_START_TIME = datetime.now()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= УНИВЕРСАЛЬНЫЙ ДЕКОРАТОР КОМАНД =================
def _match_command(message: types.Message, name_lower: str) -> bool:
    """Срабатывает на .команда / !команда / /команда / команда (без префикса)."""
    if not message.text:
        return False
    txt = message.text.strip()
    if not txt:
        return False

    # Отрезаем префикс . ! /
    if txt[0] in ".!/":
        txt = txt[1:].lstrip()
    # Дальше берём первое слово
    if not txt:
        return False
    first_word = txt.split(maxsplit=1)[0].lower()
    return first_word == name_lower


def cmd(name: str):
    """
    Универсальный декоратор команд.
    Работает с: .команда, !команда, /команда, команда
    """
    name_lower = name.lower().strip()

    def decorator(func):
        @dp.message(lambda m: _match_command(m, name_lower))
        async def handler(message: types.Message):
            return await func(message)
        return handler
    return decorator


# ================= ПРЕМИУМ-ЭМОДЗИ =================
EMOJI = {
    "mute": "5239939553720041034", "pencil": "5395444784611480792",
    "wave": "5215248074498128418", "stats": "5884161133174067365",
    "ban": "5472267631979405211", "id": "5014902839575577394",
    "check": "5429501538806548545", "ping": "5269563867305879894",
    "cross": "5269666272211148094", "calendar": "5413879192267805083",
    "alien": "5267401355567345688", "sos": "5238025132177369293",
    "gear": "4904936030232117798", "shield": "5251203410396458957",
    "key": "5330115548900501467", "user": "5373012449597335010",
    "write": "5197269100878907942", "pin": "5291893917673868928",
    "announce": "5269669124069432917",
    "artist": "5258215635996908355",
    "like": "5391210243210353922",
    "dislike": "5864180515816345988",
    "heart": "5266996773943028034",
    "education": "5391052390277348873",
    "art": "5431456208487716895",
    "broom": "5472291748220771063",
    "briefcase": "5398037325655602784",
    "wrench": "5462921117423384478",
    "crop": "5318804172705910750",
    "notify": "5458603043203327669",
    "sport": "5409008750893734809",
    "mask": "5359441070201513074",
    "qr": "5407025283456835913",
    "eye": "5122983123188974322",
    "people": "5258513401784573443",
    "envelope": "5253742260054409879",
    "card": "5472250091332993630",
    "lab": "5411512278740640309",
    "medicine": "5433635625217563352",
    "audio": "5260652149469094137",
    "video": "5472069741261265416",
    "verified": "5411267122007397812",
    "wallet": "5269472440337078683",
    "music": "5172447776205702031",
}

UNICODE_TO_KEY = {
    "🔇": "mute", "✏️": "pencil", "👋": "wave", "📊": "stats",
    "🚫": "ban", "🆔": "id", "✅": "check", "🏓": "ping",
    "❌": "cross", "🗓": "calendar", "🆘": "sos", "⚙️": "gear",
    "🛡": "shield", "🔑": "key", "👤": "user", "✍️": "write",
    "📌": "pin", "👽": "alien",
    "📣": "announce", "👩‍🎨": "artist", "👍": "like", "👎": "dislike",
    "❤️": "heart", "🎓": "education", "🎨": "art", "🧹": "broom",
    "💼": "briefcase", "🛠": "wrench", "✂️": "crop", "🔔": "notify",
    "🏆": "sport", "🎭": "mask", "📱": "qr", "👁": "eye",
    "👥": "people", "✉️": "envelope", "💳": "card", "🧪": "lab",
    "💊": "medicine", "🎙": "audio", "🎬": "video", "✔️": "verified",
    "👛": "wallet", "🎵": "music",
}

def em(name, fallback="•"):
    eid = EMOJI.get(name)
    if not eid:
        return fallback
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'

def mention(user):
    if getattr(user, 'username', None):
        return f'<a href="https://t.me/{user.username}">{user.first_name}</a>'
    return f'<b>{user.first_name}</b>'

def mention_by_id(user_id, first_name, username=None):
    if username:
        return f'<a href="https://t.me/{username}">{first_name}</a>'
    return f'<b>{first_name}</b>'

def user_link(user_id, first_name="Пользователь", username=None):
    if username:
        return f'<a href="https://t.me/{username}">{first_name}</a>'
    return f'<b>{first_name}</b>'

def auto_premium(text: str) -> str:
    if not text:
        return text
    for uni, key in UNICODE_TO_KEY.items():
        eid = EMOJI.get(key)
        if eid and uni in text:
            text = text.replace(uni, f'<tg-emoji emoji-id="{eid}">{uni}</tg-emoji>')
    return text

# ================= РАНГИ ЧАТА =================
RANK_NAMES = {0: "👤 Участник", 1: "🛡️ Мл. Модератор", 2: "🛡️ Ст. Модератор",
              3: "👑 Мл. Админ", 4: "👑 Ст. Админ", 5: "⚜️ Владелец"}

AGENT_RANKS = {
    1: "🛡 Мл. Агент",
    2: "🛡 Агент",
    3: "🛡 Ст. Агент",
    4: "⚜️ Гл. Агент",
}

# ================= БАЗА ДАННЫХ =================
def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS agents (user_id INTEGER PRIMARY KEY, added_by INTEGER)")
        c.execute("""CREATE TABLE IF NOT EXISTS agent_ranks (
            user_id INTEGER PRIMARY KEY,
            rank INTEGER DEFAULT 1,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("CREATE TABLE IF NOT EXISTS antispam (user_id INTEGER PRIMARY KEY, reason TEXT, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS ignore_list (user_id INTEGER, chat_id INTEGER, reason TEXT, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_codes (chat_id INTEGER PRIMARY KEY, code TEXT UNIQUE)")
        c.execute("CREATE TABLE IF NOT EXISTS messages_stats (user_id INTEGER, chat_id INTEGER, date DATE, count INTEGER DEFAULT 1, UNIQUE(user_id, chat_id, date))")
        c.execute("CREATE TABLE IF NOT EXISTS banned_chats (chat_id INTEGER PRIMARY KEY, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER, chat_id INTEGER, rank INTEGER DEFAULT 1, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS bot_promoted (user_id INTEGER, chat_id INTEGER, promoted_by INTEGER, promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS warns (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, reason TEXT, warned_by INTEGER, warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS candies (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS candy_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS agent_activity (user_id INTEGER PRIMARY KEY, last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS greetings (chat_id INTEGER PRIMARY KEY, text TEXT, updated_by INTEGER, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, first_name TEXT, username TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS captcha (user_id INTEGER, chat_id INTEGER, message_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS business_connections (user_id INTEGER PRIMARY KEY, connection_id TEXT, connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS chat_bans (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER, reason TEXT, banned_by INTEGER, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, until_date TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS grids (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, creator_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS grid_chats (grid_id INTEGER, chat_id INTEGER, hidden INTEGER DEFAULT 0, description TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS grid_moderators (grid_id INTEGER, user_id INTEGER, rank INTEGER DEFAULT 1, is_admin INTEGER DEFAULT 0, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, user_id))")
        c.execute("CREATE TABLE IF NOT EXISTS grid_bans (grid_id INTEGER, user_id INTEGER, reason TEXT, banned_by INTEGER, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, user_id))")
        c.execute("CREATE TABLE IF NOT EXISTS grid_mutes (grid_id INTEGER, user_id INTEGER, until_date TIMESTAMP, muted_by INTEGER, UNIQUE(grid_id, user_id))")
        c.execute("""CREATE TABLE IF NOT EXISTS grid_user_ranks (
            grid_id INTEGER, user_id INTEGER, rank INTEGER DEFAULT 1, added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, user_id)
        )""")
        c.execute("CREATE TABLE IF NOT EXISTS marriages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user1_id INTEGER, user2_id INTEGER, user1_name TEXT, user2_name TEXT, married_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, divorced_at TIMESTAMP, status TEXT DEFAULT 'active', in_top INTEGER DEFAULT 0, extra_days INTEGER DEFAULT 0, UNIQUE(chat_id, user1_id), UNIQUE(chat_id, user2_id))")
        c.execute("CREATE TABLE IF NOT EXISTS marriage_settings (chat_id INTEGER PRIMARY KEY, divorce_mode TEXT DEFAULT 'off', divorce_price INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, from_id INTEGER, to_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, name TEXT, text TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(chat_id, name))")
        c.execute("CREATE TABLE IF NOT EXISTS coins (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, last_farm TIMESTAMP, total_farmed INTEGER DEFAULT 0, last_tax TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS coin_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, reason TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS chat_coins (chat_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS catalog (chat_id INTEGER PRIMARY KEY, title TEXT, description TEXT, link TEXT, submitted_by INTEGER, submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'pending', show_moderators INTEGER DEFAULT 0, approved_by INTEGER, approved_at TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS catalog_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, submitted_by INTEGER, action TEXT, status TEXT DEFAULT 'pending', reviewed_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(chat_id, action))")
        c.execute("CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, emoji TEXT DEFAULT '🏅', description TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, achievement_id INTEGER, given_by INTEGER, given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id, achievement_id))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_settings (chat_id INTEGER PRIMARY KEY, channels_allowed INTEGER DEFAULT 0, reactions_allowed INTEGER DEFAULT 1, auto_requests INTEGER DEFAULT 0, description TEXT, invite_link TEXT, request_link TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_tags (user_id INTEGER, chat_id INTEGER, tag TEXT, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS citizenship (user_id INTEGER PRIMARY KEY, chat_id INTEGER, became_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS user_nicks (user_id INTEGER, chat_id INTEGER, nick TEXT, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS user_about (user_id INTEGER PRIMARY KEY, text TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_ranks (user_id INTEGER, chat_id INTEGER, rank TEXT, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_rules (chat_id INTEGER PRIMARY KEY, text TEXT, updated_by INTEGER, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS user_profiles (user_id INTEGER PRIMARY KEY, gender TEXT, birth_date TEXT, birth_visibility TEXT DEFAULT 'месяц', city TEXT, bio TEXT, motto TEXT, show_citizenship INTEGER DEFAULT 1, is_hidden INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS vip_settings (chat_id INTEGER PRIMARY KEY, price INTEGER DEFAULT 100)")
        c.execute("CREATE TABLE IF NOT EXISTS vip_users (user_id INTEGER PRIMARY KEY, expires_at TIMESTAMP, emoji TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS rp_commands (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, name TEXT, emoji TEXT, text TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(chat_id, name))")
        c.execute("CREATE TABLE IF NOT EXISTS global_rp_commands (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, emoji TEXT, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, name))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_antispam_settings (chat_id INTEGER PRIMARY KEY, antispam_enabled INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS stars_settings (chat_id INTEGER PRIMARY KEY, stars_per_candy INTEGER DEFAULT 2)")
        c.execute("CREATE TABLE IF NOT EXISTS stars_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, amount_candies INTEGER, stars_paid INTEGER, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS antispam_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, reason TEXT, admin_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS link_filter (chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS hidden_agents (user_id INTEGER PRIMARY KEY, hidden_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS global_settings (key TEXT PRIMARY KEY, value TEXT)")

        c.execute("INSERT OR IGNORE INTO agents (user_id, added_by) VALUES (?, ?)", (OWNER_ID, OWNER_ID))
        c.execute("""INSERT OR IGNORE INTO agent_ranks (user_id, rank, added_by) 
            VALUES (?, 4, ?)""", (OWNER_ID, OWNER_ID))

        conn.commit()# ================= РАНГИ ЧАТА =================
def get_rank(chat_id, user_id):
    if user_id == OWNER_ID:
        return 5
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT rank FROM admins WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        r = c.fetchone()
        return r[0] if r else 0

def set_rank(chat_id, user_id, rank, added_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO admins (user_id, chat_id, rank, added_by) VALUES (?, ?, ?, ?)", (user_id, chat_id, rank, added_by))
        conn.commit()

def remove_rank(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM admins WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()

def get_all_admins(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, rank FROM admins WHERE chat_id = ? ORDER BY rank DESC", (chat_id,))
        return c.fetchall()

def can_manage(chat_id, actor_id, target_id):
    if actor_id == OWNER_ID:
        return True
    return get_rank(chat_id, actor_id) > get_rank(chat_id, target_id)

def has_permission(chat_id, user_id, required_rank):
    return get_rank(chat_id, user_id) >= required_rank

# ================= РАНГИ АГЕНТОВ =================
def is_agent(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM agents WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None

def get_agent_rank(user_id):
    if user_id == OWNER_ID:
        return 4
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT rank FROM agent_ranks WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return r[0] if r else 0

def set_agent_rank(user_id, rank, added_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO agents (user_id, added_by) VALUES (?, ?)", (user_id, added_by))
        c.execute("INSERT OR REPLACE INTO agent_ranks (user_id, rank, added_by) VALUES (?, ?, ?)", (user_id, rank, added_by))
        conn.commit()

def remove_agent(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM agents WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM agent_ranks WHERE user_id = ?", (user_id,))
        conn.commit()

def has_agent_rank(user_id, min_rank):
    if user_id == OWNER_ID:
        return True
    return get_agent_rank(user_id) >= min_rank

# ================= СКРЫТЫЕ АГЕНТЫ =================
def is_hidden_agent(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM hidden_agents WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None

def hide_agent(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO hidden_agents (user_id) VALUES (?)", (user_id,))
        conn.commit()

def unhide_agent(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM hidden_agents WHERE user_id = ?", (user_id,))
        conn.commit()

def get_hidden_agents():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM hidden_agents")
        return [r[0] for r in c.fetchall()]

# ================= АНТИСПАМ =================
def is_in_antispam(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM antispam WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None

def is_ignored(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM ignore_list WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        return c.fetchone() is not None

def is_antispam_enabled(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT antispam_enabled FROM chat_antispam_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if r is None:
            c.execute("INSERT INTO chat_antispam_settings (chat_id, antispam_enabled) VALUES (?, 1)", (chat_id,))
            conn.commit()
            return True
        return bool(r[0])

def set_antispam_enabled(chat_id, enabled):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO chat_antispam_settings (chat_id, antispam_enabled) VALUES (?, ?)", (chat_id, 1 if enabled else 0))
        conn.commit()

def get_all_antispam_chats():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT DISTINCT sub.chat_id FROM (
            SELECT chat_id FROM messages_stats
            UNION
            SELECT chat_id FROM chat_codes
            UNION
            SELECT chat_id FROM admins
        ) sub
        LEFT JOIN chat_antispam_settings s ON s.chat_id = sub.chat_id
        WHERE COALESCE(s.antispam_enabled, 1) = 1""")
        return [r[0] for r in c.fetchall()]

def is_chat_banned(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM banned_chats WHERE chat_id = ?", (chat_id,))
        return c.fetchone() is not None

def get_chat_by_code(code):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id FROM chat_codes WHERE code = ?", (code.upper(),))
        r = c.fetchone()
        return r[0] if r else None

def get_chat_code(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT code FROM chat_codes WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if r:
            return r[0]
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        c.execute("INSERT INTO chat_codes (chat_id, code) VALUES (?, ?)", (chat_id, code))
        conn.commit()
        return code

def get_user_stats(user_id, chat_id):
    today = datetime.now().date().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(count) FROM messages_stats WHERE user_id = ? AND chat_id = ? AND date = ?", (user_id, chat_id, today))
        today_count = c.fetchone()[0] or 0
        c.execute("SELECT SUM(count) FROM messages_stats WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        all_count = c.fetchone()[0] or 0
        return today_count, all_count

async def is_tg_admin(chat_id, user_id):
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        return m.status in ['creator', 'administrator']
    except:
        return False

async def resolve_target(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user, None
    args = message.text.split()
    for a in args[1:]:
        if a.startswith('@'):
            username = a[1:]
            try:
                return await bot.get_chat(a), a
            except:
                with sqlite3.connect(DATABASE_PATH) as conn:
                    c = conn.cursor()
                    c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
                    r = c.fetchone()
                    if r:
                        try:
                            return await bot.get_chat(r[0]), a
                        except:
                            pass
            continue
        if a.isdigit():
            try:
                return await bot.get_chat(int(a)), a
            except:
                continue
    return None, None

async def get_chat_link(chat_id):
    try:
        chat = await bot.get_chat(chat_id)
        if chat.username:
            return f"https://t.me/{chat.username}"
    except:
        pass
    try:
        link = await bot.create_chat_invite_link(chat_id)
        return link.invite_link
    except:
        return None

async def kick_in_all_antispam_chats(target_id, max_parallel=10):
    all_chats = get_all_antispam_chats()
    sem = asyncio.Semaphore(max_parallel)
    results = {"success": 0, "failed": 0}

    async def kick(chat_id):
        async with sem:
            try:
                await bot.ban_chat_member(chat_id, target_id)
                await bot.unban_chat_member(chat_id, target_id)
                results["success"] += 1
            except:
                results["failed"] += 1

    if all_chats:
        await asyncio.gather(*[kick(cid) for cid in all_chats])
    return results["success"], results["failed"], len(all_chats)

# ================= ФИЛЬТР ССЫЛОК =================
def is_link_filter_enabled(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT enabled FROM link_filter WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if r is None:
            c.execute("INSERT INTO link_filter (chat_id, enabled) VALUES (?, 0)", (chat_id,))
            conn.commit()
            return False
        return bool(r[0])

def set_link_filter(chat_id, enabled):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO link_filter (chat_id, enabled) VALUES (?, ?)", (chat_id, 1 if enabled else 0))
        conn.commit()

def has_link(text):
    if not text:
        return False
    if re.search(r'(https?://|tg://|t\.me/)', text, re.IGNORECASE):
        return True
    if re.search(r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', text, re.IGNORECASE):
        return True
    return False

async def delete_later(message: types.Message, seconds: int = 60):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except:
        pass

# ================= ИСТОРИЯ АНТИСПАМА =================
def log_antispam_action(user_id, action, reason, admin_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO antispam_history 
            (user_id, action, reason, admin_id) VALUES (?, ?, ?, ?)""",
            (user_id, action, reason, admin_id))
        conn.commit()

def get_last_antispam_history(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT action, reason, admin_id, created_at 
            FROM antispam_history WHERE user_id = ? ORDER BY id DESC LIMIT 1""", (user_id,))
        return c.fetchone()

def get_antispam_info(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT reason, added_by, added_at FROM antispam WHERE user_id = ?", (user_id,))
        return c.fetchone()

def cancel_last_antispam_add(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, reason FROM antispam_history 
            WHERE user_id = ? AND action = 'add' ORDER BY id DESC LIMIT 1""", (user_id,))
        row = c.fetchone()
        if not row:
            return None
        hist_id, reason = row
        c.execute("DELETE FROM antispam_history WHERE id = ?", (hist_id,))
        conn.commit()
    return reason

# ================= РАНГИ В СЕТКЕ =================
def set_grid_user_rank(grid_id, user_id, rank, added_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO grid_user_ranks 
            (grid_id, user_id, rank, added_by, added_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (grid_id, user_id, rank, added_by))
        conn.commit()

def get_grid_user_rank(grid_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT rank FROM grid_user_ranks WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        r = c.fetchone()
        return r[0] if r else 0

def remove_grid_user_rank(grid_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM grid_user_ranks WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        conn.commit()

def get_all_grid_user_ranks(grid_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, rank FROM grid_user_ranks WHERE grid_id = ? ORDER BY rank DESC", (grid_id,))
        return c.fetchall()

# ================= СТАТИСТИКА БАНОВ =================
def get_all_user_bans(user_id):
    now = datetime.now().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT chat_id, reason, banned_by, banned_at, until_date FROM chat_bans 
            WHERE user_id = ? AND (until_date IS NULL OR until_date > ?) ORDER BY banned_at DESC""", (user_id, now))
        return c.fetchall()

def count_user_chat_bans(user_id):
    now = datetime.now().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM chat_bans WHERE user_id = ? AND (until_date IS NULL OR until_date > ?)""", (user_id, now))
        return c.fetchone()[0] or 0

def count_user_spam_bans(user_id):
    now = datetime.now().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM chat_bans WHERE user_id = ? AND LOWER(reason) LIKE '%спам%' 
            AND (until_date IS NULL OR until_date > ?)""", (user_id, now))
        return c.fetchone()[0] or 0

def auto_add_to_antispam_if_needed(user_id):
    if is_in_antispam(user_id):
        return False
    spam_bans = count_user_spam_bans(user_id)
    if spam_bans < 5:
        return False
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO antispam (user_id, reason, added_by, added_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)""", (user_id, "автоматическая блокировка спамера", 0))
        conn.commit()
    log_antispam_action(user_id, "add", "автоматическая блокировка спамера", 0)
    return True

# ================= TELEGRAM STARS =================
def get_global_stars_per_candy():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS global_settings (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("SELECT value FROM global_settings WHERE key = 'stars_per_candy'")
        r = c.fetchone()
        if not r:
            c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES ('stars_per_candy', '2')")
            conn.commit()
            return 2
        return int(r[0])

def set_global_stars_per_candy(value):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS global_settings (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES ('stars_per_candy', ?)", (str(value),))
        conn.commit()

def get_stars_per_candy(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT stars_per_candy FROM stars_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if not r:
            return get_global_stars_per_candy()
        return r[0]

def set_stars_per_candy(chat_id, value):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO stars_settings (chat_id, stars_per_candy) VALUES (?, ?)", (chat_id, value))
        conn.commit()

def create_stars_payment(user_id, chat_id, amount_candies, stars):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO stars_payments (user_id, chat_id, amount_candies, stars_paid, status)
            VALUES (?, ?, ?, ?, 'pending')""", (user_id, chat_id, amount_candies, stars))
        conn.commit()
        return c.lastrowid

def complete_stars_payment(payment_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, chat_id, amount_candies, stars_paid, status FROM stars_payments WHERE id = ?", (payment_id,))
        r = c.fetchone()
        if not r:
            return None
        user_id, chat_id, amount_candies, stars_paid, status = r
        if status == "completed":
            return None
        c.execute("UPDATE stars_payments SET status = 'completed' WHERE id = ?", (payment_id,))
        conn.commit()
    add_candies(user_id, amount_candies, 0)
    return (user_id, chat_id, amount_candies, stars_paid)

# ================= ГРАФИКИ =================
def generate_user_activity_chart(user_id, days=30):
    """Активность пользователя по ВСЕМ чатам."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT date, SUM(count) FROM messages_stats WHERE user_id = ? GROUP BY date ORDER BY date DESC LIMIT ?", (user_id, days))
        rows = c.fetchall()
    if not rows:
        return None
    rows = rows[::-1]
    today = datetime.now().date()
    date_counts = {d: cnt or 0 for d, cnt in rows}
    full_dates, full_counts = [], []
    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        full_dates.append(day)
        full_counts.append(date_counts.get(day, 0))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x_labels = [d[5:] for d in full_dates]
    bars = ax.bar(range(len(full_dates)), full_counts, color='#a6e22e', width=0.7)
    step = max(1, len(full_dates) // 10)
    ax.set_xticks(range(0, len(full_dates), step))
    ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], fontsize=8)
    ax.set_title("Активность по всем чатам", fontsize=12, pad=15)
    ax.set_ylabel("Сообщений", fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    for bar, cnt in zip(bars, full_counts):
        if cnt > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, str(cnt), ha='center', va='bottom', fontsize=7)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=90, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

def generate_user_chat_activity_chart(user_id, chat_id, days=30):
    """Активность пользователя ИМЕННО в этом чате."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT date, SUM(count) FROM messages_stats 
            WHERE user_id = ? AND chat_id = ? GROUP BY date ORDER BY date DESC LIMIT ?""",
            (user_id, chat_id, days))
        rows = c.fetchall()
    if not rows:
        return None
    rows = rows[::-1]
    today = datetime.now().date()
    date_counts = {d: cnt or 0 for d, cnt in rows}
    full_dates, full_counts = [], []
    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        full_dates.append(day)
        full_counts.append(date_counts.get(day, 0))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x_labels = [d[5:] for d in full_dates]
    bars = ax.bar(range(len(full_dates)), full_counts, color='#a6e22e', width=0.7)
    step = max(1, len(full_dates) // 10)
    ax.set_xticks(range(0, len(full_dates), step))
    ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], fontsize=8)
    ax.set_title("Активность в этом чате", fontsize=12, pad=15)
    ax.set_ylabel("Сообщений", fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    for bar, cnt in zip(bars, full_counts):
        if cnt > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, str(cnt), ha='center', va='bottom', fontsize=7)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=90, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

def generate_chat_activity_chart(chat_id, days=30):
    """Общая активность чата."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT date, SUM(count) FROM messages_stats WHERE chat_id = ? GROUP BY date ORDER BY date DESC LIMIT ?", (chat_id, days))
        rows = c.fetchall()
    if not rows:
        return None
    rows = rows[::-1]
    today = datetime.now().date()
    date_counts = {d: cnt or 0 for d, cnt in rows}
    full_dates, full_counts = [], []
    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        full_dates.append(day)
        full_counts.append(date_counts.get(day, 0))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x_labels = [d[5:] for d in full_dates]
    bars = ax.bar(range(len(full_dates)), full_counts, color='#66c2ff', width=0.7)
    step = max(1, len(full_dates) // 10)
    ax.set_xticks(range(0, len(full_dates), step))
    ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], fontsize=8)
    ax.set_title("Активность чата", fontsize=12, pad=15)
    ax.set_ylabel("Сообщений", fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    for bar, cnt in zip(bars, full_counts):
        if cnt > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, str(cnt), ha='center', va='bottom', fontsize=7)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=90, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

# ================= ВАРНЫ =================
def add_warn(user_id, chat_id, reason, warned_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO warns (user_id, chat_id, reason, warned_by) VALUES (?, ?, ?, ?)", (user_id, chat_id, reason, warned_by))
        conn.commit()

def get_warns(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, reason, warned_at FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY warned_at DESC", (user_id, chat_id))
        return c.fetchall()

def count_warns(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM warns WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        return c.fetchone()[0]

def remove_last_warn(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM warns WHERE id = (SELECT id FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY warned_at DESC LIMIT 1)", (user_id, chat_id))
        conn.commit()

def clear_warns(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM warns WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()

def get_top_users(chat_id, period="today", limit=10):
    today = datetime.now().date()
    if period == "today":
        query = "SELECT user_id, SUM(count) FROM messages_stats WHERE chat_id = ? AND date = ? GROUP BY user_id ORDER BY SUM(count) DESC LIMIT ?"
        params = (chat_id, today.isoformat(), limit)
    elif period == "week":
        query = "SELECT user_id, SUM(count) FROM messages_stats WHERE chat_id = ? AND date >= ? GROUP BY user_id ORDER BY SUM(count) DESC LIMIT ?"
        params = (chat_id, (today - timedelta(days=7)).isoformat(), limit)
    elif period == "month":
        query = "SELECT user_id, SUM(count) FROM messages_stats WHERE chat_id = ? AND date >= ? GROUP BY user_id ORDER BY SUM(count) DESC LIMIT ?"
        params = (chat_id, (today - timedelta(days=30)).isoformat(), limit)
    else:
        query = "SELECT user_id, SUM(count) FROM messages_stats WHERE chat_id = ? GROUP BY user_id ORDER BY SUM(count) DESC LIMIT ?"
        params = (chat_id, limit)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        return c.fetchall()

# ================= КОНФЕТКИ =================
def get_balance(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM candies WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return r[0] if r else 0

def add_candies(user_id, amount, added_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO candies (user_id, balance) VALUES (?, 0)", (user_id,))
        c.execute("UPDATE candies SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        c.execute("INSERT INTO candy_log (user_id, amount, added_by) VALUES (?, ?, ?)", (user_id, amount, added_by))
        conn.commit()

def get_top_candies(limit=10):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, balance FROM candies ORDER BY balance DESC LIMIT ?", (limit,))
        return c.fetchall()

# ================= КОИНЫ =================
def get_coins(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM coins WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return r[0] if r else 0

def add_coins(user_id, amount, reason="начисление"):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO coins (user_id, balance) VALUES (?, 0)", (user_id,))
        c.execute("UPDATE coins SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        c.execute("INSERT INTO coin_log (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, amount, reason))
        conn.commit()

def get_coins_info(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT balance, last_farm, total_farmed, last_tax FROM coins WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        if not r:
            c.execute("INSERT INTO coins (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return (0, None, 0, datetime.now().isoformat())
        return r

def update_farm_time(user_id, total_farmed):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE coins SET last_farm = CURRENT_TIMESTAMP, total_farmed = ? WHERE user_id = ?", (total_farmed, user_id))
        conn.commit()

def apply_tax(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT balance, last_tax FROM coins WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        if not r:
            return
        balance, last_tax = r
        if balance <= 0:
            return
        try:
            last_tax_dt = datetime.strptime(last_tax[:19], "%Y-%m-%d %H:%M:%S")
        except:
            last_tax_dt = datetime.now()
        if (datetime.now() - last_tax_dt).days >= 2:
            tax = max(1, int(balance * 0.01))
            c.execute("UPDATE coins SET balance = balance - ?, last_tax = CURRENT_TIMESTAMP WHERE user_id = ?", (tax, user_id))
            c.execute("INSERT INTO coin_log (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, -tax, "налог 1%"))
            conn.commit()

def get_farm_reward(user_id):
    info = get_coins_info(user_id)
    balance, last_farm, total_farmed, last_tax = info
    if not last_farm:
        return 5, 0
    try:
        last_farm_dt = datetime.strptime(last_farm[:19], "%Y-%m-%d %H:%M:%S")
    except:
        return 5, 0
    delta = datetime.now() - last_farm_dt
    hours = delta.total_seconds() / 3600
    if hours < 4:
        return 0, int((4 - hours) * 60)
    base = 5
    bonus = min(45, int(hours * 0.5))
    return base + bonus, 0

def get_coins_top(limit=10):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, balance FROM coins ORDER BY balance DESC LIMIT ?", (limit,))
        return c.fetchall()

def get_chat_coins(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM chat_coins WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        return r[0] if r else 0

def add_chat_coins(chat_id, amount):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO chat_coins (chat_id, balance) VALUES (?, 0)", (chat_id,))
        c.execute("UPDATE chat_coins SET balance = balance + ? WHERE chat_id = ?", (amount, chat_id))
        conn.commit()

# ================= АГЕНТЫ — СТАТУС =================
def update_agent_activity(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO agent_activity (user_id, last_seen) VALUES (?, CURRENT_TIMESTAMP)", (user_id,))
        conn.commit()

def get_agents_status():
    online, offline = [], []
    now = datetime.now()
    hidden = get_hidden_agents()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM agents")
        agents = c.fetchall()
        for (agent_id,) in agents:
            if agent_id in hidden:
                continue
            if agent_id == OWNER_ID:
                online.append(agent_id)
                continue
            c.execute("SELECT last_seen FROM agent_activity WHERE user_id = ?", (agent_id,))
            r = c.fetchone()
            if r:
                try:
                    ls = datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
                    if (now - ls).total_seconds() <= 600:
                        online.append(agent_id)
                    else:
                        offline.append(agent_id)
                except:
                    offline.append(agent_id)
            else:
                offline.append(agent_id)
    return online, offline

# ================= USERS =================
def register_user(user_id, first_name, username):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if c.fetchone() is None:
            c.execute("INSERT INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
            conn.commit()

def get_user_info(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT first_seen, first_name, username FROM users WHERE user_id = ?", (user_id,))
        return c.fetchone()

def get_total_stats(user_id):
    today = datetime.now().date().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(count) FROM messages_stats WHERE user_id = ?", (user_id,))
        total = c.fetchone()[0] or 0
        c.execute("SELECT SUM(count) FROM messages_stats WHERE user_id = ? AND date = ?", (user_id, today))
        today_count = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(DISTINCT chat_id) FROM messages_stats WHERE user_id = ?", (user_id,))
        chat_count = c.fetchone()[0] or 0
        c.execute("SELECT MIN(date) FROM messages_stats WHERE user_id = ?", (user_id,))
        first_msg_date = c.fetchone()[0]
        return total, today_count, chat_count, first_msg_date

# ================= BOT PROMOTED =================
def mark_bot_promoted(user_id, chat_id, promoted_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO bot_promoted (user_id, chat_id, promoted_by) VALUES (?, ?, ?)", (user_id, chat_id, promoted_by))
        conn.commit()

def is_bot_promoted(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM bot_promoted WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        return c.fetchone() is not None

def unmark_bot_promoted(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM bot_promoted WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()

# ================= CHAT BANS =================
def add_chat_ban(chat_id, user_id, reason, banned_by, until_date=None):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO chat_bans (chat_id, user_id, reason, banned_by, until_date) VALUES (?, ?, ?, ?, ?)", (chat_id, user_id, reason, banned_by, until_date))
        conn.commit()

def get_last_chat_ban(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT reason, banned_by, banned_at, until_date FROM chat_bans WHERE chat_id = ? AND user_id = ? ORDER BY banned_at DESC LIMIT 1", (chat_id, user_id))
        return c.fetchone()

def clear_chat_ban(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM chat_bans WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        conn.commit()

def get_expired_bans():
    now = datetime.now().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, user_id FROM chat_bans WHERE until_date IS NOT NULL AND until_date <= ?", (now,))
        return c.fetchall()

# ================= ПРИВЕТСТВИЕ =================
def get_greeting(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT text FROM greetings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        return r[0] if r else None

def set_greeting(chat_id, text, updated_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO greetings (chat_id, text, updated_by) VALUES (?, ?, ?)", (chat_id, text, updated_by))
        conn.commit()

def reset_greeting(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM greetings WHERE chat_id = ?", (chat_id,))
        conn.commit()

def format_greeting(text, user, chat):
    chat_title = chat.title or "чат"
    return (text
        .replace("{name}", user.first_name)
        .replace("{first_name}", user.first_name)
        .replace("{chat}", chat_title)
        .replace("{rules}", "правила")
        .replace("{link}", SUPPORT_CHAT_LINK))

def is_link(text):
    if not text:
        return False
    return bool(re.search(r'(https?://[^\s]+|t\.me/[^\s]+)', text))

# ================= КАПЧА =================
def save_captcha(user_id, chat_id, message_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO captcha (user_id, chat_id, message_id) VALUES (?, ?, ?)", (user_id, chat_id, message_id))
        conn.commit()

def get_captcha(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT message_id FROM captcha WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        r = c.fetchone()
        return r[0] if r else None

def remove_captcha(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM captcha WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()

# ================= BUSINESS =================
def save_business_connection(user_id, connection_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO business_connections (user_id, connection_id) VALUES (?, ?)", (user_id, connection_id))
        conn.commit()

def get_business_owner_by_conn(connection_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM business_connections WHERE connection_id = ?", (connection_id,))
        r = c.fetchone()
        return r[0] if r else None# ================= СЕТКА =================
def create_grid(name, creator_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO grids (name, creator_id) VALUES (?, ?)", (name, creator_id))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            return None

def get_grid_by_name(name):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        if name.isdigit():
            c.execute("SELECT id, name FROM grids WHERE id = ?", (int(name),))
        else:
            c.execute("SELECT id, name FROM grids WHERE LOWER(name) = LOWER(?)", (name,))
        return c.fetchone()

def add_chat_to_grid(grid_id, chat_id, hidden=0, description=""):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO grid_chats (grid_id, chat_id, hidden, description) VALUES (?, ?, ?, ?)", (grid_id, chat_id, hidden, description))
        conn.commit()

def get_grid_chats(grid_id, include_hidden=False):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        if include_hidden:
            c.execute("SELECT chat_id, hidden, description FROM grid_chats WHERE grid_id = ?", (grid_id,))
        else:
            c.execute("SELECT chat_id, hidden, description FROM grid_chats WHERE grid_id = ? AND hidden = 0", (grid_id,))
        return c.fetchall()

def get_chat_grid(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT grid_id FROM grid_chats WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        return r[0] if r else None

def is_grid_moderator(grid_id, user_id, min_rank=1):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT creator_id FROM grids WHERE id = ?", (grid_id,))
        creator = c.fetchone()
        if creator and creator[0] == user_id:
            return True
        if user_id == OWNER_ID:
            return True
        c.execute("SELECT rank, is_admin FROM grid_moderators WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        r = c.fetchone()
        if not r:
            return False
        if r[1] == 1:
            return True
        return r[0] >= min_rank

def add_grid_moderator(grid_id, user_id, rank=1, is_admin=0):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO grid_moderators (grid_id, user_id, rank, is_admin) VALUES (?, ?, ?, ?)", (grid_id, user_id, rank, is_admin))
        conn.commit()

def remove_grid_moderator(grid_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM grid_moderators WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        conn.commit()

def add_grid_ban(grid_id, user_id, reason, banned_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO grid_bans (grid_id, user_id, reason, banned_by) VALUES (?, ?, ?, ?)", (grid_id, user_id, reason, banned_by))
        conn.commit()

def remove_grid_ban(grid_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM grid_bans WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        conn.commit()

def add_grid_mute(grid_id, user_id, until_date, muted_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO grid_mutes (grid_id, user_id, until_date, muted_by) VALUES (?, ?, ?, ?)", (grid_id, user_id, until_date, muted_by))
        conn.commit()

def remove_grid_mute(grid_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM grid_mutes WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        conn.commit()

# ================= БРАКИ =================
def get_marriage(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, user1_id, user2_id, user1_name, user2_name, married_at, status, divorced_at, in_top, extra_days
            FROM marriages WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'""", (chat_id, user_id, user_id))
        return c.fetchone()

def get_divorced_marriage(chat_id, user_id):
    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, user1_id, user2_id, user1_name, user2_name, divorced_at
            FROM marriages WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) 
            AND status = 'divorced' AND divorced_at >= ? ORDER BY divorced_at DESC LIMIT 1""", (chat_id, user_id, user_id, three_days_ago))
        return c.fetchone()

def create_marriage(chat_id, u1_id, u1_name, u2_id, u2_name):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO marriages (chat_id, user1_id, user2_id, user1_name, user2_name) VALUES (?, ?, ?, ?, ?)", (chat_id, u1_id, u2_id, u1_name, u2_name))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            return None

def restore_marriage(marriage_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriages SET status = 'active', divorced_at = NULL WHERE id = ?", (marriage_id,))
        conn.commit()

def divorce_marriage(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriages SET status = 'divorced', divorced_at = CURRENT_TIMESTAMP WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'", (chat_id, user_id, user_id))
        conn.commit()

def get_all_marriages(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user1_id, user1_name, user2_id, user2_name, married_at, extra_days FROM marriages WHERE chat_id = ? AND status = 'active' ORDER BY married_at ASC", (chat_id,))
        return c.fetchall()

def add_proposal(chat_id, from_id, to_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM proposals WHERE chat_id = ? AND from_id = ?", (chat_id, from_id))
        c.execute("INSERT INTO proposals (chat_id, from_id, to_id) VALUES (?, ?, ?)", (chat_id, from_id, to_id))
        conn.commit()

def get_proposal(chat_id, from_id, to_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM proposals WHERE chat_id = ? AND from_id = ? AND to_id = ?", (chat_id, from_id, to_id))
        r = c.fetchone()
        return r[0] if r else None

def remove_proposal(chat_id, from_id, to_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM proposals WHERE chat_id = ? AND from_id = ? AND to_id = ?", (chat_id, from_id, to_id))
        conn.commit()

def get_marriage_settings(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT divorce_mode, divorce_price FROM marriage_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if not r:
            c.execute("INSERT INTO marriage_settings (chat_id) VALUES (?)", (chat_id,))
            conn.commit()
            return ("off", 0)
        return r

def format_marriage_duration(married_at_str, extra_days=0):
    try:
        married_at = datetime.strptime(married_at_str[:19], "%Y-%m-%d %H:%M:%S")
    except:
        try:
            married_at = datetime.strptime(married_at_str[:10], "%Y-%m-%d")
        except:
            return "неизвестно"
    now = datetime.now()
    delta = now - married_at
    days = delta.days + (extra_days or 0)
    if days < 0:
        days = 0
    years = days // 365
    months = (days % 365) // 30
    remaining_days = (days % 365) % 30
    parts = []
    if years > 0:
        parts.append(f"{years} г.")
    if months > 0:
        parts.append(f"{months} мес.")
    if remaining_days > 0 or not parts:
        parts.append(f"{remaining_days} дн.")
    return " ".join(parts)

# ================= ЗАМЕТКИ =================
def add_note(chat_id, name, text, created_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO notes (chat_id, name, text, created_by) VALUES (?, ?, ?, ?)", (chat_id, name, text, created_by))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            return None

def get_note_by_name(chat_id, name):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, text FROM notes WHERE chat_id = ? AND LOWER(name) = LOWER(?)", (chat_id, name))
        return c.fetchone()

def get_note_by_number(chat_id, number):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, text FROM notes WHERE chat_id = ? ORDER BY id ASC LIMIT 1 OFFSET ?", (chat_id, number - 1))
        return c.fetchone()

def get_all_notes(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM notes WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
        return c.fetchall()

def delete_note(chat_id, note_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM notes WHERE chat_id = ? AND id = ?", (chat_id, note_id))
        conn.commit()

# ================= КАТАЛОГ =================
def get_catalog_entry(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, title, description, link, submitted_by, submitted_at, status, show_moderators FROM catalog WHERE chat_id = ?", (chat_id,))
        return c.fetchone()

def add_to_catalog_queue(chat_id, submitted_by, action):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM catalog_queue WHERE chat_id = ? AND action = ?", (chat_id, action))
        c.execute("INSERT INTO catalog_queue (chat_id, submitted_by, action) VALUES (?, ?, ?)", (chat_id, submitted_by, action))
        conn.commit()
        return c.lastrowid

def update_catalog_queue_status(qid, status, reviewed_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE catalog_queue SET status = ?, reviewed_by = ? WHERE id = ?", (status, reviewed_by, qid))
        conn.commit()

def get_catalog_queue_entry(qid):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, submitted_by, action, status FROM catalog_queue WHERE id = ?", (qid,))
        return c.fetchone()

def add_catalog_chat(chat_id, title, description, link, submitted_by, show_moderators=0):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO catalog (chat_id, title, description, link, submitted_by, status, show_moderators, approved_by, approved_at)
            VALUES (?, ?, ?, ?, ?, 'approved', ?, ?, CURRENT_TIMESTAMP)""", (chat_id, title, description, link, submitted_by, show_moderators, submitted_by))
        conn.commit()

def get_catalog_list(limit=100):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, title, description, link FROM catalog WHERE status = 'approved' ORDER BY approved_at DESC LIMIT ?", (limit,))
        return c.fetchall()

# ================= АЧИВКИ =================
def get_achievement_by_name(name):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, emoji, description FROM achievements WHERE LOWER(name) = LOWER(?)", (name,))
        return c.fetchone()

def create_achievement(name, emoji, description):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO achievements (name, emoji, description) VALUES (?, ?, ?)", (name, emoji, description))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            return None

def get_user_achievements(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT a.id, a.name, a.emoji, a.description, ua.given_at FROM user_achievements ua JOIN achievements a ON a.id = ua.achievement_id WHERE ua.user_id = ? AND ua.chat_id = ? ORDER BY ua.given_at DESC", (user_id, chat_id))
        return c.fetchall()

def give_achievement(user_id, chat_id, achievement_id, given_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO user_achievements (user_id, chat_id, achievement_id, given_by) VALUES (?, ?, ?, ?)", (user_id, chat_id, achievement_id, given_by))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def remove_achievement(user_id, chat_id, achievement_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_achievements WHERE user_id = ? AND chat_id = ? AND achievement_id = ?", (user_id, chat_id, achievement_id))
        conn.commit()

def get_all_achievements():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, emoji, description FROM achievements ORDER BY id ASC")
        return c.fetchall()

def delete_achievement(aid):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_achievements WHERE achievement_id = ?", (aid,))
        c.execute("DELETE FROM achievements WHERE id = ?", (aid,))
        conn.commit()

# ================= УПРАВЛЕНИЕ ЧАТОМ =================
def update_chat_setting(chat_id, field, value):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
        c.execute(f"UPDATE chat_settings SET {field} = ? WHERE chat_id = ?", (value, chat_id))
        conn.commit()

def is_auto_requests_enabled(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT auto_requests FROM chat_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        return r and r[0] == 1

# ================= ГРАЖДАНСТВО =================
def get_citizenship_info(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, became_at FROM citizenship WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return r if r else None

def set_citizenship(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO citizenship (user_id, chat_id, became_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (user_id, chat_id))
        conn.commit()

def remove_citizenship(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM citizenship WHERE user_id = ?", (user_id,))
        conn.commit()

def get_chat_citizens(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, became_at FROM citizenship WHERE chat_id = ? ORDER BY became_at ASC", (chat_id,))
        return c.fetchall()

def format_citizenship_duration(became_at_str):
    try:
        became_at = datetime.strptime(became_at_str[:19], "%Y-%m-%d %H:%M:%S")
    except:
        try:
            became_at = datetime.strptime(became_at_str[:10], "%Y-%m-%d")
        except:
            return "недавно"
    delta = datetime.now() - became_at
    days = delta.days
    if days < 1:
        return "только что"
    elif days < 30:
        return f"{days} дн."
    months = days // 30
    remaining = days % 30
    if months < 12:
        return f"{months} мес. {remaining} дн."
    years = months // 12
    months = months % 12
    return f"{years} г. {months} мес."

# ================= ПРОФИЛЬ =================
def get_user_nick(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT nick FROM user_nicks WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        r = c.fetchone()
        return r[0] if r else None

def set_user_nick(user_id, chat_id, nick):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_nicks (user_id, chat_id, nick) VALUES (?, ?, ?)", (user_id, chat_id, nick))
        conn.commit()

def remove_user_nick(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_nicks WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()

def get_user_about(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT text FROM user_about WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return r[0] if r else None

def set_user_about(user_id, text):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_about (user_id, text) VALUES (?, ?)", (user_id, text))
        conn.commit()

def remove_user_about(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_about WHERE user_id = ?", (user_id,))
        conn.commit()

def get_user_rank_text(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT rank FROM user_ranks WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        r = c.fetchone()
        return r[0] if r else None

def set_user_rank_text(user_id, chat_id, rank):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_ranks (user_id, chat_id, rank) VALUES (?, ?, ?)", (user_id, chat_id, rank))
        conn.commit()

def remove_user_rank_text(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_ranks WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()

# ================= ПРАВИЛА =================
def get_chat_rules(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT text FROM chat_rules WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        return r[0] if r else None

def set_chat_rules(chat_id, text, updated_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO chat_rules (chat_id, text, updated_by, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", (chat_id, text, updated_by))
        conn.commit()

def reset_chat_rules(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM chat_rules WHERE chat_id = ?", (chat_id,))
        conn.commit()

# ================= АНКЕТА =================
def get_user_profile(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT gender, birth_date, city, bio, is_hidden, birth_visibility, motto, show_citizenship FROM user_profiles WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        if not r:
            c.execute("INSERT INTO user_profiles (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return (None, None, None, None, 1, 'месяц', None, 1)
        return r

def update_user_profile(user_id, field, value):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (user_id,))
        c.execute(f"UPDATE user_profiles SET {field} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()

def get_activity_stats(user_id):
    today = datetime.now().date()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(count) FROM messages_stats WHERE user_id = ? AND date = ?", (user_id, today.isoformat()))
        day = c.fetchone()[0] or 0
        week_ago = (today - timedelta(days=7)).isoformat()
        c.execute("SELECT SUM(count) FROM messages_stats WHERE user_id = ? AND date >= ?", (user_id, week_ago))
        week = c.fetchone()[0] or 0
        month_ago = (today - timedelta(days=30)).isoformat()
        c.execute("SELECT SUM(count) FROM messages_stats WHERE user_id = ? AND date >= ?", (user_id, month_ago))
        month = c.fetchone()[0] or 0
        c.execute("SELECT SUM(count) FROM messages_stats WHERE user_id = ?", (user_id,))
        total = c.fetchone()[0] or 0
        return day, week, month, total

def get_stars_title(stars):
    if stars >= 10000:
        return "🌟 Легенда"
    elif stars >= 5000:
        return "💫 Суперзвезда"
    elif stars >= 2000:
        return "✨ Звезда"
    elif stars >= 1000:
        return "😎 Его узнают на улице"
    elif stars >= 500:
        return "🔥 Популярный"
    elif stars >= 100:
        return "⭐ Известный"
    elif stars >= 10:
        return "🌱 Новичок"
    else:
        return "👤 Неизвестный"

def format_number(n):
    if n < 1000:
        return str(n)
    elif n < 10000:
        return f"{n/1000:.1f}k"
    elif n < 1000000:
        return f"{n//1000}k"
    else:
        return f"{n/1000000:.1f}M"

def format_time_since(date_str):
    if not date_str:
        return "недавно"
    try:
        if isinstance(date_str, str):
            d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        else:
            d = date_str
        delta = datetime.now() - d
        days = delta.days
        if days < 30:
            return f"{days} дн."
        months = days // 30
        remaining = days % 30
        if months < 12:
            return f"{months} мес. {remaining} дн."
        years = months // 12
        months = months % 12
        return f"{years} г. {months} мес."
    except:
        return "недавно"

# ================= VIP =================
def get_vip_price(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT price FROM vip_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if not r:
            c.execute("INSERT INTO vip_settings (chat_id, price) VALUES (?, 100)", (chat_id,))
            conn.commit()
            return 100
        return r[0]

def set_vip_price(chat_id, price):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO vip_settings (chat_id, price) VALUES (?, ?)", (chat_id, price))
        conn.commit()

def get_vip(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT expires_at, emoji FROM vip_users WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        if not r:
            return None
        expires_at, emoji = r
        try:
            exp_dt = datetime.strptime(expires_at[:19], "%Y-%m-%d %H:%M:%S")
            if exp_dt < datetime.now():
                c.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
                conn.commit()
                return None
        except:
            pass
        return (expires_at, emoji)

def add_vip_months(user_id, months):
    current = get_vip(user_id)
    if current:
        try:
            exp_dt = datetime.strptime(current[0][:19], "%Y-%m-%d %H:%M:%S")
            if exp_dt < datetime.now():
                exp_dt = datetime.now()
        except:
            exp_dt = datetime.now()
        emoji = current[1]
    else:
        exp_dt = datetime.now()
        emoji = None
    new_exp = exp_dt + timedelta(days=30 * months)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO vip_users (user_id, expires_at, emoji) VALUES (?, ?, ?)", (user_id, new_exp.isoformat(), emoji))
        conn.commit()
    return new_exp

def set_vip_emoji(user_id, emoji):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE vip_users SET emoji = ? WHERE user_id = ?", (emoji, user_id))
        conn.commit()

def get_vip_days_left(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT expires_at FROM vip_users WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        if not r:
            return 0
        try:
            exp_dt = datetime.strptime(r[0][:19], "%Y-%m-%d %H:%M:%S")
            delta = exp_dt - datetime.now()
            if delta.total_seconds() < 0:
                return 0
            return delta.days
        except:
            return 0

def get_vip_list(chat_id, only_vip=True, limit=50):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT user_id FROM messages_stats WHERE chat_id = ?", (chat_id,))
        all_users = [r[0] for r in c.fetchall()]
    result = []
    for uid in all_users:
        is_vip = get_vip(uid) is not None
        if only_vip == is_vip:
            result.append(uid)
    return result[:limit]

def get_vip_emoji(user_id):
    v = get_vip(user_id)
    if v and v[1]:
        return v[1]
    return ""

# ================= ПОГОДА =================
def get_weather(city: str):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(city)}&count=1&language=ru&format=json"
        with urlopen(geo_url, timeout=10) as response:
            geo_data = json.loads(response.read().decode("utf-8"))
        if not geo_data.get("results"):
            return None
        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        name = location["name"]
        country = location.get("country", "")
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&timezone=auto"
        with urlopen(weather_url, timeout=10) as response:
            weather_data = json.loads(response.read().decode("utf-8"))
        current = weather_data.get("current", {})
        return {"name": name, "country": country, "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"), "wind": current.get("wind_speed_10m"),
                "code": current.get("weather_code")}
    except Exception as e:
        print(f"Ошибка погоды: {e}")
        return None

def get_weather_emoji(code: int):
    if code == 0: return "☀️ Ясно"
    elif code in [1, 2, 3]: return "⛅ Переменная облачность"
    elif code in [45, 48]: return "🌫️ Туман"
    elif code in [51, 53, 55, 56, 57]: return "🌦️ Морось"
    elif code in [61, 63, 65, 66, 67]: return "🌧️ Дождь"
    elif code in [71, 73, 75, 77]: return "❄️ Снег"
    elif code in [80, 81, 82]: return "🌦️ Ливень"
    elif code in [85, 86]: return "❄️ Снегопад"
    elif code in [95, 96, 99]: return "⛈️ Гроза"
    else: return "🌡️ Погода"

# ================= АВТОРАЗБАН =================
async def auto_unban_loop():
    while True:
        try:
            expired = get_expired_bans()
            for chat_id, user_id in expired:
                try:
                    await bot.unban_chat_member(chat_id, user_id)
                    clear_chat_ban(chat_id, user_id)
                    try:
                        await bot.send_message(chat_id, f"♻️ {mention_by_id(user_id, 'Пользователь')} разбанен (срок истёк).", parse_mode="HTML", disable_web_page_preview=True)
                    except:
                        pass
                except:
                    pass
        except Exception as e:
            print(f"Ошибка в auto_unban_loop: {e}")
        await asyncio.sleep(300)# ================= /START =================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    try:
        me = await bot.get_me()
        bot_username = me.username
    except:
        bot_username = ""

    add_url = (
        f"https://t.me/{bot_username}?startgroup=true"
        f"&admin=delete_messages+ban_users+invite_users"
        f"+pin_messages+manage_video_chats+change_info"
    )

    text = (
        f"🧑‍💻 <b>Mos | Чат-менеджер</b> вас приветствует!\n\n"
        f"📖 <b>Мои команды:</b>\n"
        f"🔗 <a href='{TELETYPE_URL}'>Mos-command</a>\n\n"
        f"🛡 <b>Агенты:</b>\n"
    )

    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT a.user_id, COALESCE(r.rank, 1) FROM agents a
                     LEFT JOIN agent_ranks r ON r.user_id = a.user_id
                     ORDER BY COALESCE(r.rank, 1) DESC LIMIT 20""")
        agents = c.fetchall()

    if agents:
        for uid, rank in agents:
            try:
                u = await bot.get_chat(uid)
                rank_icon = {1: "🛡", 2: "🛡", 3: "🛡", 4: "⚜️"}.get(rank, "🛡")
                text += f"  {rank_icon} {user_link(uid, u.first_name, u.username)}\n"
            except:
                pass
    else:
        text += "  <i>пока нет</i>\n"

    text += f"\n{em('sos', '🆘')} <b>Поддержка:</b> {SUPPORT_CHAT_LINK}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить бота в чат", url=add_url)],
        [InlineKeyboardButton(text="🍬 Купить ириски", callback_data="buy_candies_menu")],
        [
            InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_CHAT_LINK),
            InlineKeyboardButton(text="📢 Канал", url=SUPPORT_CHANNEL_LINK)
        ]
    ])

    await message.reply(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=keyboard
    )

# ================= КУПИТЬ ИРИСКИ (меню) =================
@dp.callback_query(lambda c: c.data == "buy_candies_menu")
async def buy_candies_menu(callback: types.CallbackQuery):
    price = get_stars_per_candy(callback.message.chat.id)
    await callback.message.answer(
        f"🍬 <b>Купить ириски за ⭐ Stars</b>\n\n"
        f"💰 Курс: <b>{price} ⭐ = 1 🍬</b>\n\n"
        f"📌 Напишите:\n"
        f"<code>.купитьириски 10</code> → {price * 10} ⭐\n"
        f"<code>.купитьириски 50</code> → {price * 50} ⭐\n"
        f"<code>.купитьириски 100</code> → {price * 100} ⭐",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()

# ================= ПОМОЩЬ =================
@cmd("помощь")
async def help_cmd(message: types.Message):
    online, offline = get_agents_status()
    agents_text = ""
    if online:
        agents_text += f"{em('check', '✅')} <b>В сети:</b>\n"
        for uid in online:
            try:
                user = await bot.get_chat(uid)
                link = user_link(uid, user.first_name, user.username)
                agents_text += f"  • {link}\n"
            except:
                agents_text += f"  • ID: <code>{uid}</code>\n"
    else:
        agents_text += f"{em('cross', '❌')} <b>В сети:</b> нет\n"
    if offline:
        agents_text += f"\n{em('cross', '❌')} <b>Не в сети:</b>\n"
        for uid in offline:
            try:
                user = await bot.get_chat(uid)
                agents_text += f"  • {user_link(uid, user.first_name, user.username)}\n"
            except:
                agents_text += f"  • ID: <code>{uid}</code>\n"

    help_text = (
        f"{em('sos', '🆘')} <b>Помощь по боту {BOT_NAME}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{agents_text}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📖 <b>Команды:</b> <a href='{TELETYPE_URL}'>Mos-command</a>\n"
        f"{em('sos', '🆘')} <b>Поддержка:</b> <a href=\"{SUPPORT_CHAT_LINK}\">Перейти</a>\n"
        f"📢 <b>Канал:</b> <a href=\"{SUPPORT_CHANNEL_LINK}\">Перейти</a>"
    )
    await message.reply(help_text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("пинг")
async def ping_cmd(message: types.Message):
    await message.reply(f"{em('ping', '🏓')} Понг!", parse_mode="HTML", disable_web_page_preview=True)

@cmd("инфо")
async def info_cmd(message: types.Message):
    chat_id = message.chat.id
    chat_title = message.chat.title or "Без названия"
    code = get_chat_code(chat_id)
    link = await get_chat_link(chat_id)
    if link:
        link_text = f'<a href="{link}">Чат-ссылка</a>'
    else:
        link_text = "Ссылка недоступна"
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        today = datetime.now().date().isoformat()
        c.execute("SELECT SUM(count) FROM messages_stats WHERE chat_id = ? AND date = ?", (chat_id, today))
        today_count = c.fetchone()[0] or 0
        c.execute("SELECT SUM(count) FROM messages_stats WHERE chat_id = ?", (chat_id,))
        all_count = c.fetchone()[0] or 0
    await message.reply(
        f"{em('stats', '📊')} <b>{chat_title}</b>\n"
        f"{em('key', '🔑')} {link_text} | Код: <code>{code}</code>\n"
        f"{em('calendar', '🗓')} {datetime.now().strftime('%d.%m.%Y')}\n\n"
        f"{em('stats', '📊')} Сегодня: {today_count} | Всего: {all_count}",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@cmd("инфобот")
async def bot_info_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    start = datetime.now()
    sent = await message.reply("🏓 Считаю...")
    ping_ms = int((datetime.now() - start).total_seconds() * 1000)
    try:
        await sent.delete()
    except:
        pass
    uptime = datetime.now() - BOT_START_TIME
    days = uptime.days
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    if days > 0:
        uptime_str = f"{days} д. {hours} ч."
    elif hours > 0:
        uptime_str = f"{hours} ч. {minutes} мин."
    else:
        uptime_str = f"{minutes} мин."
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0] or 0
        c.execute("SELECT SUM(count) FROM messages_stats")
        total_messages = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(DISTINCT chat_id) FROM messages_stats")
        total_chats = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM agents")
        total_agents = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM antispam")
        total_antispam = c.fetchone()[0] or 0
    try:
        db_size = os.path.getsize(DATABASE_PATH)
        if db_size < 1024:
            db_size_str = f"{db_size} Б"
        elif db_size < 1024 * 1024:
            db_size_str = f"{db_size / 1024:.1f} КБ"
        else:
            db_size_str = f"{db_size / (1024 * 1024):.2f} МБ"
    except:
        db_size_str = "—"
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"⏱ Аптайм: <b>{uptime_str}</b>\n"
        f"🏓 Пинг: <b>{ping_ms} мс</b>\n"
        f"💾 База: <b>{db_size_str}</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"💬 Сообщений: <b>{total_messages}</b>\n"
        f"🗂 Чатов: <b>{total_chats}</b>\n"
        f"🛡 Агентов: <b>{total_agents}</b>\n"
        f"🚫 В антиспаме: <b>{total_antispam}</b>"
    )
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("профиль")
async def profile_cmd(message: types.Message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            try:
                if args[1].startswith('@'):
                    target = await bot.get_chat(args[1])
                elif args[1].isdigit():
                    target = await bot.get_chat(int(args[1]))
            except:
                return await message.reply(f"{em('cross', '❌')} Пользователь не найден", parse_mode="HTML", disable_web_page_preview=True)
    if not target:
        target = message.from_user
    today_count, all_count = get_user_stats(target.id, message.chat.id)
    in_antispam = is_in_antispam(target.id)
    in_ignore = is_ignored(message.chat.id, target.id)
    if in_antispam and in_ignore:
        status = f"{em('ban', '🚫')} В антиспаме + {em('mute', '🔇')} В игноре"
    elif in_antispam:
        status = f"{em('ban', '🚫')} В антиспаме"
    elif in_ignore:
        status = f"{em('mute', '🔇')} В игноре"
    else:
        status = f"{em('check', '✅')} Чист"
    if is_agent(target.id):
        ar = get_agent_rank(target.id)
        status += f" | {em('shield', '🛡')} {AGENT_RANKS.get(ar, 'Агент')}"
    rank = get_rank(message.chat.id, target.id)
    rank_name = RANK_NAMES.get(rank, "👤 Участник")
    nick = get_user_nick(target.id, message.chat.id)
    rank_text = get_user_rank_text(target.id, message.chat.id)
    about = get_user_about(target.id)
    cit = get_citizenship_info(target.id)
    cit_line = ""
    if cit:
        cit_chat_id, cit_date = cit
        try:
            cit_chat = await bot.get_chat(cit_chat_id)
            cit_title = cit_chat.title or f"Чат {cit_chat_id}"
        except:
            cit_title = f"Чат {cit_chat_id}"
        cit_duration = format_citizenship_duration(cit_date)
        cit_line = f"\n🏠 Гражданин чата «{cit_title}» {cit_duration}"
    vip_emoji = get_vip_emoji(target.id)
    text = (
        f"{em('user', '👤')} <b>Профиль {vip_emoji}{mention(target)}{vip_emoji}</b>\n\n"
        f"{em('id', '🆔')} ID: <code>{target.id}</code>\n"
        f"📛 Имя: {target.first_name}\n"
        f"🔤 Ник: {nick or '—'}\n"
        f"📌 Звание: {rank_text or '—'}\n"
        f"🏆 Ранг: {rank_name}\n"
        f"{em('stats', '📊')} Сегодня: {today_count}\n"
        f"{em('stats', '📊')} Всего: {all_count}\n"
        f"{em('shield', '🛡')} Статус: {status}"
        f"{cit_line}"
    )
    user_ach = get_user_achievements(target.id, message.chat.id)
    if user_ach:
        ach_text = " ".join([f"{a[2]}{a[1]}" for a in user_ach])
        text += f"\n\n🎖 Ачивки: {ach_text}"
    if about:
        text += f"\n\n✏️ <b>О себе:</b>\n{about}"
    chart_buf = None
    try:
        # График активности ИМЕННО участника в ЭТОМ чате
        chart_buf = generate_user_chat_activity_chart(target.id, message.chat.id, days=30)
    except Exception as e:
        print(f"Ошибка графика: {e}")
    if chart_buf:
        await message.reply_photo(
            photo=types.BufferedInputFile(chart_buf.getvalue(), filename="user_chat_activity.png"),
            caption=text,
            parse_mode="HTML"
        )
    else:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("анкета")
async def profile_full_cmd(message: types.Message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            try:
                if args[1].startswith('@'):
                    target = await bot.get_chat(args[1])
                elif args[1].isdigit():
                    target = await bot.get_chat(int(args[1]))
            except:
                return await message.reply(f"{em('cross', '❌')} Пользователь не найден", parse_mode="HTML", disable_web_page_preview=True)
    if not target:
        target = message.from_user
    register_user(target.id, target.first_name, target.username or "")
    user_info = get_user_info(target.id)
    if not user_info:
        first_seen = datetime.now()
    else:
        try:
            first_seen = datetime.strptime(user_info[0], "%Y-%m-%d %H:%M:%S")
        except:
            first_seen = datetime.now()
    profile = get_user_profile(target.id)
    gender, birth_date, city, bio, is_hidden, birth_visibility, motto, show_cit = profile
    stars = 0
    day, week, month, total = get_activity_stats(target.id)
    stars_title = get_stars_title(stars)
    cit = get_citizenship_info(target.id)
    cit_line = ""
    if cit and show_cit:
        cit_chat_id, cit_date = cit
        try:
            cit_chat = await bot.get_chat(cit_chat_id)
            cit_title = cit_chat.title or f"Чат {cit_chat_id}"
        except:
            cit_title = f"Чат {cit_chat_id}"
        cit_duration = format_citizenship_duration(cit_date)
        cit_line = f"\n🏠 Гражданин чата «{cit_title}» {cit_duration}"
    reg_date = first_seen.strftime("%d.%m.%Y")
    time_in_universe = format_time_since(first_seen.strftime("%Y-%m-%d"))
    vip_emoji = get_vip_emoji(target.id)
    if is_hidden and target.id != message.from_user.id and not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        text = (
            f"👤 <b>Это {vip_emoji}{mention(target)}{vip_emoji}</b>\n"
            f"🆔 <code>@{target.id}</code>\n\n"
            f"⏱ Во вселенной mos: с {reg_date} ({time_in_universe})\n"
            f"👨 Пол: {gender or 'не указан'}\n"
            f"📆 Дата рождения: {birth_date or 'не указана'}\n"
            f"🗺 Город: {city or 'не указан'}\n"
            f"📊 Активность (день|нед|мес|всего): {format_number(day)} | {format_number(week)} | {format_number(month)} | {format_number(total)}\n"
            f"✨ Звёздность: [{stars}] {stars_title} ({format_number(stars)})"
            f"{cit_line}\n\n"
            f"💬 <b>Анкета скрыта</b>"
        )
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)
        return
    text = (
        f"👤 <b>Это {vip_emoji}{mention(target)}{vip_emoji}</b>\n"
        f"🆔 <code>@{target.id}</code>\n\n"
        f"⏱ Во вселенной mos: с {reg_date} ({time_in_universe})\n"
        f"👨 Пол: {gender or 'не указан'}\n"
        f"📆 Дата рождения: {birth_date or 'не указана'}\n"
        f"🗺 Город: {city or 'не указан'}\n"
        f"📊 Активность (день|нед|мес|всего): {format_number(day)} | {format_number(week)} | {format_number(month)} | {format_number(total)}\n"
        f"✨ Звёздность: [{stars}] {stars_title} ({format_number(stars)})"
        f"{cit_line}"
    )
    if motto:
        text += f"\n\n💭 Девиз: <i>{motto}</i>"
    if bio:
        text += f"\n\n📝 <b>О себе:</b> {bio}"
    chart_buf = None
    try:
        chart_buf = generate_user_activity_chart(target.id, days=30)
    except Exception as e:
        print(f"Ошибка графика: {e}")
    if chart_buf:
        await message.reply_photo(
            photo=types.BufferedInputFile(chart_buf.getvalue(), filename="user_activity.png"),
            caption=text,
            parse_mode="HTML"
        )
    else:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("моя стата")
async def my_stats_cmd(message: types.Message):
    target = message.from_user
    try:
        chart_buf = generate_user_activity_chart(target.id, days=30)
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} Ошибка графика: {e}", parse_mode="HTML", disable_web_page_preview=True)
    if not chart_buf:
        return await message.reply("📭 Нет данных для графика.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply_photo(
        photo=types.BufferedInputFile(chart_buf.getvalue(), filename="my_stats.png"),
        caption=f"📊 Статистика {mention(target)} за 30 дней (по всем чатам)",
        parse_mode="HTML"
    )

@cmd("мойид")
async def myid_cmd(message: types.Message):
    await message.reply(f"{em('id', '🆔')} Ваш ID: <code>{message.from_user.id}</code>", parse_mode="HTML", disable_web_page_preview=True)

@cmd("кодчата")
async def chat_code_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) >= 2:
        if message.from_user.id != OWNER_ID:
            return await message.reply(f"{em('cross', '❌')} Только владелец бота.", parse_mode="HTML", disable_web_page_preview=True)
        new_code = args[1].strip().upper()
        if len(new_code) < 3 or len(new_code) > 20:
            return await message.reply(f"{em('cross', '❌')} Код от 3 до 20 символов.", parse_mode="HTML", disable_web_page_preview=True)
        if not re.match(r'^[A-ZА-Я0-9_]+$', new_code):
            return await message.reply(f"{em('cross', '❌')} Только буквы, цифры и <code>_</code>.", parse_mode="HTML", disable_web_page_preview=True)
        chat_id = message.chat.id
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT chat_id FROM chat_codes WHERE code = ? AND chat_id != ?", (new_code, chat_id))
            if c.fetchone():
                return await message.reply(f"{em('cross', '❌')} Код занят.", parse_mode="HTML", disable_web_page_preview=True)
            c.execute("INSERT OR REPLACE INTO chat_codes (chat_id, code) VALUES (?, ?)", (chat_id, new_code))
            conn.commit()
        return await message.reply(f"{em('check', '✅')} Код изменён на <code>{new_code}</code>", parse_mode="HTML", disable_web_page_preview=True)
    code = get_chat_code(message.chat.id)
    await message.reply(f"{em('key', '🔑')} Код чата: <code>{code}</code>", parse_mode="HTML", disable_web_page_preview=True)

@cmd("ид")
async def get_id_cmd(message: types.Message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            arg = args[1]
            if arg.isdigit():
                user_id = int(arg)
                try:
                    target = await bot.get_chat(user_id)
                except:
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        c = conn.cursor()
                        c.execute("SELECT first_name, username FROM users WHERE user_id = ?", (user_id,))
                        r = c.fetchone()
                        if r:
                            return await message.reply(f"{em('id', '🆔')} ID: <code>{user_id}</code>\n📛 Имя: {r[0]}", parse_mode="HTML", disable_web_page_preview=True)
                    return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML", disable_web_page_preview=True)
            elif arg.startswith('@'):
                try:
                    target = await bot.get_chat(arg)
                except:
                    return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML", disable_web_page_preview=True)
    if not target:
        target = message.from_user
    await message.reply(
        f"{em('id', '🆔')} <b>Информация</b>\n\n👤 Имя: {mention(target)}\n🆔 ID: <code>{target.id}</code>\n👤 Username: @{target.username if target.username else '—'}",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@cmd("чатид")
async def get_chat_id_cmd(message: types.Message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        fwd = message.reply_to_message.forward_from_chat
        return await message.reply(
            f"{em('id', '🆔')} <b>ID пересланного чата</b>\n\n📛 Название: <b>{fwd.title or 'Без названия'}</b>\n🆔 ID: <code>{fwd.id}</code>\n👤 Username: @{fwd.username if fwd.username else '—'}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    await message.reply(
        f"{em('id', '🆔')} <b>Информация о чате</b>\n\n📛 Название: <b>{message.chat.title or 'Личный чат'}</b>\n🆔 ID: <code>{message.chat.id}</code>\n👤 Username: @{message.chat.username if message.chat.username else '—'}",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@cmd("топ")
async def top_cmd(message: types.Message):
    args = message.text.split()
    period = "today"
    period_name = "за сегодня"
    if len(args) >= 2:
        p = args[1].lower()
        if p in ["неделя", "week", "н"]: period, period_name = "week", "за неделю"
        elif p in ["месяц", "month", "м"]: period, period_name = "month", "за месяц"
        elif p in ["все", "all", "всё"]: period, period_name = "all", "за всё время"
    top_users = get_top_users(message.chat.id, period, limit=10)
    if not top_users:
        return await message.reply(f"📭 Нет данных {period_name}.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"{em('stats', '📊')} <b>Топ {period_name}:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, count) in enumerate(top_users, 1):
        try:
            user = await bot.get_chat(user_id)
            name = user_link(user_id, user.first_name, user.username)
        except:
            name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{count}</b>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= +АГЕНТ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+агент"))
async def add_agent_cmd(message: types.Message):
    actor_id = message.from_user.id
    if actor_id != OWNER_ID and not has_agent_rank(actor_id, 4):
        return await message.reply(f"{em('cross', '❌')} Только Гл. Агент (4).", parse_mode="HTML", disable_web_page_preview=True)

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>+Агент @user 2</code>\n"
            "<code>+Агент</code> (ответом) <code>2</code>\n\n"
            "🎖 <b>Ранги:</b>\n"
            "1 — Мл. Агент\n"
            "2 — Агент\n"
            "3 — Ст. Агент\n"
            "4 — Гл. Агент",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if target.id == OWNER_ID:
        return await message.reply("⛔ Владельца нельзя.", parse_mode="HTML", disable_web_page_preview=True)

    args = message.text.split()
    rank = 1
    for a in args[1:]:
        if a.isdigit():
            rank = int(a)
            break
    if rank not in [1, 2, 3, 4]:
        return await message.reply(f"{em('cross', '❌')} Ранг от 1 до 4.", parse_mode="HTML", disable_web_page_preview=True)

    actor_rank = get_agent_rank(actor_id)
    if actor_id != OWNER_ID and rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя выдать ранг ≥ твоего.", parse_mode="HTML", disable_web_page_preview=True)

    target_was_agent = is_agent(target.id)
    set_agent_rank(target.id, rank, actor_id)
    rank_name = AGENT_RANKS.get(rank, "🛡 Агент")

    if target_was_agent:
        chat_msg = f"🎖 {mention(target)} повышен: <b>{rank_name}</b>"
    else:
        chat_msg = f"{em('check', '✅')} {mention(target)} теперь <b>{rank_name}</b>!"
    await message.reply(chat_msg, parse_mode="HTML", disable_web_page_preview=True)

    try:
        if target_was_agent:
            text_ls = (
                f"🎖 <b>Ваш ранг в боте повышен</b>\n\n"
                f"📊 Новый ранг: <b>{rank_name}</b>\n\n"
                f"Пользуйтесь своими полномочиями на славу <b>Mos</b>! 🛡"
            )
        else:
            text_ls = (
                f"{em('shield', '🛡')} <b>Вас назначили агентом Mos!</b>\n\n"
                f"📊 Ранг: <b>{rank_name}</b>\n\n"
                f"Пользуйтесь своими полномочиями на славу <b>Mos</b>! 🛡"
            )
        await bot.send_message(target.id, text_ls, parse_mode="HTML", disable_web_page_preview=True)
    except:
        pass

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-агент"))
async def remove_agent_cmd(message: types.Message):
    actor_id = message.from_user.id
    if actor_id != OWNER_ID and not has_agent_rank(actor_id, 4):
        return await message.reply(f"{em('cross', '❌')} Только Гл. Агент (4).", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("📌 <code>-Агент @user</code>", parse_mode="HTML", disable_web_page_preview=True)
    if target.id == OWNER_ID:
        return await message.reply("⛔ Владельца нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    if not is_agent(target.id):
        return await message.reply("⚠️ Не агент.", parse_mode="HTML", disable_web_page_preview=True)
    remove_agent(target.id)
    await message.reply(f"{em('cross', '❌')} {mention(target)} больше не агент.", parse_mode="HTML", disable_web_page_preview=True)
    try:
        await bot.send_message(target.id, f"❌ <b>Вас сняли с должности агента Mos.</b>\n\nСпасибо за службу! 🛡", parse_mode="HTML", disable_web_page_preview=True)
    except:
        pass

@cmd("агенты")
async def list_agents_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT a.user_id, COALESCE(r.rank, 1) FROM agents a
                     LEFT JOIN agent_ranks r ON r.user_id = a.user_id
                     ORDER BY COALESCE(r.rank, 1) DESC""")
        rows = c.fetchall()
    if not rows:
        return await message.reply("📭 Нет агентов.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"{em('shield', '🛡')} <b>Агенты Mos:</b>\n\n"
    for uid, rank in rows:
        try:
            u = await bot.get_chat(uid)
            name = user_link(uid, u.first_name, u.username)
        except:
            name = f"ID {uid}"
        rank_name = AGENT_RANKS.get(rank, "🛡 Агент")
        text += f"{rank_name} — {name}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= +ПОМОЩЬ / -ПОМОЩЬ =================
@dp.message(lambda m: m.text and m.text.lower().strip() == "-помощь")
async def hide_from_help_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_agent(user_id) and user_id != OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Только агенты могут использовать.", parse_mode="HTML", disable_web_page_preview=True)
    if is_hidden_agent(user_id):
        return await message.reply(f"ℹ️ Вы уже <b>скрыты</b>.", parse_mode="HTML", disable_web_page_preview=True)
    hide_agent(user_id)
    await message.reply(
        f"{em('check', '✅')} <b>Вы скрыты из списка агентов!</b>\n\n"
        f"👻 В <code>.помощь</code> вас больше не видно\n"
        f"↩️ Вернуться: <code>+помощь</code>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.message(lambda m: m.text and m.text.lower().strip() == "+помощь")
async def show_in_help_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_agent(user_id) and user_id != OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Только агенты могут использовать.", parse_mode="HTML", disable_web_page_preview=True)
    if not is_hidden_agent(user_id):
        return await message.reply(f"ℹ️ Вы <b>не скрыты</b>.", parse_mode="HTML", disable_web_page_preview=True)
    unhide_agent(user_id)
    await message.reply(
        f"{em('check', '✅')} <b>Вы снова в списке агентов!</b>\n\n"
        f"🛡 Вас видно в <code>.помощь</code>\n"
        f"🙈 Скрыться: <code>-помощь</code>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ================= .СКРЫТЫЕ (владелец) =================
@cmd("скрытые")
async def list_hidden_agents_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    hidden = get_hidden_agents()
    if not hidden:
        return await message.reply("📭 Нет скрытых агентов.", disable_web_page_preview=True)
    text = f"👻 <b>Скрытых агентов:</b> {len(hidden)}\n\n"
    for uid in hidden:
        try:
            u = await bot.get_chat(uid)
            name = user_link(uid, u.first_name, u.username)
        except:
            name = f"ID {uid}"
        rank = get_agent_rank(uid)
        rank_name = AGENT_RANKS.get(rank, "—")
        text += f"• {name} — {rank_name}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= .ПОВЫСИТЬ =================
@cmd("повысить")
async def promote_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>.повысить @user 3</code>\n"
            "<code>.повысить</code> (ответом) <code>3</code>\n\n"
            "🎖 <b>Ранги чата:</b>\n"
            "1 — Мл. Модератор\n"
            "2 — Ст. Модератор\n"
            "3 — Мл. Админ\n"
            "4 — Ст. Админ\n"
            "5 — Владелец",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if not can_manage(message.chat.id, message.from_user.id, target.id):
        return await message.reply(f"{em('cross', '❌')} Нельзя управлять.", parse_mode="HTML", disable_web_page_preview=True)

    current_rank = get_rank(message.chat.id, target.id)
    if target.id == OWNER_ID:
        return await message.reply("⚠️ Владельца нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    if current_rank >= 5:
        return await message.reply("⚠️ Это владелец.", parse_mode="HTML", disable_web_page_preview=True)

    args = message.text.split()
    new_rank = None
    for a in args[1:]:
        if a.isdigit():
            new_rank = int(a)
            break

    if new_rank is None:
        new_rank = current_rank + 1
        if new_rank > 5:
            new_rank = 5

    if new_rank not in [1, 2, 3, 4, 5]:
        return await message.reply(f"{em('cross', '❌')} Ранг от 1 до 5.", parse_mode="HTML", disable_web_page_preview=True)

    if message.from_user.id != OWNER_ID and new_rank >= actor_rank:
        return await message.reply(
            f"{em('cross', '❌')} Нельзя выдать ранг ≥ твоего (твой: {actor_rank}).",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if new_rank <= current_rank:
        return await message.reply(
            f"⚠️ У юзера уже {RANK_NAMES.get(current_rank, '—')}.\n"
            f"Для понижения: <code>.понизить {new_rank}</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    set_rank(message.chat.id, target.id, new_rank, message.from_user.id)
    rank_name = RANK_NAMES[new_rank]

    await message.reply(
        f"🏆 {mention(target)} повышен до: {rank_name}",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    try:
        chat_title = message.chat.title or "чат"
        actor_link = user_link(message.from_user.id, message.from_user.first_name, message.from_user.username)
        await bot.send_message(
            target.id,
            f"🏆 <b>Вас повысили!</b>\n\n"
            f"📊 Новый ранг: <b>{rank_name}</b>\n"
            f"📍 Чат: <b>{chat_title}</b>\n"
            f"👮 Повысил: {actor_link}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except:
        pass

# ================= .ПОНИЗИТЬ =================
@cmd("понизить")
async def demote_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>.понизить @user 1</code>\n"
            "<code>.понизить</code> (ответом) <code>1</code>\n\n"
            "🎖 <b>Ранги чата:</b>\n"
            "0 — Снять всё\n"
            "1 — Мл. Модератор\n"
            "2 — Ст. Модератор\n"
            "3 — Мл. Админ\n"
            "4 — Ст. Админ",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if target.id == OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    if not can_manage(message.chat.id, message.from_user.id, target.id):
        return await message.reply(f"{em('cross', '❌')} Нельзя управлять.", parse_mode="HTML", disable_web_page_preview=True)

    current_rank = get_rank(message.chat.id, target.id)
    if current_rank == 0:
        return await message.reply("⚠️ И так участник.", parse_mode="HTML", disable_web_page_preview=True)

    args = message.text.split()
    new_rank = None
    for a in args[1:]:
        if a.isdigit():
            new_rank = int(a)
            break

    if new_rank is None:
        new_rank = current_rank - 1

    if new_rank < 0 or new_rank > 5:
        return await message.reply(f"{em('cross', '❌')} Ранг от 0 до 5.", parse_mode="HTML", disable_web_page_preview=True)

    if message.from_user.id != OWNER_ID and new_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя поставить ранг ≥ твоего.", parse_mode="HTML", disable_web_page_preview=True)

    if new_rank >= current_rank:
        return await message.reply(
            f"⚠️ У юзера уже {RANK_NAMES.get(current_rank, '—')}.\n"
            f"Для повышения: <code>.повысить {new_rank}</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    chat_title = message.chat.title or "чат"
    actor_link = user_link(message.from_user.id, message.from_user.first_name, message.from_user.username)

    if new_rank == 0:
        remove_rank(message.chat.id, target.id)
        await message.reply(f"📉 {mention(target)} разжалован (участник).", parse_mode="HTML", disable_web_page_preview=True)
        try:
            await bot.send_message(
                target.id,
                f"📉 <b>Вас разжаловали</b>\n\n"
                f"📊 Теперь: <b>👤 Участник</b>\n"
                f"📍 Чат: <b>{chat_title}</b>\n"
                f"👮 Снял: {actor_link}",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except:
            pass
    else:
        set_rank(message.chat.id, target.id, new_rank, message.from_user.id)
        rank_name = RANK_NAMES[new_rank]
        await message.reply(f"📉 {mention(target)} понижен: {rank_name}", parse_mode="HTML", disable_web_page_preview=True)
        try:
            await bot.send_message(
                target.id,
                f"📉 <b>Вас понизили</b>\n\n"
                f"📊 Новый ранг: <b>{rank_name}</b>\n"
                f"📍 Чат: <b>{chat_title}</b>\n"
                f"👮 Понизил: {actor_link}",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except:
            pass

@cmd("разжаловать")
@cmd("снять")
async def demote_all_cmd(message: types.Message):
    actor_id = message.from_user.id
    actor_rank = get_rank(message.chat.id, actor_id)
    if actor_id != OWNER_ID and actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    if target.id == OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    target_rank = get_rank(message.chat.id, target.id)
    if target_rank == 0:
        return await message.reply(f"⚠️ И так без прав.", parse_mode="HTML", disable_web_page_preview=True)
    if target_rank == 5 and actor_id != OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    if actor_id != OWNER_ID and target_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    remove_rank(message.chat.id, target.id)
    await message.reply(f"{em('cross', '❌')} {mention(target)} разжалован.", parse_mode="HTML", disable_web_page_preview=True)

# ================= .АДМИНЫ =================
@cmd("админы")
async def list_admins_cmd(message: types.Message):
    admins = get_all_admins(message.chat.id)
    if not admins:
        return await message.reply("📭 Нет админов.", parse_mode="HTML", disable_web_page_preview=True)
    text = "🏆 <b>Админы чата:</b>\n\n"
    for user_id, rank in admins:
        try:
            user = await bot.get_chat(user_id)
            name = user_link(user_id, user.first_name, user.username)
        except:
            name = f"ID: {user_id}"
        agent_badge = f" {em('shield', '🛡')}" if is_agent(user_id) else ""
        text += f"{RANK_NAMES.get(rank, '👤 Участник')} — {name}{agent_badge}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("восстановить")
async def restore_creator_cmd(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status != "creator":
            return await message.reply(f"{em('cross', '❌')} Только создатель.", parse_mode="HTML", disable_web_page_preview=True)
    except:
        return await message.reply(f"{em('cross', '❌')} Ошибка.", parse_mode="HTML", disable_web_page_preview=True)
    current_rank = get_rank(chat_id, user_id)
    if current_rank == 5:
        return await message.reply(f"ℹ️ Вы уже владелец.", parse_mode="HTML", disable_web_page_preview=True)
    set_rank(chat_id, user_id, 5, user_id)
    await message.reply(f"{em('check', '✅')} Вы владелец чата!", parse_mode="HTML", disable_web_page_preview=True)

# ================= +АДМИН =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+админ"))
async def grant_admin_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)

    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return await message.reply(f"{em('cross', '❌')} Я не админ.", parse_mode="HTML", disable_web_page_preview=True)
        if bot_member.status == 'administrator' and not bot_member.can_promote_members:
            return await message.reply(f"{em('cross', '❌')} Нет права добавлять админов.", parse_mode="HTML", disable_web_page_preview=True)
    except:
        return await message.reply(f"{em('cross', '❌')} Ошибка проверки прав.", parse_mode="HTML", disable_web_page_preview=True)

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>+Админ @user</code>\n"
            "<code>+Админ</code> (ответом на сообщение)\n\n"
            "<i>Юзер должен быть повышен в боте (ранг 1+)</i>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if target.id == OWNER_ID:
        return await message.reply("⛔ Владелец и так имеет все права.", parse_mode="HTML", disable_web_page_preview=True)

    target_rank = get_rank(message.chat.id, target.id)
    if target_rank < 1:
        return await message.reply(
            f"⚠️ Сначала повысьте в боте:\n<code>.повысить {target.id} 1</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if message.from_user.id != OWNER_ID and target_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя управлять равным или выше.", parse_mode="HTML", disable_web_page_preview=True)

    try:
        await bot.promote_chat_member(
            chat_id=message.chat.id, user_id=target.id,
            can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_promote_members=True, can_change_info=True,
            can_invite_users=True, can_pin_messages=True
        )
        mark_bot_promoted(target.id, message.chat.id, message.from_user.id)
        await message.reply(
            f"{em('check', '✅')} {mention(target)} теперь <b>ТГ-админ</b> в этом чате!\n"
            f"👮 Выдал: {mention(message.from_user)}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)# ================= МОДЕРАЦИЯ =================
@cmd("бан")
async def ban_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    args = message.text.split()
    duration_seconds = None
    duration_text = "навсегда"
    if len(args) >= 3 and args[1].isdigit():
        amount = int(args[1])
        unit = args[2].lower().rstrip('.,!?')
        if amount > 0:
            if unit in ['сек', 'секунд']: duration_seconds, duration_text = amount, f"{amount} сек."
            elif unit in ['мин', 'минут', 'м']: duration_seconds, duration_text = amount * 60, f"{amount} мин."
            elif unit in ['час', 'часа', 'часов', 'ч']: duration_seconds, duration_text = amount * 3600, f"{amount} ч."
            elif unit in ['день', 'дня', 'дней', 'д']: duration_seconds, duration_text = amount * 86400, f"{amount} дн."
            elif unit in ['неделя', 'недели', 'недель', 'н']: duration_seconds, duration_text = amount * 604800, f"{amount} нед."
            elif unit in ['месяц', 'месяца', 'месяцев']: duration_seconds, duration_text = amount * 30 * 86400, f"{amount} мес."
    if duration_seconds and duration_seconds > 366 * 86400:
        return await message.reply(f"{em('cross', '❌')} Максимум 366 дней.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID:
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        reason = parts[1].strip()
    try:
        if duration_seconds:
            until = datetime.now() + timedelta(seconds=duration_seconds)
            await bot.ban_chat_member(message.chat.id, target.id, until_date=until)
            add_chat_ban(message.chat.id, target.id, reason, message.from_user.id, until.isoformat())
            ban_type = f"на <b>{duration_text}</b>"
        else:
            await bot.ban_chat_member(message.chat.id, target.id)
            add_chat_ban(message.chat.id, target.id, reason, message.from_user.id, None)
            ban_type = "<b>навсегда</b>"

        auto_added = auto_add_to_antispam_if_needed(target.id)

        response = (
            f"{em('ban', '🚫')} {mention(target)} получает бан {ban_type}\n"
            f"👮 Модератор: {mention(message.from_user)}\n📝 Причина: {reason}"
        )

        if auto_added:
            response += (
                f"\n\n☢️ <b>Юзер автоматически добавлен в антиспам!</b>\n"
                f"📊 Причина: 5+ банов за спам\n"
                f"💬 Внесён ботом"
            )

        await message.reply(response, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)

@cmd("разбан")
async def unban_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    try:
        await bot.unban_chat_member(message.chat.id, target.id)
        clear_chat_ban(message.chat.id, target.id)
        await message.reply(f"{em('check', '✅')} {mention(target)} разбанен", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)

@cmd("мут")
async def mute_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    args = message.text.split()
    duration_seconds = 1800
    duration_text = "30 мин."
    if len(args) >= 3 and args[1].isdigit():
        amount = int(args[1])
        unit = args[2].lower().rstrip('.,!?')
        if amount > 0:
            if unit in ['сек', 'секунд']: duration_seconds, duration_text = amount, f"{amount} сек."
            elif unit in ['мин', 'минут', 'м']: duration_seconds, duration_text = amount * 60, f"{amount} мин."
            elif unit in ['час', 'часа', 'часов', 'ч']: duration_seconds, duration_text = amount * 3600, f"{amount} ч."
            elif unit in ['день', 'дня', 'дней', 'д']: duration_seconds, duration_text = amount * 86400, f"{amount} дн."
            elif unit in ['неделя', 'недели', 'недель', 'н']: duration_seconds, duration_text = amount * 604800, f"{amount} нед."
    if duration_seconds > 366 * 86400:
        return await message.reply(f"{em('cross', '❌')} Максимум 366 дней.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID:
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        reason = parts[1].strip()
    try:
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(seconds=duration_seconds)
        )
        await message.reply(
            f"{em('mute', '🔇')} {mention(target)} замучен на <b>{duration_text}</b>\n"
            f"👮 Модератор: {mention(message.from_user)}\n📝 Причина: {reason}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)

@cmd("размут")
async def unmute_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    try:
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        )
        await message.reply(f"🔈 {mention(target)} размучен", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)

@cmd("кик")
async def kick_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID:
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"👢 {mention(target)} кикнут", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-смс"))
async def delete_message_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return
    if not message.reply_to_message:
        return
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return
        if bot_member.status == 'administrator' and not bot_member.can_delete_messages:
            return
    except:
        return
    args = message.text.split()
    count = 1
    if len(args) >= 2 and args[1].isdigit():
        count = int(args[1])
        if count < 1 or count > 100:
            count = 1
    if count == 1:
        try:
            await message.reply_to_message.delete()
        except:
            pass
    else:
        start_id = message.reply_to_message.message_id
        end_id = message.message_id
        for msg_id in range(start_id, end_id + 1):
            if msg_id != message.message_id:
                try:
                    await bot.delete_message(message.chat.id, msg_id)
                except:
                    pass
    try:
        await message.delete()
    except:
        pass

# ================= ПИН / АНПИН =================
@cmd("пин")
@cmd("закрепить")
async def pin_message_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", disable_web_page_preview=True)
    if not message.reply_to_message:
        return await message.reply(
            "📌 <b>Как использовать:</b>\n"
            "Ответьте на сообщение и напишите <code>.пин</code>\n\n"
            "🔕 <b>Тихо:</b> <code>.пин тихо</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return await message.reply(f"{em('cross', '❌')} Я не админ — не могу закрепить.", disable_web_page_preview=True)
        if bot_member.status == 'administrator' and not bot_member.can_pin_messages:
            return await message.reply(f"{em('cross', '❌')} Нет права закреплять сообщения.", disable_web_page_preview=True)
    except:
        return
    args = message.text.split()
    silent = len(args) >= 2 and args[1].lower() in ["тихо", "silent", "s", "тих"]
    notify = not silent
    try:
        await bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id,
            disable_notification=not notify
        )
        mode = "🔕 тихо" if silent else "🔔 с уведомлением"
        try:
            await message.delete()
        except:
            pass
        confirm = await message.answer(f"{em('check', '✅')} Закреплено ({mode})", disable_web_page_preview=True)
        await asyncio.sleep(3)
        try:
            await confirm.delete()
        except:
            pass
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", disable_web_page_preview=True)

@cmd("анпин")
@cmd("открепить")
@cmd("унпин")
async def unpin_message_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return
        if bot_member.status == 'administrator' and not bot_member.can_pin_messages:
            return
    except:
        return
    try:
        if message.reply_to_message:
            await bot.unpin_chat_message(
                chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id
            )
            await message.reply(f"{em('check', '✅')} Откреплено.", disable_web_page_preview=True)
        else:
            await bot.unpin_all_chat_messages(chat_id=message.chat.id)
            await message.reply(f"{em('check', '✅')} Все закрепы сняты.", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", disable_web_page_preview=True)

# ================= ВАРНЫ =================
@cmd("варн")
async def warn_cmd(message: types.Message):
    actor_id = message.from_user.id
    actor_rank = get_rank(message.chat.id, actor_id)
    if actor_rank < 1:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    target_rank = get_rank(message.chat.id, target.id)
    target_is_tg_admin = await is_tg_admin(message.chat.id, target.id)
    if actor_rank == 5:
        pass
    elif actor_rank == 4:
        if target_rank >= 4:
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    else:
        if target_rank >= actor_rank:
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
        if target_is_tg_admin:
            return await message.reply("⛔ Нельзя варнить ТГ-админа.", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        reason = parts[1].strip()
    add_warn(target.id, message.chat.id, reason, actor_id)
    warns_count = count_warns(target.id, message.chat.id)
    if warns_count >= 3:
        removed_admin = False
        if target_is_tg_admin and is_bot_promoted(target.id, message.chat.id):
            try:
                await bot.promote_chat_member(
                    chat_id=message.chat.id, user_id=target.id,
                    can_manage_chat=False, can_delete_messages=False,
                    can_manage_video_chats=False, can_restrict_members=False,
                    can_promote_members=False, can_change_info=False,
                    can_invite_users=False, can_pin_messages=False
                )
                unmark_bot_promoted(target.id, message.chat.id)
                removed_admin = True
            except:
                pass
        try:
            await bot.restrict_chat_member(
                message.chat.id, target.id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(seconds=3600)
            )
            clear_warns(target.id, message.chat.id)
            result_text = f"{em('pencil', '✏️')} {mention(target)} получил 3-й варн!\n"
            if removed_admin:
                result_text += "👑 ТГ-админка снята.\n"
            result_text += f"{em('mute', '🔇')} Мут на 1 час.\n📝 Причина: {reason}"
            await message.reply(result_text, parse_mode="HTML", disable_web_page_preview=True)
            return
        except Exception as e:
            await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)
            return
    await message.reply(
        f"{em('pencil', '✏️')} {mention(target)} получил предупреждение!\n📝 Причина: {reason}\n{em('stats', '📊')} Всего: {warns_count}/3",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@cmd("варны")
async def warns_list_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    warns = get_warns(target.id, message.chat.id)
    if not warns:
        return await message.reply(f"{em('check', '✅')} У {mention(target)} нет варнов.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"{em('pencil', '✏️')} <b>Варны {mention(target)}:</b> ({len(warns)}/3)\n\n"
    for i, (warn_id, reason, warned_at) in enumerate(warns, 1):
        text += f"{i}. {reason}\n   {em('calendar', '🗓')} {warned_at[:10]}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("снятьварн")
async def unwarn_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    warns = get_warns(target.id, message.chat.id)
    if not warns:
        return await message.reply(f"{em('check', '✅')} Нет варнов.", parse_mode="HTML", disable_web_page_preview=True)
    remove_last_warn(target.id, message.chat.id)
    new_count = count_warns(target.id, message.chat.id)
    await message.reply(f"{em('check', '✅')} Снят последний варн. Осталось: {new_count}/3", parse_mode="HTML", disable_web_page_preview=True)

@cmd("сбросварнов")
async def clear_warns_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    count = count_warns(target.id, message.chat.id)
    if count == 0:
        return await message.reply(f"{em('check', '✅')} Нет варнов.", parse_mode="HTML", disable_web_page_preview=True)
    clear_warns(target.id, message.chat.id)
    await message.reply(f"♻️ Все варны ({count}) сброшены.", parse_mode="HTML", disable_web_page_preview=True)

# ================= НАКАЗАНИЯ =================
@cmd("наказания")
async def show_punishments(message: types.Message):
    if not await is_tg_admin(message.chat.id, message.from_user.id):
        return
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            try:
                if args[1].startswith('@'): target = await bot.get_chat(args[1])
                elif args[1].isdigit(): target = await bot.get_chat(int(args[1]))
            except:
                return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML", disable_web_page_preview=True)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    chat_id = message.chat.id
    user_id = target.id
    name = mention(target)
    blocks = []
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status == "kicked":
            ban_info = get_last_chat_ban(chat_id, user_id)
            if ban_info:
                reason, banned_by, banned_at, until_date = ban_info
                try:
                    mod = await bot.get_chat(banned_by)
                    mod_name = user_link(banned_by, mod.first_name, mod.username)
                except: mod_name = f"ID {banned_by}"
                blocks.append(f"{em('ban', '🚫')} <b>Забанен</b>\n📝 {reason}\n👮 {mod_name}")
            else:
                blocks.append(f"{em('ban', '🚫')} <b>Забанен</b>\n📝 <i>неизвестна</i>")
    except: pass
    grid_id = get_chat_grid(chat_id)
    if grid_id:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT reason, banned_by FROM grid_bans WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
            r = c.fetchone()
            if r:
                reason, banned_by = r
                try:
                    mod = await bot.get_chat(banned_by)
                    mod_name = user_link(banned_by, mod.first_name, mod.username)
                except: mod_name = f"ID {banned_by}"
                blocks.append(f"{em('ban', '🚫')} <b>Забанен в сетке</b>\n📝 {reason}\n👮 {mod_name}")
    if is_in_antispam(user_id):
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT reason FROM antispam WHERE user_id = ?", (user_id,))
            r = c.fetchone()
            if r: blocks.append(f"{em('shield', '🛡')} <b>В антиспаме MOS</b>\n📝 {r[0]}")
    if not blocks:
        return await message.reply(f"{em('check', '✅')} {name} <b>чист</b>", parse_mode="HTML", disable_web_page_preview=True)
    text = f"{em('calendar', '🗓')} <b>Наказания {name}</b>\n\n" + "\n\n".join(blocks)
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= .БАНЫ =================
@cmd("баны")
async def show_bans(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)

    user_id = target.id
    name = user_link(user_id, target.first_name, target.username)

    bans = get_all_user_bans(user_id)
    total_bans = len(bans)
    spam_bans = count_user_spam_bans(user_id)

    text = f"{em('ban', '🚫')} <b>Баны {name}</b>\n"
    text += f"{em('id', '🆔')} <code>{user_id}</code>\n\n"

    if is_in_antispam(user_id):
        info = get_antispam_info(user_id)
        if info:
            reason, added_by, added_at = info
            date_str = added_at[:10] if added_at else "—"
            if added_by == 0:
                admin_line = "🤖 <i>Автоматическая блокировка</i>"
            else:
                try:
                    admin_chat = await bot.get_chat(added_by)
                    admin_line = user_link(added_by, admin_chat.first_name, admin_chat.username)
                except:
                    admin_line = f"<code>{added_by}</code>"
            text += f"☢️ <b>В АНТИСПАМЕ MOS</b>\n"
            text += f"📝 Причина: {reason}\n"
            text += f"👮 Занёс: {admin_line}\n"
            text += f"{em('calendar', '🗓')} {date_str}\n\n"
        else:
            text += f"☢️ <b>В АНТИСПАМЕ MOS</b>\n\n"
    else:
        last = get_last_antispam_history(user_id)
        if last and last[0] == "remove":
            action, old_reason, admin_id, created_at = last
            if admin_id == 0:
                admin_line = "🤖 <i>Автоматически</i>"
            else:
                try:
                    admin_chat = await bot.get_chat(admin_id)
                    admin_line = user_link(admin_id, admin_chat.first_name, admin_chat.username)
                except:
                    admin_line = f"<code>{admin_id}</code>"
            text += f"{em('check', '✅')} <b>Не в антиспаме</b>\n"
            text += f"📝 <i>Прошлый АС:</i> {old_reason}\n"
            text += f"👮 <i>Вынес:</i> {admin_line}\n"
            text += f"{em('calendar', '🗓')} <i>Дата:</i> {created_at[:10] if created_at else '—'}\n\n"
        else:
            text += f"{em('check', '✅')} <b>Не в антиспаме</b>\n\n"

    text += f"{em('stats', '📊')} <b>Статистика:</b>\n"
    text += f"• Активных банов: <b>{total_bans}</b>\n"
    text += f"• Из них за спам: <b>{spam_bans}</b>\n\n"

    if not bans:
        text += "📭 <i>Активных банов нет</i>"
    else:
        text += f"📋 <b>Список банов:</b>\n\n"
        for i, (chat_id, reason, banned_by, banned_at, until_date) in enumerate(bans, 1):
            date_str = banned_at[:10] if banned_at else "—"
            if until_date:
                try:
                    until_dt = datetime.strptime(until_date[:19], "%Y-%m-%d %H:%M:%S")
                    if until_dt < datetime.now():
                        until_str = "истёк"
                    else:
                        until_str = f"до {until_dt.strftime('%d.%m.%Y')}"
                except:
                    until_str = "—"
            else:
                until_str = "навсегда"

            text += f"<b>{i}.</b> 📝 {reason}\n"
            text += f"   {em('calendar', '🗓')} {date_str} ({until_str})\n\n"

    if not is_in_antispam(user_id) and spam_bans >= 3 and spam_bans < 5:
        text += f"\n⚠️ <i>До авто-блокировки: {5 - spam_bans} банов за спам</i>"

    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= АЧИВКИ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+ачивка создать"))
async def create_achievement_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 3):
        return
    parts = message.text.split(maxsplit=4)
    if len(parts) < 4:
        return await message.reply("📌 <code>+Ачивка создать Название 🏅 Описание</code>", parse_mode="HTML", disable_web_page_preview=True)
    name = parts[2]
    emoji = parts[3]
    description = parts[4] if len(parts) >= 5 else ""
    aid = create_achievement(name, emoji, description)
    if not aid:
        return await message.reply(f"{em('cross', '❌')} Ачивка уже есть.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"✅ Ачивка создана!\n{emoji} <b>{name}</b>\n📝 {description or '—'}", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+ачивка ") and not m.text.lower().strip().startswith("+ачивка создать"))
async def add_achievement_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 2):
        return
    parts = message.text.split("\n", 1)
    first_line = parts[0].strip()
    args = first_line.split()
    target = None
    achievement_name = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        if len(args) >= 2: achievement_name = " ".join(args[1:])
    else:
        if len(args) >= 3:
            try:
                target = await bot.get_chat(args[1])
                achievement_name = " ".join(args[2:])
            except: return await message.reply(f"{em('cross', '❌')} Не найден.", parse_mode="HTML", disable_web_page_preview=True)
    if not target or not achievement_name:
        return await message.reply(f"📌 <code>+Ачивка @user Название</code>", parse_mode="HTML", disable_web_page_preview=True)
    ach = get_achievement_by_name(achievement_name)
    if not ach:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    aid, name, emoji, desc = ach
    ok = give_achievement(target.id, message.chat.id, aid, message.from_user.id)
    if not ok:
        return await message.reply(f"⚠️ У {mention(target)} уже есть.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"🎖 {mention(target)} получил {emoji} <b>{name}</b>!", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-ачивка удалить"))
async def delete_achievement_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 3):
        return
    args = message.text.split()
    if len(args) < 3:
        return await message.reply("📌 <code>-Ачивка удалить Название</code>", parse_mode="HTML", disable_web_page_preview=True)
    name = " ".join(args[2:])
    ach = get_achievement_by_name(name)
    if not ach:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    delete_achievement(ach[0])
    await message.reply(f"🗑 Удалена.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-ачивка ") and not m.text.lower().strip().startswith("-ачивка удалить"))
async def remove_achievement_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 2):
        return
    parts = message.text.split("\n", 1)
    first_line = parts[0].strip()
    args = first_line.split()
    target = None
    achievement_name = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        if len(args) >= 2: achievement_name = " ".join(args[1:])
    else:
        if len(args) >= 3:
            try:
                target = await bot.get_chat(args[1])
                achievement_name = " ".join(args[2:])
            except: return
    if not target or not achievement_name:
        return await message.reply(f"📌 <code>-Ачивка @user Название</code>", parse_mode="HTML", disable_web_page_preview=True)
    ach = get_achievement_by_name(achievement_name)
    if not ach:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    remove_achievement(target.id, message.chat.id, ach[0])
    await message.reply(f"❌ С {mention(target)} снята {ach[2]} <b>{ach[1]}</b>.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("ачивки")
@cmd("все ачивки")
async def list_achievements_cmd(message: types.Message):
    all_ach = get_all_achievements()
    if not all_ach:
        return await message.reply("📭 Нет ачивок.", parse_mode="HTML", disable_web_page_preview=True)
    text = "🎖 <b>Все ачивки:</b>\n\n"
    for aid, name, emoji, desc in all_ach:
        text += f"{emoji} <b>{name}</b>"
        if desc: text += f" — <i>{desc}</i>"
        text += f"\n   <code>ID: {aid}</code>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= КОНФЕТКИ =================
@cmd("пополнить")
async def add_candies_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 3):
        return await message.reply("⛔ Только агенты ранга 3+.", parse_mode="HTML", disable_web_page_preview=True)
    args = message.text.split()
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        amount_arg = args[1] if len(args) >= 2 else None
    else:
        if len(args) < 3:
            return await message.reply("❌ <code>.пополнить @user 10</code>", parse_mode="HTML", disable_web_page_preview=True)
        try:
            if args[1].startswith('@'): target = await bot.get_chat(args[1])
            elif args[1].isdigit(): target = await bot.get_chat(int(args[1]))
        except: return await message.reply("❌ Не найден", parse_mode="HTML", disable_web_page_preview=True)
        amount_arg = args[2]
    if not target:
        return await message.reply("❌ Не удалось определить.", parse_mode="HTML", disable_web_page_preview=True)
    try:
        amount = int(amount_arg)
        if amount <= 0 or amount > 100000:
            return await message.reply("❌ Некорректно.", parse_mode="HTML", disable_web_page_preview=True)
    except: return await message.reply("❌ Некорректно.", parse_mode="HTML", disable_web_page_preview=True)
    add_candies(target.id, amount, message.from_user.id)
    new_balance = get_balance(target.id)
    await message.reply(f"🍬 {mention(target)} +{amount}\n💰 Баланс: <b>{new_balance}</b>", parse_mode="HTML", disable_web_page_preview=True)
    try:
        await bot.send_message(target.id, f"🎁 Вам пополнили мешок на <b>{amount}</b>!\n💰 Баланс: <b>{new_balance}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True)
    except: pass

@cmd("мешок")
async def my_candies_cmd(message: types.Message):
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            try:
                if args[1].startswith('@'): target = await bot.get_chat(args[1])
                elif args[1].isdigit(): target = await bot.get_chat(int(args[1]))
            except: return await message.reply("❌ Не найден", parse_mode="HTML", disable_web_page_preview=True)
        else: target = message.from_user
    balance = get_balance(target.id)
    coins_balance = get_coins(target.id)
    text = (
        f"🎒 <b>Мешок {mention(target)}</b>\n\n"
        f"🍬 Ириски: <b>{balance}</b>\n"
        f"☢️ Mos-коины: <b>{coins_balance}</b> i¢"
    )
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("мешки")
async def top_candies_cmd(message: types.Message):
    top = get_top_candies(limit=10)
    if not top:
        return await message.reply("📭 Пусто.", parse_mode="HTML", disable_web_page_preview=True)
    text = "🏆 <b>Топ мешков:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, balance) in enumerate(top, 1):
        try:
            user = await bot.get_chat(user_id)
            name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{balance}</b> 🍬\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= TELEGRAM STARS =================
@cmd("купитьириски")
@cmd("купить-ириски")
@cmd("buycandies")
async def buy_candies_stars_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        price = get_stars_per_candy(message.chat.id)
        return await message.reply(
            f"🍬 <b>Покупка ирисок за Telegram Stars</b>\n\n"
            f"💰 Курс: <b>{price} ⭐ = 1 🍬</b>\n\n"
            f"📌 <b>Формат:</b>\n"
            f"<code>.купитьириски 10</code> — купить 10 ирисок за {price * 10} ⭐\n"
            f"<code>.купитьириски 50</code> — купить 50 ирисок за {price * 50} ⭐\n"
            f"<code>.купитьириски 100</code> — купить 100 ирисок за {price * 100} ⭐",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    amount = int(args[1])
    if amount < 1 or amount > 10000:
        return await message.reply(f"{em('cross', '❌')} Количество от 1 до 10 000.", parse_mode="HTML", disable_web_page_preview=True)
    price = get_stars_per_candy(message.chat.id)
    total_stars = amount * price
    payment_id = create_stars_payment(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        amount_candies=amount,
        stars=total_stars
    )
    try:
        await bot.send_invoice(
            chat_id=message.chat.id,
            title=f"🍬 {amount} ирисок",
            description=f"Покупка {amount} ирисок за {total_stars} ⭐ Telegram Stars",
            payload=f"candies_{payment_id}",
            provider_token="",
            currency="XTR",
            prices=[types.LabeledPrice(label=f"{amount} ирисок", amount=total_stars)],
            start_parameter=f"buy_candies_{payment_id}"
        )
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)

@cmd("курс")
async def change_stars_price_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    is_private = message.chat.type == "private"
    args = message.text.split()

    if len(args) < 2:
        price = get_global_stars_per_candy() if is_private else get_stars_per_candy(message.chat.id)
        scope = "🌐 глобальный" if is_private else f"📍 чат <code>{message.chat.id}</code>"
        return await message.reply(
            f"💰 <b>Текущий курс ({scope}):</b> {price} ⭐ = 1 🍬\n\n"
            f"📌 <code>.курс 15</code> — изменить\n\n"
            f"<i>В ЛС меняется глобальный курс.</i>\n"
            f"<i>В группе — только для этой группы.</i>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if not args[1].isdigit():
        return await message.reply(f"{em('cross', '❌')} Введите число.", parse_mode="HTML", disable_web_page_preview=True)

    new_price = int(args[1])
    if new_price < 1 or new_price > 1000:
        return await message.reply(f"{em('cross', '❌')} Курс от 1 до 1000.", parse_mode="HTML", disable_web_page_preview=True)

    if is_private:
        set_global_stars_per_candy(new_price)
        await message.reply(f"{em('check', '✅')} <b>Глобальный курс:</b> {new_price} ⭐ = 1 🍬", parse_mode="HTML", disable_web_page_preview=True)
    else:
        set_stars_per_candy(message.chat.id, new_price)
        await message.reply(f"{em('check', '✅')} Курс для этого чата: <b>{new_price} ⭐ = 1 🍬</b>", parse_mode="HTML", disable_web_page_preview=True)

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    try:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except Exception as e:
        print(f"Ошибка pre_checkout: {e}")
        try:
            await bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Ошибка обработки платежа"
            )
        except:
            pass

@dp.message(lambda m: m.successful_payment is not None)
async def successful_payment_handler(message: types.Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    try:
        payment_id = int(payload.split("_")[1])
    except:
        return await message.reply(f"{em('cross', '❌')} Ошибка идентификации платежа.", parse_mode="HTML", disable_web_page_preview=True)
    result = complete_stars_payment(payment_id)
    if not result:
        return await message.reply("⚠️ Этот платёж уже был обработан.", parse_mode="HTML", disable_web_page_preview=True)
    user_id, chat_id, amount_candies, stars_paid = result
    await message.reply(
        f"{em('check', '✅')} <b>Покупка успешна!</b>\n\n"
        f"🍬 Получено ирисок: <b>+{amount_candies}</b>\n"
        f"💰 Оплачено: <b>{stars_paid} ⭐</b>\n"
        f"💼 Баланс: <b>{get_balance(user_id)} 🍬</b>\n\n"
        f"Спасибо за покупку! 🎉",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    try:
        await bot.send_message(
            OWNER_ID,
            f"💎 <b>Новая покупка ирисок!</b>\n\n"
            f"👤 {user_link(user_id, 'Покупатель')} (<code>{user_id}</code>)\n"
            f"🍬 {amount_candies} ирисок\n"
            f"⭐ {stars_paid} звёзд\n"
            f"📍 Чат: <code>{chat_id}</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except:
        pass

# ================= КОИНЫ =================
@cmd("коины")
@cmd("баланс")
async def coins_balance_cmd(message: types.Message):
    user_id = message.from_user.id
    apply_tax(user_id)
    info = get_coins_info(user_id)
    balance, last_farm, total_farmed, last_tax = info
    text = (
        f"☢️ <b>Mos-коины</b>\n\n"
        f"💰 Баланс: <b>{balance}</b> i¢\n"
        f"📈 Всего добыто: <b>{total_farmed}</b> i¢\n"
    )
    if last_farm:
        try:
            last_farm_dt = datetime.strptime(last_farm[:19], "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - last_farm_dt
            hours = delta.total_seconds() / 3600
            if hours < 4:
                minutes_left = int((4 - hours) * 60)
                text += f"\n⛏ Ферма через: <b>{minutes_left} мин.</b>"
            else:
                reward, _ = get_farm_reward(user_id)
                text += f"\n⛏ Ферма готова! Награда: <b>{reward} i¢</b>"
        except: text += f"\n⛏ Ферма готова!"
    else:
        text += f"\n⛏ Ферма доступна! <code>Ферма</code>"
    text += f"\n\n💱 <code>Купить коины 10</code> (1 🍬 = 100 i¢)"
    text += f"\n💸 <code>Бкоин 100</code>"
    text += f"\n📊 Налог: 1% раз в 2 дня"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("ферма")
async def farm_cmd(message: types.Message):
    user_id = message.from_user.id
    apply_tax(user_id)
    reward, wait_minutes = get_farm_reward(user_id)
    if reward == 0:
        return await message.reply(f"⏳ Ферма не готова. Ещё <b>{wait_minutes} мин.</b>", parse_mode="HTML", disable_web_page_preview=True)
    info = get_coins_info(user_id)
    total_farmed = (info[2] or 0) + reward
    add_coins(user_id, reward, "ферма")
    update_farm_time(user_id, total_farmed)
    await message.reply(f"⛏ <b>Урожай собран!</b>\n💰 +{reward} i¢\n📈 Всего: <b>{total_farmed} i¢</b>", parse_mode="HTML", disable_web_page_preview=True)

@cmd("купить коины")
async def buy_coins_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 3 or not args[-1].isdigit():
        return await message.reply("📌 <code>Купить коины 10</code> → 1000 i¢", parse_mode="HTML", disable_web_page_preview=True)
    candies_amount = int(args[-1])
    if candies_amount <= 0:
        return await message.reply(f"{em('cross', '❌')} Больше нуля.", parse_mode="HTML", disable_web_page_preview=True)
    user_id = message.from_user.id
    balance = get_balance(user_id)
    if balance < candies_amount:
        return await message.reply(f"{em('cross', '❌')} Недостаточно ирисок. Нужно: <b>{candies_amount}</b>, у вас: <b>{balance}</b>", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (candies_amount, user_id))
        conn.commit()
    coins_amount = candies_amount * 100
    add_coins(user_id, coins_amount, f"обмен {candies_amount} 🍬")
    new_balance = get_coins(user_id)
    await message.reply(f"💱 Обмен выполнен!\n💸 Списано: <b>{candies_amount}</b> 🍬\n💰 Получено: <b>+{coins_amount}</b> i¢\n📊 Баланс: <b>{new_balance}</b> i¢", parse_mode="HTML", disable_web_page_preview=True)

@cmd("бкоин")
async def bkoin_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[-1].isdigit():
        return await message.reply("📌 <code>Бкоин {число}</code>", parse_mode="HTML", disable_web_page_preview=True)
    amount = int(args[-1])
    if amount < 1:
        return await message.reply(f"{em('cross', '❌')} Больше нуля.", parse_mode="HTML", disable_web_page_preview=True)
    user_id = message.from_user.id
    balance = get_coins(user_id)
    if balance < amount:
        return await message.reply(f"{em('cross', '❌')} Недостаточно коинов. Нужно: <b>{amount}</b>, у вас: <b>{balance}</b>", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE coins SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        c.execute("INSERT INTO coin_log (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, -amount, "взнос в счёт чата"))
        conn.commit()
    add_chat_coins(message.chat.id, amount)
    total = get_chat_coins(message.chat.id)
    text = f"💸 Взнос: <b>{amount}</b> i¢\n🏦 Счёт чата: <b>{total}</b> i¢"
    if total >= 35000:
        text += f"\n\n{em('check', '✅')} <b>Можно добавить в каталог!</b>\n<code>Каталог добавить</code>"
    else:
        text += f"\n\n📊 До каталога: <b>{35000 - total}</b> i¢"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("коинытоп")
async def coins_top_cmd(message: types.Message):
    top = get_coins_top(limit=10)
    if not top:
        return await message.reply("📭 Пусто.", parse_mode="HTML", disable_web_page_preview=True)
    text = "☢️ <b>Топ коинов:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, balance) in enumerate(top, 1):
        try:
            user = await bot.get_chat(user_id)
            name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{balance}</b> i¢\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= АНТИСПАМ =================
@dp.message(lambda m: m.text and m.text.lower().strip() == "+антиспам")
async def enable_antispam_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True)
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Только агенты.", parse_mode="HTML", disable_web_page_preview=True)
    if is_antispam_enabled(message.chat.id):
        return await message.reply(f"ℹ️ Антиспам уже <b>включён</b> в этом чате.", parse_mode="HTML", disable_web_page_preview=True)
    set_antispam_enabled(message.chat.id, True)
    await message.reply(f"{em('check', '✅')} <b>Антиспам включён</b>!\n\n{em('ban', '🚫')} Юзеры из базы будут баниться при входе.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-антиспам")
async def disable_antispam_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True)
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Только агенты.", parse_mode="HTML", disable_web_page_preview=True)
    if not is_antispam_enabled(message.chat.id):
        return await message.reply("ℹ️ Антиспам уже <b>выключен</b>.", parse_mode="HTML", disable_web_page_preview=True)
    set_antispam_enabled(message.chat.id, False)
    await message.reply(f"{em('check', '✅')} <b>Антиспам выключен</b>.\n\n{em('check', '✅')} Юзеры из базы <b>будут впускаться</b>.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("антиспам")
async def antispam_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    enabled = is_antispam_enabled(message.chat.id)
    status = "🟢 <b>включён</b>" if enabled else "🔴 <b>выключен</b>"
    await message.reply(
        f"{em('shield', '🛡')} <b>Антиспам в этом чате:</b> {status}\n\n"
        f"Управление:\n"
        f"• <code>+антиспам</code> — включить\n"
        f"• <code>-антиспам</code> — выключить",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+ак") and not m.text.lower().strip().startswith("+аки"))
async def add_antispam_kick(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1: reason = parts[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target.id, reason, message.from_user.id))
        conn.commit()
    log_antispam_action(target.id, "add", reason, message.from_user.id)
    success, failed, total = await kick_in_all_antispam_chats(target.id)
    await message.reply(
        f"{em('check', '✅')} {mention(target)} в «Антиспам»\n"
        f"👢 Кикнут в <b>{success}</b> из <b>{total}</b> чатов" + (f" (ошибок: {failed})" if failed else "") + "\n"
        f"📝 {reason}",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+аки"))
async def add_antispam_kick_ignore(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1: reason = parts[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target.id, reason, message.from_user.id))
        c.execute("INSERT OR REPLACE INTO ignore_list (user_id, chat_id, reason, added_by) VALUES (?, ?, ?, ?)", (target.id, message.chat.id, reason, message.from_user.id))
        conn.commit()
    log_antispam_action(target.id, "add", reason, message.from_user.id)
    success, failed, total = await kick_in_all_antispam_chats(target.id)
    await message.reply(
        f"{em('check', '✅')} {mention(target)} в «Антиспам» + игнор\n"
        f"👢 Кикнут в <b>{success}</b> из <b>{total}</b> чатов" + (f" (ошибок: {failed})" if failed else "") + "\n"
        f"📝 {reason}",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+аигн"))
async def add_antispam_ignore(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1: reason = parts[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target.id, reason, message.from_user.id))
        c.execute("INSERT OR REPLACE INTO ignore_list (user_id, chat_id, reason, added_by) VALUES (?, ?, ?, ?)", (target.id, message.chat.id, reason, message.from_user.id))
        conn.commit()
    log_antispam_action(target.id, "add", reason, message.from_user.id)
    await message.reply(f"{em('check', '✅')} {mention(target)} в «Антиспам»\n{em('mute', '🔇')} Игнор\n📝 {reason}", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+ас") and not m.text.lower().strip().startswith("+ачивка"))
async def add_antispam(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1: reason = parts[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target.id, reason, message.from_user.id))
        conn.commit()
    log_antispam_action(target.id, "add", reason, message.from_user.id)
    await message.reply(f"{em('check', '✅')} {mention(target)} в «Антиспам»\n📝 {reason}", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-ас"))
async def remove_antispam(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Только агенты.", parse_mode="HTML", disable_web_page_preview=True)

    args = message.text.split()
    is_error_mode = len(args) >= 2 and args[1].lower() == "ошибка"

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)

    if not is_in_antispam(target.id):
        return await message.reply("⚠️ Не в антиспаме.", parse_mode="HTML", disable_web_page_preview=True)

    info = get_antispam_info(target.id)
    old_reason = info[0] if info else "неизвестно"

    if is_error_mode:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM antispam WHERE user_id = ?", (target.id,))
            c.execute("DELETE FROM ignore_list WHERE user_id = ?", (target.id,))
            conn.commit()

        cancelled_reason = cancel_last_antispam_add(target.id)

        msg = f"{em('check', '✅')} {mention(target)} вынесен из АС <b>(ошибочно)</b>\n"
        msg += f"📝 Была причина: {old_reason}\n"
        if cancelled_reason:
            msg += f"🗑 Запись удалена из истории"
        else:
            msg += f"⚠️ Запись в истории не найдена"
        msg += f"\n👮 Отменил: {mention(message.from_user)}"

        await message.reply(msg, parse_mode="HTML", disable_web_page_preview=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, вынести", callback_data=f"rm_as_confirm:{target.id}:{message.from_user.id}:{message.chat.id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"rm_as_cancel:{target.id}:{message.from_user.id}")
    ]])

    await message.reply(
        f"❓ <b>Вы уверены?</b>\n\n"
        f"👤 {mention(target)}\n"
        f"📝 Текущая причина АС: {old_reason}\n\n"
        f"<i>После выноса юзер будет впускаться во все чаты.</i>\n\n"
        f"💡 <i>Ошиблись? — <code>-ас ошибка @user</code></i>",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("rm_as_confirm:"))
async def rm_as_confirm_handler(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    target_id = int(parts[1])
    admin_id = int(parts[2])
    chat_id = int(parts[3])

    if callback.from_user.id != admin_id:
        return await callback.answer("⛔ Не ты вызывал", show_alert=True)

    if admin_id != OWNER_ID and not has_agent_rank(admin_id, 1):
        return await callback.answer("⛔ Нет прав", show_alert=True)

    if not is_in_antispam(target_id):
        await callback.message.edit_text("⚠️ Юзер уже не в антиспаме.")
        return await callback.answer()

    info = get_antispam_info(target_id)
    old_reason = info[0] if info else "неизвестно"

    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM antispam WHERE user_id = ?", (target_id,))
        c.execute("DELETE FROM ignore_list WHERE user_id = ?", (target_id,))
        conn.commit()

    log_antispam_action(target_id, "remove", old_reason, admin_id)

    try:
        target_chat = await bot.get_chat(target_id)
        target_name = target_chat.first_name or "Юзер"
        target_username = target_chat.username
    except:
        target_name = "Юзер"
        target_username = None

    if target_username:
        user_display = f"<a href='https://t.me/{target_username}'>{target_name}</a>"
    else:
        user_display = f"<b>{target_name}</b>"

    try:
        await callback.message.edit_text(
            f"{em('check', '✅')} {user_display} вынесен из АС\n"
            f"📝 <b>Была причина:</b> {old_reason}\n"
            f"👮 Вынес: {callback.from_user.first_name}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except: pass
    await callback.answer(f"{em('check', '✅')} Вынесен")

@dp.callback_query(lambda c: c.data and c.data.startswith("rm_as_cancel:"))
async def rm_as_cancel_handler(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    admin_id = int(parts[2])
    if callback.from_user.id != admin_id:
        return await callback.answer("⛔ Не ты вызывал", show_alert=True)

    try:
        await callback.message.edit_text(f"{em('cross', '❌')} Отменено. Юзер остался в АС.", parse_mode="HTML", disable_web_page_preview=True)
    except:
        pass
    await callback.answer(f"{em('cross', '❌')} Отменено")

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-аигн"))
async def remove_ignore(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    if not is_ignored(message.chat.id, target.id):
        return await message.reply("⚠️ Не в игноре.", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM ignore_list WHERE user_id = ? AND chat_id = ?", (target.id, message.chat.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} убран из игнора", parse_mode="HTML", disable_web_page_preview=True)

# ================= ПРАВИЛА =================
@cmd("правила")
async def rules_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        rules = get_chat_rules(message.chat.id)
        if not rules:
            return await message.reply("📭 Правила не установлены.", parse_mode="HTML", disable_web_page_preview=True)
        return await message.reply(f"📜 <b>Правила чата:</b>\n\n{rules}", parse_mode="HTML", disable_web_page_preview=True)
    sub = args[1].strip().lower()
    if sub.startswith("установить"):
        if not has_permission(message.chat.id, message.from_user.id, 3):
            return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
        parts = message.text.split("\n", 1)
        if len(parts) < 2:
            return await message.reply("📌 <code>.правила установить</code> (текст на новой строке)", parse_mode="HTML", disable_web_page_preview=True)
        text = parts[1].strip()[:3500]
        text = auto_premium(text)
        set_chat_rules(message.chat.id, text, message.from_user.id)
        return await message.reply(f"{em('check', '✅')} Правила установлены!", parse_mode="HTML", disable_web_page_preview=True)
    if sub in ["сброс", "удалить"]:
        if not has_permission(message.chat.id, message.from_user.id, 3):
            return
        reset_chat_rules(message.chat.id)
        return await message.reply(f"{em('check', '✅')} Сброшено.", parse_mode="HTML", disable_web_page_preview=True)
    if sub in ["закрепить", "пин"]:
        if not has_permission(message.chat.id, message.from_user.id, 3):
            return
        rules = get_chat_rules(message.chat.id)
        if not rules: return await message.reply("📭 Пусто.", parse_mode="HTML", disable_web_page_preview=True)
        try:
            msg = await message.reply(f"📜 <b>Правила:</b>\n\n{rules}", parse_mode="HTML", disable_web_page_preview=True)
            await bot.pin_chat_message(message.chat.id, msg.message_id, disable_notification=True)
        except Exception as e:
            return await message.reply(f"{em('cross', '❌')} {e}", parse_mode="HTML", disable_web_page_preview=True)
        return
    rules = get_chat_rules(message.chat.id)
    if rules:
        await message.reply(f"📜 <b>Правила:</b>\n\n{rules}", parse_mode="HTML", disable_web_page_preview=True)

# ================= ФИЛЬТР ССЫЛОК =================
@cmd("фильтрссылок")
async def link_filter_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True)
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен ранг Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True)

    args = message.text.split(maxsplit=1)
    sub = args[1].strip().lower() if len(args) >= 2 else ""

    if not sub:
        enabled = is_link_filter_enabled(message.chat.id)
        status = "🟢 <b>включён</b>" if enabled else "🔴 <b>выключен</b>"
        return await message.reply(
            f"🔗 <b>Фильтр ссылок:</b> {status}\n\n"
            f"<b>Команды:</b>\n"
            f"• <code>.фильтрссылок вкл</code>\n"
            f"• <code>.фильтрссылок выкл</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if sub in ["вкл", "on", "включить", "+"]:
        set_link_filter(message.chat.id, True)
        return await message.reply(
            f"{em('check', '✅')} <b>Фильтр ссылок включён</b>\n\n"
            f"🔗 Все ссылки будут <b>удаляться</b>\n"
            f"{em('ban', '🚫')} Отправители — <b>баниться</b>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if sub in ["выкл", "off", "выключить", "-"]:
        set_link_filter(message.chat.id, False)
        return await message.reply(f"{em('check', '✅')} <b>Фильтр ссылок выключен</b>\n\n🔗 Ссылки снова <b>разрешены</b>", parse_mode="HTML", disable_web_page_preview=True)

    await message.reply(
        "📌 <b>Команды:</b>\n"
        "• <code>.фильтрссылок вкл</code>\n"
        "• <code>.фильтрссылок выкл</code>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ================= ПРИВЕТСТВИЕ =================
@cmd("приветствие")
async def greeting_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True)
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен ранг Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True)
    args = message.text.split(maxsplit=1)
    sub = args[1].strip().lower() if len(args) >= 2 else ""
    if not sub:
        current = get_greeting(message.chat.id)
        if not current:
            return await message.reply(
                "📭 Приветствие <b>не установлено</b>.\n\n"
                "📌 <b>Как установить:</b>\n"
                "<code>.приветствие установить\n"
                "Привет, {name}! Добро пожаловать в {chat} 🎉\n"
                "Правила: {rules}</code>\n\n"
                "🔤 <b>Плейсхолдеры:</b> <code>{name}</code>, <code>{chat}</code>, <code>{rules}</code>, <code>{link}</code>",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        return await message.reply(f"📜 <b>Текущее приветствие:</b>\n\n<code>{current}</code>", parse_mode="HTML", disable_web_page_preview=True)
    if sub.startswith("установить"):
        parts = message.text.split("\n", 1)
        if len(parts) < 2:
            return await message.reply("📌 <b>Формат:</b>\n<code>.приветствие установить\nПривет, {name}!</code>", parse_mode="HTML", disable_web_page_preview=True)
        text = parts[1].strip()
        if not text:
            return await message.reply(f"{em('cross', '❌')} Текст пустой.", parse_mode="HTML", disable_web_page_preview=True)
        if len(text) > 1000:
            return await message.reply(f"{em('cross', '❌')} Максимум 1000 символов.", parse_mode="HTML", disable_web_page_preview=True)
        text = auto_premium(text)
        set_greeting(message.chat.id, text, message.from_user.id)
        return await message.reply(
            f"{em('check', '✅')} <b>Приветствие установлено!</b>\n\n"
            f"📝 <i>Проверка:</i>\n{format_greeting(text, message.from_user, message.chat)}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    if sub in ["сброс", "удалить"]:
        current = get_greeting(message.chat.id)
        if not current:
            return await message.reply("📭 И так пусто.", parse_mode="HTML", disable_web_page_preview=True)
        reset_greeting(message.chat.id)
        return await message.reply(f"{em('check', '✅')} Приветствие сброшено.", parse_mode="HTML", disable_web_page_preview=True)
    if sub in ["пример", "тест"]:
        current = get_greeting(message.chat.id)
        if not current:
            return await message.reply("📭 Приветствие не установлено.", parse_mode="HTML", disable_web_page_preview=True)
        preview = format_greeting(current, message.from_user, message.chat)
        return await message.reply(f"👁 <b>Предпросмотр:</b>\n\n{preview}", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(
        "📌 <b>Команды:</b>\n"
        "• <code>.приветствие</code>\n"
        "• <code>.приветствие установить</code>\n"
        "• <code>.приветствие пример</code>\n"
        "• <code>.приветствие сброс</code>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ================= ЗАЯВКИ =================
@cmd("заявки")
async def requests_settings_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True)
    if not has_permission(message.chat.id, message.from_user.id, 4):
        return await message.reply(f"{em('cross', '❌')} Нужен ранг Ст. Админ (4).", parse_mode="HTML", disable_web_page_preview=True)

    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO chat_settings (chat_id, auto_requests) VALUES (?, 0)", (message.chat.id,))
        conn.commit()

    args = message.text.split(maxsplit=1)
    sub = args[1].strip().lower() if len(args) >= 2 else ""

    if not sub:
        auto = is_auto_requests_enabled(message.chat.id)
        status = "🟢 <b>включено</b>" if auto else "🔴 <b>выключено</b>"
        return await message.reply(
            f"📥 <b>Заявки на вступление</b>\n\n"
            f"Текущий режим: {status}\n\n"
            f"<b>Команды:</b>\n"
            f"• <code>.заявки вкл</code>\n"
            f"• <code>.заявки выкл</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if sub in ["вкл", "on", "авто", "auto"]:
        update_chat_setting(message.chat.id, "auto_requests", 1)
        return await message.reply(
            f"{em('check', '✅')} <b>Обработка заявок включена!</b>\n\n"
            f"🤖 Бот сам одобряет и отклоняет\n"
            f"⚠️ Антиспам работает всегда",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if sub in ["выкл", "off", "стоп"]:
        update_chat_setting(message.chat.id, "auto_requests", 0)
        return await message.reply(
            f"{em('check', '✅')} <b>Обработка заявок выключена.</b>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    await message.reply(
        "📌 <b>Команды:</b>\n"
        "• <code>.заявки вкл</code>\n"
        "• <code>.заявки выкл</code>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )# ================= ГРАЖДАНСТВО =================
@dp.message(lambda m: m.text and m.text.lower().strip() == "+гражданство")
async def become_citizen_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_id = message.from_user.id
    chat_id = message.chat.id
    current = get_citizenship_info(user_id)
    if current:
        if current[0] == chat_id:
            return await message.reply("ℹ️ Вы уже гражданин этого чата.", parse_mode="HTML", disable_web_page_preview=True)
        try:
            old_chat = await bot.get_chat(current[0])
            old_title = old_chat.title or f"Чат {current[0]}"
        except: old_title = f"Чат {current[0]}"
        return await message.reply(f"⚠️ Вы уже гражданин чата «{old_title}».\n\nСначала: <code>-гражданство</code>", parse_mode="HTML", disable_web_page_preview=True)
    set_citizenship(user_id, chat_id)
    chat_title = message.chat.title or "чат"
    await message.reply(f"🏠 <b>Поздравляем!</b>\n{mention(message.from_user)} стал гражданином <b>«{chat_title}»</b>.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("гражданство")
async def citizenship_info_cmd(message: types.Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    info = get_citizenship_info(target.id)
    if not info:
        return await message.reply(f"ℹ️ {mention(target)} не гражданин.", parse_mode="HTML", disable_web_page_preview=True)
    chat_id, became_at = info
    try:
        chat = await bot.get_chat(chat_id)
        title = chat.title or f"Чат {chat_id}"
    except: title = f"Чат {chat_id}"
    duration = format_citizenship_duration(became_at)
    await message.reply(f"🏠 <b>Гражданство</b>\n\n👤 {mention(target)}\n🏠 {title}\n📅 {became_at[:10]}\n⏳ {duration}", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-гражданство")
async def leave_citizenship_cmd(message: types.Message):
    info = get_citizenship_info(message.from_user.id)
    if not info:
        return await message.reply("ℹ️ Вы не гражданин.", parse_mode="HTML", disable_web_page_preview=True)
    chat_id, _ = info
    remove_citizenship(message.from_user.id)
    if chat_id == message.chat.id:
        await message.reply("👋 Вы больше не гражданин.", parse_mode="HTML", disable_web_page_preview=True)
    else:
        try:
            old = await bot.get_chat(chat_id)
            await message.reply(f"👋 Вы больше не гражданин чата «{old.title or ''}».", parse_mode="HTML", disable_web_page_preview=True)
        except: pass

@cmd("кто гражданин")
async def citizens_list_cmd(message: types.Message):
    citizens = get_chat_citizens(message.chat.id)
    if not citizens:
        return await message.reply("📭 Нет граждан.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"🏠 <b>Граждане</b> ({len(citizens)}):\n\n"
    for i, (user_id, became_at) in enumerate(citizens, 1):
        try:
            user = await bot.get_chat(user_id)
            name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        text += f"{i}. {name} — <i>{format_citizenship_duration(became_at)}</i>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= НИК =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+ник"))
async def set_nick_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("📌 <code>+Ник ваш текст</code>", parse_mode="HTML", disable_web_page_preview=True)
    set_user_nick(message.from_user.id, message.chat.id, args[1].strip()[:50])
    await message.reply(f"✅ Ник установлен: <b>{args[1].strip()[:50]}</b>", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-ник")
async def remove_nick_cmd(message: types.Message):
    remove_user_nick(message.from_user.id, message.chat.id)
    await message.reply("✅ Ник удалён.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("ник")
async def show_my_nick_cmd(message: types.Message):
    nick = get_user_nick(message.from_user.id, message.chat.id)
    if not nick:
        return await message.reply("📭 Нет ника.\n\n📌 <code>+Ник ВашеИмя</code>", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"🔤 Ваш ник: <b>{nick}</b>", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("ник ") and not m.text.lower().strip() == "ник")
async def show_user_nick_cmd(message: types.Message):
    target, _ = await resolve_target(message)
    if not target: return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True)
    nick = get_user_nick(target.id, message.chat.id)
    if not nick: return await message.reply("📭 Нет ника.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"🔤 Ник {mention(target)}: <b>{nick}</b>", parse_mode="HTML", disable_web_page_preview=True)

# ================= О СЕБЕ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+о себе"))
async def set_about_cmd(message: types.Message):
    parts = message.text.split("\n", 1)
    if len(parts) < 2:
        return await message.reply("📌 <code>+О себе</code> (текст на новой строке)", parse_mode="HTML", disable_web_page_preview=True)
    set_user_about(message.from_user.id, auto_premium(parts[1].strip()[:500]))
    await message.reply("✅ Описание сохранено.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-о себе")
async def remove_about_cmd(message: types.Message):
    remove_user_about(message.from_user.id)
    await message.reply("✅ Описание удалено.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("о себе")
async def show_my_about_cmd(message: types.Message):
    text = get_user_about(message.from_user.id)
    if not text: return await message.reply("📭 Нет описания.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"✏️ <b>О себе:</b>\n\n{text}", parse_mode="HTML", disable_web_page_preview=True)

# ================= ЗВАНИЕ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+звание"))
async def set_rank_text_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("📌 <code>+Звание текст</code>", parse_mode="HTML", disable_web_page_preview=True)
    set_user_rank_text(message.from_user.id, message.chat.id, args[1].strip()[:50])
    await message.reply(f"✅ Звание: <b>{args[1].strip()[:50]}</b>", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-звание")
async def remove_rank_text_cmd(message: types.Message):
    remove_user_rank_text(message.from_user.id, message.chat.id)
    await message.reply("✅ Звание удалено.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("звание")
async def show_my_rank_text_cmd(message: types.Message):
    rank_text = get_user_rank_text(message.from_user.id, message.chat.id)
    if not rank_text: return await message.reply("📭 Нет звания.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"📌 Ваше звание: <b>{rank_text}</b>", parse_mode="HTML", disable_web_page_preview=True)

# ================= АНКЕТА =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("мой пол"))
async def set_gender_cmd(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("📌 <code>Мой пол м/ж/др</code>", parse_mode="HTML", disable_web_page_preview=True)
    v = args[2].strip().lower()
    if v in ["м", "муж", "мужской"]: v = "Мужской"
    elif v in ["ж", "жен", "женский"]: v = "Женский"
    else: v = "Другой"
    update_user_profile(message.from_user.id, "gender", v)
    await message.reply(f"✅ Пол: <b>{v}</b>", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-мой пол")
async def remove_gender_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "gender", None)
    await message.reply("✅ Пол удалён.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("!мой город"))
async def set_city_cmd(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("📌 <code>!Мой город Москва</code>", parse_mode="HTML", disable_web_page_preview=True)
    update_user_profile(message.from_user.id, "city", args[2].strip()[:50])
    await message.reply(f"✅ Город: <b>{args[2].strip()[:50]}</b>", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-мой город")
async def remove_city_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "city", None)
    await message.reply("✅ Город удалён.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("мой др"))
async def set_birth_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        return await message.reply("📌 <code>Мой др 15.05.2000 [всё/месяц/год]</code>", parse_mode="HTML", disable_web_page_preview=True)
    date = args[2].strip()
    vis = args[3].lower() if len(args) >= 4 else "месяц"
    update_user_profile(message.from_user.id, "birth_date", date)
    update_user_profile(message.from_user.id, "birth_visibility", vis)
    await message.reply(f"✅ ДР: <b>{date}</b>", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-мой др")
async def remove_birth_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "birth_date", None)
    await message.reply("✅ ДР удалён.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() in ["+анкета", "+ анкета"])
async def show_profile_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "is_hidden", 0)
    await message.reply("✅ Анкета открыта.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() in ["-анкета", "- анкета"])
async def hide_profile_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "is_hidden", 1)
    await message.reply("✅ Анкета скрыта.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "+видимость гражданства")
async def show_citizenship_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "show_citizenship", 1)
    await message.reply("✅ Гражданство будет отображаться.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-видимость гражданства")
async def hide_citizenship_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "show_citizenship", 0)
    await message.reply("✅ Гражданство скрыто.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+девиз"))
async def set_motto_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("📌 <code>+Девиз ваш текст</code>", parse_mode="HTML", disable_web_page_preview=True)
    update_user_profile(message.from_user.id, "motto", args[1].strip()[:100])
    await message.reply("✅ Девиз установлен.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-девиз")
async def remove_motto_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "motto", None)
    await message.reply("✅ Девиз удалён.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("девиз")
async def show_motto_cmd(message: types.Message):
    profile = get_user_profile(message.from_user.id)
    motto = profile[6] if len(profile) > 6 else None
    if not motto: return await message.reply("📭 Нет девиза.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"💭 Ваш девиз: <i>{motto}</i>", parse_mode="HTML", disable_web_page_preview=True)

# ================= БРАКИ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("брак ") and "@" in m.text)
async def marriage_proposal_cmd(message: types.Message):
    target, _ = await resolve_target(message)
    if not target: return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True)
    if target.id == message.from_user.id: return
    if get_marriage(message.chat.id, message.from_user.id): return await message.reply(f"{em('cross', '❌')} Вы в браке.", parse_mode="HTML", disable_web_page_preview=True)
    if get_marriage(message.chat.id, target.id): return await message.reply(f"{em('cross', '❌')} {mention(target)} в браке.", parse_mode="HTML", disable_web_page_preview=True)
    div = get_divorced_marriage(message.chat.id, message.from_user.id)
    if div:
        restore_marriage(div[0])
        return await message.reply("💞 <b>Брак восстановлен!</b>", parse_mode="HTML", disable_web_page_preview=True)
    add_proposal(message.chat.id, message.from_user.id, target.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept:{message.from_user.id}:{target.id}:{message.chat.id}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"marry_reject:{message.from_user.id}:{target.id}:{message.chat.id}")
    ]])
    await message.reply(f"💍 <b>Предложение!</b>\n\n{mention(message.from_user)} → {mention(target)}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("брак ") and "@" not in m.text and not m.text.lower().startswith("брак цена") and not m.text.lower().startswith("брак продлить") and not m.text.lower().startswith("брак режим"))
async def marriage_proposal_reply(message: types.Message):
    if not message.reply_to_message: return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id: return
    if get_marriage(message.chat.id, message.from_user.id): return await message.reply(f"{em('cross', '❌')} Вы в браке.", parse_mode="HTML", disable_web_page_preview=True)
    if get_marriage(message.chat.id, target.id): return await message.reply(f"{em('cross', '❌')} {mention(target)} в браке.", parse_mode="HTML", disable_web_page_preview=True)
    div = get_divorced_marriage(message.chat.id, message.from_user.id)
    if div:
        restore_marriage(div[0])
        return await message.reply("💞 <b>Брак восстановлен!</b>", parse_mode="HTML", disable_web_page_preview=True)
    add_proposal(message.chat.id, message.from_user.id, target.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept:{message.from_user.id}:{target.id}:{message.chat.id}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"marry_reject:{message.from_user.id}:{target.id}:{message.chat.id}")
    ]])
    await message.reply("💍 <b>Предложение!</b>", parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb)

@dp.callback_query(lambda c: c.data and (c.data.startswith("marry_accept:") or c.data.startswith("marry_reject:")))
async def marriage_response(callback: types.CallbackQuery):
    action, from_id_str, to_id_str, chat_id_str = callback.data.split(":")
    from_id = int(from_id_str)
    to_id = int(to_id_str)
    chat_id = int(chat_id_str)
    if callback.from_user.id != to_id:
        return await callback.answer("⛔ Не тебе!", show_alert=True)
    if get_proposal(chat_id, from_id, to_id) is None:
        return await callback.answer("⚠️ Неактивно.", show_alert=True)
    try:
        fu = await bot.get_chat(from_id)
        tu = await bot.get_chat(to_id)
    except: return await callback.answer(f"{em('cross', '❌')} Ошибка.", show_alert=True)
    if action == "marry_accept":
        res = create_marriage(chat_id, from_id, fu.first_name, to_id, tu.first_name)
        if not res: return await callback.answer(f"{em('cross', '❌')} Кто-то в браке.", show_alert=True)
        remove_proposal(chat_id, from_id, to_id)
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except: pass
        await bot.send_message(chat_id, f"💍💐 <b>Свадьба!</b>\n\n{mention_by_id(from_id, fu.first_name, fu.username)} и {mention_by_id(to_id, tu.first_name, tu.username)} теперь в браке!", parse_mode="HTML", disable_web_page_preview=True)
        await callback.answer("💍 Вы в браке!")
    else:
        remove_proposal(chat_id, from_id, to_id)
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except: pass
        await bot.send_message(chat_id, f"💔 {mention_by_id(to_id, tu.first_name, tu.username)} отказал(а).", parse_mode="HTML", disable_web_page_preview=True)
        await callback.answer(f"{em('cross', '❌')} Отказано.")

@cmd("развод")
async def divorce_cmd(message: types.Message):
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar: return await message.reply(f"{em('cross', '❌')} Вы не в браке.", parse_mode="HTML", disable_web_page_preview=True)
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra = mar
    partner_id = u2_id if u1_id == message.from_user.id else u1_id
    partner_name = u2_name if u1_id == message.from_user.id else u1_name
    duration = format_marriage_duration(married_at, extra or 0)
    divorce_marriage(message.chat.id, message.from_user.id)
    await message.reply(f"💔 {mention(message.from_user)} и {mention_by_id(partner_id, partner_name)} развелись.\n📅 Длился: <b>{duration}</b>", parse_mode="HTML", disable_web_page_preview=True)

@cmd("мой брак")
@cmd("моя пара")
async def my_marriage_cmd(message: types.Message):
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar: return await message.reply("💔 Вы не в браке.", parse_mode="HTML", disable_web_page_preview=True)
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra = mar
    partner_id = u2_id if u1_id == message.from_user.id else u1_id
    partner_name = u2_name if u1_id == message.from_user.id else u1_name
    duration = format_marriage_duration(married_at, extra or 0)
    text = f"💍 <b>Ваш брак</b>\n\n👫 {mention(message.from_user)} 💞 {mention_by_id(partner_id, partner_name)}\n📅 {married_at[:10]}\n⏳ Вместе: <b>{duration}</b>"
    if extra and extra > 0: text += f"\n🛒 Куплено дней: <b>{extra}</b>"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("браки")
async def marriages_list_cmd(message: types.Message):
    pairs = get_all_marriages(message.chat.id)
    if not pairs: return await message.reply("📭 Нет браков.", parse_mode="HTML", disable_web_page_preview=True)
    text = "💍 <b>Браки:</b>\n\n"
    for i, (u1_id, u1_name, u2_id, u2_name, married_at, extra) in enumerate(pairs, 1):
        duration = format_marriage_duration(married_at, extra or 0)
        text += f"{i}. {mention_by_id(u1_id, u1_name)} 💞 {mention_by_id(u2_id, u2_name)} — <i>{duration}</i>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("брак продлить"))
async def extend_marriage(message: types.Message):
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar: return await message.reply(f"{em('cross', '❌')} Вы не в браке.", parse_mode="HTML", disable_web_page_preview=True)
    args = message.text.split()
    if len(args) < 3 or not args[-1].isdigit():
        return await message.reply("📌 <code>брак продлить {дни}</code>", parse_mode="HTML", disable_web_page_preview=True)
    days = int(args[-1])
    if days <= 0: return
    _, price = get_marriage_settings(message.chat.id)
    total = days * price
    if total > 0:
        balance = get_balance(message.from_user.id)
        if balance < total: return await message.reply(f"{em('cross', '❌')} Нужно: <b>{total}</b>, у вас: <b>{balance}</b>", parse_mode="HTML", disable_web_page_preview=True)
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (total, message.from_user.id))
            conn.commit()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriages SET extra_days = extra_days + ? WHERE id = ?", (days, mar[0]))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Брак продлён на <b>{days}</b> дн. за <b>{total}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True)

# ================= ЗАМЕТКИ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+заметка "))
async def create_note_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен ранг Мл. Админ.", parse_mode="HTML", disable_web_page_preview=True)
    parts = message.text.split("\n", 1)
    name = parts[0].replace("+Заметка", "").replace("+заметка", "").strip()
    if not name or len(parts) < 2: return
    body = parts[1].strip()[:3500]
    body = auto_premium(body)
    note_id = add_note(message.chat.id, name, body, message.from_user.id)
    if not note_id: return await message.reply(f"{em('cross', '❌')} Заметка уже есть.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"{em('check', '✅')} Заметка <b>{name}</b> создана (ID: {note_id})", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-заметка "))
async def delete_note_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    arg = message.text[len("-Заметка"):].strip()
    if not arg: return
    note = get_note_by_number(message.chat.id, int(arg)) if arg.isdigit() else get_note_by_name(message.chat.id, arg)
    if not note: return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    delete_note(message.chat.id, note[0])
    await message.reply(f"{em('check', '✅')} Заметка <b>{note[1]}</b> удалена.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("заметки")
async def list_notes_cmd(message: types.Message):
    args = message.text.split()
    page = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 1
    notes = get_all_notes(message.chat.id)
    if not notes: return await message.reply("📭 Нет заметок.", parse_mode="HTML", disable_web_page_preview=True)
    per = 20
    tp = (len(notes) + per - 1) // per
    if page > tp: page = tp
    start = (page - 1) * per
    end = start + per
    text = f"📋 <b>Заметки</b> (стр. {page}/{tp})\n\n"
    for i, (nid, name) in enumerate(notes[start:end], start=start+1):
        text += f"{i}. <b>{name}</b>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("заметка ") and not m.text.lower().strip().startswith("заметки"))
async def get_note_cmd(message: types.Message):
    arg = message.text[len("Заметка"):].strip()
    if not arg: return
    note = get_note_by_number(message.chat.id, int(arg)) if arg.isdigit() else get_note_by_name(message.chat.id, arg)
    if not note: return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(note[2], parse_mode="HTML", disable_web_page_preview=True)

# ================= VIP =================
@cmd("вип")
async def vip_info_cmd(message: types.Message):
    args = message.text.split()
    price = get_vip_price(message.chat.id)
    if len(args) >= 2 and args[1].isdigit():
        if not has_permission(message.chat.id, message.from_user.id, 4):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг Ст. Админ (4).", parse_mode="HTML", disable_web_page_preview=True)
        new_price = int(args[1])
        if new_price < 10 or new_price > 10000:
            return await message.reply(f"{em('cross', '❌')} Цена от 10 до 10 000.", parse_mode="HTML", disable_web_page_preview=True)
        set_vip_price(message.chat.id, new_price)
        return await message.reply(f"{em('check', '✅')} Цена VIP: <b>{new_price}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(
        f"💎 <b>VIP-статус</b>\n\n"
        f"💰 Цена: <b>{price}</b> 🍬 / мес\n\n"
        f"📌 <b>Команды:</b>\n"
        f"• <code>Купить вип</code>\n"
        f"• <code>Купить вип N</code>\n"
        f"• <code>Купить вип @user</code>\n"
        f"• <code>Мой вип</code>\n"
        f"• <code>Кто вип</code> / <code>Кто не вип</code>\n"
        f"• <code>+Вип эмодзи 😎</code>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@cmd("купить вип")
async def buy_vip_cmd(message: types.Message):
    args = message.text.split()
    months = 1
    target = message.from_user
    for a in args[2:]:
        if a.isdigit():
            months = int(a)
        else:
            try: target = await bot.get_chat(a)
            except: pass
    if months < 1 or months > 12:
        return await message.reply(f"{em('cross', '❌')} Месяцев: 1-12.", parse_mode="HTML", disable_web_page_preview=True)
    total = get_vip_price(message.chat.id) * months
    balance = get_balance(message.from_user.id)
    if balance < total:
        return await message.reply(f"{em('cross', '❌')} Нужно: <b>{total}</b> 🍬, у вас: <b>{balance}</b>", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (total, message.from_user.id))
        conn.commit()
    new_exp = add_vip_months(target.id, months)
    if target.id == message.from_user.id:
        await message.reply(f"💎 <b>VIP активирован!</b>\n📅 До: <b>{new_exp.strftime('%d.%m.%Y')}</b>\n💰 -{total} 🍬", parse_mode="HTML", disable_web_page_preview=True)
    else:
        await message.reply(f"🎁 {mention(target)} получил VIP на <b>{months}</b> мес.\n📅 До: <b>{new_exp.strftime('%d.%m.%Y')}</b>", parse_mode="HTML", disable_web_page_preview=True)
        try: await bot.send_message(target.id, f"🎁 Вам подарили VIP на {months} мес.!", parse_mode="HTML", disable_web_page_preview=True)
        except: pass

@cmd("мой вип")
async def my_vip_cmd(message: types.Message):
    v = get_vip(message.from_user.id)
    if not v:
        return await message.reply("💎 Нет VIP.", parse_mode="HTML", disable_web_page_preview=True)
    days = get_vip_days_left(message.from_user.id)
    await message.reply(f"💎 <b>Ваш VIP</b>\n📅 Осталось: <b>{days} дн.</b>\n😎 Эмодзи: {v[1] or '—'}", parse_mode="HTML", disable_web_page_preview=True)

@cmd("кто вип")
async def who_vip_cmd(message: types.Message):
    users = get_vip_list(message.chat.id, only_vip=True, limit=50)
    if not users:
        return await message.reply("💎 Нет VIP.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"💎 <b>VIP</b> ({len(users)}):\n\n"
    for i, uid in enumerate(users, 1):
        try:
            u = await bot.get_chat(uid)
            emoji = get_vip_emoji(uid)
            name = user_link(uid, u.first_name, u.username)
            text += f"{i}. {emoji}{name}{emoji} — {get_vip_days_left(uid)} дн.\n"
        except: pass
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("кто не вип")
async def who_not_vip_cmd(message: types.Message):
    users = get_vip_list(message.chat.id, only_vip=False, limit=50)
    if not users:
        return await message.reply("📭 Все VIP.", parse_mode="HTML", disable_web_page_preview=True)
    text = "👤 <b>Без VIP</b>:\n\n"
    for i, uid in enumerate(users, 1):
        try:
            u = await bot.get_chat(uid)
            text += f"{i}. {user_link(uid, u.first_name, u.username)}\n"
        except: pass
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+вип эмодзи"))
async def set_vip_emoji_cmd(message: types.Message):
    if not get_vip(message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Нет VIP.", parse_mode="HTML", disable_web_page_preview=True)
    args = message.text.split()
    if len(args) < 3:
        return await message.reply("📌 <code>+Вип эмодзи 😎</code>", parse_mode="HTML", disable_web_page_preview=True)
    set_vip_emoji(message.from_user.id, args[2])
    await message.reply(f"{em('check', '✅')} Эмодзи: {args[2]}", parse_mode="HTML", disable_web_page_preview=True)

# ================= РП =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+мрп"))
async def create_rp_cmd(message: types.Message):
    if not get_vip(message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Только для VIP.", parse_mode="HTML", disable_web_page_preview=True)
    parts = message.text.split("/", 2)
    if len(parts) < 3:
        return await message.reply("📌 <code>+Мрп Название / 😀 / текст</code>", parse_mode="HTML", disable_web_page_preview=True)
    name = parts[0].replace("+Мрп", "").replace("+мрп", "").strip()[:30]
    emoji = parts[1].strip()[:5]
    text = parts[2].strip()[:200]
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO rp_commands (chat_id, name, emoji, text, created_by) VALUES (?, ?, ?, ?, ?)", (message.chat.id, name, emoji, text, message.from_user.id))
            conn.commit()
            await message.reply(f"{em('check', '✅')} РП: {emoji} <b>{name}</b>", parse_mode="HTML", disable_web_page_preview=True)
        except:
            await message.reply(f"{em('cross', '❌')} Такая РП уже есть.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("мрп")
async def list_rp_cmd(message: types.Message):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, emoji FROM rp_commands WHERE chat_id = ? AND created_by = ? ORDER BY id", (message.chat.id, message.from_user.id))
        rows = c.fetchall()
    if not rows:
        return await message.reply("📭 Нет РП.", parse_mode="HTML", disable_web_page_preview=True)
    text = "📋 <b>Ваши РП:</b>\n\n"
    for i, (rid, name, emoji) in enumerate(rows, 1):
        text += f"{i}. {emoji} <b>{name}</b>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-мрп"))
async def delete_rp_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.reply("📌 <code>-Мрп название</code>", parse_mode="HTML", disable_web_page_preview=True)
    name = args[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM rp_commands WHERE chat_id = ? AND name = ? AND created_by = ?", (message.chat.id, name, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Удалено.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+гмрп"))
async def create_global_rp_cmd(message: types.Message):
    if not get_vip(message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Только для VIP.", parse_mode="HTML", disable_web_page_preview=True)
    parts = message.text.split("/", 2)
    if len(parts) < 3:
        return await message.reply("📌 <code>+Гмрп Название / 😀 / текст</code>", parse_mode="HTML", disable_web_page_preview=True)
    name = parts[0].replace("+Гмрп", "").replace("+гмрп", "").strip()[:30]
    emoji = parts[1].strip()[:5]
    text = parts[2].strip()[:200]
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO global_rp_commands (user_id, name, emoji, text) VALUES (?, ?, ?, ?)", (message.from_user.id, name, emoji, text))
            conn.commit()
            await message.reply(f"🌍 ГМРП: {emoji} <b>{name}</b>", parse_mode="HTML", disable_web_page_preview=True)
        except:
            await message.reply(f"{em('cross', '❌')} Такая уже есть.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("гмрп")
async def list_global_rp_cmd(message: types.Message):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, emoji FROM global_rp_commands WHERE user_id = ? ORDER BY id", (message.from_user.id,))
        rows = c.fetchall()
    if not rows:
        return await message.reply("📭 Нет ГМРП.", parse_mode="HTML", disable_web_page_preview=True)
    text = "🌍 <b>Ваши ГМРП:</b>\n\n"
    for i, (rid, name, emoji) in enumerate(rows, 1):
        text += f"{i}. {emoji} <b>{name}</b>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-гмрп"))
async def delete_global_rp_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.reply("📌 <code>-Гмрп название</code>", parse_mode="HTML", disable_web_page_preview=True)
    name = args[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM global_rp_commands WHERE user_id = ? AND name = ?", (message.from_user.id, name))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Удалено.", parse_mode="HTML", disable_web_page_preview=True)

# ================= ПОГОДА =================
@cmd("погода")
async def weather_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("📌 <code>.погода Москва</code>", parse_mode="HTML", disable_web_page_preview=True)
    city = args[1].strip()
    weather = get_weather(city)
    if not weather:
        return await message.reply(f"{em('cross', '❌')} Город не найден.", parse_mode="HTML", disable_web_page_preview=True)
    text = (
        f"🌍 <b>Погода в {weather['name']}</b>"
        + (f", {weather['country']}" if weather['country'] else "")
        + f"\n\n{get_weather_emoji(weather['code'])}\n"
        f"🌡️ <b>{weather['temperature']}°C</b>\n"
        f"💧 {weather['humidity']}%\n"
        f"💨 {weather['wind']} км/ч\n\n"
        f"<i>Источник: Open-Meteo</i>"
    )
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= +ЧАТ/-ЧАТ =================
@dp.message(lambda m: m.text and m.text.lower().strip() == "+чат")
async def enable_chat_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 4): return
    try:
        await bot.set_chat_permissions(chat_id=message.chat.id, permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True, can_invite_users=True, can_change_info=False, can_pin_messages=False))
        await message.reply(f"{em('check', '✅')} Чат включён.", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e: await message.reply(f"{em('cross', '❌')} {e}", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip() == "-чат")
async def disable_chat_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 4): return
    try:
        await bot.set_chat_permissions(chat_id=message.chat.id, permissions=types.ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False, can_send_polls=False, can_invite_users=True, can_change_info=False, can_pin_messages=False))
        await message.reply(f"{em('mute', '🔇')} Чат отключён.", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e: await message.reply(f"{em('cross', '❌')} {e}", parse_mode="HTML", disable_web_page_preview=True)# ================= СЕТКИ =================
@cmd("создать сетку")
async def create_grid_cmd(message: types.Message):
    if message.chat.type != "private": return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return await message.reply("📌 <code>создать сетку {название}</code>", parse_mode="HTML", disable_web_page_preview=True)
    name = args[2].strip().replace(" ", "_")[:24]
    if not name: return await message.reply(f"{em('cross', '❌')} Название пустое.", parse_mode="HTML", disable_web_page_preview=True)
    grid_id = create_grid(name, message.from_user.id)
    if not grid_id: return await message.reply(f"{em('cross', '❌')} Уже существует.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"{em('check', '✅')} Сетка <b>{name}</b> (ID: <code>{grid_id}</code>)", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("сетка ") and m.chat.type != "private"
    and not m.text.lower().strip().startswith("сетка повысить")
    and not m.text.lower().strip().startswith("сетка понизить")
    and not m.text.lower().strip().startswith("сетка +админ"))
async def set_grid_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return
    grid = get_grid_by_name(args[1].strip())
    if not grid: return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    grid_id, grid_name = grid
    if not is_grid_moderator(grid_id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return await message.reply("⛔ Только админ чата.", parse_mode="HTML", disable_web_page_preview=True)
    add_chat_to_grid(grid_id, message.chat.id, hidden=0)
    await message.reply(f"{em('check', '✅')} Чат привязан к <b>{grid_name}</b>!", parse_mode="HTML", disable_web_page_preview=True)

# ================= СЕТКА: ПОВЫСИТЬ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("сетка повысить"))
async def grid_promote_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply(f"{em('cross', '❌')} Чат не привязан к сетке.", parse_mode="HTML", disable_web_page_preview=True)

    if not is_grid_moderator(grid_id, message.from_user.id, 3):
        return await message.reply("⛔ Только гл. модератор сетки (ранг 3+).", parse_mode="HTML", disable_web_page_preview=True)

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>сетка повысить @user 3</code>\n"
            "<code>сетка повысить</code> (ответом) <code>3</code>\n\n"
            "🎖 <b>Ранги в сетке:</b>\n"
            "1 — Мл. Модератор\n"
            "2 — Ст. Модератор\n"
            "3 — Мл. Админ\n"
            "4 — Ст. Админ",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if target.id == OWNER_ID:
        return await message.reply("⛔ Владельца нельзя.", parse_mode="HTML", disable_web_page_preview=True)

    args = message.text.split()
    new_rank = None
    for a in args[2:]:
        if a.isdigit():
            new_rank = int(a)
            break

    if new_rank is None:
        return await message.reply(f"{em('cross', '❌')} Укажите ранг цифрой (1-4)", parse_mode="HTML", disable_web_page_preview=True)

    if new_rank not in [1, 2, 3, 4]:
        return await message.reply(f"{em('cross', '❌')} Ранг от 1 до 4.", parse_mode="HTML", disable_web_page_preview=True)

    actor_grid_rank = get_grid_user_rank(grid_id, message.from_user.id)
    if actor_grid_rank and new_rank >= actor_grid_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя выдать ранг ≥ твоего ({actor_grid_rank}).", parse_mode="HTML", disable_web_page_preview=True)

    set_grid_user_rank(grid_id, target.id, new_rank, message.from_user.id)

    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    failed = 0
    notified = 0

    rank_name = RANK_NAMES.get(new_rank, f"Ранг {new_rank}")
    actor_name = message.from_user.first_name
    actor_username = message.from_user.username
    actor_link = user_link(message.from_user.id, actor_name, actor_username)

    for chat_id, hidden, desc in chats:
        try:
            set_rank(chat_id, target.id, new_rank, message.from_user.id)
            success += 1

            try:
                notify_text = (
                    f"🏆 <b>Новое повышение!</b>\n\n"
                    f"👤 {mention(target)}\n"
                    f"📊 Новый ранг: <b>{rank_name}</b>\n"
                    f"👮 Повысил: {actor_link}"
                )
                await bot.send_message(chat_id, notify_text, parse_mode="HTML", disable_web_page_preview=True)
                notified += 1
            except Exception as e:
                print(f"⚠️ Не удалось уведомить чат {chat_id}: {e}")
        except Exception as e:
            print(f"❌ Ошибка ранга в чате {chat_id}: {e}")
            failed += 1

    await message.reply(
        f"🏆 {mention(target)} <b>повышен в сетке</b>\n\n"
        f"📊 Новый ранг: <b>{rank_name}</b>\n"
        f"✅ Ранг установлен: <b>{success}</b> из <b>{len(chats)}</b> чатов\n"
        f"📢 Уведомлено: <b>{notified}</b> чатов"
        + (f"\n⚠️ Ошибок: {failed}" if failed else ""),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    try:
        await bot.send_message(
            target.id,
            f"🏆 <b>Вас повысили в сетке чатов!</b>\n\n"
            f"📊 Ранг: <b>{rank_name}</b>\n"
            f"🌐 Чатов: <b>{success}</b>\n"
            f"👮 Повысил: {actor_link}\n\n"
            f"Пользуйтесь полномочиями на славу <b>Mos</b>! 🛡",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except:
        pass

# ================= СЕТКА: ПОНИЗИТЬ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("сетка понизить"))
async def grid_demote_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply(f"{em('cross', '❌')} Чат не привязан к сетке.", parse_mode="HTML", disable_web_page_preview=True)

    if not is_grid_moderator(grid_id, message.from_user.id, 3):
        return await message.reply("⛔ Только гл. модератор сетки (ранг 3+).", parse_mode="HTML", disable_web_page_preview=True)

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>сетка понизить @user 1</code>\n"
            "<code>сетка понизить @user 0</code> — снять всё",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if target.id == OWNER_ID:
        return await message.reply("⛔ Владельца нельзя.", parse_mode="HTML", disable_web_page_preview=True)

    args = message.text.split()
    new_rank = None
    for a in args[2:]:
        if a.isdigit():
            new_rank = int(a)
            break

    if new_rank is None:
        current = get_grid_user_rank(grid_id, target.id)
        new_rank = max(0, current - 1)

    if new_rank < 0 or new_rank > 4:
        return await message.reply(f"{em('cross', '❌')} Ранг от 0 до 4.", parse_mode="HTML", disable_web_page_preview=True)

    actor_grid_rank = get_grid_user_rank(grid_id, message.from_user.id)
    if actor_grid_rank and new_rank >= actor_grid_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя поставить ранг ≥ твоего.", parse_mode="HTML", disable_web_page_preview=True)

    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    failed = 0
    notified = 0

    actor_name = message.from_user.first_name
    actor_username = message.from_user.username
    actor_link = user_link(message.from_user.id, actor_name, actor_username)

    if new_rank == 0:
        remove_grid_user_rank(grid_id, target.id)
        rank_name = "👤 Участник"
        result_text = "разжалован во всей сетке"

        for chat_id, hidden, desc in chats:
            try:
                remove_rank(chat_id, target.id)
                success += 1
                try:
                    notify_text = (
                        f"📉 <b>Разжалование в сетке</b>\n\n"
                        f"👤 {mention(target)}\n"
                        f"📊 Теперь: <b>{rank_name}</b>\n"
                        f"👮 Снял: {actor_link}"
                    )
                    await bot.send_message(chat_id, notify_text, parse_mode="HTML", disable_web_page_preview=True)
                    notified += 1
                except:
                    pass
            except:
                failed += 1
    else:
        set_grid_user_rank(grid_id, target.id, new_rank, message.from_user.id)
        rank_name = RANK_NAMES.get(new_rank, f"Ранг {new_rank}")
        result_text = "понижен в сетке"

        for chat_id, hidden, desc in chats:
            try:
                set_rank(chat_id, target.id, new_rank, message.from_user.id)
                success += 1
                try:
                    notify_text = (
                        f"📉 <b>Понижение в сетке</b>\n\n"
                        f"👤 {mention(target)}\n"
                        f"📊 Новый ранг: <b>{rank_name}</b>\n"
                        f"👮 Понизил: {actor_link}"
                    )
                    await bot.send_message(chat_id, notify_text, parse_mode="HTML", disable_web_page_preview=True)
                    notified += 1
                except:
                    pass
            except:
                failed += 1

    await message.reply(
        f"📉 {mention(target)} <b>{result_text}</b>\n\n"
        f"📊 Новый ранг: <b>{rank_name}</b>\n"
        f"✅ Ранг обновлён: <b>{success}</b> из <b>{len(chats)}</b> чатов\n"
        f"📢 Уведомлено: <b>{notified}</b> чатов"
        + (f"\n⚠️ Ошибок: {failed}" if failed else ""),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    try:
        await bot.send_message(
            target.id,
            f"📉 <b>Понижение в сетке чатов</b>\n\n"
            f"📊 Ранг: <b>{rank_name}</b>\n"
            f"🌐 Чатов: <b>{success}</b>\n"
            f"👮 Понизил: {actor_link}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except:
        pass

# ================= СЕТКА: +АДМИН (ТГ-админка во всех чатах) =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("сетка +админ"))
async def grid_tg_admin_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply(f"{em('cross', '❌')} Чат не привязан к сетке.", parse_mode="HTML", disable_web_page_preview=True)

    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT creator_id FROM grids WHERE id = ?", (grid_id,))
        r = c.fetchone()
        creator_id = r[0] if r else None

    if message.from_user.id != creator_id and message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Только создатель сетки или владелец бота.", parse_mode="HTML", disable_web_page_preview=True)

    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>сетка +админ @user</code>\n"
            "<code>сетка +админ</code> (ответом)\n\n"
            "<i>Выдаёт ТГ-админку во всех чатах сетки</i>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if target.id == OWNER_ID:
        return await message.reply("⛔ Владельца нельзя.", parse_mode="HTML", disable_web_page_preview=True)

    chats = get_grid_chats(grid_id, include_hidden=True)
    if not chats:
        return await message.reply(f"{em('cross', '❌')} В сетке нет чатов.", parse_mode="HTML", disable_web_page_preview=True)

    success = 0
    failed = 0
    notified = 0
    actor_link = user_link(message.from_user.id, message.from_user.first_name, message.from_user.username)

    for chat_id, hidden, desc in chats:
        try:
            await bot.promote_chat_member(
                chat_id=chat_id, user_id=target.id,
                can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
                can_restrict_members=True, can_promote_members=True, can_change_info=True,
                can_invite_users=True, can_pin_messages=True
            )
            mark_bot_promoted(target.id, chat_id, message.from_user.id)
            success += 1

            try:
                chat = await bot.get_chat(chat_id)
                chat_title = chat.title or f"Чат {chat_id}"
                await bot.send_message(
                    chat_id,
                    f"{em('check', '✅')} {mention(target)} теперь <b>ТГ-админ</b>\n"
                    f"👮 Выдал: {actor_link}",
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                notified += 1
            except:
                pass
        except Exception as e:
            print(f"❌ Ошибка +админ в чате {chat_id}: {e}")
            failed += 1

    await message.reply(
        f"{em('check', '✅')} {mention(target)} теперь <b>ТГ-админ</b> в сетке\n\n"
        f"✅ Успешно: <b>{success}</b> из <b>{len(chats)}</b>\n"
        f"📢 Уведомлено: <b>{notified}</b>"
        + (f"\n⚠️ Ошибок: {failed}" if failed else ""),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    try:
        await bot.send_message(
            target.id,
            f"👑 <b>Вы теперь ТГ-админ в сетке чатов!</b>\n\n"
            f"🌐 Чатов: <b>{success}</b>\n"
            f"👮 Назначил: {actor_link}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except:
        pass

@cmd("чаты")
async def list_grid_chats(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return await message.reply(f"{em('cross', '❌')} Чат не привязан.", parse_mode="HTML", disable_web_page_preview=True)
    chats = get_grid_chats(grid_id, include_hidden=False)
    text = "📋 <b>Чаты сетки:</b>\n\n"
    for chat_id, hidden, desc in chats:
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title or f"Чат {chat_id}"
            link = None
            if chat.username: link = f"https://t.me/{chat.username}"
            else:
                try:
                    invite = await bot.create_chat_invite_link(chat_id)
                    link = invite.invite_link
                except: pass
            if link: text += f"• <a href='{link}'>{title}</a>\n"
            else: text += f"• {title}\n"
        except: text += f"• Чат {chat_id}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("глобан"))
async def global_ban_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return await message.reply(f"{em('cross', '❌')} Чат не в сетке.", parse_mode="HTML", disable_web_page_preview=True)
    if not is_grid_moderator(grid_id, message.from_user.id, 2):
        return await message.reply("⛔ Только гл. модератор.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target: return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1: reason = parts[1].strip()
    add_grid_ban(grid_id, target.id, reason, message.from_user.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.ban_chat_member(chat_id, target.id)
            success += 1
        except: pass
    await message.reply(f"{em('ban', '🚫')} {mention(target)} забанен ({success}/{len(chats)}).\n📝 {reason}", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("глоразбан"))
async def global_unban_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    if not is_grid_moderator(grid_id, message.from_user.id, 2): return
    target, _ = await resolve_target(message)
    if not target: return
    remove_grid_ban(grid_id, target.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.unban_chat_member(chat_id, target.id)
            success += 1
        except: pass
    await message.reply(f"{em('check', '✅')} {mention(target)} разбанен ({success}/{len(chats)}).", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("гломут"))
async def global_mute_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    if not is_grid_moderator(grid_id, message.from_user.id, 2): return
    target, _ = await resolve_target(message)
    if not target: return
    until = datetime.now() + timedelta(hours=24)
    add_grid_mute(grid_id, target.id, until.isoformat(), message.from_user.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.restrict_chat_member(chat_id, target.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
            success += 1
        except: pass
    await message.reply(f"{em('mute', '🔇')} {mention(target)} замучен ({success}/{len(chats)}).", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("глоразмут"))
async def global_unmute_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    if not is_grid_moderator(grid_id, message.from_user.id, 2): return
    target, _ = await resolve_target(message)
    if not target: return
    remove_grid_mute(grid_id, target.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.restrict_chat_member(chat_id, target.id, permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
            success += 1
        except: pass
    await message.reply(f"🔈 {mention(target)} размучен ({success}/{len(chats)}).", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+глмодер"))
async def add_global_moderator(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    if not is_grid_moderator(grid_id, message.from_user.id, 3): return
    target, _ = await resolve_target(message)
    if not target: return
    add_grid_moderator(grid_id, target.id, rank=1, is_admin=0)
    await message.reply(f"{em('check', '✅')} {mention(target)} гл. модератор!", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-глмодер"))
async def remove_global_moderator(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    if not is_grid_moderator(grid_id, message.from_user.id, 3): return
    target, _ = await resolve_target(message)
    if not target: return
    remove_grid_moderator(grid_id, target.id)
    await message.reply(f"{em('check', '✅')} {mention(target)} больше не гл. модератор.", parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+гладмин"))
async def add_global_admin(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT creator_id FROM grids WHERE id = ?", (grid_id,))
        r = c.fetchone()
        creator_id = r[0] if r else None
    if message.from_user.id != creator_id and message.from_user.id != OWNER_ID: return
    target, _ = await resolve_target(message)
    if not target: return
    add_grid_moderator(grid_id, target.id, rank=5, is_admin=1)
    await message.reply(f"{em('check', '✅')} {mention(target)} гл. админ!", parse_mode="HTML", disable_web_page_preview=True)

@cmd("удалить из сетки")
async def remove_from_grid(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    if not is_grid_moderator(grid_id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id): return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM grid_chats WHERE chat_id = ?", (message.chat.id,))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Чат удалён из сетки.", parse_mode="HTML", disable_web_page_preview=True)

# ================= КАТАЛОГ =================
@cmd("каталог добавить")
async def catalog_add_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await is_tg_admin(message.chat.id, message.from_user.id): return
    chat_balance = get_chat_coins(message.chat.id)
    if chat_balance < 35000:
        return await message.reply(f"{em('cross', '❌')} Нужно: <b>35 000</b> i¢\nСейчас: <b>{chat_balance}</b>\n\n<code>Бкоин {35000 - chat_balance}</code>", parse_mode="HTML", disable_web_page_preview=True)
    existing = get_catalog_entry(message.chat.id)
    if existing and existing[6] == "approved": return await message.reply(f"{em('check', '✅')} Уже в каталоге.", parse_mode="HTML", disable_web_page_preview=True)
    qid = add_to_catalog_queue(message.chat.id, message.from_user.id, "add")
    chat_title = message.chat.title or "Без названия"
    chat_desc = message.chat.description or "—"
    link = await get_chat_link(message.chat.id)
    mod_text = f"📥 <b>Заявка в каталог</b>\n\n📍 {chat_title}\n🆔 <code>{message.chat.id}</code>\n👤 {mention(message.from_user)}\n💰 {chat_balance} i¢\n📝 {chat_desc}\n🔗 {link or '—'}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"catalog_approve:{qid}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"catalog_reject:{qid}")
    ]])
    try: await bot.send_message(MODERATION_CHAT_ID, mod_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    except: pass
    await message.reply(f"📥 Заявка отправлена!\n💰 Коины не списываются.", parse_mode="HTML", disable_web_page_preview=True)

@cmd("каталог чатов")
async def catalog_list_cmd(message: types.Message):
    chats = get_catalog_list(limit=100)
    if not chats: return await message.reply("📭 Каталог пуст.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"📚 <b>Каталог</b> ({len(chats)})\n\n"
    for i, (chat_id, title, description, link) in enumerate(chats, 1):
        text += f"{i}. <b>{title}</b>\n"
        if description: text += f"   <i>{description[:80]}</i>\n"
        if link: text += f"   🔗 <a href='{link}'>Перейти</a>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@cmd("каталог")
async def catalog_slash_cmd(message: types.Message):
    chats = get_catalog_list(limit=100)
    if not chats: return await message.reply("📭 Пусто.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"📚 <b>Каталог</b> ({len(chats)})\n\n"
    for i, (chat_id, title, description, link) in enumerate(chats, 1):
        text += f"{i}. <b>{title}</b>\n"
        if link: text += f"   🔗 <a href='{link}'>Перейти</a>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.callback_query(lambda c: c.data and (c.data.startswith("catalog_approve:") or c.data.startswith("catalog_reject:")))
async def catalog_review_handler(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID and not has_agent_rank(callback.from_user.id, 2):
        return await callback.answer("⛔ Только агенты 2+.", show_alert=True)
    action, qid_str = callback.data.split(":")
    qid = int(qid_str)
    entry = get_catalog_queue_entry(qid)
    if not entry: return await callback.answer("⚠️ Уже.", show_alert=True)
    chat_id, submitted_by, act, status = entry
    if status != "pending": return await callback.answer("⚠️ Уже.", show_alert=True)
    reviewer = mention(callback.from_user)
    if action == "catalog_approve":
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title or "Чат"
            desc = chat.description or ""
        except: title, desc = "Чат", ""
        link = await get_chat_link(chat_id)
        add_catalog_chat(chat_id, title, desc, link or "", submitted_by)
        update_catalog_queue_status(qid, "approved", callback.from_user.id)
        try: await bot.send_message(chat_id, f"{em('check', '✅')} Ваш чат одобрен и в каталоге!", parse_mode="HTML", disable_web_page_preview=True)
        except: pass
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.reply(f"{em('check', '✅')} Одобрено {reviewer}", disable_web_page_preview=True)
        except: pass
        await callback.answer(f"{em('check', '✅')} Одобрено!")
    else:
        update_catalog_queue_status(qid, "rejected", callback.from_user.id)
        try: await bot.send_message(chat_id, f"{em('cross', '❌')} Ваш чат отклонён.", parse_mode="HTML", disable_web_page_preview=True)
        except: pass
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.reply(f"{em('cross', '❌')} Отклонено {reviewer}", disable_web_page_preview=True)
        except: pass
        await callback.answer(f"{em('cross', '❌')} Отклонено!")

# ================= ВЛАДЕЛЕЦ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+опасно"))
async def ban_chat_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) >= 2:
        code = args[1].upper()
        chat_id = get_chat_by_code(code)
        if not chat_id: return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML", disable_web_page_preview=True)
        try:
            chat = await bot.get_chat(chat_id)
            chat_name = chat.title or f"Чат {chat_id}"
        except: chat_name = f"Чат {chat_id}"
    else:
        chat_id = message.chat.id
        chat_name = message.chat.title or f"Чат {chat_id}"
    if is_chat_banned(chat_id): return await message.reply("⚠️ Уже в ЧС", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO banned_chats (chat_id, added_by) VALUES (?, ?)", (chat_id, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('ban', '🚫')} Чат «{chat_name}» забанен.", parse_mode="HTML", disable_web_page_preview=True)
    try: await bot.leave_chat(chat_id)
    except: pass

@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+безопасно"))
async def unban_chat_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) >= 2:
        code = args[1].upper()
        chat_id = get_chat_by_code(code)
        if not chat_id: return
        try:
            chat = await bot.get_chat(chat_id)
            chat_name = chat.title or f"Чат {chat_id}"
        except: chat_name = f"Чат {chat_id}"
    else:
        chat_id = message.chat.id
        chat_name = message.chat.title or f"Чат {chat_id}"
    if not is_chat_banned(chat_id): return await message.reply("⚠️ И так не в ЧС", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM banned_chats WHERE chat_id = ?", (chat_id,))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Чат «{chat_name}» убран.", parse_mode="HTML", disable_web_page_preview=True)

# ================= БЭКАП (ручной) =================
@cmd("бэкап")
async def backup_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("💾 Создаю бэкап...", disable_web_page_preview=True)
    try:
        with open(DATABASE_PATH, "rb") as f:
            data = f.read()
        size_kb = len(data) / 1024
        await message.reply_document(
            types.BufferedInputFile(data, filename=f"bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"),
            caption=f"💾 Бэкап базы\n📦 Размер: {size_kb:.1f} КБ"
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", disable_web_page_preview=True)

@cmd("бэкапы")
async def list_backups_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        if not os.path.exists("backups"):
            return await message.reply("📭 Папка бэкапов пуста.", disable_web_page_preview=True)
        files = sorted([f for f in os.listdir("backups") if f.startswith("bot_")], reverse=True)
        if not files:
            return await message.reply("📭 Бэкапов нет.", disable_web_page_preview=True)
        text = f"📋 <b>Бэкапы</b> ({len(files)}):\n\n"
        for f in files[:20]:
            path = os.path.join("backups", f)
            size_kb = os.path.getsize(path) / 1024
            text += f"📄 <code>{f}</code> — {size_kb:.1f} КБ\n"
        if len(files) > 20:
            text += f"\n<i>...и ещё {len(files)-20}</i>"
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", disable_web_page_preview=True)

@cmd("бэкапсейчас")
async def backup_now_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        import shutil
        os.makedirs("backups", exist_ok=True)
        local_backup = f"backups/bot_{timestamp}.db"
        shutil.copy2(DATABASE_PATH, local_backup)

        with open(DATABASE_PATH, "rb") as f:
            data = f.read()
        size_kb = len(data) / 1024

        await message.reply_document(
            types.BufferedInputFile(data, filename=f"mos_backup_{timestamp}.db"),
            caption=(
                f"💾 <b>Бэкап по запросу</b>\n\n"
                f"📅 {now.strftime('%d.%m.%Y %H:%M')}\n"
                f"📦 {size_kb:.1f} КБ"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", disable_web_page_preview=True)

# ================= ИМПОРТ БАЗЫ =================
@cmd("импорт")
async def import_db_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply(
            f"{em('cross', '❌')} <b>Ответьте</b> на <code>.db</code> файл командой <code>.импорт</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    doc = message.reply_to_message.document
    if not doc.file_name.lower().endswith(".db"):
        return await message.reply(
            f"{em('cross', '❌')} Только <code>.db</code> файлы.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        return await message.reply(
            f"{em('cross', '❌')} Файл слишком большой (макс 20 МБ).",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    status_msg = await message.reply("📥 Скачиваю базу...", disable_web_page_preview=True)
    temp_path = f"temp_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, temp_path)

        import sqlite3 as _sql
        try:
            with _sql.connect(temp_path) as test_conn:
                test_cursor = test_conn.cursor()
                test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in test_cursor.fetchall()]
        except Exception as e:
            os.remove(temp_path)
            await status_msg.edit_text(
                f"{em('cross', '❌')} <b>Файл повреждён</b>\n\n"
                f"Не удалось открыть как SQLite: <code>{e}</code>",
                parse_mode="HTML"
            )
            return

        required_tables = ["users", "messages_stats", "agents"]
        missing = [t for t in required_tables if t not in tables]

        if missing:
            os.remove(temp_path)
            await status_msg.edit_text(
                f"{em('cross', '❌')} <b>Это не база Mos-бота</b>\n\n"
                f"Не найдены таблицы: <code>{', '.join(missing)}</code>\n\n"
                f"<i>Найдено: {len(tables)} таблиц</i>",
                parse_mode="HTML"
            )
            return

        os.makedirs("backups", exist_ok=True)
        old_backup = f"backups/old_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil

        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, old_backup)

        with _sql.connect(temp_path) as test_conn:
            test_cursor = test_conn.cursor()
            try:
                test_cursor.execute("SELECT COUNT(*) FROM users")
                users_count = test_cursor.fetchone()[0]
            except:
                users_count = "?"
            try:
                test_cursor.execute("SELECT COUNT(*) FROM messages_stats")
                messages_count = test_cursor.fetchone()[0]
            except:
                messages_count = "?"
            try:
                test_cursor.execute("SELECT COUNT(*) FROM agents")
                agents_count = test_cursor.fetchone()[0]
            except:
                agents_count = "?"

        shutil.move(temp_path, DATABASE_PATH)

        size_mb = doc.file_size / (1024 * 1024) if doc.file_size else 0

        await status_msg.edit_text(
            f"{em('check', '✅')} <b>База импортирована!</b>\n\n"
            f"📊 <b>Статистика новой базы:</b>\n"
            f"👥 Пользователей: <b>{users_count}</b>\n"
            f"💬 Записей активности: <b>{messages_count}</b>\n"
            f"🛡 Агентов: <b>{agents_count}</b>\n\n"
            f"💾 Размер: <b>{size_mb:.1f} МБ</b>\n"
            f"🗂 Старая база сохранена:\n"
            f"<code>{old_backup}</code>\n\n"
            f"⚠️ <b>Перезапустите бота</b>, чтобы изменения вступили в силу.",
            parse_mode="HTML"
        )

    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        await status_msg.edit_text(
            f"{em('cross', '❌')} <b>Ошибка импорта</b>\n\n"
            f"<code>{e}</code>",
            parse_mode="HTML"
        )

# ================= ОТКАТ =================
@cmd("откат")
async def restore_old_backup_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    if not os.path.exists("backups"):
        return await message.reply("📭 Нет бэкапов.", disable_web_page_preview=True)

    files = sorted(
        [f for f in os.listdir("backups") if f.startswith("bot_") or f.startswith("old_before_")],
        reverse=True
    )

    if not files:
        return await message.reply("📭 Нет бэкапов.", disable_web_page_preview=True)

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        text = f"📋 <b>Бэкапы для отката</b> ({len(files)}):\n\n"
        for i, f in enumerate(files[:15], 1):
            path = os.path.join("backups", f)
            size_kb = os.path.getsize(path) / 1024
            text += f"<b>{i}.</b> <code>{f}</code> — {size_kb:.1f} КБ\n"
        text += f"\n📌 <code>.откат N</code> — восстановить N-й бэкап"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

    num = int(args[1])
    if num < 1 or num > len(files):
        return await message.reply(f"{em('cross', '❌')} Номер от 1 до {len(files)}", parse_mode="HTML", disable_web_page_preview=True)

    src = os.path.join("backups", files[num - 1])

    try:
        os.makedirs("backups", exist_ok=True)
        import shutil
        safety = f"backups/before_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, safety)

        shutil.copy2(src, DATABASE_PATH)

        await message.reply(
            f"{em('check', '✅')} <b>Откат выполнен!</b>\n\n"
            f"📄 Источник: <code>{files[num-1]}</code>\n"
            f"🛡 Текущая база сохранена: <code>{safety}</code>\n\n"
            f"⚠️ <b>Перезапустите бота</b>, чтобы изменения вступили в силу.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)

# ================= АВТО-БЭКАП (09:00 + 21:00 МСК) =================
async def auto_backup_loop():
    while True:
        try:
            now = datetime.now(timezone.utc) + timedelta(hours=3)
            current_hour = now.hour
            current_minute = now.minute

            is_morning = (current_hour == 9 and current_minute < 5)
            is_evening = (current_hour == 21 and current_minute < 5)

            if is_morning or is_evening:
                period = "morning" if is_morning else "evening"
                marker_file = f"backups/.last_sent_{period}_{now.date().isoformat()}"
                os.makedirs("backups", exist_ok=True)

                if not os.path.exists(marker_file):
                    import shutil
                    timestamp = now.strftime("%Y%m%d_%H%M%S")
                    local_backup = f"backups/bot_{timestamp}.db"
                    shutil.copy2(DATABASE_PATH, local_backup)

                    with open(DATABASE_PATH, "rb") as f:
                        data = f.read()
                    size_kb = len(data) / 1024

                    try:
                        emoji_icon = "🌅" if is_morning else "🌆"
                        period_text = "Утренний" if is_morning else "Вечерний"
                        await bot.send_document(
                            OWNER_ID,
                            types.BufferedInputFile(data, filename=f"mos_backup_{timestamp}.db"),
                            caption=(
                                f"{emoji_icon} <b>{period_text} бэкап базы</b>\n\n"
                                f"📅 Дата: <b>{now.strftime('%d.%m.%Y')}</b>\n"
                                f"⏰ Время: <b>{now.strftime('%H:%M')}</b> (МСК)\n"
                                f"📦 Размер: <b>{size_kb:.1f} КБ</b>\n\n"
                                f"<i>Автоматический бэкап</i>"
                            ),
                            parse_mode="HTML"
                        )
                        print(f"✅ {period_text} бэкап отправлен владельцу")
                    except Exception as e:
                        print(f"❌ Не удалось отправить бэкап: {e}")

                    with open(marker_file, "w") as f:
                        f.write(str(now))

                    try:
                        for f_name in os.listdir("backups"):
                            fp = os.path.join("backups", f_name)
                            if os.path.isfile(fp) and (f_name.startswith("bot_") or f_name.startswith("mos_backup_")):
                                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                                if (datetime.now() - mtime).days > 7:
                                    os.remove(fp)
                    except Exception as e:
                        print(f"⚠️ Ошибка очистки бэкапов: {e}")

        except Exception as e:
            print(f"❌ Ошибка в auto_backup_loop: {e}")

        await asyncio.sleep(300)# ================= ОБРАБОТКА ВСЕХ СООБЩЕНИЙ =================
@dp.message()
async def all_messages(message: types.Message):
    if not message.from_user or message.from_user.is_bot:
        return

    # ===== ФИЛЬТР ССЫЛОК =====
    if message.chat.type in ["group", "supergroup"]:
        if is_link_filter_enabled(message.chat.id):
            is_staff = (
                message.from_user.id == OWNER_ID
                or has_agent_rank(message.from_user.id, 1)
                or await is_tg_admin(message.chat.id, message.from_user.id)
            )
            text_to_check = message.text or message.caption or ""
            has_link_in_entities = False
            entities = message.entities or message.caption_entities or []
            for e in entities:
                if e.type in ("url", "text_link"):
                    has_link_in_entities = True
                    break

            if not is_staff and (has_link(text_to_check) or has_link_in_entities):
                try:
                    await message.delete()
                except:
                    pass

                try:
                    await bot.ban_chat_member(message.chat.id, message.from_user.id)
                    add_chat_ban(
                        message.chat.id,
                        message.from_user.id,
                        "спам",
                        message.from_user.id,
                        None
                    )
                except Exception as e:
                    print(f"❌ Не удалось забанить: {e}")

                user_id = message.from_user.id

                alert = (
                    f"<b>ССЫЛКИ ЗАПРЕЩЕНЫ В ГРУППЕ</b>\n"
                    f"<code>.бан {user_id}</code>\n"
                    f"<code>спам</code>"
                )

                try:
                    sent = await message.answer(alert, parse_mode="HTML", disable_web_page_preview=True)
                    asyncio.create_task(delete_later(sent, 60))
                except:
                    pass

                try:
                    auto_add_to_antispam_if_needed(user_id)
                except:
                    pass

                return

    # ===== ОБЫЧНАЯ ЛОГИКА =====
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status == "creator":
            current_rank = get_rank(message.chat.id, message.from_user.id)
            if current_rank < 5:
                set_rank(message.chat.id, message.from_user.id, 5, message.from_user.id)
    except:
        pass

    register_user(message.from_user.id, message.from_user.first_name, message.from_user.username or "")

    if is_agent(message.from_user.id) or message.from_user.id == OWNER_ID:
        update_agent_activity(message.from_user.id)

    today = datetime.now().date().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO messages_stats (user_id, chat_id, date, count) VALUES (?, ?, ?, 1) "
            "ON CONFLICT(user_id, chat_id, date) DO UPDATE SET count = count + 1",
            (message.from_user.id, message.chat.id, today)
        )
        conn.commit()

    # РП-команды (реплаи по имени)
    if message.text and not message.text.startswith(('.', '+', '-', '!', '/')):
        txt = message.text.strip()
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT emoji, text FROM rp_commands WHERE chat_id = ? AND name = ?", (message.chat.id, txt))
            rp = c.fetchone()
            if rp:
                emoji, rp_text = rp
                reply_user = f" → {mention(message.reply_to_message.from_user)}" if message.reply_to_message else ""
                await message.reply(f"{emoji} {mention(message.from_user)}{reply_user}: {rp_text}", parse_mode="HTML", disable_web_page_preview=True)
                return
        if get_vip(message.from_user.id):
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT emoji, text FROM global_rp_commands WHERE user_id = ? AND name = ?", (message.from_user.id, txt))
                rp = c.fetchone()
                if rp:
                    emoji, rp_text = rp
                    reply_user = f" → {mention(message.reply_to_message.from_user)}" if message.reply_to_message else ""
                    await message.reply(f"{emoji} {mention(message.from_user)}{reply_user}: {rp_text}", parse_mode="HTML", disable_web_page_preview=True)
                    return

    if is_ignored(message.chat.id, message.from_user.id):
        try:
            await message.delete()
        except:
            pass

# ================= ВХОД В ЧАТ =================
@dp.chat_member()
async def on_join(event: types.ChatMemberUpdated):
    if event.new_chat_member.status != "member":
        return
    user = event.new_chat_member.user
    chat_id = event.chat.id
    chat_title = event.chat.title or "чат"
    if is_antispam_enabled(chat_id) and is_in_antispam(user.id):
        try:
            await bot.ban_chat_member(chat_id, user.id)
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT reason FROM antispam WHERE user_id = ?", (user.id,))
                r = c.fetchone()
                reason_text = r[0] if r and r[0] else "спамер"
            await bot.send_message(
                chat_id,
                f"{em('ban', '🚫')} {mention(user)} в антиспаме\n📝 {reason_text}",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except: pass
        return
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            greeting = get_greeting(chat_id)
            if greeting:
                text = format_greeting(greeting, user, event.chat)
                await bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
            return
    except: return
    try:
        await bot.restrict_chat_member(chat_id=chat_id, user_id=user.id, permissions=types.ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False, can_send_polls=False, can_change_info=False, can_invite_users=False, can_pin_messages=False))
    except: pass
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Я не бот", callback_data=f"captcha_pass:{user.id}:{chat_id}")]])
    try:
        captcha_msg = await bot.send_message(chat_id, f"{em('wave', '👋')} Привет, {mention(user)}!\n\n🤖 Нажми кнопку в течение <b>2 минут</b>.", reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)
        save_captcha(user.id, chat_id, captcha_msg.message_id)
        asyncio.create_task(captcha_timeout(user.id, chat_id))
    except: pass

async def captcha_timeout(user_id, chat_id):
    await asyncio.sleep(120)
    if get_captcha(user_id, chat_id) is not None:
        try:
            await bot.ban_chat_member(chat_id, user_id)
            await bot.unban_chat_member(chat_id, user_id)
        except: pass
        msg_id = get_captcha(user_id, chat_id)
        if msg_id:
            try: await bot.delete_message(chat_id, msg_id)
            except: pass
        remove_captcha(user_id, chat_id)

@dp.callback_query(lambda c: c.data and c.data.startswith("captcha_pass:"))
async def captcha_pass_handler(callback: types.CallbackQuery):
    data = callback.data.split(":")
    target_user_id = int(data[1])
    chat_id = int(data[2])
    if callback.from_user.id != target_user_id:
        return await callback.answer("⛔ Не твоя капча!", show_alert=True)
    if get_captcha(target_user_id, chat_id) is None:
        return await callback.answer("⚠️ Неактивна.", show_alert=True)
    try:
        await bot.restrict_chat_member(chat_id=chat_id, user_id=target_user_id, permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True, can_invite_users=True, can_pin_messages=False, can_change_info=False))
    except Exception as e:
        return await callback.answer(f"{em('cross', '❌')} {e}", show_alert=True)
    remove_captcha(target_user_id, chat_id)
    try: await callback.message.delete()
    except: pass
    user = callback.from_user
    greeting = get_greeting(chat_id)
    if greeting:
        try:
            chat = await bot.get_chat(chat_id)
            await bot.send_message(chat_id, format_greeting(greeting, user, chat), parse_mode="HTML", disable_web_page_preview=True)
        except: pass
    else:
        await bot.send_message(chat_id, f"{em('wave', '👋')} Привет, {mention(user)}!", parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer(f"{em('check', '✅')} Капча пройдена!")

# ================= ЗАЯВКИ НА ВСТУПЛЕНИЕ =================
@dp.chat_join_request()
async def on_join_request(request: types.ChatJoinRequest):
    chat_id = request.chat.id
    user = request.from_user

    if is_antispam_enabled(chat_id) and is_in_antispam(user.id):
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT reason FROM antispam WHERE user_id = ?", (user.id,))
            r = c.fetchone()
            reason = r[0] if r and r[0] else "Автоматическая блокировка спамера"
        try:
            await request.decline()
        except:
            pass
        try:
            await bot.send_message(
                user.id,
                f"🗓 <b>Вы находитесь в базе «MOS-Антиспам»</b>, заявка отклонена.\n\n"
                f"💬 <b>Причина:</b> {reason}\n\n"
                f"💬 Список банов: /my_bans\n"
                f"📖 Поддержка: {SUPPORT_CHAT_LINK}",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except:
            pass
        return

    try:
        await request.approve()
        try:
            chat = await bot.get_chat(chat_id)
            await bot.send_message(
                user.id,
                f"{em('check', '✅')} <b>Ваша заявка в «{chat.title or 'чат'}» одобрена!</b>",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except:
            pass
        return
    except Exception as e:
        print(f"❌ Ошибка авто-одобрения: {e}")

# ================= /MY_BANS =================
@dp.message(Command("my_bans"))
async def my_bans_cmd(message: types.Message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    bans = []
    in_antispam = False

    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT reason, banned_at, until_date, banned_by FROM chat_bans 
            WHERE user_id = ? 
            AND (until_date IS NULL OR until_date > ?)
            ORDER BY banned_at DESC""", (user_id, datetime.now().isoformat()))
        rows = c.fetchall()
        for reason, banned_at, until_date, banned_by in rows:
            until_str = f"до {until_date[:10]}" if until_date else "навсегда"
            bans.append(f"{em('ban', '🚫')} 📝 {reason}\n{em('calendar', '🗓')} {banned_at[:10]} ({until_str})")

    if is_in_antispam(user_id):
        in_antispam = True
        info = get_antispam_info(user_id)
        if info:
            reason, added_by, added_at = info
            bans.append(
                f"☢️ <b>Антиспам MOS</b>\n"
                f"📝 {reason}\n"
                f"{em('calendar', '🗓')} {added_at[:10] if added_at else '—'}"
            )
        else:
            bans.append("☢️ <b>Антиспам MOS</b>")
    else:
        last = get_last_antispam_history(user_id)
        if last and last[0] == "remove":
            action, old_reason, admin_id, created_at = last
            bans.append(
                f"{em('check', '✅')} <b>Не в АС</b>\n"
                f"📝 <i>Прошлый АС:</i> {old_reason}\n"
                f"{em('calendar', '🗓')} <i>Вынесен:</i> {created_at[:10] if created_at else '—'}"
            )

    if not bans:
        return await message.reply(f"{em('check', '✅')} У вас нет банов.", parse_mode="HTML", disable_web_page_preview=True)

    text = "📋 <b>Ваши баны:</b>\n\n" + "\n\n".join(bans)
    if in_antispam:
        text += f"\n\n{em('sos', '🆘')} За разблокировкой: {SUPPORT_CHAT_LINK}"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

# ================= БОТ ДОБАВЛЕН =================
@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    if event.new_chat_member.status not in ["member", "administrator"]:
        return
    chat_id = event.chat.id
    chat_type = event.chat.type
    if is_chat_banned(chat_id):
        try: await bot.leave_chat(chat_id)
        except: pass
        try: await bot.send_message(OWNER_ID, f"{em('ban', '🚫')} Бот добавлен в опасный чат! ID: {chat_id}", parse_mode="HTML", disable_web_page_preview=True)
        except: pass
        return
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.status == "creator":
                set_rank(chat_id, admin.user.id, 5, admin.user.id)
                break
    except: pass
    if chat_type in ["group", "supergroup"]:
        text = (
            f"{em('wave', '👋')} <b>Всем привет!</b>\n\n"
            f"Я <b>{BOT_NAME}</b> — помогу навести порядок.\n\n"
            f"{em('shield', '🛡')} Умею: ловить спам, выдавать варны, капча, статистика.\n\n"
            f"⚙️ Выдайте мне права администратора.\n\n"
            f"{em('sos', '🆘')} {SUPPORT_CHAT_LINK}"
        )
        try: await bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
        except: pass
        try: await bot.send_message(OWNER_ID, f"{em('check', '✅')} Бот добавлен: <b>{event.chat.title or '—'}</b>", parse_mode="HTML", disable_web_page_preview=True)
        except: pass

# ================= BUSINESS =================
@dp.business_connection()
async def on_business_connection(connection: types.BusinessConnection):
    if connection.is_enabled:
        save_business_connection(connection.user.id, connection.id)
        try:
            await bot.send_message(connection.user.id, f"{em('check', '✅')} Бот подключён к Business-аккаунту!\n\nКоманды: +ас / +аигн / -ас / -аигн / .ид / .анкета", parse_mode="HTML", disable_web_page_preview=True)
        except: pass
    else:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM business_connections WHERE user_id = ?", (connection.user.id,))
            conn.commit()

@dp.business_message()
async def on_business_message(message: types.Message):
    text = message.text or message.caption or ""
    sender_id = message.from_user.id
    conn_id = message.business_connection_id
    if not conn_id: return
    owner_id = get_business_owner_by_conn(conn_id)
    if not owner_id: return
    if sender_id != owner_id and sender_id != bot.id: return
    is_privileged = (owner_id == OWNER_ID) or has_agent_rank(owner_id, 1)
    async def rt():
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            return u.id, u.first_name
        return None, None
    if text.startswith(".ид") or text.startswith("/ид"):
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            await bot.send_message(chat_id=message.chat.id, text=f"{em('id', '🆔')} <code>{u.id}</code>\n👤 {u.first_name}", parse_mode="HTML", business_connection_id=conn_id)
        return
    if text.startswith(".анкета") or text.startswith("/анкета"):
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            total, today_count, chat_count, first_msg_date = get_total_stats(u.id)
            await bot.send_message(chat_id=message.chat.id, text=f"👤 <b>{u.first_name}</b>\nID: <code>{u.id}</code>\nВсего: <b>{total}</b>", parse_mode="HTML", business_connection_id=conn_id)
        return
    if not is_privileged: return
    if text.startswith("-аигн"):
        target, name = await rt()
        if target:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM ignore_list WHERE user_id = ?", (target,))
                conn.commit()
            await bot.send_message(chat_id=message.chat.id, text=f"{em('check', '✅')} {name} убран из игнора", business_connection_id=conn_id)
        return
    if text.startswith("-ас"):
        target, name = await rt()
        if target:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM antispam WHERE user_id = ?", (target,))
                c.execute("DELETE FROM ignore_list WHERE user_id = ?", (target,))
                conn.commit()
            await bot.send_message(chat_id=message.chat.id, text=f"{em('check', '✅')} {name} вынесен из базы", business_connection_id=conn_id)
        return
    if text.startswith("+аигн"):
        target, name = await rt()
        if target:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target, "Business", sender_id))
                c.execute("INSERT OR REPLACE INTO ignore_list (user_id, chat_id, reason, added_by) VALUES (?, ?, ?, ?)", (target, message.chat.id, "Business", sender_id))
                conn.commit()
            log_antispam_action(target, "add", "Business", sender_id)
            await bot.send_message(chat_id=message.chat.id, text=f"{em('check', '✅')} {name} в «Антиспам» + игнор", business_connection_id=conn_id)
        return
    if text.startswith("+ас"):
        target, name = await rt()
        if target:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target, "Business", sender_id))
                conn.commit()
            log_antispam_action(target, "add", "Business", sender_id)
            await bot.send_message(chat_id=message.chat.id, text=f"{em('check', '✅')} {name} в «Антиспам»", business_connection_id=conn_id)
        return

# ================= ЗАПУСК =================
async def main():
    init_db()
    print("✅ Бот запущен!")
    asyncio.create_task(auto_unban_loop())
    asyncio.create_task(auto_backup_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
