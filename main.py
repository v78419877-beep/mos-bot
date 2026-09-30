import asyncio
import sqlite3
import random
import string
import os
import re
from datetime import datetime, timedelta
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
DATABASE_PATH = "bot.db"
BOT_NAME = "Mos | Чат-менеджер"
SUPPORT_CHAT_LINK = "https://t.me/mospodd"
SUPPORT_CHANNEL_LINK = "https://t.me/moskanalp"
MODERATION_CHAT_ID = -1004438332613
SUPPORT_CHAT_ID = -1004438332613

BOT_START_TIME = datetime.now()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= ПРЕМИУМ-ЭМОДЗИ =================
EMOJI = {
    "mute": "5239939553720041034",
    "pencil": "5395444784611480792",
    "wave": "5215248074498128418",
    "stats": "5884161133174067365",
    "ban": "5472267631979405211",
    "id": "5014902839575577394",
    "check": "5429501538806548545",
    "ping": "5269563867305879894",
    "cross": "5269666272211148094",
    "calendar": "5413879192267805083",
    "alien": "5267401355567345688",
    "sos": "5238025132177369293",
    "gear": "4904936030232117798",
    "shield": "5251203410396458957",
    "key": "5330115548900501467",
    "user": "5373012449597335010",
    "write": "5197269100878907942",
    "pin": "5291893917673868928",
}

def em(name, fallback="•"):
    eid = EMOJI.get(name)
    if not eid:
        return fallback
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'

def mention(user):
    return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

def mention_by_id(user_id, first_name):
    return f'<a href="tg://user?id={user_id}">{first_name}</a>'

# ================= РАНГИ =================
RANK_NAMES = {
    0: "👤 Участник",
    1: "🛡️ Мл. Модератор",
    2: "🛡️ Ст. Модератор",
    3: "👑 Мл. Админ",
    4: "👑 Ст. Админ",
    5: "⚜️ Владелец"
}

# ================= БАЗА ДАННЫХ =================
def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS agents (user_id INTEGER PRIMARY KEY, added_by INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS antispam (user_id INTEGER PRIMARY KEY, reason TEXT, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS ignore_list (user_id INTEGER, chat_id INTEGER, reason TEXT, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_codes (chat_id INTEGER PRIMARY KEY, code TEXT UNIQUE)")
        c.execute("CREATE TABLE IF NOT EXISTS messages_stats (user_id INTEGER, chat_id INTEGER, date DATE, count INTEGER DEFAULT 1, UNIQUE(user_id, chat_id, date))")
        c.execute("CREATE TABLE IF NOT EXISTS banned_chats (chat_id INTEGER PRIMARY KEY, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS agent_chats (chat_id INTEGER PRIMARY KEY, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER, chat_id INTEGER, rank INTEGER DEFAULT 1, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS bot_promoted (user_id INTEGER, chat_id INTEGER, promoted_by INTEGER, promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS warns (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, reason TEXT, warned_by INTEGER, warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS candies (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS candy_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS agent_activity (user_id INTEGER PRIMARY KEY, last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS greetings (chat_id INTEGER PRIMARY KEY, text TEXT, updated_by INTEGER, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, first_name TEXT, username TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS captcha (user_id INTEGER, chat_id INTEGER, message_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("""CREATE TABLE IF NOT EXISTS greeting_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, admin_id INTEGER, text TEXT,
            status TEXT DEFAULT 'pending', reviewed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS business_connections (
            user_id INTEGER PRIMARY KEY,
            connection_id TEXT,
            connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS chat_bans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, user_id INTEGER, reason TEXT,
            banned_by INTEGER, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            until_date TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS grids (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
            creator_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS grid_chats (
            grid_id INTEGER, chat_id INTEGER, hidden INTEGER DEFAULT 0,
            description TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(grid_id, chat_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS grid_moderators (
            grid_id INTEGER, user_id INTEGER, rank INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(grid_id, user_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS grid_bans (
            grid_id INTEGER, user_id INTEGER, reason TEXT, banned_by INTEGER,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, user_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS grid_mutes (
            grid_id INTEGER, user_id INTEGER, until_date TIMESTAMP,
            muted_by INTEGER, UNIQUE(grid_id, user_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS marriages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, user1_id INTEGER, user2_id INTEGER,
            user1_name TEXT, user2_name TEXT,
            married_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            divorced_at TIMESTAMP, status TEXT DEFAULT 'active',
            in_top INTEGER DEFAULT 0,
            extra_days INTEGER DEFAULT 0,
            UNIQUE(chat_id, user1_id), UNIQUE(chat_id, user2_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS marriage_settings (
            chat_id INTEGER PRIMARY KEY, divorce_mode TEXT DEFAULT 'off',
            divorce_price INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, from_id INTEGER, to_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, name TEXT, text TEXT,
            created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, name))""")
        # Коины
        c.execute("""CREATE TABLE IF NOT EXISTS coins (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_farm TIMESTAMP,
            total_farmed INTEGER DEFAULT 0,
            last_tax TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS coin_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, amount INTEGER,
            reason TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS chat_coins (
            chat_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0)""")
        # Каталог
        c.execute("""CREATE TABLE IF NOT EXISTS catalog (
            chat_id INTEGER PRIMARY KEY,
            title TEXT, description TEXT, link TEXT,
            submitted_by INTEGER, submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            show_moderators INTEGER DEFAULT 0,
            approved_by INTEGER, approved_at TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS catalog_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, submitted_by INTEGER, action TEXT,
            status TEXT DEFAULT 'pending', reviewed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, action))""")
        # Ачивки
        c.execute("""CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE, emoji TEXT DEFAULT '🏅',
            description TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, chat_id INTEGER, achievement_id INTEGER,
            given_by INTEGER, given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, chat_id, achievement_id))""")
        conn.commit()

# ================= РАНГИ =================
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

# ================= ВСПОМОГАТЕЛЬНЫЕ =================
def is_agent(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM agents WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None

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

# ================= ГРАФИКИ =================
def generate_user_activity_chart(user_id, days=30):
    """График активности пользователя ПО ВСЕМ ЧАТАМ"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT date, SUM(count) FROM messages_stats 
            WHERE user_id = ?
            GROUP BY date
            ORDER BY date DESC LIMIT ?
        """, (user_id, days))
        rows = c.fetchall()
    if not rows:
        return None
    rows = rows[::-1]
    today = datetime.now().date()
    date_counts = {}
    for d, cnt in rows:
        date_counts[d] = cnt or 0
    full_dates = []
    full_counts = []
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

def generate_chat_activity_chart(chat_id, days=30):
    """График активности ЧАТА"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT date, SUM(count) FROM messages_stats 
            WHERE chat_id = ? GROUP BY date ORDER BY date DESC LIMIT ?
        """, (chat_id, days))
        rows = c.fetchall()
    if not rows:
        return None
    rows = rows[::-1]
    today = datetime.now().date()
    date_counts = {}
    for d, cnt in rows:
        date_counts[d] = cnt or 0
    full_dates = []
    full_counts = []
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

# ================= АГЕНТЫ =================
def update_agent_activity(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO agent_activity (user_id, last_seen) VALUES (?, CURRENT_TIMESTAMP)", (user_id,))
        conn.commit()

def get_agents_status():
    online, offline = [], []
    now = datetime.now()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM agents")
        agents = c.fetchall()
        for (agent_id,) in agents:
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
        .replace("{rules}", "/правила")
        .replace("{link}", SUPPORT_CHAT_LINK))

# ================= ССЫЛКИ + ОЧЕРЕДЬ =================
def is_link(text):
    if not text:
        return False
    return bool(re.search(r'(https?://[^\s]+|t\.me/[^\s]+)', text))

def add_greeting_to_queue(chat_id, admin_id, text):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO greeting_queue (chat_id, admin_id, text) VALUES (?, ?, ?)", (chat_id, admin_id, text))
        conn.commit()
        return c.lastrowid

def get_greeting_from_queue(qid):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, admin_id, text, status FROM greeting_queue WHERE id = ?", (qid,))
        return c.fetchone()

def update_greeting_status(qid, status, reviewed_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE greeting_queue SET status = ?, reviewed_by = ? WHERE id = ?", (status, reviewed_by, qid))
        conn.commit()

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
        return r[0] if r else None

# ================= СЕТКА =================
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

def get_user_grids(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT g.id, g.name FROM grids g WHERE g.creator_id = ?
            UNION SELECT g.id, g.name FROM grids g JOIN grid_moderators gm ON gm.grid_id = g.id WHERE gm.user_id = ?""", (user_id, user_id))
        return c.fetchall()

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
            c.execute("""INSERT INTO marriages (chat_id, user1_id, user2_id, user1_name, user2_name)
                VALUES (?, ?, ?, ?, ?)""", (chat_id, u1_id, u2_id, u1_name, u2_name))
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
        c.execute("""UPDATE marriages SET status = 'divorced', divorced_at = CURRENT_TIMESTAMP
            WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'""", (chat_id, user_id, user_id))
        conn.commit()

def get_all_marriages(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT user1_id, user1_name, user2_id, user2_name, married_at, extra_days
            FROM marriages WHERE chat_id = ? AND status = 'active' ORDER BY married_at ASC""", (chat_id,))
        return c.fetchall()

def get_marriage_top(chat_id, limit=10):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT user1_id, user1_name, user2_id, user2_name, married_at, extra_days
            FROM marriages WHERE chat_id = ? AND status = 'active' AND in_top = 1
            ORDER BY married_at ASC LIMIT ?""", (chat_id, limit))
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

def set_divorce_mode(chat_id, mode):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO marriage_settings (chat_id) VALUES (?)", (chat_id,))
        c.execute("UPDATE marriage_settings SET divorce_mode = ? WHERE chat_id = ?", (mode, chat_id))
        conn.commit()

def set_divorce_price(chat_id, price):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO marriage_settings (chat_id) VALUES (?)", (chat_id,))
        c.execute("UPDATE marriage_settings SET divorce_price = ? WHERE chat_id = ?", (price, chat_id))
        conn.commit()

def add_to_top(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriages SET in_top = 1 WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?)", (chat_id, user_id, user_id))
        conn.commit()

def remove_from_top(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriages SET in_top = 0 WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?)", (chat_id, user_id, user_id))
        conn.commit()

def reset_all_marriages(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM marriages WHERE chat_id = ?", (chat_id,))
        conn.commit()

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

def update_note_text(chat_id, note_id, text):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE notes SET text = ?, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ? AND id = ?", (text, chat_id, note_id))
        conn.commit()

def update_note_name(chat_id, note_id, name):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("UPDATE notes SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ? AND id = ?", (name, chat_id, note_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

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

def get_catalog_queue(chat_id, action):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM catalog_queue WHERE chat_id = ? AND action = ? AND status = 'pending'", (chat_id, action))
        r = c.fetchone()
        return r[0] if r else None

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
        c.execute("""INSERT OR REPLACE INTO catalog 
            (chat_id, title, description, link, submitted_by, status, show_moderators, approved_by, approved_at)
            VALUES (?, ?, ?, ?, ?, 'approved', ?, ?, CURRENT_TIMESTAMP)""",
            (chat_id, title, description, link, submitted_by, show_moderators, submitted_by))
        conn.commit()

def update_catalog_chat(chat_id, title, description, link):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE catalog SET title = ?, description = ?, link = ? WHERE chat_id = ?", (title, description, link, chat_id))
        conn.commit()

def remove_catalog_chat(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM catalog WHERE chat_id = ?", (chat_id,))
        conn.commit()

def get_catalog_list(limit=100):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, title, description, link FROM catalog WHERE status = 'approved' ORDER BY approved_at DESC LIMIT ?", (limit,))
        return c.fetchall()

def set_catalog_moderators(chat_id, show):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE catalog SET show_moderators = ? WHERE chat_id = ?", (1 if show else 0, chat_id))
        conn.commit()

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
        c.execute("""SELECT a.id, a.name, a.emoji, a.description, ua.given_at 
            FROM user_achievements ua JOIN achievements a ON a.id = ua.achievement_id 
            WHERE ua.user_id = ? AND ua.chat_id = ? ORDER BY ua.given_at DESC""", (user_id, chat_id))
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
                        await bot.send_message(chat_id, f"♻️ {mention_by_id(user_id, 'Пользователь')} разбанен (срок истёк).", parse_mode="HTML")
                    except:
                        pass
                except:
                    pass
        except Exception as e:
            print(f"Ошибка в auto_unban_loop: {e}")
        await asyncio.sleep(300) # ================= ОБЩИЕ КОМАНДЫ =================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.reply(
        f"{em('wave', '👋')} Привет, {mention(message.from_user)}!\n\n"
        f"🤖 Я бот <b>{BOT_NAME}</b>\n\n"
        f"{em('sos', '🆘')} Поддержка: {SUPPORT_CHAT_LINK}",
        parse_mode="HTML"
    )

@dp.message(Command("помощь", prefix="."))
@dp.message(Command("помощь"))
async def help_cmd(message: types.Message):
    online, offline = get_agents_status()
    agents_text = ""
    if online:
        agents_text += f"{em('check', '✅')} <b>В сети:</b>\n"
        for uid in online:
            try:
                user = await bot.get_chat(uid)
                if uid == OWNER_ID:
                    agents_text += f"  ⚜️ {mention_by_id(uid, user.first_name)} <i>(владелец)</i>\n"
                else:
                    agents_text += f"  • {mention_by_id(uid, user.first_name)}\n"
            except:
                agents_text += f"  • ID: <code>{uid}</code>\n"
    else:
        agents_text += f"{em('cross', '❌')} <b>В сети:</b> нет\n"
    if offline:
        agents_text += f"\n{em('cross', '❌')} <b>Не в сети:</b>\n"
        for uid in offline:
            try:
                user = await bot.get_chat(uid)
                agents_text += f"  • {mention_by_id(uid, user.first_name)}\n"
            except:
                agents_text += f"  • ID: <code>{uid}</code>\n"
    help_text = (
        f"{em('sos', '🆘')} <b>Помощь по боту {BOT_NAME}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{agents_text}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{em('sos', '🆘')} <b>Техподдержка:</b> <a href=\"{SUPPORT_CHAT_LINK}\">Перейти в чат</a>\n"
        f"📢 <b>Канал:</b> <a href=\"{SUPPORT_CHANNEL_LINK}\">Перейти в канал</a>"
    )
    try:
        me = await bot.get_me()
        bot_username = me.username
    except:
        bot_username = ""
    add_url = f"https://t.me/{bot_username}?startgroup=true&admin=delete_messages+ban_users+invite_users+pin_messages+manage_video_chats+change_info"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить бота в чат", url=add_url)],
        [
            InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_CHAT_LINK),
            InlineKeyboardButton(text="📢 Канал", url=SUPPORT_CHANNEL_LINK)
        ]
    ])
    await message.reply(help_text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard)

@dp.message(Command("пинг", prefix="."))
@dp.message(Command("пинг"))
async def ping_cmd(message: types.Message):
    await message.reply(f"{em('ping', '🏓')} Понг!", parse_mode="HTML")

@dp.message(Command("инфо", prefix="."))
@dp.message(Command("инфо"))
async def info_cmd(message: types.Message):
    chat_id = message.chat.id
    chat_title = message.chat.title or "Без названия"
    code = get_chat_code(chat_id)
    link = await get_chat_link(chat_id)
    if link:
        link_text = f'<a href="{link}">Чат-ссылка</a>'
    else:
        link_text = "Ссылка недоступна (дайте боту право «Приглашать по ссылке»)"
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
        parse_mode="HTML"
    )

@dp.message(Command("инфобот", prefix="."))
@dp.message(Command("инфобот"))
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
    await message.reply(text, parse_mode="HTML")

@dp.message(Command("профиль", prefix="."))
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
                return await message.reply(f"{em('cross', '❌')} Пользователь не найден", parse_mode="HTML")
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
        status += f" | {em('shield', '🛡')} Агент"
    rank = get_rank(message.chat.id, target.id)
    rank_name = RANK_NAMES.get(rank, "👤 Участник")
    text = (
        f"{em('user', '👤')} <b>Профиль {mention(target)}</b>\n\n"
        f"{em('id', '🆔')} ID: <code>{target.id}</code>\n"
        f"📛 Имя: {target.first_name}\n"
        f"🏆 Ранг: {rank_name}\n"
        f"{em('stats', '📊')} Сегодня: {today_count}\n"
        f"{em('stats', '📊')} Всего: {all_count}\n"
        f"{em('shield', '🛡')} Статус: {status}"
    )
    # Ачивки
    user_ach = get_user_achievements(target.id, message.chat.id)
    if user_ach:
        ach_text = " ".join([f"{a[2]}{a[1]}" for a in user_ach])
        text += f"\n\n🎖 Ачивки: {ach_text}"
    await message.reply(text, parse_mode="HTML")

@dp.message(Command("анкета", prefix="."))
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
                return await message.reply(f"{em('cross', '❌')} Пользователь не найден", parse_mode="HTML")
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
    now = datetime.now()
    delta = now - first_seen
    days_in_bot = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    if days_in_bot > 0:
        time_in_bot = f"{days_in_bot} д. {hours} ч."
    elif hours > 0:
        time_in_bot = f"{hours} ч. {minutes} мин."
    else:
        time_in_bot = f"{minutes} мин."
    total, today_count, chat_count, first_msg_date = get_total_stats(target.id)
    rank = get_rank(message.chat.id, target.id)
    rank_name = RANK_NAMES.get(rank, "👤 Участник")
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
    reg_date = first_seen.strftime("%d.%m.%Y")
    # Ачивки
    user_ach = get_user_achievements(target.id, message.chat.id)
    achievements_text = " ".join([f"{a[2]}{a[1]}" for a in user_ach]) if user_ach else "—"
    caption = (
        f"{em('user', '👤')} <b>Анкета {mention(target)}</b>\n\n"
        f"{em('id', '🆔')} ID: <code>{target.id}</code>\n"
        f"📛 Имя: {target.first_name}\n"
        f"🏆 Ранг: {rank_name}\n"
        f"{em('calendar', '🗓')} В боте с: <b>{reg_date}</b>\n"
        f"⏳ Время в боте: <b>{time_in_bot}</b>\n\n"
        f"{em('stats', '📊')} Всего сообщений: <b>{total}</b>\n"
        f"{em('stats', '📊')} Сегодня: <b>{today_count}</b>\n"
        f"{em('stats', '📊')} Чатов активно: <b>{chat_count}</b>\n\n"
        f"🎖 Ачивки: {achievements_text}\n"
        f"{em('shield', '🛡')} Статус: {status}"
    )
    chart_buf = None
    try:
        chart_buf = generate_user_activity_chart(target.id, days=30)
    except Exception as e:
        print(f"Ошибка графика: {e}")
    if chart_buf:
        await message.reply_photo(
            photo=types.BufferedInputFile(chart_buf.getvalue(), filename="user_activity.png"),
            caption=caption,
            parse_mode="HTML"
        )
    else:
        await message.reply(caption, parse_mode="HTML")

@dp.message(Command("мойид", prefix="."))
async def myid_cmd(message: types.Message):
    await message.reply(f"{em('id', '🆔')} Ваш ID: <code>{message.from_user.id}</code>", parse_mode="HTML")

@dp.message(Command("кодчата", prefix="."))
async def chat_code_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) >= 2:
        if message.from_user.id != OWNER_ID:
            return await message.reply(f"{em('cross', '❌')} Менять код чата может только владелец бота.", parse_mode="HTML")
        new_code = args[1].strip().upper()
        if len(new_code) < 3 or len(new_code) > 20:
            return await message.reply(f"{em('cross', '❌')} Код должен быть от 3 до 20 символов.", parse_mode="HTML")
        if not re.match(r'^[A-ZА-Я0-9_]+$', new_code):
            return await message.reply(f"{em('cross', '❌')} Только русские, английские буквы, цифры и <code>_</code>.", parse_mode="HTML")
        chat_id = message.chat.id
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT chat_id FROM chat_codes WHERE code = ? AND chat_id != ?", (new_code, chat_id))
            if c.fetchone():
                return await message.reply(f"{em('cross', '❌')} Код <b>{new_code}</b> уже занят.", parse_mode="HTML")
            c.execute("INSERT OR REPLACE INTO chat_codes (chat_id, code) VALUES (?, ?)", (chat_id, new_code))
            conn.commit()
        return await message.reply(f"{em('check', '✅')} Код чата изменён на <code>{new_code}</code>", parse_mode="HTML")
    code = get_chat_code(message.chat.id)
    await message.reply(f"{em('key', '🔑')} Код чата: <code>{code}</code>", parse_mode="HTML")

@dp.message(Command("ид", prefix="."))
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
                            return await message.reply(f"{em('id', '🆔')} ID: <code>{user_id}</code>\n📛 Имя: {r[0]}\n👤 Username: @{r[1] if r[1] else '—'}", parse_mode="HTML")
                    return await message.reply(f"{em('cross', '❌')} Пользователь не найден", parse_mode="HTML")
            elif arg.startswith('@'):
                username = arg[1:]
                try:
                    target = await bot.get_chat(arg)
                except:
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        c = conn.cursor()
                        c.execute("SELECT user_id, first_name FROM users WHERE username = ?", (username,))
                        r = c.fetchone()
                        if r:
                            return await message.reply(f"{em('id', '🆔')} ID: <code>{r[0]}</code>\n📛 Имя: {r[1]}\n👤 Username: @{username}", parse_mode="HTML")
                    return await message.reply(f"{em('cross', '❌')} Пользователь не найден", parse_mode="HTML")
    if not target:
        target = message.from_user
    await message.reply(
        f"{em('id', '🆔')} <b>Информация о пользователе</b>\n\n"
        f"👤 Имя: {mention(target)}\n"
        f"🆔 ID: <code>{target.id}</code>\n"
        f"📛 First name: {target.first_name}\n"
        f"👤 Username: @{target.username if target.username else '—'}",
        parse_mode="HTML"
    )

@dp.message(Command("чатид", prefix="."))
async def get_chat_id_cmd(message: types.Message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        fwd = message.reply_to_message.forward_from_chat
        chat_type_ru = {"private": "личный", "group": "группа", "supergroup": "супергруппа", "channel": "канал"}.get(fwd.type, fwd.type)
        return await message.reply(
            f"{em('id', '🆔')} <b>ID пересланного чата</b>\n\n"
            f"📛 Название: <b>{fwd.title or 'Без названия'}</b>\n"
            f"🆔 ID: <code>{fwd.id}</code>\n"
            f"👤 Username: @{fwd.username if fwd.username else '—'}\n"
            f"📁 Тип: {chat_type_ru}",
            parse_mode="HTML"
        )
    chat_type_ru = {"private": "личный", "group": "группа", "supergroup": "супергруппа", "channel": "канал"}.get(message.chat.type, message.chat.type)
    await message.reply(
        f"{em('id', '🆔')} <b>Информация о чате</b>\n\n"
        f"📛 Название: <b>{message.chat.title or 'Личный чат'}</b>\n"
        f"🆔 ID: <code>{message.chat.id}</code>\n"
        f"👤 Username: @{message.chat.username if message.chat.username else '—'}\n"
        f"📁 Тип: {chat_type_ru}",
        parse_mode="HTML"
    )

@dp.message(Command("топ", prefix="."))
async def top_cmd(message: types.Message):
    args = message.text.split()
    period = "today"
    period_name = "за сегодня"
    if len(args) >= 2:
        p = args[1].lower()
        if p in ["неделя", "week", "н"]: period, period_name = "week", "за неделю"
        elif p in ["месяц", "month", "м"]: period, period_name = "month", "за месяц"
        elif p in ["все", "all", "всё"]: period, period_name = "all", "за всё время"
        elif p in ["сегодня", "today", "д"]: period, period_name = "today", "за сегодня"
        else:
            return await message.reply(f"{em('cross', '❌')} Неверный период.", parse_mode="HTML")
    top_users = get_top_users(message.chat.id, period, limit=10)
    if not top_users:
        return await message.reply(f"📭 Нет данных {period_name}.")
    text = f"{em('stats', '📊')} <b>Топ участников {period_name}:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, count) in enumerate(top_users, 1):
        try:
            user = await bot.get_chat(user_id)
            name = mention_by_id(user_id, user.first_name)
        except:
            name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{count}</b> сообщ.\n"
    await message.reply(text, parse_mode="HTML")

# ================= РАНГИ =================
@dp.message(Command("повысить", prefix="."))
async def promote_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if not can_manage(message.chat.id, message.from_user.id, target.id):
        return await message.reply(f"{em('cross', '❌')} Нельзя управлять этим пользователем.", parse_mode="HTML")
    current_rank = get_rank(message.chat.id, target.id)
    if current_rank >= 5:
        return await message.reply("⚠️ Это владелец.")
    new_rank = current_rank + 1
    set_rank(message.chat.id, target.id, new_rank, message.from_user.id)
    await message.reply(f"🏆 {mention(target)} повышен до ранга: {RANK_NAMES[new_rank]}", parse_mode="HTML")

@dp.message(Command("понизить", prefix="."))
async def demote_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if target.id == OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Нельзя понизить владельца бота.", parse_mode="HTML")
    if not can_manage(message.chat.id, message.from_user.id, target.id):
        return await message.reply(f"{em('cross', '❌')} Нельзя управлять этим пользователем.", parse_mode="HTML")
    current_rank = get_rank(message.chat.id, target.id)
    if current_rank == 0:
        return await message.reply("⚠️ Этот пользователь и так участник.")
    new_rank = current_rank - 1
    if new_rank == 0:
        remove_rank(message.chat.id, target.id)
    else:
        set_rank(message.chat.id, target.id, new_rank, message.from_user.id)
    await message.reply(f"📉 {mention(target)} понижен до ранга: {RANK_NAMES[new_rank]}", parse_mode="HTML")

@dp.message(Command("разжаловать", prefix="."))
@dp.message(Command("снять", prefix="."))
async def demote_all_cmd(message: types.Message):
    actor_id = message.from_user.id
    actor_rank = get_rank(message.chat.id, actor_id)
    if actor_id != OWNER_ID and actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if target.id == OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Нельзя разжаловать владельца бота.", parse_mode="HTML")
    target_rank = get_rank(message.chat.id, target.id)
    if target_rank == 0:
        return await message.reply(f"⚠️ {mention(target)} и так не имеет прав.", parse_mode="HTML")
    if target_rank == 5 and actor_id != OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Нельзя разжаловать владельца чата.", parse_mode="HTML")
    if actor_id != OWNER_ID and target_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя разжаловать того, у кого ранг выше.", parse_mode="HTML")
    remove_rank(message.chat.id, target.id)
    await message.reply(f"{em('cross', '❌')} {mention(target)} разжалован в обычного участника.", parse_mode="HTML")

@dp.message(Command("админы", prefix="."))
async def list_admins_cmd(message: types.Message):
    admins = get_all_admins(message.chat.id)
    if not admins:
        return await message.reply("📭 Нет админов в этом чате.")
    text = "🏆 <b>Админы чата:</b>\n\n"
    for user_id, rank in admins:
        try:
            user = await bot.get_chat(user_id)
            name = mention_by_id(user_id, user.first_name)
        except:
            name = f"ID: {user_id}"
        agent_badge = f" {em('shield', '🛡')}" if is_agent(user_id) else ""
        text += f"{RANK_NAMES.get(rank, '👤 Участник')} — {name}{agent_badge}\n"
    text += f"\n⚜️ Владелец бота: <code>{OWNER_ID}</code>"
    await message.reply(text, parse_mode="HTML")

@dp.message(Command("восстановить", prefix="."))
async def restore_creator_cmd(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status != "creator":
            return await message.reply(f"{em('cross', '❌')} Только создатель группы.", parse_mode="HTML")
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")
    current_rank = get_rank(chat_id, user_id)
    if current_rank == 5:
        return await message.reply(f"ℹ️ Вы уже владелец.", parse_mode="HTML")
    set_rank(chat_id, user_id, 5, user_id)
    await message.reply(f"{em('check', '✅')} Вы восстановлены как ⚜️ <b>Владелец чата</b>!", parse_mode="HTML")

@dp.message(Command("админ", prefix="+"))
async def grant_admin_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return await message.reply(f"{em('cross', '❌')} Я не админ.", parse_mode="HTML")
        if bot_member.status == 'administrator' and not bot_member.can_promote_members:
            return await message.reply(f"{em('cross', '❌')} Нет права добавлять админов.", parse_mode="HTML")
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if target.id == OWNER_ID:
        return await message.reply("⛔ Владелец бота и так имеет все права.")
    target_rank = get_rank(message.chat.id, target.id)
    if target_rank < 1:
        return await message.reply("⚠️ У пользователя нет ранга в боте.", parse_mode="HTML")
    try:
        await bot.promote_chat_member(
            chat_id=message.chat.id, user_id=target.id,
            can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_promote_members=True, can_change_info=True,
            can_invite_users=True, can_pin_messages=True
        )
        mark_bot_promoted(target.id, message.chat.id, message.from_user.id)
        await message.reply(f"{em('check', '✅')} {mention(target)} теперь админ Telegram!", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

# ================= МОДЕРАЦИЯ =================
@dp.message(Command("бан", prefix="."))
async def ban_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    args = message.text.split()
    duration_seconds = None
    duration_text = "навсегда"
    if len(args) >= 3 and args[1].isdigit():
        amount = int(args[1])
        unit = args[2].lower().rstrip('.,!?')
        if amount > 0:
            if unit in ['сек', 'сек.', 'секунд', 's', 'sec']:
                duration_seconds = amount; duration_text = f"{amount} сек."
            elif unit in ['мин', 'мин.', 'минут', 'м', 'm']:
                duration_seconds = amount * 60; duration_text = f"{amount} мин."
            elif unit in ['час', 'часа', 'часов', 'ч', 'h']:
                duration_seconds = amount * 3600; duration_text = f"{amount} ч."
            elif unit in ['день', 'дня', 'дней', 'д', 'd']:
                duration_seconds = amount * 86400; duration_text = f"{amount} дн."
            elif unit in ['неделя', 'недели', 'недель', 'нед', 'н', 'w']:
                duration_seconds = amount * 604800; duration_text = f"{amount} нед."
            elif unit in ['месяц', 'месяца', 'месяцев', 'мес']:
                duration_seconds = amount * 30 * 86400; duration_text = f"{amount} мес."
            elif unit in ['год', 'года', 'лет', 'г', 'y']:
                duration_seconds = amount * 365 * 86400; duration_text = f"{amount} г."
    if duration_seconds and duration_seconds > 366 * 86400:
        return await message.reply(f"{em('cross', '❌')} Максимум 366 дней.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID:
            return await message.reply(f"{em('cross', '❌')} Нельзя банить того, у кого ранг выше.", parse_mode="HTML")
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
        await message.reply(
            f"{em('ban', '🚫')} {mention(target)} получает бан {ban_type}\n"
            f"👮 Модератор: {mention(message.from_user)}\n"
            f"📝 Причина: {reason}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

@dp.message(Command("разбан", prefix="."))
async def unban_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    try:
        await bot.unban_chat_member(message.chat.id, target.id)
        clear_chat_ban(message.chat.id, target.id)
        await message.reply(f"{em('check', '✅')} {mention(target)} разбанен", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

@dp.message(Command("мут", prefix="."))
async def mute_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    args = message.text.split()
    duration_seconds = 1800
    duration_text = "30 мин."
    if len(args) >= 3 and args[1].isdigit():
        amount = int(args[1])
        unit = args[2].lower().rstrip('.,!?')
        if amount > 0:
            if unit in ['сек', 'сек.', 'секунд', 's', 'sec']:
                duration_seconds = amount; duration_text = f"{amount} сек."
            elif unit in ['мин', 'мин.', 'минут', 'м', 'm']:
                duration_seconds = amount * 60; duration_text = f"{amount} мин."
            elif unit in ['час', 'часа', 'часов', 'ч', 'h']:
                duration_seconds = amount * 3600; duration_text = f"{amount} ч."
            elif unit in ['день', 'дня', 'дней', 'д', 'd']:
                duration_seconds = amount * 86400; duration_text = f"{amount} дн."
            elif unit in ['неделя', 'недели', 'недель', 'нед', 'н', 'w']:
                duration_seconds = amount * 604800; duration_text = f"{amount} нед."
    if duration_seconds > 366 * 86400:
        return await message.reply(f"{em('cross', '❌')} Максимум 366 дней.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID:
            return await message.reply(f"{em('cross', '❌')} Нельзя мутить того, у кого ранг выше.", parse_mode="HTML")
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
            f"👮 Модератор: {mention(message.from_user)}\n"
            f"📝 Причина: {reason}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

@dp.message(Command("размут", prefix="."))
async def unmute_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    try:
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        )
        await message.reply(f"🔈 {mention(target)} размучен", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

@dp.message(Command("кик", prefix="."))
async def kick_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID:
            return await message.reply(f"{em('cross', '❌')} Нельзя кикнуть того, у кого ранг выше.", parse_mode="HTML")
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"👢 {mention(target)} кикнут", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

@dp.message(Command("смс", prefix="-"))
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

# ================= ВАРНЫ =================
@dp.message(Command("варн", prefix="."))
async def warn_cmd(message: types.Message):
    actor_id = message.from_user.id
    actor_rank = get_rank(message.chat.id, actor_id)
    if actor_rank < 1:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    target_rank = get_rank(message.chat.id, target.id)
    target_is_tg_admin = await is_tg_admin(message.chat.id, target.id)
    if actor_rank == 5:
        pass
    elif actor_rank == 4:
        if target_rank >= 4:
            return await message.reply(f"{em('cross', '❌')} Нельзя варнить того, у кого ранг выше.", parse_mode="HTML")
    else:
        if target_rank >= actor_rank:
            return await message.reply(f"{em('cross', '❌')} Нельзя варнить того, у кого ранг выше.", parse_mode="HTML")
        if target_is_tg_admin:
            return await message.reply("⛔ Нельзя варнить ТГ-админа.", parse_mode="HTML")
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
            result_text += f"{em('mute', '🔇')} Мут на 1 час.\n📝 Причина: {reason}\n♻️ Варны сброшены."
            await message.reply(result_text, parse_mode="HTML")
            return
        except Exception as e:
            await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")
            return
    await message.reply(
        f"{em('pencil', '✏️')} {mention(target)} получил предупреждение!\n"
        f"📝 Причина: {reason}\n"
        f"{em('stats', '📊')} Всего варнов: {warns_count}/3",
        parse_mode="HTML"
    )

@dp.message(Command("варны", prefix="."))
async def warns_list_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    warns = get_warns(target.id, message.chat.id)
    if not warns:
        return await message.reply(f"{em('check', '✅')} У {mention(target)} нет варнов.", parse_mode="HTML")
    text = f"{em('pencil', '✏️')} <b>Варны {mention(target)}:</b> ({len(warns)}/3)\n\n"
    for i, (warn_id, reason, warned_at) in enumerate(warns, 1):
        text += f"{i}. {reason}\n   {em('calendar', '🗓')} {warned_at[:10]}\n"
    await message.reply(text, parse_mode="HTML")

@dp.message(Command("снятьварн", prefix="."))
async def unwarn_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    warns = get_warns(target.id, message.chat.id)
    if not warns:
        return await message.reply(f"{em('check', '✅')} У {mention(target)} нет варнов.", parse_mode="HTML")
    remove_last_warn(target.id, message.chat.id)
    new_count = count_warns(target.id, message.chat.id)
    await message.reply(f"{em('check', '✅')} С {mention(target)} снят последний варн.\nОсталось: {new_count}/3", parse_mode="HTML")

@dp.message(Command("сбросварнов", prefix="."))
async def clear_warns_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    count = count_warns(target.id, message.chat.id)
    if count == 0:
        return await message.reply(f"{em('check', '✅')} У {mention(target)} нет варнов.", parse_mode="HTML")
    clear_warns(target.id, message.chat.id)
    await message.reply(f"♻️ Все варны ({count}) с {mention(target)} сброшены.", parse_mode="HTML")

# ================= НАКАЗАНИЯ =================
@dp.message(Command("наказания", prefix="."))
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
                if args[1].startswith('@'):
                    target = await bot.get_chat(args[1])
                elif args[1].isdigit():
                    target = await bot.get_chat(int(args[1]))
            except:
                return await message.reply(f"{em('cross', '❌')} Пользователь не найден", parse_mode="HTML")
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
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
                    mod_name = mention_by_id(banned_by, mod.first_name)
                except:
                    mod_name = f"ID {banned_by}"
                blocks.append(f"{em('ban', '🚫')} <b>Забанен в этом чате</b>\n📝 Причина: {reason}\n👮 Модератор: {mod_name}")
            else:
                blocks.append(f"{em('ban', '🚫')} <b>Забанен в этом чате</b>\n📝 Причина: <i>неизвестна</i>")
    except:
        pass
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
                    mod_name = mention_by_id(banned_by, mod.first_name)
                except:
                    mod_name = f"ID {banned_by}"
                blocks.append(f"{em('ban', '🚫')} <b>Забанен в сетке чатов</b>\n📝 Причина: {reason}\n👮 Модератор: {mod_name}")
    if is_in_antispam(user_id):
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT reason FROM antispam WHERE user_id = ?", (user_id,))
            r = c.fetchone()
            if r:
                blocks.append(f"{em('shield', '🛡')} <b>В антиспаме MOS</b>\n📝 Причина: {r[0]}")
    if not blocks:
        return await message.reply(f"{em('check', '✅')} {name} <b>чист</b> — нет наказаний.", parse_mode="HTML")
    text = f"{em('calendar', '🗓')} <b>Список наказаний {name}</b>\n\n" + "\n\n".join(blocks)
    await message.reply(text, parse_mode="HTML")

@dp.message(Command("баны", prefix="."))
async def show_bans(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if not is_in_antispam(target.id):
        return await message.reply(f"{em('check', '✅')} {mention(target)} чист", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT reason, added_at FROM antispam WHERE user_id = ?", (target.id,))
        r = c.fetchone()
    await message.reply(f"{em('ban', '🚫')} {mention(target)} в антиспаме\n📝 Причина: {r[0]}\n{em('calendar', '🗓')} {r[1][:10]}", parse_mode="HTML")

# ================= АЧИВКИ =================
@dp.message(lambda m: m.text and m.text.lower().startswith("+ачивка создать"))
async def create_achievement_cmd(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    parts = message.text.split(maxsplit=4)
    if len(parts) < 4:
        return await message.reply(f"📌 <code>+Ачивка создать Название 🏅 Описание</code>", parse_mode="HTML")
    name = parts[2]
    emoji = parts[3] if len(parts) >= 4 else "🏅"
    description = parts[4] if len(parts) >= 5 else ""
    aid = create_achievement(name, emoji, description)
    if not aid:
        return await message.reply(f"{em('cross', '❌')} Ачивка уже есть.", parse_mode="HTML")
    await message.reply(f"✅ Ачивка создана!\n{emoji} <b>{name}</b>\n📝 {description or 'Без описания'}", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("+ачивка"))
async def add_achievement_cmd(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    parts = message.text.split("\n", 1)
    first_line = parts[0].strip()
    args = first_line.split()
    target = None
    achievement_name = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        if len(args) >= 2:
            achievement_name = " ".join(args[1:])
    else:
        if len(args) >= 3:
            try:
                target = await bot.get_chat(args[1])
                achievement_name = " ".join(args[2:])
            except:
                return await message.reply(f"{em('cross', '❌')} Пользователь не найден.", parse_mode="HTML")
    if not target or not achievement_name:
        return await message.reply(f"📌 <code>+Ачивка @user Название</code> или ответом: <code>+Ачивка Название</code>", parse_mode="HTML")
    ach = get_achievement_by_name(achievement_name)
    if not ach:
        return await message.reply(f"{em('cross', '❌')} Ачивка не найдена.", parse_mode="HTML")
    aid, name, emoji, desc = ach
    ok = give_achievement(target.id, message.chat.id, aid, message.from_user.id)
    if not ok:
        return await message.reply(f"⚠️ У {mention(target)} уже есть эта ачивка.", parse_mode="HTML")
    await message.reply(f"🎖 {mention(target)} получил ачивку {emoji} <b>{name}</b>!\n👮 Выдал: {mention(message.from_user)}", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("-ачивка удалить"))
async def delete_achievement_cmd(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        return await message.reply("📌 <code>-Ачивка удалить Название</code>", parse_mode="HTML")
    name = " ".join(args[2:])
    ach = get_achievement_by_name(name)
    if not ach:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML")
    delete_achievement(ach[0])
    await message.reply(f"🗑 Ачивка <b>{ach[1]}</b> удалена.", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("-ачивка"))
async def remove_achievement_cmd(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    parts = message.text.split("\n", 1)
    first_line = parts[0].strip()
    args = first_line.split()
    target = None
    achievement_name = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        if len(args) >= 2:
            achievement_name = " ".join(args[1:])
    else:
        if len(args) >= 3:
            try:
                target = await bot.get_chat(args[1])
                achievement_name = " ".join(args[2:])
            except:
                return await message.reply(f"{em('cross', '❌')} Пользователь не найден.", parse_mode="HTML")
    if not target or not achievement_name:
        return await message.reply(f"📌 <code>-Ачивка @user Название</code>", parse_mode="HTML")
    ach = get_achievement_by_name(achievement_name)
    if not ach:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML")
    remove_achievement(target.id, message.chat.id, ach[0])
    await message.reply(f"❌ С {mention(target)} снята ачивка {ach[2]} <b>{ach[1]}</b>.", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().strip() in ["ачивки", "все ачивки"])
async def list_achievements_cmd(message: types.Message):
    all_ach = get_all_achievements()
    if not all_ach:
        return await message.reply("📭 Пока нет ачивок.", parse_mode="HTML")
    text = "🎖 <b>Список всех ачивок:</b>\n\n"
    for aid, name, emoji, desc in all_ach:
        text += f"{emoji} <b>{name}</b>"
        if desc:
            text += f" — <i>{desc}</i>"
        text += f"\n   <code>ID: {aid}</code>\n"
    await message.reply(text, parse_mode="HTML") # ================= ПИН =================
@dp.message(Command("пин", prefix="."))
async def pin_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    if not message.reply_to_message:
        return await message.reply(f"{em('cross', '❌')} Ответьте на сообщение.", parse_mode="HTML")
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return await message.reply(f"{em('cross', '❌')} Я не админ.", parse_mode="HTML")
        if bot_member.status == 'administrator' and not bot_member.can_pin_messages:
            return await message.reply(f"{em('cross', '❌')} Нет права закреплять.", parse_mode="HTML")
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")
    args = message.text.split()
    notify = len(args) >= 2 and args[1].lower() in ["уведомить", "notify", "всех", "всем"]
    try:
        await bot.pin_chat_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id, disable_notification=not notify)
        await message.reply(f"{em('pin', '📌')} Сообщение закреплено!", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

@dp.message(Command("открепить", prefix="."))
@dp.message(Command("анпин", prefix="."))
async def unpin_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    try:
        await bot.unpin_chat_message(chat_id=message.chat.id)
        await message.reply(f"{em('pin', '📌')} Сообщение откреплено!", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

# ================= ЗАКРЫТИЕ / ОТКРЫТИЕ ЧАТА =================
@dp.message(Command("чат", prefix="-"))
async def close_chat_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 4 and message.from_user.id != OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Нужен ранг Ст. Админ (4) или Владелец бота.", parse_mode="HTML")
    try:
        await bot.set_chat_permissions(
            chat_id=message.chat.id,
            permissions=types.ChatPermissions(
                can_send_messages=False, can_send_media_messages=False,
                can_send_other_messages=False, can_add_web_page_previews=False,
                can_send_polls=False, can_invite_users=True,
                can_change_info=False, can_pin_messages=False
            )
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔓 Открыть чат", callback_data=f"open_chat:{message.chat.id}")]])
        await message.reply(
            f"{em('mute', '🔇')} <b>Чат закрыт</b>\n👮 Закрыл: {mention(message.from_user)}",
            reply_markup=keyboard, parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

@dp.callback_query(lambda c: c.data and c.data.startswith("open_chat:"))
async def open_chat_callback(callback: types.CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    user_rank = get_rank(chat_id, user_id)
    if user_rank < 4 and user_id != OWNER_ID:
        return await callback.answer("⛔ Только Ст. Админ (4) или Владелец.", show_alert=True)
    try:
        await bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=types.ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_send_polls=True, can_invite_users=True,
                can_change_info=False, can_pin_messages=False
            )
        )
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        await callback.message.reply(f"✅ <b>Чат открыт</b>\n👮 Открыл: {mention(callback.from_user)}", parse_mode="HTML")
        await callback.answer("✅ Чат открыт!")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@dp.message(Command("чат", prefix="+"))
async def open_chat_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 4 and message.from_user.id != OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Нужен ранг Ст. Админ (4) или Владелец бота.", parse_mode="HTML")
    try:
        await bot.set_chat_permissions(
            chat_id=message.chat.id,
            permissions=types.ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_send_polls=True, can_invite_users=True,
                can_change_info=False, can_pin_messages=False
            )
        )
        await message.reply(f"✅ <b>Чат открыт</b>", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")

# ================= ПРИВЕТСТВИЕ (с премиум-эмодзи) =================
@dp.message(Command("приветствие", prefix="."))
async def greeting_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = get_greeting(message.chat.id)
        if current:
            preview = format_greeting(current, message.from_user, message.chat)
            return await message.reply(f"{em('wave', '👋')} <b>Текущее приветствие:</b>\n\n<code>{current}</code>\n\n📝 Предпросмотр:\n{preview}", parse_mode="HTML")
        else:
            return await message.reply(
                f"{em('wave', '👋')} Приветствие не установлено.\n\n"
                f"<b>Переменные:</b>\n• <code>{{name}}</code>\n• <code>{{first_name}}</code>\n• <code>{{chat}}</code>\n• <code>{{rules}}</code>\n• <code>{{link}}</code>\n\n"
                f"<i>Установить: <code>.приветствие текст</code> (ранг 3+)</i>",
                parse_mode="HTML"
            )
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    # Собираем текст с учётом премиум-эмодзи
    raw_text = message.text
    prefix = args[0]
    body = raw_text[len(prefix):].lstrip()
    offset_shift = raw_text.index(body) if body else 0
    result = ""
    last_pos = 0
    entities = sorted(message.entities or [], key=lambda e: e.offset)
    for entity in entities:
        if entity.offset < offset_shift:
            continue
        start = entity.offset - offset_shift
        end = start + entity.length
        if start < 0 or end > len(body):
            continue
        result += body[last_pos:start]
        entity_text = body[start:end]
        if entity.type == "custom_emoji":
            result += f'<tg-emoji emoji-id="{entity.custom_emoji_id}">{entity_text}</tg-emoji>'
        elif entity.type == "bold":
            result += f"<b>{entity_text}</b>"
        elif entity.type == "italic":
            result += f"<i>{entity_text}</i>"
        elif entity.type == "underline":
            result += f"<u>{entity_text}</u>"
        elif entity.type == "strikethrough":
            result += f"<s>{entity_text}</s>"
        elif entity.type == "code":
            result += f"<code>{entity_text}</code>"
        elif entity.type == "pre":
            result += f"<pre>{entity_text}</pre>"
        elif entity.type == "text_link":
            result += f'<a href="{entity.url}">{entity_text}</a>'
        elif entity.type == "blockquote":
            result += f"<blockquote>{entity_text}</blockquote>"
        elif entity.type == "spoiler":
            result += f"<tg-spoiler>{entity_text}</tg-spoiler>"
        else:
            result += entity_text
        last_pos = end
    result += body[last_pos:]
    text = result.strip()
    if text.lower() in ["сброс", "reset", "удалить", "стоп"]:
        reset_greeting(message.chat.id)
        return await message.reply(f"{em('check', '✅')} Приветствие сброшено.", parse_mode="HTML")
    if len(text) > 1000:
        return await message.reply(f"{em('cross', '❌')} Слишком длинное (макс. 1000).", parse_mode="HTML")
    if is_link(text):
        queue_id = add_greeting_to_queue(message.chat.id, message.from_user.id, text)
        chat_title = message.chat.title or f"Чат {message.chat.id}"
        mod_text = (
            f"🔗 <b>Приветствие на проверку</b>\n\n"
            f"📍 Чат: <b>{chat_title}</b>\n"
            f"🆔 ID чата: <code>{message.chat.id}</code>\n"
            f"👤 Автор: {mention(message.from_user)}\n\n"
            f"📝 <b>Текст:</b>\n{text}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"greet_approve:{queue_id}"),
            InlineKeyboardButton(text="❌ Не одобрять", callback_data=f"greet_reject:{queue_id}")
        ]])
        try:
            await bot.send_message(MODERATION_CHAT_ID, mod_text, reply_markup=keyboard, parse_mode="HTML")
            await message.reply(f"⏳ Отправлено на проверку.", parse_mode="HTML")
        except Exception as e:
            await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")
        return
    set_greeting(message.chat.id, text, message.from_user.id)
    preview = format_greeting(text, message.from_user, message.chat)
    await message.reply(f"{em('check', '✅')} <b>Приветствие установлено!</b>\n\n📝 Предпросмотр:\n{preview}", parse_mode="HTML")

@dp.callback_query(lambda c: c.data and (c.data.startswith("greet_approve:") or c.data.startswith("greet_reject:")))
async def greeting_review_handler(callback: types.CallbackQuery):
    if not is_agent(callback.from_user.id) and callback.from_user.id != OWNER_ID:
        return await callback.answer("⛔ Только агенты.", show_alert=True)
    action, qid_str = callback.data.split(":")
    qid = int(qid_str)
    row = get_greeting_from_queue(qid)
    if not row:
        return await callback.answer("⚠️ Уже обработано.", show_alert=True)
    chat_id, admin_id, text, status = row
    if status != "pending":
        return await callback.answer("⚠️ Уже обработано.", show_alert=True)
    reviewer = mention(callback.from_user)
    if action == "greet_approve":
        set_greeting(chat_id, text, admin_id)
        update_greeting_status(qid, "approved", callback.from_user.id)
        try:
            await bot.send_message(admin_id, f"✅ Приветствие одобрено {reviewer}.", parse_mode="HTML")
        except:
            pass
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.reply(f"✅ Одобрено {reviewer}")
        except:
            pass
        await callback.answer("✅ Одобрено!")
    else:
        update_greeting_status(qid, "rejected", callback.from_user.id)
        try:
            await bot.send_message(admin_id, f"❌ Приветствие отклонено {reviewer}.", parse_mode="HTML")
        except:
            pass
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.reply(f"❌ Отклонено {reviewer}")
        except:
            pass
        await callback.answer("❌ Отклонено!")

# ================= КОНФЕТКИ =================
@dp.message(Command("пополнить", prefix="."))
async def add_candies_cmd(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Только агенты.")
    args = message.text.split()
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        amount_arg = args[1] if len(args) >= 2 else None
    else:
        if len(args) < 3:
            return await message.reply("❌ <code>.пополнить @user 10</code>", parse_mode="HTML")
        try:
            if args[1].startswith('@'):
                target = await bot.get_chat(args[1])
            elif args[1].isdigit():
                target = await bot.get_chat(int(args[1]))
        except:
            return await message.reply("❌ Пользователь не найден", parse_mode="HTML")
        amount_arg = args[2]
    if not target:
        return await message.reply("❌ Не удалось определить пользователя.", parse_mode="HTML")
    try:
        amount = int(amount_arg)
        if amount <= 0 or amount > 100000:
            return await message.reply("❌ Некорректное количество.", parse_mode="HTML")
    except:
        return await message.reply("❌ Некорректное количество.", parse_mode="HTML")
    add_candies(target.id, amount, message.from_user.id)
    new_balance = get_balance(target.id)
    await message.reply(f"🍬 {mention(target)} получил <b>{amount}</b>!\n💰 Баланс: <b>{new_balance}</b>", parse_mode="HTML")
    try:
        await bot.send_message(target.id, f"🎁 Вам пополнили мешок на <b>{amount}</b>!\n💰 Баланс: <b>{new_balance}</b> 🍬", parse_mode="HTML")
    except:
        pass

@dp.message(Command("мешок", prefix="."))
async def my_candies_cmd(message: types.Message):
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
                return await message.reply("❌ Пользователь не найден", parse_mode="HTML")
        else:
            target = message.from_user
    balance = get_balance(target.id)
    coins_balance = get_coins(target.id)
    text = (
        f"🎒 <b>Мешок {mention(target)}</b>\n\n"
        f"🍬 Ириски: <b>{balance}</b>\n"
        f"☢️ Mos-коины: <b>{coins_balance}</b> i¢"
    )
    await message.reply(text, parse_mode="HTML")

@dp.message(Command("мешки", prefix="."))
async def top_candies_cmd(message: types.Message):
    top = get_top_candies(limit=10)
    if not top:
        return await message.reply("📭 Пока ни у кого нет конфеток.")
    text = "🏆 <b>Топ мешков:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, balance) in enumerate(top, 1):
        try:
            user = await bot.get_chat(user_id)
            name = mention_by_id(user_id, user.first_name)
        except:
            name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{balance}</b> 🍬\n"
    await message.reply(text, parse_mode="HTML")

# ================= КОМАНДЫ КОИНОВ =================
@dp.message(Command("коины", prefix="."))
@dp.message(Command("баланс", prefix="."))
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
                text += f"\n⛏ Ферма доступна через: <b>{minutes_left} мин.</b>"
            else:
                reward, _ = get_farm_reward(user_id)
                text += f"\n⛏ Ферма готова! Награда: <b>{reward} i¢</b>"
        except:
            text += f"\n⛏ Ферма готова!"
    else:
        text += f"\n⛏ Ферма доступна! Используйте <code>Ферма</code>"
    text += f"\n\n💱 Обмен: <code>Купить коины 10</code> (1 🍬 = 100 i¢)"
    text += f"\n💸 Взнос в счёт чата: <code>Бкоин 100</code>"
    text += f"\n\n📊 Налог: 1% раз в 2 дня"
    await message.reply(text, parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().strip() == "ферма")
async def farm_cmd(message: types.Message):
    user_id = message.from_user.id
    apply_tax(user_id)
    reward, wait_minutes = get_farm_reward(user_id)
    if reward == 0:
        return await message.reply(f"⏳ Ферма не готова. Подожди ещё <b>{wait_minutes} мин.</b>", parse_mode="HTML")
    info = get_coins_info(user_id)
    total_farmed = (info[2] or 0) + reward
    add_coins(user_id, reward, "ферма")
    update_farm_time(user_id, total_farmed)
    await message.reply(f"⛏ <b>Урожай собран!</b>\n💰 Получено: <b>+{reward} i¢</b>\n📈 Всего: <b>{total_farmed} i¢</b>", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("купить коины"))
async def buy_coins_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 3 or not args[-1].isdigit():
        return await message.reply("📌 <code>Купить коины 10</code> → 1000 i¢", parse_mode="HTML")
    candies_amount = int(args[-1])
    if candies_amount <= 0:
        return await message.reply("❌ Число должно быть больше нуля.", parse_mode="HTML")
    user_id = message.from_user.id
    balance = get_balance(user_id)
    if balance < candies_amount:
        return await message.reply(f"❌ Недостаточно ирисок. Нужно: <b>{candies_amount}</b> 🍬, у тебя: <b>{balance}</b> 🍬", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (candies_amount, user_id))
        conn.commit()
    coins_amount = candies_amount * 100
    add_coins(user_id, coins_amount, f"обмен {candies_amount} 🍬")
    new_balance = get_coins(user_id)
    await message.reply(f"💱 Обмен выполнен!\n💸 Списано: <b>{candies_amount}</b> 🍬\n💰 Получено: <b>+{coins_amount}</b> i¢\n📊 Баланс: <b>{new_balance}</b> i¢", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("бкоин"))
async def bkoin_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[-1].isdigit():
        return await message.reply("📌 <code>Бкоин {число}</code> — взнос в счёт чата.", parse_mode="HTML")
    amount = int(args[-1])
    if amount < 1:
        return await message.reply("❌ Число больше нуля.", parse_mode="HTML")
    user_id = message.from_user.id
    balance = get_coins(user_id)
    if balance < amount:
        return await message.reply(f"❌ Недостаточно коинов. Нужно: <b>{amount}</b> i¢, у тебя: <b>{balance}</b> i¢", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE coins SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        c.execute("INSERT INTO coin_log (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, -amount, "взнос в счёт чата"))
        conn.commit()
    add_chat_coins(message.chat.id, amount)
    total = get_chat_coins(message.chat.id)
    text = f"💸 Взнос в счёт чата\n💰 Внесено: <b>{amount}</b> i¢\n🏦 Счёт чата: <b>{total}</b> i¢"
    if total >= 35000:
        text += f"\n\n✅ <b>Можно добавить чат в каталог!</b>\nКоманда: <code>Каталог добавить</code>"
    else:
        text += f"\n\n📊 До каталога: <b>{35000 - total}</b> i¢"
    await message.reply(text, parse_mode="HTML")

@dp.message(Command("коинытоп", prefix="."))
async def coins_top_cmd(message: types.Message):
    top = get_coins_top(limit=10)
    if not top:
        return await message.reply("📭 Пока ни у кого нет коинов.", parse_mode="HTML")
    text = "☢️ <b>Топ по коинам:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, balance) in enumerate(top, 1):
        try:
            user = await bot.get_chat(user_id)
            name = mention_by_id(user_id, user.first_name)
        except:
            name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{balance}</b> i¢\n"
    await message.reply(text, parse_mode="HTML")

# ================= АГЕНТСКИЕ КОМАНДЫ =================
@dp.message(Command("аки", prefix="+"))
async def add_antispam_kick_ignore(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        reason = parts[1].strip()
    kick_status = "👢 Кикнут"
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
    except:
        kick_status = "⚠️ Не удалось кикнуть"
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target.id, reason, message.from_user.id))
        c.execute("INSERT OR REPLACE INTO ignore_list (user_id, chat_id, reason, added_by) VALUES (?, ?, ?, ?)", (target.id, message.chat.id, reason, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} в «Антиспам - MOS»\n{em('mute', '🔇')} В игнор\n{kick_status}\n📝 {reason}", parse_mode="HTML")

@dp.message(Command("аигн", prefix="+"))
async def add_antispam_ignore(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        reason = parts[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target.id, reason, message.from_user.id))
        c.execute("INSERT OR REPLACE INTO ignore_list (user_id, chat_id, reason, added_by) VALUES (?, ?, ?, ?)", (target.id, message.chat.id, reason, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} в «Антиспам - MOS»\n{em('mute', '🔇')} В игнор\n📝 {reason}", parse_mode="HTML")

@dp.message(Command("ак", prefix="+"))
async def add_antispam_kick(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        reason = parts[1].strip()
    kick_status = "👢 Кикнут"
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
    except:
        kick_status = "⚠️ Не удалось кикнуть"
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target.id, reason, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} в «Антиспам - MOS»\n{kick_status}\n📝 {reason}", parse_mode="HTML")

@dp.message(Command("ас", prefix="+"))
async def add_antispam(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        reason = parts[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target.id, reason, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} в «Антиспам - MOS»\n📝 {reason}", parse_mode="HTML")

@dp.message(Command("аигн", prefix="-"))
async def remove_ignore(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if not is_ignored(message.chat.id, target.id):
        return await message.reply(f"⚠️ {mention(target)} не в игноре", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM ignore_list WHERE user_id = ? AND chat_id = ?", (target.id, message.chat.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} убран из игнора", parse_mode="HTML")

@dp.message(Command("ас", prefix="-"))
async def remove_antispam(message: types.Message):
    if not is_agent(message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML")
    if not is_in_antispam(target.id):
        return await message.reply(f"⚠️ {mention(target)} не в антиспаме", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM antispam WHERE user_id = ?", (target.id,))
        c.execute("DELETE FROM ignore_list WHERE user_id = ? AND chat_id = ?", (target.id, message.chat.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} вынесен", parse_mode="HTML")

# ================= ВЛАДЕЛЕЦ =================
@dp.message(Command("опасно", prefix="+"))
async def ban_chat_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    args = message.text.split()
    if len(args) >= 2:
        code = args[1].upper()
        chat_id = get_chat_by_code(code)
        if not chat_id:
            return await message.reply(f"{em('cross', '❌')} Чат не найден", parse_mode="HTML")
        try:
            chat = await bot.get_chat(chat_id)
            chat_name = chat.title or f"Чат {chat_id}"
        except:
            chat_name = f"Чат {chat_id}"
    else:
        chat_id = message.chat.id
        chat_name = message.chat.title or f"Чат {chat_id}"
    if is_chat_banned(chat_id):
        return await message.reply("⚠️ Уже в ЧС", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO banned_chats (chat_id, added_by) VALUES (?, ?)", (chat_id, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('ban', '🚫')} Чат «{chat_name}» забанен.", parse_mode="HTML")
    try:
        await bot.leave_chat(chat_id)
    except:
        pass

@dp.message(Command("безопасно", prefix="+"))
async def unban_chat_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    args = message.text.split()
    if len(args) >= 2:
        code = args[1].upper()
        chat_id = get_chat_by_code(code)
        if not chat_id:
            return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML")
        try:
            chat = await bot.get_chat(chat_id)
            chat_name = chat.title or f"Чат {chat_id}"
        except:
            chat_name = f"Чат {chat_id}"
    else:
        chat_id = message.chat.id
        chat_name = message.chat.title or f"Чат {chat_id}"
    if not is_chat_banned(chat_id):
        return await message.reply("⚠️ И так не в ЧС", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM banned_chats WHERE chat_id = ?", (chat_id,))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Чат «{chat_name}» убран из ЧС.", parse_mode="HTML")

@dp.message(Command("добавитьагента"))
async def add_agent_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO agents (user_id, added_by) VALUES (?, ?)", (target.id, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} теперь агент!", parse_mode="HTML")

@dp.message(Command("убратьагента"))
async def remove_agent_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM agents WHERE user_id = ?", (target.id,))
        conn.commit()
    await message.reply(f"{em('check', '✅')} {mention(target)} больше не агент", parse_mode="HTML")

@dp.message(Command("агенты"))
async def list_agents(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM agents")
        agents = c.fetchall()
    if not agents:
        return await message.reply("📭 Нет агентов")
    text = f"{em('shield', '🛡')} Агенты:\n"
    for a in agents:
        text += f"• <code>{a[0]}</code>\n"
    await message.reply(text, parse_mode="HTML")

# ================= СЕТКА =================
@dp.message(lambda m: m.text and m.text.lower().startswith("создать сетку"))
async def create_grid_cmd(message: types.Message):
    if message.chat.type != "private":
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("📌 <code>создать сетку {название}</code>", parse_mode="HTML")
    name = args[2].strip().replace(" ", "_")[:24]
    if not name:
        return await message.reply("❌ Название пустое.")
    grid_id = create_grid(name, message.from_user.id)
    if not grid_id:
        return await message.reply("❌ Сетка уже существует.")
    await message.reply(f"✅ Сетка <b>{name}</b> создана (ID: <code>{grid_id}</code>)", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("сетка ") and m.chat.type != "private")
async def set_grid_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return
    name = args[1].strip()
    grid = get_grid_by_name(name)
    if not grid:
        return await message.reply(f"❌ Сетка «{name}» не найдена.", parse_mode="HTML")
    grid_id, grid_name = grid
    if not is_grid_moderator(grid_id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return await message.reply("⛔ Только админ чата.", parse_mode="HTML")
    add_chat_to_grid(grid_id, message.chat.id, hidden=0)
    await message.reply(f"✅ Чат привязан к сетке <b>{grid_name}</b>!", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().strip() == "чаты")
async def list_grid_chats(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не привязан к сетке.")
    chats = get_grid_chats(grid_id, include_hidden=False)
    text = "📋 <b>Чаты сетки:</b>\n\n"
    for chat_id, hidden, desc in chats:
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title or f"Чат {chat_id}"
            link = None
            if chat.username:
                link = f"https://t.me/{chat.username}"
            else:
                try:
                    invite = await bot.create_chat_invite_link(chat_id)
                    link = invite.invite_link
                except:
                    link = None
            if link:
                text += f"• <a href='{link}'>{title}</a>\n"
            else:
                text += f"• {title}\n"
        except:
            text += f"• Чат {chat_id}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(lambda m: m.text and m.text.lower().startswith("глобан"))
async def global_ban_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не в сетке.")
    if not is_grid_moderator(grid_id, message.from_user.id, 2):
        return await message.reply("⛔ Только глобальный модератор.")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        reason = parts[1].strip()
    add_grid_ban(grid_id, target.id, reason, message.from_user.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.ban_chat_member(chat_id, target.id)
            success += 1
        except:
            pass
    await message.reply(f"🚫 {mention(target)} забанен в сетке ({success}/{len(chats)}).\n📝 {reason}", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("глоразбан"))
async def global_unban_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не в сетке.")
    if not is_grid_moderator(grid_id, message.from_user.id, 2):
        return await message.reply("⛔ Только глобальный модератор.")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    remove_grid_ban(grid_id, target.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.unban_chat_member(chat_id, target.id)
            success += 1
        except:
            pass
    await message.reply(f"✅ {mention(target)} разбанен в сетке ({success}/{len(chats)}).", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("гломут"))
async def global_mute_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не в сетке.")
    if not is_grid_moderator(grid_id, message.from_user.id, 2):
        return await message.reply("⛔ Только глобальный модератор.")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    until = datetime.now() + timedelta(hours=24)
    add_grid_mute(grid_id, target.id, until.isoformat(), message.from_user.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.restrict_chat_member(chat_id, target.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
            success += 1
        except:
            pass
    await message.reply(f"🔇 {mention(target)} замучен в сетке на 24 часа ({success}/{len(chats)}).", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("глоразмут"))
async def global_unmute_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не в сетке.")
    if not is_grid_moderator(grid_id, message.from_user.id, 2):
        return await message.reply("⛔ Только глобальный модератор.")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    remove_grid_mute(grid_id, target.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.restrict_chat_member(chat_id, target.id, permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
            success += 1
        except:
            pass
    await message.reply(f"🔈 {mention(target)} размучен в сетке ({success}/{len(chats)}).", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("+глмодер"))
async def add_global_moderator(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не в сетке.")
    if not is_grid_moderator(grid_id, message.from_user.id, 3):
        return await message.reply("⛔ Только глобальный админ.")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    add_grid_moderator(grid_id, target.id, rank=1, is_admin=0)
    await message.reply(f"✅ {mention(target)} назначен глобальным модератором!", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("-глмодер"))
async def remove_global_moderator(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не в сетке.")
    if not is_grid_moderator(grid_id, message.from_user.id, 3):
        return await message.reply("⛔ Только глобальный админ.")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    remove_grid_moderator(grid_id, target.id)
    await message.reply(f"✅ {mention(target)} больше не глобальный модератор.", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("+гладмин"))
async def add_global_admin(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не в сетке.")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT creator_id FROM grids WHERE id = ?", (grid_id,))
        r = c.fetchone()
        creator_id = r[0] if r else None
    if message.from_user.id != creator_id and message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Только создатель сетки.", parse_mode="HTML")
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("❌ Ответьте или укажите @user", parse_mode="HTML")
    add_grid_moderator(grid_id, target.id, rank=5, is_admin=1)
    await message.reply(f"✅ {mention(target)} назначен глобальным админом!", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().strip() == "удалить из сетки")
async def remove_from_grid(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не в сетке.")
    if not is_grid_moderator(grid_id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return await message.reply("⛔ Только админ чата.", parse_mode="HTML")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM grid_chats WHERE chat_id = ?", (message.chat.id,))
        conn.commit()
    await message.reply("✅ Чат удалён из сетки.")

# ================= БРАКИ =================
@dp.message(lambda m: m.text and m.text.lower().startswith("брак ") and "@" in m.text)
async def marriage_proposal_cmd(message: types.Message):
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user", parse_mode="HTML")
    if target.id == message.from_user.id:
        return await message.reply("❌ Нельзя на себе.", parse_mode="HTML")
    if get_marriage(message.chat.id, message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Вы уже в браке.", parse_mode="HTML")
    if get_marriage(message.chat.id, target.id):
        return await message.reply(f"{em('cross', '❌')} {mention(target)} уже в браке.", parse_mode="HTML")
    divorced = get_divorced_marriage(message.chat.id, message.from_user.id)
    if divorced:
        restore_marriage(divorced[0])
        return await message.reply(f"💞 <b>Брак восстановлен!</b>", parse_mode="HTML")
    add_proposal(message.chat.id, message.from_user.id, target.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept:{message.from_user.id}:{target.id}:{message.chat.id}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"marry_reject:{message.from_user.id}:{target.id}:{message.chat.id}")
    ]])
    await message.reply(f"💍 <b>Предложение!</b>\n\n{mention(message.from_user)} → {mention(target)}\n\n{mention(target)}, ты согласен(на)?", parse_mode="HTML", reply_markup=keyboard)

@dp.message(lambda m: m.text and m.text.lower().startswith("брак ") and "@" not in m.text and not m.text.lower().startswith("брак цена") and not m.text.lower().startswith("брак продлить") and not m.text.lower().startswith("брак режим"))
async def marriage_proposal_reply(message: types.Message):
    if not message.reply_to_message:
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        return await message.reply("❌ Нельзя на себе.", parse_mode="HTML")
    if get_marriage(message.chat.id, message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Вы уже в браке.", parse_mode="HTML")
    if get_marriage(message.chat.id, target.id):
        return await message.reply(f"{em('cross', '❌')} {mention(target)} уже в браке.", parse_mode="HTML")
    divorced = get_divorced_marriage(message.chat.id, message.from_user.id)
    if divorced:
        restore_marriage(divorced[0])
        return await message.reply(f"💞 <b>Брак восстановлен!</b>", parse_mode="HTML")
    add_proposal(message.chat.id, message.from_user.id, target.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept:{message.from_user.id}:{target.id}:{message.chat.id}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"marry_reject:{message.from_user.id}:{target.id}:{message.chat.id}")
    ]])
    await message.reply(f"💍 <b>Предложение!</b>\n\n{mention(message.from_user)} → {mention(target)}", parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and (c.data.startswith("marry_accept:") or c.data.startswith("marry_reject:")))
async def marriage_response(callback: types.CallbackQuery):
    action, from_id_str, to_id_str, chat_id_str = callback.data.split(":")
    from_id = int(from_id_str)
    to_id = int(to_id_str)
    chat_id = int(chat_id_str)
    if callback.from_user.id != to_id:
        return await callback.answer("⛔ Это не тебе предложили!", show_alert=True)
    if get_proposal(chat_id, from_id, to_id) is None:
        return await callback.answer("⚠️ Неактивно.", show_alert=True)
    try:
        from_user = await bot.get_chat(from_id)
        to_user = await bot.get_chat(to_id)
    except:
        return await callback.answer("❌ Ошибка.", show_alert=True)
    if action == "marry_accept":
        result = create_marriage(chat_id, from_id, from_user.first_name, to_id, to_user.first_name)
        if not result:
            return await callback.answer("❌ Кто-то уже в браке.", show_alert=True)
        remove_proposal(chat_id, from_id, to_id)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        await bot.send_message(chat_id, f"💍💐 <b>Свадьба!</b>\n\n{mention_by_id(from_id, from_user.first_name)} и {mention_by_id(to_id, to_user.first_name)} теперь в браке!", parse_mode="HTML")
        await callback.answer("💍 Вы в браке!")
    else:
        remove_proposal(chat_id, from_id, to_id)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        await bot.send_message(chat_id, f"💔 {mention_by_id(to_id, to_user.first_name)} отказал(а).", parse_mode="HTML")
        await callback.answer("❌ Отказано.")

@dp.message(lambda m: m.text and m.text.lower().strip() in ["!развод", "развод"])
async def divorce_cmd(message: types.Message):
    marriage = get_marriage(message.chat.id, message.from_user.id)
    if not marriage:
        return await message.reply(f"{em('cross', '❌')} Вы не в браке.", parse_mode="HTML")
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra_days = marriage
    partner_id = u2_id if u1_id == message.from_user.id else u1_id
    partner_name = u2_name if u1_id == message.from_user.id else u1_name
    duration = format_marriage_duration(married_at, extra_days or 0)
    divorce_marriage(message.chat.id, message.from_user.id)
    await message.reply(f"💔 Развод\n{mention(message.from_user)} и {mention_by_id(partner_id, partner_name)} развелись.\n📅 Длился: <b>{duration}</b>", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().strip() in ["мой брак", "моя пара"])
async def my_marriage_cmd(message: types.Message):
    marriage = get_marriage(message.chat.id, message.from_user.id)
    if not marriage:
        return await message.reply(f"💔 Вы не в браке.", parse_mode="HTML")
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra_days = marriage
    partner_id = u2_id if u1_id == message.from_user.id else u1_id
    partner_name = u2_name if u1_id == message.from_user.id else u1_name
    duration = format_marriage_duration(married_at, extra_days or 0)
    text = f"💍 <b>Ваш брак</b>\n\n👫 {mention(message.from_user)} 💞 {mention_by_id(partner_id, partner_name)}\n📅 Зарегистрирован: <b>{married_at[:10]}</b>\n⏳ Вместе: <b>{duration}</b>"
    if extra_days and extra_days > 0:
        text += f"\n🛒 Куплено дней: <b>{extra_days}</b>"
    await message.reply(text, parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().strip() == "браки")
async def marriages_list_cmd(message: types.Message):
    pairs = get_all_marriages(message.chat.id)
    if not pairs:
        return await message.reply("📭 Нет браков.", parse_mode="HTML")
    text = "💍 <b>Браки:</b>\n\n"
    for i, (u1_id, u1_name, u2_id, u2_name, married_at, extra_days) in enumerate(pairs, 1):
        duration = format_marriage_duration(married_at, extra_days or 0)
        text += f"{i}. {mention_by_id(u1_id, u1_name)} 💞 {mention_by_id(u2_id, u2_name)} — <i>{duration}</i>\n"
    await message.reply(text, parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("брак продлить"))
async def extend_marriage(message: types.Message):
    marriage = get_marriage(message.chat.id, message.from_user.id)
    if not marriage:
        return await message.reply(f"{em('cross', '❌')} Вы не в браке.", parse_mode="HTML")
    args = message.text.split()
    if len(args) < 3 or not args[-1].isdigit():
        return await message.reply("📌 <code>брак продлить {дни}</code>", parse_mode="HTML")
    days = int(args[-1])
    if days <= 0:
        return await message.reply("❌ Дни больше нуля.", parse_mode="HTML")
    mode, price = get_marriage_settings(message.chat.id)
    total = days * price
    if total > 0:
        balance = get_balance(message.from_user.id)
        if balance < total:
            return await message.reply(f"{em('cross', '❌')} Нужно: <b>{total}</b>, у вас: <b>{balance}</b>", parse_mode="HTML")
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (total, message.from_user.id))
            conn.commit()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriages SET extra_days = extra_days + ? WHERE id = ?", (days, marriage[0]))
        conn.commit()
    await message.reply(f"✅ Брак продлён на <b>{days}</b> дн. за <b>{total}</b> 🍬", parse_mode="HTML")

# ================= ЗАМЕТКИ =================
@dp.message(lambda m: m.text and m.text.lower().startswith("+заметка "))
async def create_note_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен ранг Мл. Админ (3).", parse_mode="HTML")
    parts = message.text.split("\n", 1)
    first_line = parts[0].replace("+Заметка", "").replace("+заметка", "").strip()
    name = first_line.strip()
    if not name:
        return await message.reply(f"{em('cross', '❌')} Укажите название.", parse_mode="HTML")
    if len(parts) < 2 or not parts[1].strip():
        return await message.reply(f"{em('cross', '❌')} Текст пуст.", parse_mode="HTML")
    full_text = message.text
    first_newline = full_text.find("\n")
    if first_newline == -1:
        return await message.reply(f"{em('cross', '❌')} Текст на новой строке.", parse_mode="HTML")
    body_offset = first_newline + 1
    body_raw = full_text[body_offset:]
    result = ""
    last_pos = 0
    entities = sorted([e for e in (message.entities or []) if e.offset >= body_offset], key=lambda e: e.offset)
    for entity in entities:
        start = entity.offset - body_offset
        end = start + entity.length
        if start < 0 or end > len(body_raw):
            continue
        result += body_raw[last_pos:start]
        entity_text = body_raw[start:end]
        if entity.type == "custom_emoji":
            result += f'<tg-emoji emoji-id="{entity.custom_emoji_id}">{entity_text}</tg-emoji>'
        elif entity.type == "bold":
            result += f"<b>{entity_text}</b>"
        elif entity.type == "italic":
            result += f"<i>{entity_text}</i>"
        elif entity.type == "underline":
            result += f"<u>{entity_text}</u>"
        elif entity.type == "strikethrough":
            result += f"<s>{entity_text}</s>"
        elif entity.type == "code":
            result += f"<code>{entity_text}</code>"
        elif entity.type == "pre":
            result += f"<pre>{entity_text}</pre>"
        elif entity.type == "text_link":
            result += f'<a href="{entity.url}">{entity_text}</a>'
        elif entity.type == "blockquote":
            result += f"<blockquote>{entity_text}</blockquote>"
        elif entity.type == "spoiler":
            result += f"<tg-spoiler>{entity_text}</tg-spoiler>"
        else:
            result += entity_text
        last_pos = end
    result += body_raw[last_pos:]
    note_text = result.strip()
    if not note_text:
        return await message.reply(f"{em('cross', '❌')} Текст пуст.", parse_mode="HTML")
    note_id = add_note(message.chat.id, name, note_text, message.from_user.id)
    if not note_id:
        return await message.reply(f"{em('cross', '❌')} Заметка уже существует.", parse_mode="HTML")
    await message.reply(f"{em('check', '✅')} Заметка <b>{name}</b> создана (ID: <code>{note_id}</code>)", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("-заметка "))
async def delete_note_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML")
    arg = message.text[len("-Заметка"):].strip()
    if not arg:
        return await message.reply(f"{em('cross', '❌')} Укажите название или номер.", parse_mode="HTML")
    note = None
    if arg.isdigit():
        note = get_note_by_number(message.chat.id, int(arg))
    if not note:
        note = get_note_by_name(message.chat.id, arg)
    if not note:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML")
    delete_note(message.chat.id, note[0])
    await message.reply(f"{em('check', '✅')} Заметка <b>{note[1]}</b> удалена.", parse_mode="HTML")

@dp.message(lambda m: m.text and (m.text.lower().strip() == "заметки" or m.text.lower().startswith("заметки ")))
async def list_notes_cmd(message: types.Message):
    args = message.text.split()
    page = 1
    if len(args) >= 2 and args[1].isdigit():
        page = max(1, int(args[1]))
    notes = get_all_notes(message.chat.id)
    if not notes:
        return await message.reply("📭 Нет заметок.", parse_mode="HTML")
    per_page = 20
    total_pages = (len(notes) + per_page - 1) // per_page
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    text = f"📋 <b>Заметки</b> (стр. {page}/{total_pages})\n\n"
    for i, (note_id, name) in enumerate(notes[start:end], start=start+1):
        text += f"{i}. <b>{name}</b>\n"
    if total_pages > 1:
        text += f"\n<i>Следующая: <code>Заметки {page+1}</code></i>"
    await message.reply(text, parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("заметка ") and not m.text.lower().startswith("заметки"))
async def get_note_cmd(message: types.Message):
    arg = message.text[len("Заметка"):].strip()
    if not arg:
        return
    note = None
    if arg.isdigit():
        note = get_note_by_number(message.chat.id, int(arg))
    if not note:
        note = get_note_by_name(message.chat.id, arg)
    if not note:
        return await message.reply(f"{em('cross', '❌')} Заметка не найдена.", parse_mode="HTML")
    await message.reply(note[2], parse_mode="HTML", disable_web_page_preview=True)

# ================= КАТАЛОГ =================
@dp.message(lambda m: m.text and m.text.lower().strip() == "каталог добавить")
async def catalog_add_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("❌ Только для групп.", parse_mode="HTML")
    if not await is_tg_admin(message.chat.id, message.from_user.id):
        return await message.reply("⛔ Только админ чата.", parse_mode="HTML")
    chat_balance = get_chat_coins(message.chat.id)
    if chat_balance < 35000:
        return await message.reply(
            f"❌ Недостаточно коинов в счёте чата.\n\n"
            f"Нужно: <b>35 000</b> i¢\n"
            f"Сейчас: <b>{chat_balance}</b> i¢\n\n"
            f"💡 Пополнить: <code>Бкоин {35000 - chat_balance}</code>",
            parse_mode="HTML"
        )
    existing = get_catalog_entry(message.chat.id)
    if existing and existing[6] == "approved":
        return await message.reply("✅ Чат уже в каталоге.", parse_mode="HTML")
    qid = add_to_catalog_queue(message.chat.id, message.from_user.id, "add")
    chat_title = message.chat.title or "Без названия"
    chat_desc = message.chat.description or "Описание не указано"
    link = await get_chat_link(message.chat.id)
    mod_text = (
        f"📥 <b>Заявка в каталог</b>\n\n"
        f"📍 Чат: <b>{chat_title}</b>\n"
        f"🆔 ID: <code>{message.chat.id}</code>\n"
        f"👤 Отправил: {mention(message.from_user)}\n"
        f"💰 Счёт чата: <b>{chat_balance}</b> i¢\n\n"
        f"📝 Описание: {chat_desc}\n"
        f"🔗 Ссылка: {link or 'недоступна'}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"catalog_approve:{qid}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"catalog_reject:{qid}")
    ]])
    try:
        await bot.send_message(MODERATION_CHAT_ID, mod_text, reply_markup=keyboard, parse_mode="HTML")
    except:
        pass
    await message.reply(f"📥 <b>Заявка отправлена!</b>\n⏳ Ожидайте одобрения.\n💰 Коины не списываются.", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().strip() == "каталог")
async def catalog_card_cmd(message: types.Message):
    existing = get_catalog_entry(message.chat.id)
    if not existing:
        return await message.reply("❌ Чат не в каталоге.", parse_mode="HTML")
    _, title, description, link, submitted_by, submitted_at, status, show_mods = existing
    status_text = {"pending": "⏳ На модерации", "approved": "✅ В каталоге", "rejected": "❌ Отклонено"}.get(status, status)
    await message.reply(
        f"📋 <b>Карточка чата</b>\n\n"
        f"📛 Название: <b>{title}</b>\n"
        f"📝 Описание: {description}\n"
        f"🔗 Ссылка: {link or 'недоступна'}\n\n"
        f"📊 Статус: {status_text}\n"
        f"📅 Добавлен: {submitted_at[:10] if submitted_at else '—'}",
        parse_mode="HTML", disable_web_page_preview=True
    )

@dp.message(lambda m: m.text and m.text.lower().strip() in ["каталог чатов", "каталог список"])
async def catalog_list_cmd(message: types.Message):
    chats = get_catalog_list(limit=100)
    if not chats:
        return await message.reply("📭 Каталог пуст.", parse_mode="HTML")
    text = f"📚 <b>Каталог чатов</b> ({len(chats)})\n\n"
    for i, (chat_id, title, description, link) in enumerate(chats, 1):
        text += f"{i}. <b>{title}</b>\n"
        if description:
            text += f"   <i>{description[:80]}</i>\n"
        if link:
            text += f"   🔗 <a href='{link}'>Перейти</a>\n"
        text += "\n"
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await message.reply(text[i:i+4000], parse_mode="HTML", disable_web_page_preview=True)
    else:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(Command("каталог"))
async def catalog_slash_cmd(message: types.Message):
    chats = get_catalog_list(limit=100)
    if not chats:
        return await message.reply("📭 Каталог пуст.", parse_mode="HTML")
    text = f"📚 <b>Каталог чатов</b> ({len(chats)})\n\n"
    for i, (chat_id, title, description, link) in enumerate(chats, 1):
        text += f"{i}. <b>{title}</b>\n"
        if description:
            text += f"   <i>{description[:80]}</i>\n"
        if link:
            text += f"   🔗 <a href='{link}'>Перейти</a>\n"
        text += "\n"
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await message.reply(text[i:i+4000], parse_mode="HTML", disable_web_page_preview=True)
    else:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.callback_query(lambda c: c.data and (c.data.startswith("catalog_approve:") or c.data.startswith("catalog_reject:")))
async def catalog_review_handler(callback: types.CallbackQuery):
    if not is_agent(callback.from_user.id) and callback.from_user.id != OWNER_ID:
        return await callback.answer("⛔ Только агенты.", show_alert=True)
    action, qid_str = callback.data.split(":")
    qid = int(qid_str)
    entry = get_catalog_queue_entry(qid)
    if not entry:
        return await callback.answer("⚠️ Уже обработано.", show_alert=True)
    chat_id, submitted_by, act, status = entry
    if status != "pending":
        return await callback.answer("⚠️ Уже обработано.", show_alert=True)
    reviewer = mention(callback.from_user)
    if action == "catalog_approve":
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title or "Без названия"
            desc = chat.description or ""
        except:
            title = "Чат"
            desc = ""
        link = await get_chat_link(chat_id)
        add_catalog_chat(chat_id, title, desc, link or "", submitted_by)
        update_catalog_queue_status(qid, "approved", callback.from_user.id)
        try:
            await bot.send_message(chat_id, "✅ <b>Ваш чат одобрен и добавлен в каталог!</b>", parse_mode="HTML")
        except:
            pass
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.reply(f"✅ Одобрено {reviewer}")
        except:
            pass
        await callback.answer("✅ Одобрено!")
    else:
        update_catalog_queue_status(qid, "rejected", callback.from_user.id)
        try:
            await bot.send_message(chat_id, "❌ <b>Ваш чат отклонён.</b>", parse_mode="HTML")
        except:
            pass
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.reply(f"❌ Отклонено {reviewer}")
        except:
            pass
        await callback.answer("❌ Отклонено!")

# ================= BUSINESS =================
@dp.business_connection()
async def on_business_connection(connection: types.BusinessConnection):
    if connection.is_enabled:
        save_business_connection(connection.user.id, connection.id)
        try:
            await bot.send_message(
                connection.user.id,
                f"{em('check', '✅')} Бот подключён к Business-аккаунту!\n\n"
                f"• <code>+ас</code> / <code>+аигн</code>\n"
                f"• <code>-ас</code> / <code>-аигн</code>\n"
                f"• <code>.ид</code> / <code>.анкета</code>",
                parse_mode="HTML"
            )
        except:
            pass
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
    if not conn_id:
        return
    owner_id = get_business_owner_by_conn(conn_id)
    if not owner_id:
        return
    if sender_id != owner_id and sender_id != bot.id:
        return
    is_privileged = is_agent(owner_id) or owner_id == OWNER_ID
    async def resolve_biz_target():
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            return u.id, u.first_name
        parts = text.split()
        if len(parts) >= 2 and parts[1].isdigit():
            tid = int(parts[1])
            try:
                u = await bot.get_chat(tid)
                return tid, u.first_name
            except:
                return tid, f"ID {tid}"
        return None, None
    if text.startswith(".ид") or text.startswith("/ид"):
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            await bot.send_message(chat_id=message.chat.id, text=f"🆔 ID: <code>{u.id}</code>\n👤 {u.first_name}", parse_mode="HTML", business_connection_id=conn_id)
        return
    if text.startswith(".анкета") or text.startswith("/анкета"):
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            total, today_count, chat_count, first_msg_date = get_total_stats(u.id)
            banned = "🚫 В антиспаме" if is_in_antispam(u.id) else "✅ Чист"
            await bot.send_message(chat_id=message.chat.id, text=f"👤 <b>{u.first_name}</b>\nID: <code>{u.id}</code>\nВсего: <b>{total}</b>\nСтатус: {banned}", parse_mode="HTML", business_connection_id=conn_id)
        return
    if not is_privileged:
        return
    if text.startswith("-аигн"):
        target, name = await resolve_biz_target()
        if target:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM ignore_list WHERE user_id = ?", (target,))
                conn.commit()
            await bot.send_message(chat_id=message.chat.id, text=f"✅ {name} убран из игнора", business_connection_id=conn_id)
        return
    if text.startswith("-ас"):
        target, name = await resolve_biz_target()
        if target:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM antispam WHERE user_id = ?", (target,))
                c.execute("DELETE FROM ignore_list WHERE user_id = ?", (target,))
                conn.commit()
            await bot.send_message(chat_id=message.chat.id, text=f"✅ {name} вынесен из базы", business_connection_id=conn_id)
        return
    if text.startswith("+аигн"):
        target, name = await resolve_biz_target()
        if target:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target, "Business", sender_id))
                c.execute("INSERT OR REPLACE INTO ignore_list (user_id, chat_id, reason, added_by) VALUES (?, ?, ?, ?)", (target, message.chat.id, "Business", sender_id))
                conn.commit()
            await bot.send_message(chat_id=message.chat.id, text=f"✅ {name} в «Антиспам» + игнор", business_connection_id=conn_id)
        return
    if text.startswith("+ас"):
        target, name = await resolve_biz_target()
        if target:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by) VALUES (?, ?, ?)", (target, "Business", sender_id))
                conn.commit()
            await bot.send_message(chat_id=message.chat.id, text=f"✅ {name} в «Антиспам»", business_connection_id=conn_id)
        return

# ================= ОБРАБОТКА ВСЕХ СООБЩЕНИЙ =================
@dp.message()
async def all_messages(message: types.Message):
    if message.from_user and not message.from_user.is_bot:
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
            c.execute("INSERT INTO messages_stats (user_id, chat_id, date, count) VALUES (?, ?, ?, 1) ON CONFLICT(user_id, chat_id, date) DO UPDATE SET count = count + 1", (message.from_user.id, message.chat.id, today))
            conn.commit()
        if is_ignored(message.chat.id, message.from_user.id):
            try:
                await message.delete()
            except:
                pass

# ================= ВХОД В ЧАТ + КАПЧА =================
@dp.chat_member()
async def on_join(event: types.ChatMemberUpdated):
    if event.new_chat_member.status != "member":
        return
    user = event.new_chat_member.user
    chat_id = event.chat.id
    chat_title = event.chat.title or "чат"
    if is_in_antispam(user.id):
        try:
            await bot.ban_chat_member(chat_id, user.id)
            await bot.send_message(chat_id, f"{em('ban', '🚫')} {mention(user)} в антиспаме", parse_mode="HTML")
        except:
            pass
        return
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            greeting = get_greeting(chat_id)
            if greeting:
                text = format_greeting(greeting, user, event.chat)
                await bot.send_message(chat_id, text, parse_mode="HTML")
            return
    except:
        return
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id, user_id=user.id,
            permissions=types.ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False, can_send_polls=False, can_change_info=False, can_invite_users=False, can_pin_messages=False)
        )
    except:
        pass
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Я не бот", callback_data=f"captcha_pass:{user.id}:{chat_id}")]])
    text = f"{em('wave', '👋')} Привет, {mention(user)}!\n\n🤖 Нажми на кнопку в течение <b>2 минут</b>."
    try:
        captcha_msg = await bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
        save_captcha(user.id, chat_id, captcha_msg.message_id)
        asyncio.create_task(captcha_timeout(user.id, chat_id))
    except:
        pass

async def captcha_timeout(user_id, chat_id):
    await asyncio.sleep(120)
    if get_captcha(user_id, chat_id) is not None:
        try:
            await bot.ban_chat_member(chat_id, user_id)
            await bot.unban_chat_member(chat_id, user_id)
        except:
            pass
        msg_id = get_captcha(user_id, chat_id)
        if msg_id:
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
        remove_captcha(user_id, chat_id)

@dp.callback_query(lambda c: c.data and c.data.startswith("captcha_pass:"))
async def captcha_pass_handler(callback: types.CallbackQuery):
    data = callback.data.split(":")
    target_user_id = int(data[1])
    chat_id = int(data[2])
    if callback.from_user.id != target_user_id:
        return await callback.answer("⛔ Это не твоя капча!", show_alert=True)
    if get_captcha(target_user_id, chat_id) is None:
        return await callback.answer("⚠️ Неактивна.", show_alert=True)
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id, user_id=target_user_id,
            permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True, can_invite_users=True, can_pin_messages=False, can_change_info=False)
        )
    except Exception as e:
        return await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
    remove_captcha(target_user_id, chat_id)
    try:
        await callback.message.delete()
    except:
        pass
    user = callback.from_user
    greeting = get_greeting(chat_id)
    if greeting:
        try:
            chat = await bot.get_chat(chat_id)
            text = format_greeting(greeting, user, chat)
            await bot.send_message(chat_id, text, parse_mode="HTML")
        except:
            pass
    else:
        await bot.send_message(chat_id, f"{em('wave', '👋')} Привет, {mention(user)}!", parse_mode="HTML")
    await callback.answer(f"{em('check', '✅')} Капча пройдена!")

# ================= ДОБАВЛЕНИЕ БОТА В ЧАТ =================
@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    if event.new_chat_member.status not in ["member", "administrator"]:
        return
    chat_id = event.chat.id
    chat_type = event.chat.type
    if is_chat_banned(chat_id):
        try:
            await bot.leave_chat(chat_id)
        except:
            pass
        try:
            await bot.send_message(OWNER_ID, f"{em('ban', '🚫')} Бот добавлен в опасный чат!\nЧат ID: {chat_id}", parse_mode="HTML")
        except:
            pass
        return
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.status == "creator":
                set_rank(chat_id, admin.user.id, 5, admin.user.id)
                break
    except:
        pass
    if chat_type in ["group", "supergroup"]:
        text = (
            f"{em('wave', '👋')} <b>Всем привет!</b>\n\n"
            f"Я <b>{BOT_NAME}</b> — помогу навести порядок.\n\n"
            f"{em('shield', '🛡')} <b>Что я умею:</b>\n"
            f"• Ловить спамеров и ботов\n"
            f"• Выдавать варны и мут\n"
            f"• Проверять новичков через капчу\n"
            f"• Хранить статистику\n\n"
            f"⚙️ <b>Выдайте мне права администратора.</b>\n\n"
            f"{em('sos', '🆘')} Поддержка: {SUPPORT_CHAT_LINK}\n"
            f"📢 Канал: {SUPPORT_CHANNEL_LINK}"
        )
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
        except:
            pass
        try:
            await bot.send_message(OWNER_ID, f"{em('check', '✅')} Бот добавлен в чат!\n📍 <b>{event.chat.title or 'Без названия'}</b>\n🆔 <code>{chat_id}</code>", parse_mode="HTML")
        except:
            pass

# ================= ЗАПУСК =================
async def main():
    init_db()
    print("✅ Бот запущен!")
    asyncio.create_task(auto_unban_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
