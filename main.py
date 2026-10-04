import asyncio
import sqlite3
import random
import string
import os
import re
import json
import logging
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

logging.basicConfig(level=logging.INFO)

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
TERMS_URL = "https://teletype.in/@sirenie3/POLSVATELCKOEMOS"

BOT_START_TIME = datetime.now()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ================= УНИВЕРСАЛЬНЫЙ ДЕКОРАТОР КОМАНД =================
def _match_command(message: types.Message, name_lower: str) -> bool:
    if not message.text:
        return False
    txt = message.text.strip()
    if not txt:
        return False
    if txt[0] in ".!/":
        txt = txt[1:].lstrip()
    if not txt:
        return False
    txt_lower = txt.lower()
    words_needed = name_lower.split()
    words_have = txt_lower.split()
    if len(words_have) < len(words_needed):
        return False
    return words_have[:len(words_needed)] == words_needed


def cmd(name: str):
    name_lower = name.lower().strip()

    def decorator(func):
        @dp.message(lambda m: _match_command(m, name_lower))
        async def handler(message: types.Message):
            if not await check_command_access(message, name_lower):
                return
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
    "announce": "5269669124069432917", "artist": "5258215635996908355",
    "like": "5391210243210353922", "dislike": "5864180515816345988",
    "heart": "5266996773943028034", "education": "5391052390277348873",
    "art": "5431456208487716895", "broom": "5472291748220771063",
    "briefcase": "5398037325655602784", "wrench": "5462921117423384478",
    "crop": "5318804172705910750", "notify": "5458603043203327669",
    "sport": "5409008750893734809", "mask": "5359441070201513074",
    "qr": "5407025283456835913", "eye": "5122983123188974322",
    "people": "5258513401784573443", "envelope": "5253742260054409879",
    "card": "5472250091332993630", "lab": "5411512278740640309",
    "medicine": "5433635625217563352", "audio": "5260652149469094137",
    "video": "5472069741261265416", "verified": "5411267122007397812",
    "wallet": "5269472440337078683", "music": "5172447776205702031",
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


def html_escape_text(text: str) -> str:
    if not text:
        return ""
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ================= TELEGRAM ENTITIES → HTML =================
def entities_to_html(message: types.Message) -> str:
    if not message.text:
        return ""
    text = message.text
    entities = message.entities or []
    if not entities:
        return html_escape_text(text)

    sorted_ents = sorted(entities, key=lambda e: (e.offset, -e.length))

    def render_range(start: int, end: int, ent_list) -> str:
        result = []
        pos = start
        inner = [e for e in ent_list if e.offset >= start and e.offset + e.length <= end]
        top = []
        for e in inner:
            if not top or e.offset >= top[-1].offset + top[-1].length:
                top.append(e)

        for e in top:
            if e.offset > pos:
                result.append(html_escape_text(text[pos:e.offset]))
            raw = text[e.offset:e.offset + e.length]
            inner_text = render_range(e.offset, e.offset + e.length,
                                       [x for x in inner if x is not e])

            if e.type == "bold": result.append(f"<b>{inner_text}</b>")
            elif e.type == "italic": result.append(f"<i>{inner_text}</i>")
            elif e.type == "underline": result.append(f"<u>{inner_text}</u>")
            elif e.type == "strikethrough": result.append(f"<s>{inner_text}</s>")
            elif e.type == "spoiler": result.append(f"<tg-spoiler>{inner_text}</tg-spoiler>")
            elif e.type == "code": result.append(f"<code>{html_escape_text(raw)}</code>")
            elif e.type == "pre":
                lang = getattr(e, "language", None)
                if lang:
                    result.append(f'<pre><code class="language-{lang}">{html_escape_text(raw)}</code></pre>')
                else:
                    result.append(f"<pre>{html_escape_text(raw)}</pre>")
            elif e.type == "blockquote": result.append(f"<blockquote>{inner_text}</blockquote>")
            elif e.type == "expandable_blockquote": result.append(f"<blockquote expandable>{inner_text}</blockquote>")
            elif e.type == "text_link":
                url = getattr(e, "url", "") or ""
                result.append(f'<a href="{url}">{inner_text}</a>')
            elif e.type == "custom_emoji": result.append(html_escape_text(raw))
            else: result.append(inner_text)
            pos = e.offset + e.length
        if pos < end:
            result.append(html_escape_text(text[pos:end]))
        return "".join(result)

    return render_range(0, len(text), sorted_ents).strip()


def entities_to_html_from(message: types.Message, char_index: int) -> str:
    if not message.text:
        return ""
    text = message.text
    entities = message.entities or []
    shifted = []
    for e in entities:
        if e.offset + e.length <= char_index:
            continue
        new_off = max(0, e.offset - char_index)
        if e.offset < char_index:
            new_len = e.offset + e.length - char_index
        else:
            new_len = e.length
        clone = type(e)(
            type=e.type, offset=new_off, length=new_len,
            url=getattr(e, "url", None),
            language=getattr(e, "language", None),
            custom_emoji_id=getattr(e, "custom_emoji_id", None),
        )
        shifted.append(clone)

    fragment = text[char_index:]
    fake = types.Message(
        message_id=0, date=message.date, chat=message.chat,
        from_user=message.from_user, text=fragment, entities=shifted,
    )
    return entities_to_html(fake).strip()


def _extract_html_after(message: types.Message, char_index: int) -> str:
    html = entities_to_html_from(message, char_index)
    return re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', html, flags=re.DOTALL)


# ================= РАНГИ =================
RANK_NAMES = {0: "👤 Участник", 1: "🛡️ Мл. Модератор", 2: "🛡️ Ст. Модератор",
              3: "👑 Мл. Админ", 4: "👑 Ст. Админ", 5: "⚜️ Владелец"}

AGENT_RANKS = {1: "🛡 Мл. Агент", 2: "🛡 Агент", 3: "🛡 Ст. Агент", 4: "⚜️ Гл. Агент"}


# ================= ДК =================
DEFAULT_ACCESS = {
    "брак": 0, "развод": 0, "профиль": 0, "анкета": 0, "мойид": 0, "пинг": 0, "помощь": 0,
    "команды": 0, "инфо": 0, "ид": 0, "чатид": 0, "топ": 0, "погода": 0,
    "моя стата": 0, "мой брак": 0, "моя пара": 0, "браки": 0,
    "мой вип": 0, "ник": 0, "о себе": 0, "звание": 0, "девиз": 0,
    "гражданство": 0, "кто гражданин": 0, "мешок": 0,
    "мешки": 0, "перевод": 0, "коины": 0, "баланс": 0, "ферма": 0,
    "купить коины": 0, "бкоин": 0, "коинытоп": 0, "купитьириски": 0,
    "рыбалка": 0, "рыба": 0, "рыбачить": 0, "рыбтоп": 0,
    "моя рыбалка": 0, "рыбстата": 0, "магазин снастей": 0, "снасти": 0,
    "купить": 0, "инвентарь": 0, "инв": 0, "мои рыбные ачивки": 0,
    "рыбные ачивки": 0, "событие": 0, "события": 0, "турнир": 0,
    "садок": 0, "моя рыба": 0, "рыбасадок": 0, "продать": 0,
    "ачивки": 0, "все ачивки": 0, "вип": 0, "купить вип": 0,
    "мрп": 0, "репорт": 0, "админы": 0,

    "бан": 2, "разбан": 2, "мут": 1, "размут": 1, "кик": 1,
    "варн": 1, "варны": 1, "снятьварн": 2, "сбросварнов": 3,
    "наказания": 1, "баны": 1, "пин": 1, "закрепить": 1,
    "анпин": 1, "открепить": 1, "унпин": 1, "репорты": 2,

    "правила": 3, "приветствие": 3, "фильтрссылок": 3,
    "заявки": 4, "капча": 3, "автомод": 3, "автомодерация": 3,
    "обновить чат": 3, "обновитьчат": 3, "кто не писал": 2, "неактивные": 2,

    "повысить": 3, "понизить": 3, "разжаловать": 3, "снять": 3, "восстановить": 3,

    "агенты": 4, "скрытые": 5,
    "создать сетку": 5, "чаты": 1, "глобан": 2, "глоразбан": 2,

    "заметка": 3, "заметки": 3, "пополнить": 3,

    "инфобот": -2, "бэкап": -2, "импорт": -2,

    "дк": 3, "дк список": 3, "дк сброс": 3,
    "погода": 0,
}


ALIASES = {
    "рыба": "рыбалка", "рыбачить": "рыбалка",
    "commands": "команды", "rules": "правила",
    "инв": "инвентарь", "неактивные": "кто не писал",
    "снять": "разжаловать", "закрепить": "пин",
    "открепить": "анпин", "унпин": "анпин",
    "автомодерация": "автомод", "обновитьчат": "обновить чат",
    "все ачивки": "ачивки", "рыбные ачивки": "мои рыбные ачивки",
    "купить-ириски": "купитьириски", "buycandies": "купитьириски",
    "баланс": "коины", "моя пара": "мой брак",
    "события": "событие", "снасти": "магазин снастей",
    "моя рыба": "садок", "рыбасадок": "садок",
}


def _canonical(cmd_name):
    return ALIASES.get(cmd_name, cmd_name)


# ================= БАЗА ДАННЫХ =================
def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS agents (user_id INTEGER PRIMARY KEY, added_by INTEGER)")
        c.execute("""CREATE TABLE IF NOT EXISTS agent_ranks (
            user_id INTEGER PRIMARY KEY, rank INTEGER DEFAULT 1, added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("CREATE TABLE IF NOT EXISTS antispam (user_id INTEGER PRIMARY KEY, reason TEXT, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS ignore_list (user_id INTEGER, chat_id INTEGER, reason TEXT, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_codes (chat_id INTEGER PRIMARY KEY, code TEXT UNIQUE)")
        c.execute("CREATE TABLE IF NOT EXISTS messages_stats (user_id INTEGER, chat_id INTEGER, date DATE, count INTEGER DEFAULT 1, UNIQUE(user_id, chat_id, date))")
        c.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER, chat_id INTEGER, rank INTEGER DEFAULT 1, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS bot_promoted (user_id INTEGER, chat_id INTEGER, promoted_by INTEGER, promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS warns (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, reason TEXT, warned_by INTEGER, warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS candies (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS candy_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS agent_activity (user_id INTEGER PRIMARY KEY, last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS greetings (chat_id INTEGER PRIMARY KEY, text TEXT, updated_by INTEGER, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, first_name TEXT, username TEXT)")
        c.execute("""CREATE TABLE IF NOT EXISTS captcha (
            user_id INTEGER, chat_id INTEGER, message_id INTEGER,
            captcha_type TEXT, answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, chat_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS captcha_settings (
            chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 1)""")
        c.execute("""CREATE TABLE IF NOT EXISTS command_notify_settings (
            chat_id INTEGER PRIMARY KEY, notify_enabled INTEGER DEFAULT 1)""")
        c.execute("CREATE TABLE IF NOT EXISTS business_connections (user_id INTEGER PRIMARY KEY, connection_id TEXT, connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS chat_bans (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER, reason TEXT, banned_by INTEGER, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, until_date TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS grids (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, creator_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS grid_chats (grid_id INTEGER, chat_id INTEGER, hidden INTEGER DEFAULT 0, description TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS grid_moderators (grid_id INTEGER, user_id INTEGER, rank INTEGER DEFAULT 1, is_admin INTEGER DEFAULT 0, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, user_id))")
        c.execute("CREATE TABLE IF NOT EXISTS grid_bans (grid_id INTEGER, user_id INTEGER, reason TEXT, banned_by INTEGER, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, user_id))")
        c.execute("""CREATE TABLE IF NOT EXISTS grid_user_ranks (
            grid_id INTEGER, user_id INTEGER, rank INTEGER DEFAULT 1, added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, user_id))""")
        c.execute("CREATE TABLE IF NOT EXISTS marriages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user1_id INTEGER, user2_id INTEGER, user1_name TEXT, user2_name TEXT, married_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, divorced_at TIMESTAMP, status TEXT DEFAULT 'active', in_top INTEGER DEFAULT 0, extra_days INTEGER DEFAULT 0, UNIQUE(chat_id, user1_id), UNIQUE(chat_id, user2_id))")
        c.execute("CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, from_id INTEGER, to_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, name TEXT, text TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(chat_id, name))")
        c.execute("CREATE TABLE IF NOT EXISTS coins (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, last_farm TIMESTAMP, total_farmed INTEGER DEFAULT 0, last_tax TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS coin_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, reason TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS chat_coins (chat_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, emoji TEXT DEFAULT '🏅', description TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, achievement_id INTEGER, given_by INTEGER, given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id, achievement_id))")
        c.execute("CREATE TABLE IF NOT EXISTS citizenship (user_id INTEGER PRIMARY KEY, chat_id INTEGER, became_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS user_nicks (user_id INTEGER, chat_id INTEGER, nick TEXT, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS user_about (user_id INTEGER PRIMARY KEY, text TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_ranks (user_id INTEGER, chat_id INTEGER, rank TEXT, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_rules (chat_id INTEGER PRIMARY KEY, text TEXT, updated_by INTEGER, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS user_profiles (user_id INTEGER PRIMARY KEY, gender TEXT, birth_date TEXT, birth_visibility TEXT DEFAULT 'месяц', city TEXT, bio TEXT, motto TEXT, show_citizenship INTEGER DEFAULT 1, is_hidden INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS vip_settings (chat_id INTEGER PRIMARY KEY, price INTEGER DEFAULT 100)")
        c.execute("CREATE TABLE IF NOT EXISTS vip_users (user_id INTEGER PRIMARY KEY, expires_at TIMESTAMP, emoji TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS rp_commands (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, name TEXT, emoji TEXT, text TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(chat_id, name))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_antispam_settings (chat_id INTEGER PRIMARY KEY, antispam_enabled INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS stars_settings (chat_id INTEGER PRIMARY KEY, stars_per_candy INTEGER DEFAULT 2)")
        c.execute("CREATE TABLE IF NOT EXISTS stars_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, amount_candies INTEGER, stars_paid INTEGER, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS antispam_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, reason TEXT, admin_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS link_filter (chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS hidden_agents (user_id INTEGER PRIMARY KEY, hidden_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS global_settings (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_chat_id INTEGER,
            reporter_id INTEGER, reporter_name TEXT, reporter_username TEXT,
            target_id INTEGER, target_name TEXT, target_username TEXT,
            target_message_id INTEGER, message_text TEXT, reason TEXT,
            report_forward_chat_id INTEGER, forward_message_id INTEGER,
            status TEXT DEFAULT 'pending', reviewed_by INTEGER, reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS report_chats (
            chat_id INTEGER PRIMARY KEY, report_chat_id INTEGER,
            added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS fishing (
            user_id INTEGER PRIMARY KEY, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
            total_caught INTEGER DEFAULT 0, total_empty INTEGER DEFAULT 0,
            has_rod INTEGER DEFAULT 0, bait_until TIMESTAMP, last_fish TIMESTAMP,
            inventory TEXT DEFAULT '{}', legendary_caught INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS fishing_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER,
            result TEXT, fish_name TEXT, reward INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS fishing_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER,
            achievement TEXT, given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, chat_id, achievement))""")
        c.execute("""CREATE TABLE IF NOT EXISTS fishing_events (
            chat_id INTEGER PRIMARY KEY, event_type TEXT, bonus REAL DEFAULT 1.0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS fishing_events_settings (
            chat_id INTEGER PRIMARY KEY, events_enabled INTEGER DEFAULT 1)""")
        c.execute("""CREATE TABLE IF NOT EXISTS fishing_tournaments (
            chat_id INTEGER PRIMARY KEY, started_by INTEGER, started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP, prize INTEGER DEFAULT 5000)""")
        c.execute("""CREATE TABLE IF NOT EXISTS fishing_tournament_members (
            chat_id INTEGER, user_id INTEGER, caught INTEGER DEFAULT 0,
            UNIQUE(chat_id, user_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS fish_storage (
            user_id INTEGER, fish_name TEXT, fish_emoji TEXT,
            quantity INTEGER DEFAULT 0,
            UNIQUE(user_id, fish_name))""")
        c.execute("""CREATE TABLE IF NOT EXISTS automod_settings (
            chat_id INTEGER PRIMARY KEY,
            antimat INTEGER DEFAULT 0, antiflood INTEGER DEFAULT 0,
            anticaps INTEGER DEFAULT 0, antisticker INTEGER DEFAULT 0,
            antimat_action TEXT DEFAULT 'mute', antimat_mute INTEGER DEFAULT 30, antimat_ban INTEGER DEFAULT 1440,
            antiflood_action TEXT DEFAULT 'mute', antiflood_mute INTEGER DEFAULT 10, antiflood_ban INTEGER DEFAULT 1440,
            anticaps_action TEXT DEFAULT 'delete', anticaps_mute INTEGER DEFAULT 5, anticaps_ban INTEGER DEFAULT 1440,
            antisticker_action TEXT DEFAULT 'mute', antisticker_mute INTEGER DEFAULT 5, antisticker_ban INTEGER DEFAULT 1440)""")
        c.execute("""CREATE TABLE IF NOT EXISTS automod_messages (
            user_id INTEGER, chat_id INTEGER, msg_time TIMESTAMP,
            msg_type TEXT DEFAULT 'text', UNIQUE(user_id, chat_id, msg_time))""")
        c.execute("""CREATE TABLE IF NOT EXISTS command_access (
            chat_id INTEGER, command TEXT, min_rank INTEGER DEFAULT 0,
            UNIQUE(chat_id, command))""")
        c.execute("""CREATE TABLE IF NOT EXISTS pending_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT, source_chat_id INTEGER, source_key TEXT,
            placeholder TEXT, link_url TEXT, link_text TEXT, submitted_by INTEGER,
            status TEXT DEFAULT 'pending', reviewed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()


# ================= РАНГИ =================
def get_rank(chat_id, user_id):
    if user_id == OWNER_ID: return 5
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


def has_permission(chat_id, user_id, required_rank):
    return get_rank(chat_id, user_id) >= required_rank


def get_command_access(chat_id, command):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT min_rank FROM command_access WHERE chat_id = ? AND command = ?", (chat_id, command))
        r = c.fetchone()
        if r: return r[0]
    return DEFAULT_ACCESS.get(command, 0)


def set_command_access(chat_id, command, min_rank):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO command_access (chat_id, command, min_rank) VALUES (?, ?, ?)", (chat_id, command, min_rank))
        conn.commit()


def reset_command_access(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM command_access WHERE chat_id = ?", (chat_id,))
        conn.commit()


def get_all_access_for_chat(chat_id):
    result = dict(DEFAULT_ACCESS)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT command, min_rank FROM command_access WHERE chat_id = ?", (chat_id,))
        for cmd_name, min_rank in c.fetchall():
            result[cmd_name] = min_rank
    return result


def is_command_notify_enabled(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT notify_enabled FROM command_notify_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if r is None:
            c.execute("INSERT INTO command_notify_settings (chat_id, notify_enabled) VALUES (?, 1)", (chat_id,))
            conn.commit()
            return True
        return bool(r[0])


def set_command_notify_enabled(chat_id, enabled):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO command_notify_settings (chat_id, notify_enabled) VALUES (?, ?)", (chat_id, 1 if enabled else 0))
        conn.commit()


async def check_command_access(message, command):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if user_id == OWNER_ID: return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status == "creator": return True
    except: pass
    canon = _canonical(command)
    access = get_command_access(chat_id, canon)
    notify = is_command_notify_enabled(chat_id)

    if access == -1:
        if notify: await message.reply(f"{em('cross', '❌')} Команда отключена.", parse_mode="HTML")
        return False
    if access == -2:
        if notify: await message.reply(f"{em('cross', '❌')} Только создатель чата.", parse_mode="HTML")
        return False
    if access == 0: return True
    if has_permission(chat_id, user_id, access): return True
    if notify:
        await message.reply(f"{em('cross', '❌')} Недостаточно прав.\n🔒 Нужен: <b>{RANK_NAMES.get(access, access)}</b>", parse_mode="HTML")
    return False


# ================= АГЕНТЫ =================
def is_agent(user_id):
    if user_id == OWNER_ID: return False
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM agents WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None


def get_agent_rank(user_id):
    if user_id == OWNER_ID: return 0
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
    if user_id == OWNER_ID: return True
    return get_agent_rank(user_id) >= min_rank


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
        if r: return r[0]
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
    except: return False


async def resolve_target(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user, None
    args = message.text.split()
    for a in args[1:]:
        if a.startswith('@'):
            username = a[1:]
            try: return await bot.get_chat(a), a
            except:
                with sqlite3.connect(DATABASE_PATH) as conn:
                    c = conn.cursor()
                    c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
                    r = c.fetchone()
                    if r:
                        try: return await bot.get_chat(r[0]), a
                        except: pass
            continue
        if a.isdigit():
            try: return await bot.get_chat(int(a)), a
            except: continue
    return None, None


async def get_chat_link(chat_id):
    try:
        chat = await bot.get_chat(chat_id)
        if chat.username: return f"https://t.me/{chat.username}"
    except: pass
    try:
        link = await bot.create_chat_invite_link(chat_id)
        return link.invite_link
    except: return None


async def delete_later(message: types.Message, seconds: int = 60):
    await asyncio.sleep(seconds)
    try: await message.delete()
    except: pass


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
    if not text: return False
    if re.search(r'(https?://|tg://|t\.me/)', text, re.IGNORECASE): return True
    if re.search(r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', text, re.IGNORECASE): return True
    return False# ================= АВТОМОДЕРАЦИЯ =================
BAD_WORDS = [
    "блять", "блядь", "блят", "бля", "сука", "сучка", "сучонок",
    "хуй", "хуя", "хую", "хуе", "хуё", "хуи", "хуйн", "хуйня", "хуёв",
    "пизда", "пизду", "пизде", "пизды", "пиздец", "пизд",
    "ебать", "ебал", "еба", "ебёт", "ебет", "ебан", "ебану", "ебуч",
    "ёбаный", "ебаный", "ёбн", "ёб", "ёпт",
    "мудак", "мудила", "мудозвон",
    "гандон", "гондон",
    "долбоеб", "долбоёб", "долбаеб", "долбаёб",
    "уебан", "уёбан", "уёбище", "уебище",
    "залупа", "залупу", "залупе",
    "манда", "манду", "манде", "мандавошка",
    "нах", "нахуй", "нахуя", "похуй", "похую", "похуист",
    "охуе", "ахуе", "охуи",
    "пидор", "пидар", "пидр", "пидарас", "пидорас",
    "шлюха", "шлюх", "шалава",
    "хер", "херн", "херов", "херня",
    "жопа", "жоп", "жопу",
    "срать", "сру", "срака", "срак",
    "пердеть", "перд", "пердёж",
    "член",
    "яйца", "яиц", "яйцо",
    "сперм", "сперма",
    "минет", "миньет",
    "трахать", "трахал", "трах",
    "еби", "ёби",
    "сук", "падла", "падлю",
    "казел", "козел", "козёл",
    "быдло", "быдл",
    "гнида", "гнид",
    "тварь", "твар",
]


def has_bad_words(text: str) -> bool:
    if not text: return False
    lower = text.lower()
    for word in BAD_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\w*', lower):
            return True
    return False


def is_caps(text: str) -> bool:
    if not text or len(text) < 5: return False
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 5: return False
    caps = sum(1 for c in letters if c.isupper())
    return (caps / len(letters)) > 0.7


def get_automod_settings(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT antimat, antiflood, anticaps, antisticker,
            antimat_action, antimat_mute, antimat_ban,
            antiflood_action, antiflood_mute, antiflood_ban,
            anticaps_action, anticaps_mute, anticaps_ban,
            antisticker_action, antisticker_mute, antisticker_ban
            FROM automod_settings WHERE chat_id = ?""", (chat_id,))
        r = c.fetchone()
        if not r:
            c.execute("INSERT INTO automod_settings (chat_id) VALUES (?)", (chat_id,))
            conn.commit()
            return {
                "antimat": 0, "antiflood": 0, "anticaps": 0, "antisticker": 0,
                "antimat_action": "mute", "antimat_mute": 30, "antimat_ban": 1440,
                "antiflood_action": "mute", "antiflood_mute": 10, "antiflood_ban": 1440,
                "anticaps_action": "delete", "anticaps_mute": 5, "anticaps_ban": 1440,
                "antisticker_action": "mute", "antisticker_mute": 5, "antisticker_ban": 1440,
            }
        keys = [
            "antimat", "antiflood", "anticaps", "antisticker",
            "antimat_action", "antimat_mute", "antimat_ban",
            "antiflood_action", "antiflood_mute", "antiflood_ban",
            "anticaps_action", "anticaps_mute", "anticaps_ban",
            "antisticker_action", "antisticker_mute", "antisticker_ban",
        ]
        return dict(zip(keys, r))


def set_automod_setting(chat_id, field, value):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO automod_settings (chat_id) VALUES (?)", (chat_id,))
        c.execute(f"UPDATE automod_settings SET {field} = ? WHERE chat_id = ?", (value, chat_id))
        conn.commit()


def check_flood(user_id, chat_id, msg_type="text", limit=5, seconds=5) -> bool:
    now = datetime.now()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        threshold = (now - timedelta(seconds=seconds)).isoformat()
        c.execute("DELETE FROM automod_messages WHERE msg_time < ?", (threshold,))
        c.execute("""SELECT COUNT(*) FROM automod_messages 
            WHERE user_id = ? AND chat_id = ? AND msg_type = ? AND msg_time >= ?""",
            (user_id, chat_id, msg_type, threshold))
        count = c.fetchone()[0] or 0
        try:
            c.execute("""INSERT OR REPLACE INTO automod_messages 
                (user_id, chat_id, msg_time, msg_type) VALUES (?, ?, ?, ?)""",
                (user_id, chat_id, now.isoformat(), msg_type))
            conn.commit()
        except: pass
    return count >= limit


def check_sticker_spam(user_id, chat_id, limit=5, seconds=10) -> bool:
    now = datetime.now()
    threshold = (now - timedelta(seconds=seconds)).isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM automod_messages 
            WHERE user_id = ? AND chat_id = ? AND msg_type = 'sticker' AND msg_time >= ?""",
            (user_id, chat_id, threshold))
        count = c.fetchone()[0] or 0
        try:
            c.execute("""INSERT OR REPLACE INTO automod_messages 
                (user_id, chat_id, msg_time, msg_type) VALUES (?, ?, ?, 'sticker')""",
                (user_id, chat_id, now.isoformat()))
            conn.commit()
        except: pass
    return count >= limit


async def apply_automod_punishment(chat_id, user_id, rule_name, settings):
    action = settings.get(f"{rule_name}_action", "mute")
    mute_min = settings.get(f"{rule_name}_mute", 10)
    ban_min = settings.get(f"{rule_name}_ban", 1440)

    if action == "delete": return None
    if action == "mute":
        try:
            await bot.restrict_chat_member(chat_id, user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(minutes=mute_min))
        except: pass
        return f"⏱ Мут на <b>{mute_min} мин.</b>"
    if action == "warn":
        add_warn(user_id, chat_id, f"Автомод: {rule_name}", 0)
        warns_count = count_warns(user_id, chat_id)
        if warns_count >= 3:
            try:
                await bot.restrict_chat_member(chat_id, user_id,
                    permissions=types.ChatPermissions(can_send_messages=False),
                    until_date=datetime.now() + timedelta(seconds=3600))
                clear_warns(user_id, chat_id)
            except: pass
            return f"⚠️ Варн <b>{warns_count}/3</b> → <b>автомут 1 час!</b>"
        return f"⚠️ Варн <b>{warns_count}/3</b>"
    if action == "ban":
        try:
            until = datetime.now() + timedelta(minutes=ban_min) if ban_min > 0 else None
            await bot.ban_chat_member(chat_id, user_id, until_date=until)
            add_chat_ban(chat_id, user_id, f"Автомод: {rule_name}", 0, until.isoformat() if until else None)
        except: pass
        if ban_min >= 1440 * 30: return "🚫 Бан навсегда"
        elif ban_min >= 1440: return f"🚫 Бан на <b>{ban_min // 1440} дн.</b>"
        elif ban_min >= 60: return f"🚫 Бан на <b>{ban_min // 60} ч.</b>"
        else: return f"🚫 Бан на <b>{ban_min} мин.</b>"
    return None


# ================= АНТИСПАМ ИСТОРИЯ =================
def log_antispam_action(user_id, action, reason, admin_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO antispam_history (user_id, action, reason, admin_id) VALUES (?, ?, ?, ?)",
                  (user_id, action, reason, admin_id))
        conn.commit()


def get_antispam_info(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT reason, added_by, added_at FROM antispam WHERE user_id = ?", (user_id,))
        return c.fetchone()


def cancel_last_antispam_add(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, reason FROM antispam_history WHERE user_id = ? AND action = 'add' ORDER BY id DESC LIMIT 1", (user_id,))
        row = c.fetchone()
        if not row: return None
        hist_id, reason = row
        c.execute("DELETE FROM antispam_history WHERE id = ?", (hist_id,))
        conn.commit()
    return reason


# ================= РАНГ В СЕТКЕ =================
def set_grid_user_rank(grid_id, user_id, rank, added_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO grid_user_ranks 
            (grid_id, user_id, rank, added_by, added_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (grid_id, user_id, rank, added_by))
        conn.commit()


def remove_grid_user_rank(grid_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM grid_user_ranks WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        conn.commit()


# ================= БАНЫ =================
def get_all_user_bans(user_id):
    now = datetime.now().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT chat_id, reason, banned_by, banned_at, until_date FROM chat_bans 
            WHERE user_id = ? AND (until_date IS NULL OR until_date > ?) ORDER BY banned_at DESC""", (user_id, now))
        return c.fetchall()


def count_user_spam_bans(user_id):
    now = datetime.now().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM chat_bans WHERE user_id = ? 
            AND LOWER(reason) LIKE '%спам%' 
            AND (until_date IS NULL OR until_date > ?)""", (user_id, now))
        return c.fetchone()[0] or 0


def auto_add_to_antispam_if_needed(user_id):
    if is_in_antispam(user_id): return False
    spam_bans = count_user_spam_bans(user_id)
    if spam_bans < 5: return False
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by, added_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                  (user_id, "автоматическая блокировка спамера", 0))
        conn.commit()
    log_antispam_action(user_id, "add", "автоматическая блокировка спамера", 0)
    return True


# ================= STARS =================
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
        c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES ('stars_per_candy', ?)", (str(value),))
        conn.commit()


def get_stars_per_candy(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT stars_per_candy FROM stars_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if not r: return get_global_stars_per_candy()
        return r[0]


def set_stars_per_candy(chat_id, value):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO stars_settings (chat_id, stars_per_candy) VALUES (?, ?)", (chat_id, value))
        conn.commit()


def create_stars_payment(user_id, chat_id, amount_candies, stars):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO stars_payments (user_id, chat_id, amount_candies, stars_paid, status) VALUES (?, ?, ?, ?, 'pending')",
                  (user_id, chat_id, amount_candies, stars))
        conn.commit()
        return c.lastrowid


def complete_stars_payment(payment_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, chat_id, amount_candies, stars_paid, status FROM stars_payments WHERE id = ?", (payment_id,))
        r = c.fetchone()
        if not r: return None
        user_id, chat_id, amount_candies, stars_paid, status = r
        if status == "completed": return None
        c.execute("UPDATE stars_payments SET status = 'completed' WHERE id = ?", (payment_id,))
        conn.commit()
    add_candies(user_id, amount_candies, 0)
    return (user_id, chat_id, amount_candies, stars_paid)


# ================= ГРАФИКИ =================
def generate_user_activity_chart(user_id, days=30):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT date, SUM(count) FROM messages_stats WHERE user_id = ? GROUP BY date ORDER BY date DESC LIMIT ?", (user_id, days))
        rows = c.fetchall()
    if not rows: return None
    rows = rows[::-1]
    today = datetime.now().date()
    date_counts = {d: cnt or 0 for d, cnt in rows}
    full_dates, full_counts = [], []
    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        full_dates.append(day); full_counts.append(date_counts.get(day, 0))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x_labels = [d[5:] for d in full_dates]
    bars = ax.bar(range(len(full_dates)), full_counts, color='#a6e22e', width=0.7)
    step = max(1, len(full_dates) // 10)
    ax.set_xticks(range(0, len(full_dates), step))
    ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], fontsize=8)
    ax.set_title("Активность по всем чатам", fontsize=12, pad=15)
    ax.set_ylabel("Сообщений", fontsize=9)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.4); ax.set_axisbelow(True)
    for bar, cnt in zip(bars, full_counts):
        if cnt > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, str(cnt), ha='center', va='bottom', fontsize=7)
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=90, bbox_inches='tight'); buf.seek(0); plt.close()
    return buf


def generate_user_chat_activity_chart(user_id, chat_id, days=30):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT date, SUM(count) FROM messages_stats 
            WHERE user_id = ? AND chat_id = ? GROUP BY date ORDER BY date DESC LIMIT ?""",
            (user_id, chat_id, days))
        rows = c.fetchall()
    if not rows: return None
    rows = rows[::-1]
    today = datetime.now().date()
    date_counts = {d: cnt or 0 for d, cnt in rows}
    full_dates, full_counts = [], []
    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        full_dates.append(day); full_counts.append(date_counts.get(day, 0))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x_labels = [d[5:] for d in full_dates]
    bars = ax.bar(range(len(full_dates)), full_counts, color='#a6e22e', width=0.7)
    step = max(1, len(full_dates) // 10)
    ax.set_xticks(range(0, len(full_dates), step))
    ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], fontsize=8)
    ax.set_title("Активность в этом чате", fontsize=12, pad=15)
    ax.set_ylabel("Сообщений", fontsize=9)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.4); ax.set_axisbelow(True)
    for bar, cnt in zip(bars, full_counts):
        if cnt > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, str(cnt), ha='center', va='bottom', fontsize=7)
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=90, bbox_inches='tight'); buf.seek(0); plt.close()
    return buf


# ================= ВАРНЫ =================
def add_warn(user_id, chat_id, reason, warned_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO warns (user_id, chat_id, reason, warned_by) VALUES (?, ?, ?, ?)", (user_id, chat_id, reason, warned_by))
        conn.commit()


def count_warns(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM warns WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        return c.fetchone()[0]


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


def get_inactive_users(chat_id, days=7, limit=30):
    cutoff = (datetime.now().date() - timedelta(days=days)).isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT user_id, MAX(date) as last_date FROM messages_stats
            WHERE chat_id = ? GROUP BY user_id HAVING last_date < ?
            ORDER BY last_date ASC LIMIT ?""", (chat_id, cutoff, limit))
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
        if not r: return
        balance, last_tax = r
        if balance <= 0: return
        try: last_tax_dt = datetime.strptime(last_tax[:19], "%Y-%m-%d %H:%M:%S")
        except: last_tax_dt = datetime.now()
        if (datetime.now() - last_tax_dt).days >= 2:
            tax = max(1, int(balance * 0.01))
            c.execute("UPDATE coins SET balance = balance - ?, last_tax = CURRENT_TIMESTAMP WHERE user_id = ?", (tax, user_id))
            c.execute("INSERT INTO coin_log (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, -tax, "налог 1%"))
            conn.commit()


def get_farm_reward(user_id):
    info = get_coins_info(user_id)
    balance, last_farm, total_farmed, last_tax = info
    if not last_farm: return 5, 0
    try: last_farm_dt = datetime.strptime(last_farm[:19], "%Y-%m-%d %H:%M:%S")
    except: return 5, 0
    hours = (datetime.now() - last_farm_dt).total_seconds() / 3600
    if hours < 4: return 0, int((4 - hours) * 60)
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
    statuses = {}
    now = datetime.now()
    hidden = get_hidden_agents()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM agents")
        agents = c.fetchall()
        for (agent_id,) in agents:
            if agent_id in hidden: continue
            c.execute("SELECT last_seen FROM agent_activity WHERE user_id = ?", (agent_id,))
            r = c.fetchone()
            if r:
                try:
                    ls = datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
                    delta = (now - ls).total_seconds()
                    if delta <= 1800:
                        online.append(agent_id); statuses[agent_id] = "🟢 в сети"
                    else:
                        offline.append(agent_id)
                        if delta < 3600: statuses[agent_id] = f"⏱ {int(delta/60)} мин назад"
                        elif delta < 86400: statuses[agent_id] = f"⏱ {int(delta/3600)} ч назад"
                        else: statuses[agent_id] = f"⏱ {int(delta/86400)} д назад"
                except:
                    offline.append(agent_id); statuses[agent_id] = "⏱ давно"
            else:
                offline.append(agent_id); statuses[agent_id] = "⏱ не заходил"
    return online, offline, statuses


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
        c.execute("INSERT INTO chat_bans (chat_id, user_id, reason, banned_by, until_date) VALUES (?, ?, ?, ?, ?)",
                  (chat_id, user_id, reason, banned_by, until_date))
        conn.commit()


def get_last_chat_ban(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT reason, banned_by, banned_at, until_date FROM chat_bans WHERE chat_id = ? AND user_id = ? ORDER BY banned_at DESC LIMIT 1",
                  (chat_id, user_id))
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
    return (text.replace("{name}", user.first_name).replace("{first_name}", user.first_name)
        .replace("{chat}", chat_title).replace("{rules}", "правила").replace("{link}", SUPPORT_CHAT_LINK))


# ================= КАПЧА =================
import random as _random

CAPTCHA_EMOJI_ROUNDS = [
    {"question": "Выбери 🍎", "options": ["🍎", "🍌", "🍇"], "answer": "🍎"},
    {"question": "Выбери 🐱", "options": ["🐶", "🐱", "🐭"], "answer": "🐱"},
    {"question": "Выбери 🚗", "options": ["🚗", "✈️", "🚀"], "answer": "🚗"},
    {"question": "Выбери ⭐", "options": ["⭐", "🌙", "☀️"], "answer": "⭐"},
    {"question": "Выбери 💎", "options": ["💎", "💍", "👑"], "answer": "💎"},
    {"question": "Выбери 🎸", "options": ["🎸", "🎹", "🥁"], "answer": "🎸"},
    {"question": "Выбери 🍕", "options": ["🍕", "🍔", "🌮"], "answer": "🍕"},
    {"question": "Выбери 🌸", "options": ["🌸", "🌺", "🌻"], "answer": "🌸"},
    {"question": "Выбери 🐼", "options": ["🐼", "🐻", "🐨"], "answer": "🐼"},
    {"question": "Выбери 🎁", "options": ["🎁", "🎈", "🎉"], "answer": "🎁"},
]


def _make_odd_one_out():
    pools = [
        ("🍎", "🍏"), ("🐶", "🐕"), ("😀", "😃"), ("⭐", "🌟"),
        ("❤️", "🧡"), ("😺", "😸"), ("🌸", "🌼"), ("🍕", "🥪"),
    ]
    main, odd = _random.choice(pools)
    emojis = [main] * 6 + [odd]
    _random.shuffle(emojis)
    return emojis, odd


def save_captcha(user_id, chat_id, message_id, captcha_type="emoji", answer=""):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO captcha 
            (user_id, chat_id, message_id, captcha_type, answer) 
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, chat_id, message_id, captcha_type, answer))
        conn.commit()


def get_captcha(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT message_id, captcha_type, answer FROM captcha WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        return c.fetchone()


def remove_captcha(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM captcha WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()


def is_captcha_enabled(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT enabled FROM captcha_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if r is None:
            c.execute("INSERT INTO captcha_settings (chat_id, enabled) VALUES (?, 1)", (chat_id,))
            conn.commit()
            return True
        return bool(r[0])


def set_captcha_enabled(chat_id, enabled):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO captcha_settings (chat_id, enabled) VALUES (?, ?)", (chat_id, 1 if enabled else 0))
        conn.commit()


# ================= BUSINESS =================
def save_business_connection(user_id, connection_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO business_connections (user_id, connection_id) VALUES (?, ?)", (user_id, connection_id))
        conn.commit()


# ================= РЕПОРТЫ =================
def set_report_chat(chat_id, report_chat_id, added_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO report_chats (chat_id, report_chat_id, added_by, added_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                  (chat_id, report_chat_id, added_by))
        conn.commit()


def get_report_chat(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT report_chat_id FROM report_chats WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        return r[0] if r else None


def create_report(source_chat_id, reporter, target, target_message_id, message_text, reason, forward_chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO reports 
            (source_chat_id, reporter_id, reporter_name, reporter_username,
             target_id, target_name, target_username, target_message_id,
             message_text, reason, report_forward_chat_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_chat_id,
             reporter.id, reporter.first_name, reporter.username or "",
             target.id, target.first_name, target.username or "",
             target_message_id, message_text, reason, forward_chat_id))
        conn.commit()
        return c.lastrowid


def get_report(report_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, source_chat_id, reporter_id, reporter_name, reporter_username,
            target_id, target_name, target_username, target_message_id,
            message_text, reason, report_forward_chat_id, forward_message_id,
            status, reviewed_by FROM reports WHERE id = ?""", (report_id,))
        return c.fetchone()


def set_report_forward_message(report_id, forward_message_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE reports SET forward_message_id = ? WHERE id = ?", (forward_message_id, report_id))
        conn.commit()


def mark_report_reviewed(report_id, reviewed_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE reports SET status = 'reviewed', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                  (reviewed_by, report_id))
        conn.commit()# ================= РЫБАЛКА =================
FISH_LIST = [
    ("Окунь", "🐟", 1, 3, 100), ("Карась", "🐠", 2, 5, 90), ("Лещ", "🐠", 3, 8, 80),
    ("Плотва", "🐟", 2, 6, 75), ("Краснопёрка", "🐠", 3, 7, 70), ("Густера", "🐟", 4, 9, 65),
    ("Ёрш", "🐡", 3, 8, 60), ("Пескарь", "🐟", 2, 5, 55), ("Линь", "🐠", 5, 12, 50),
    ("Язь", "🐟", 6, 14, 45), ("Щука", "🐡", 8, 18, 40), ("Судак", "🐡", 10, 22, 38),
    ("Сом", "🦈", 15, 30, 30), ("Форель", "🐟", 12, 25, 28), ("Карп", "🐠", 10, 24, 25),
    ("Толстолобик", "🐡", 14, 28, 22), ("Белый амур", "🐟", 16, 32, 20), ("Налим", "🐡", 12, 26, 18),
    ("Хариус", "🐠", 10, 22, 15), ("Осётр", "🐟", 25, 50, 10), ("Стерлядь", "🐠", 20, 45, 8),
    ("Таймень", "🐡", 30, 60, 6), ("Муксун", "🐟", 28, 55, 5), ("Нельма", "🐠", 32, 65, 4),
    ("Кумжа", "🐟", 25, 50, 3.5), ("Королевский лосось", "🐠", 50, 100, 2),
    ("Белуга", "🐟", 60, 120, 1.5), ("Кета", "🐡", 45, 90, 1.2), ("Кижуч", "🐟", 55, 110, 1),
    ("Золотая рыбка", "✨", 100, 200, 0.5), ("Лунная рыба", "🌙", 150, 300, 0.2),
    ("Рыба-дракон", "🐉", 200, 400, 0.1), ("Призрачный карп", "👻", 250, 500, 0.05),
]

LEGENDARY_FISH = [
    ("Меч-рыба", "🗡", 300, 600, 30), ("Мурена", "🐍", 250, 500, 25),
    ("Гигантский сом", "🐟", 400, 800, 20), ("Акула", "🦈", 500, 1000, 15),
    ("Рыба-луна", "🌕", 600, 1200, 12), ("Голубая марлин", "🐟", 800, 1500, 10),
    ("Кит", "🐋", 1000, 2000, 5), ("Кракен", "🦑", 1500, 3000, 3),
    ("Морской дракон", "🐲", 2000, 4000, 1.5), ("Левиафан", "🐉", 5000, 10000, 0.5),
    ("Рыба-бог", "⚡", 10000, 20000, 0.1), ("Посейдон", "🔱", 20000, 50000, 0.05),
]

FISHING_GEAR = {
    "hook": {"name": "🪝 Крючок", "price": 500, "bonus": 0.05, "desc": "+5% к улову"},
    "spinning": {"name": "🎣 Спиннинг", "price": 1500, "bonus": 0.10, "desc": "+10% к улову"},
    "bucket": {"name": "🪣 Ведро", "price": 2000, "bonus": 0.0, "desc": "+1 🍬 к награде", "flat": 1},
    "boat": {"name": "🚤 Лодка", "price": 5000, "bonus": 0.0, "desc": "Шанс поймать редкую рыбу"},
    "premium_rod": {"name": "🎣 Премиум-удочка", "price": 10000, "bonus": 0.15, "desc": "+15% к улову"},
}

FISHING_EVENTS = {
    "rain": {"name": "🌧 Дождь", "bonus": 1.2, "duration": 30},
    "night": {"name": "🌙 Ночь", "bonus": 1.3, "duration": 45, "rare_boost": 2.0},
    "school": {"name": "🐟 Стая", "bonus": 1.2, "duration": 20},
    "storm": {"name": "⛈ Гроза", "bonus": 0.8, "duration": 15},
    "calm": {"name": "☀️ Штиль", "bonus": 1.0, "duration": 30},
}

FISHING_ACHIEVEMENTS = {
    "first_fish": {"name": "🥇 Первый улов", "check": lambda u: u["total_caught"] >= 1},
    "hundred_fish": {"name": "🎣 100 рыб", "check": lambda u: u["total_caught"] >= 100},
    "five_hundred": {"name": "🐟 500 рыб", "check": lambda u: u["total_caught"] >= 500},
    "level_10": {"name": "📈 Рыбак-любитель", "check": lambda u: u["level"] >= 10},
    "level_50": {"name": "🏆 Рыбак-профи", "check": lambda u: u["level"] >= 50},
    "legendary": {"name": "💎 Легендарная рыба", "check": lambda u: u["legendary_caught"] >= 1},
}

BAIT_DURATION_HOURS = 1
FISH_COOLDOWN_SECONDS = 7200
LEVEL_XP_BASE = 50


def get_fishing(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT user_id, level, xp, total_caught, total_empty,
            has_rod, bait_until, last_fish, inventory, legendary_caught 
            FROM fishing WHERE user_id = ?""", (user_id,))
        r = c.fetchone()
        if not r:
            c.execute("INSERT INTO fishing (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return (user_id, 1, 0, 0, 0, 0, None, None, "{}", 0)
        return r


def update_fishing(user_id, **kwargs):
    if not kwargs: return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [user_id]
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute(f"UPDATE fishing SET {fields} WHERE user_id = ?", values)
        conn.commit()


def set_fishing_last_fish(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE fishing SET last_fish = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
        conn.commit()


def set_fishing_bait(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE fishing SET bait_until = datetime('now', '+{} hours') WHERE user_id = ?".format(BAIT_DURATION_HOURS), (user_id,))
        conn.commit()


def log_fishing(user_id, chat_id, result, fish_name=None, reward=0):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO fishing_log (user_id, chat_id, result, fish_name, reward) VALUES (?, ?, ?, ?, ?)",
                  (user_id, chat_id, result, fish_name, reward))
        conn.commit()


def get_fishing_top(limit=10):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, total_caught, level FROM fishing WHERE total_caught > 0 ORDER BY total_caught DESC LIMIT ?", (limit,))
        return c.fetchall()


def format_fishing_cooldown(last_fish_str):
    if not last_fish_str: return 0
    try: last = datetime.strptime(last_fish_str[:19], "%Y-%m-%d %H:%M:%S")
    except: return 0
    delta = (datetime.now() - last).total_seconds()
    remaining = FISH_COOLDOWN_SECONDS - delta
    return max(0, int(remaining))


def is_bait_active(bait_until_str):
    if not bait_until_str: return False
    try:
        until = datetime.strptime(bait_until_str[:19], "%Y-%m-%d %H:%M:%S")
        return until > datetime.now()
    except: return False


def xp_needed_for_level(level):
    return LEVEL_XP_BASE * level


def get_fishing_inventory(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT inventory FROM fishing WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        if not r: return {}
        try: return json.loads(r[0] or "{}")
        except: return {}


def add_to_fishing_inventory(user_id, gear_key, count=1):
    inv = get_fishing_inventory(user_id)
    inv[gear_key] = inv.get(gear_key, 0) + count
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO fishing (user_id) VALUES (?)", (user_id,))
        c.execute("UPDATE fishing SET inventory = ? WHERE user_id = ?", (json.dumps(inv), user_id))
        conn.commit()


def get_fishing_gear_bonus(user_id):
    inv = get_fishing_inventory(user_id)
    total = 0.0; flat = 0; has_boat = False; has_premium = False
    for key, count in inv.items():
        if count <= 0: continue
        gear = FISHING_GEAR.get(key)
        if not gear: continue
        total += gear.get("bonus", 0); flat += gear.get("flat", 0)
        if key == "boat": has_boat = True
        if key == "premium_rod": has_premium = True
    return total, flat, has_boat, has_premium


def get_active_event(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("SELECT event_type, bonus, expires_at FROM fishing_events WHERE chat_id = ? AND expires_at > ?", (chat_id, now))
        return c.fetchone()


def set_event(chat_id, event_type, bonus, duration_min):
    expires = (datetime.now() + timedelta(minutes=duration_min)).isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO fishing_events (chat_id, event_type, bonus, started_at, expires_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)",
                  (chat_id, event_type, bonus, expires))
        conn.commit()


def is_events_enabled(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT events_enabled FROM fishing_events_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if r is None:
            c.execute("INSERT INTO fishing_events_settings (chat_id, events_enabled) VALUES (?, 1)", (chat_id,))
            conn.commit()
            return True
        return bool(r[0])


def set_events_enabled(chat_id, enabled):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO fishing_events_settings (chat_id, events_enabled) VALUES (?, ?)", (chat_id, 1 if enabled else 0))
        conn.commit()


def grant_fishing_achievement(user_id, chat_id, achievement_key):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO fishing_achievements (user_id, chat_id, achievement) VALUES (?, ?, ?)",
                      (user_id, chat_id, achievement_key))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def check_fishing_achievements(user_id, chat_id):
    info = get_fishing(user_id)
    (uid, level, xp, total_caught, total_empty, has_rod, bait_until, last_fish, inv, legendary) = info
    user_data = {"total_caught": total_caught, "level": level, "legendary_caught": legendary or 0}
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT achievement FROM fishing_achievements WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        have = {r[0] for r in c.fetchall()}
    new_achievements = []
    for key, ach in FISHING_ACHIEVEMENTS.items():
        if key in have: continue
        try:
            if ach["check"](user_data):
                if grant_fishing_achievement(user_id, chat_id, key):
                    new_achievements.append(ach["name"])
        except: pass
    return new_achievements


def update_legendary_count(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE fishing SET legendary_caught = legendary_caught + 1 WHERE user_id = ?", (user_id,))
        conn.commit()


def get_fish_storage(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT fish_name, fish_emoji, quantity FROM fish_storage WHERE user_id = ?", (user_id,))
        result = {}
        for name, emoji, qty in c.fetchall():
            result[name] = {"emoji": emoji, "quantity": qty}
        return result


def add_fish_to_storage(user_id, fish_name, fish_emoji, quantity=1):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO fish_storage (user_id, fish_name, fish_emoji, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, fish_name) DO UPDATE SET quantity = quantity + ?""",
            (user_id, fish_name, fish_emoji, quantity, quantity))
        conn.commit()


def remove_fish_from_storage(user_id, fish_name, quantity=1):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT quantity FROM fish_storage WHERE user_id = ? AND fish_name = ?", (user_id, fish_name))
        r = c.fetchone()
        if not r or r[0] < quantity: return False
        new_qty = r[0] - quantity
        if new_qty <= 0:
            c.execute("DELETE FROM fish_storage WHERE user_id = ? AND fish_name = ?", (user_id, fish_name))
        else:
            c.execute("UPDATE fish_storage SET quantity = ? WHERE user_id = ? AND fish_name = ?", (new_qty, user_id, fish_name))
        conn.commit()
    return True


def get_fish_price(fish_name):
    for fish in FISH_LIST:
        if fish[0] == fish_name:
            min_r, max_r = fish[2], fish[3]; weight = fish[4]
            avg = (min_r + max_r) // 2
            price = max(1, avg // 10)
            if weight >= 50: return price
            elif weight >= 15: return price + 2
            elif weight >= 3: return price + 5
            elif weight >= 0.5: return price + 10
            else: return price + 20
    for fish in LEGENDARY_FISH:
        if fish[0] == fish_name:
            avg = (fish[2] + fish[3]) // 2
            return max(50, avg // 10)
    return 5


def get_active_tournament(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("SELECT started_by, started_at, expires_at, prize FROM fishing_tournaments WHERE chat_id = ? AND expires_at > ?", (chat_id, now))
        return c.fetchone()


def create_tournament(chat_id, user_id, prize=5000, duration_min=60):
    expires = (datetime.now() + timedelta(minutes=duration_min)).isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM fishing_tournaments WHERE chat_id = ?", (chat_id,))
        c.execute("DELETE FROM fishing_tournament_members WHERE chat_id = ?", (chat_id,))
        c.execute("INSERT INTO fishing_tournaments (chat_id, started_by, expires_at, prize) VALUES (?, ?, ?, ?)",
                  (chat_id, user_id, expires, prize))
        conn.commit()


def join_tournament(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO fishing_tournament_members (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
        conn.commit()


def update_tournament_score(chat_id, user_id, count=1):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE fishing_tournament_members SET caught = caught + ? WHERE chat_id = ? AND user_id = ?",
                  (count, chat_id, user_id))
        conn.commit()


def get_tournament_members(chat_id, limit=10):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, caught FROM fishing_tournament_members WHERE chat_id = ? ORDER BY caught DESC LIMIT ?",
                  (chat_id, limit))
        return c.fetchall()


def end_tournament(chat_id):
    tour = get_active_tournament(chat_id)
    if not tour: return None
    _, _, _, prize = tour
    members = get_tournament_members(chat_id, limit=3)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM fishing_tournaments WHERE chat_id = ?", (chat_id,))
        c.execute("DELETE FROM fishing_tournament_members WHERE chat_id = ?", (chat_id,))
        conn.commit()
    if not members: return None
    winners = []
    prizes = [prize, prize // 2, prize // 4]
    for i, (uid, caught) in enumerate(members):
        add_candies(uid, prizes[i], 0)
        winners.append((uid, caught, prizes[i]))
    return winners


# ================= СТАНДАРТНЫЕ РП =================
STANDARD_RP = {
    "обнять": {"emoji": "🤗", "text": "{actor} крепко обнял(а) {target} 💞", "self_text": "{actor} обнял(а) самого себя 🤗"},
    "поцеловать": {"emoji": "💋", "text": "{actor} нежно поцеловал(а) {target} 💕", "self_text": "{actor} поцеловал(а) себя в зеркало 💋"},
    "пнуть": {"emoji": "🦵", "text": "{actor} со всей силы пнул(а) {target} под зад! 🦵💥", "self_text": "{actor} пнул(а) себя... больно же 🦵"},
    "ударить": {"emoji": "👊", "text": "{actor} ударил(а) {target} со всей силы! 💥", "self_text": "{actor} ударил(а) себя... 🤕"},
    "укусить": {"emoji": "😈", "text": "{actor} укусил(а) {target} за плечо 😈", "self_text": "{actor} укусил(а) себя 🩸"},
    "погладить": {"emoji": "🤚", "text": "{actor} погладил(а) {target} по голове ✨", "self_text": "{actor} погладил(а) себя 🤚"},
    "пощекотать": {"emoji": "😆", "text": "{actor} пощекотал(а) {target} до слёз 😆", "self_text": "{actor} пощекотал(а) себя 😅"},
    "улыбнуться": {"emoji": "😊", "text": "{actor} широко улыбнулся(ась) {target} 😊", "self_text": "{actor} улыбнулся(ась) себе 😊"},
    "подмигнуть": {"emoji": "😉", "text": "{actor} подмигнул(а) {target} 😉", "self_text": "{actor} подмигнул(а) себе 😉"},
    "потанцевать": {"emoji": "💃", "text": "{actor} пригласил(а) {target} на танец 💃🕺", "self_text": "{actor} танцует один 💃"},
    "спеть": {"emoji": "🎤", "text": "{actor} спел(а) песню для {target} 🎤🎶", "self_text": "{actor} поёт в душе 🎤"},
    "накормить": {"emoji": "🍕", "text": "{actor} накормил(а) {target} вкусным ужином 🍕", "self_text": "{actor} поел(а) один 🍽"},
    "напоить": {"emoji": "☕", "text": "{actor} напоил(а) {target} горячим чаем ☕", "self_text": "{actor} пьёт чай один 🍵"},
    "дать пять": {"emoji": "✋", "text": "{actor} дал(а) пять {target}! ✋🤚", "self_text": "{actor} хлопнул(а) в ладоши 👏"},
    "пожать руку": {"emoji": "🤝", "text": "{actor} пожал(а) руку {target} 🤝", "self_text": "{actor} пожал(а) руку себе 🤝"},
    "ущипнуть": {"emoji": "🤏", "text": "{actor} ущипнул(а) {target} за щёку 🤏", "self_text": "{actor} ущипнул(а) себя 🤏"},
    "похвалить": {"emoji": "👏", "text": "{actor} похвалил(а) {target}! 👏", "self_text": "{actor} похвалил(а) себя 👏"},
    "поругать": {"emoji": "😤", "text": "{actor} поругал(а) {target} 😤", "self_text": "{actor} ругает себя 😤"},
    "приобнять": {"emoji": "🫂", "text": "{actor} приобнял(а) {target} за плечи 🫂", "self_text": "{actor} обнял(а) себя 🫂"},
    "помириться": {"emoji": "🕊", "text": "{actor} помирился(ась) с {target} 🕊", "self_text": "{actor} помирился(ась) с собой 🕊"},
    "защитить": {"emoji": "🛡", "text": "{actor} защитил(а) {target}! 🛡", "self_text": "{actor} защищает себя 🛡"},
    "украсть": {"emoji": "🕵️", "text": "{actor} украл(а) сердечко {target} 💘", "self_text": "{actor} украл(а) что-то у себя 🤔"},
    "загипнотизировать": {"emoji": "🌀", "text": "{actor} загипнотизировал(а) {target} 🌀", "self_text": "{actor} загипнотизировал(а) себя 🌀"},
    "поклониться": {"emoji": "🙇", "text": "{actor} поклонился(ась) {target} 🙇", "self_text": "{actor} поклонился(ась) себе 🙇"},
    "сфоткаться": {"emoji": "📸", "text": "{actor} сфоткался(ась) с {target} 📸✨", "self_text": "{actor} сделал(а) селфи 📸"},
    "подарить": {"emoji": "🎁", "text": "{actor} подарил(а) {target} подарок 🎁", "self_text": "{actor} подарил(а) себе 🎁"},
    "угостить": {"emoji": "🍫", "text": "{actor} угостил(а) {target} шоколадкой 🍫", "self_text": "{actor} съел(а) один 🍫"},
    "помиловать": {"emoji": "👑", "text": "{actor} помиловал(а) {target} 👑", "self_text": "{actor} простил(а) себя 👑"},
    "проклясть": {"emoji": "🌪", "text": "{actor} проклял(а) {target} 🌪", "self_text": "{actor} проклял(а) себя 🌪"},
    "укутать": {"emoji": "🧣", "text": "{actor} укутал(а) {target} в плед 🧣", "self_text": "{actor} укутался(ась) 🧣"},
    "пожелать спокойной ночи": {"emoji": "🌙", "text": "{actor} пожелал(а) {target} спокойной ночи 🌙💤", "self_text": "{actor} себе 🌙"},
    "пожелать доброго утра": {"emoji": "☀️", "text": "{actor} пожелал(а) {target} доброго утра ☀️", "self_text": "{actor} себе ☀️"},
    "шлёпнуть": {"emoji": "✋", "text": "{actor} шлёпнул(а) {target} ✋😳", "self_text": "{actor} шлёпнул(а) себя ✋"},
    "лизнуть": {"emoji": "👅", "text": "{actor} лизнул(а) {target} 👅", "self_text": "{actor} лизнул(а) себя 🤔"},
    "укусить за ухо": {"emoji": "👂", "text": "{actor} укусил(а) {target} за ушко 👂💕", "self_text": "{actor} укусил(а) себя 👂"},
}


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


def add_chat_to_grid(grid_id, chat_id, hidden=0, description=""):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO grid_chats (grid_id, chat_id, hidden, description) VALUES (?, ?, ?, ?)",
                  (grid_id, chat_id, hidden, description))
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
        if creator and creator[0] == user_id: return True
        if user_id == OWNER_ID: return True
        c.execute("SELECT rank, is_admin FROM grid_moderators WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        r = c.fetchone()
        if not r: return False
        if r[1] == 1: return True
        return r[0] >= min_rank


def add_grid_moderator(grid_id, user_id, rank=1, is_admin=0):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO grid_moderators (grid_id, user_id, rank, is_admin) VALUES (?, ?, ?, ?)",
                  (grid_id, user_id, rank, is_admin))
        conn.commit()


def remove_grid_moderator(grid_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM grid_moderators WHERE grid_id = ? AND user_id = ?", (grid_id, user_id))
        conn.commit()


def add_grid_ban(grid_id, user_id, reason, banned_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO grid_bans (grid_id, user_id, reason, banned_by) VALUES (?, ?, ?, ?)",
                  (grid_id, user_id, reason, banned_by))
        conn.commit()


# ================= БРАКИ (DB) =================
def get_marriage(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, user1_id, user2_id, user1_name, user2_name, married_at, status, divorced_at, in_top, extra_days
            FROM marriages WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'""",
            (chat_id, user_id, user_id))
        return c.fetchone()


def get_divorced_marriage(chat_id, user_id):
    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, user1_id, user2_id, user1_name, user2_name, divorced_at
            FROM marriages WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) 
            AND status = 'divorced' AND divorced_at >= ? ORDER BY divorced_at DESC LIMIT 1""",
            (chat_id, user_id, user_id, three_days_ago))
        return c.fetchone()


def create_marriage(chat_id, u1_id, u1_name, u2_id, u2_name):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO marriages (chat_id, user1_id, user2_id, user1_name, user2_name) VALUES (?, ?, ?, ?, ?)",
                      (chat_id, u1_id, u2_id, u1_name, u2_name))
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
        c.execute("UPDATE marriages SET status = 'divorced', divorced_at = CURRENT_TIMESTAMP WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'",
                  (chat_id, user_id, user_id))
        conn.commit()


def get_all_marriages(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user1_id, user1_name, user2_id, user2_name, married_at, extra_days FROM marriages WHERE chat_id = ? AND status = 'active' ORDER BY married_at ASC",
                  (chat_id,))
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


def format_marriage_duration(married_at_str, extra_days=0):
    try: married_at = datetime.strptime(married_at_str[:19], "%Y-%m-%d %H:%M:%S")
    except:
        try: married_at = datetime.strptime(married_at_str[:10], "%Y-%m-%d")
        except: return "неизвестно"
    days = (datetime.now() - married_at).days + (extra_days or 0)
    if days < 0: days = 0
    years = days // 365
    months = (days % 365) // 30
    remaining_days = (days % 365) % 30
    parts = []
    if years > 0: parts.append(f"{years} г.")
    if months > 0: parts.append(f"{months} мес.")
    if remaining_days > 0 or not parts: parts.append(f"{remaining_days} дн.")
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
            WHERE ua.user_id = ? AND ua.chat_id = ? ORDER BY ua.given_at DESC""",
            (user_id, chat_id))
        return c.fetchall()


def give_achievement(user_id, chat_id, achievement_id, given_by):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO user_achievements (user_id, chat_id, achievement_id, given_by) VALUES (?, ?, ?, ?)",
                      (user_id, chat_id, achievement_id, given_by))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def remove_achievement(user_id, chat_id, achievement_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_achievements WHERE user_id = ? AND chat_id = ? AND achievement_id = ?",
                  (user_id, chat_id, achievement_id))
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
        c.execute("INSERT OR REPLACE INTO citizenship (user_id, chat_id, became_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                  (user_id, chat_id))
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
    try: became_at = datetime.strptime(became_at_str[:19], "%Y-%m-%d %H:%M:%S")
    except:
        try: became_at = datetime.strptime(became_at_str[:10], "%Y-%m-%d")
        except: return "недавно"
    days = (datetime.now() - became_at).days
    if days < 1: return "только что"
    elif days < 30: return f"{days} дн."
    months = days // 30
    remaining = days % 30
    if months < 12: return f"{months} мес. {remaining} дн."
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
        c.execute("INSERT OR REPLACE INTO chat_rules (chat_id, text, updated_by, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                  (chat_id, text, updated_by))
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


def format_number(n):
    if n < 1000: return str(n)
    elif n < 10000: return f"{n/1000:.1f}k"
    elif n < 1000000: return f"{n//1000}k"
    else: return f"{n/1000000:.1f}M"


def format_time_since(date_str):
    if not date_str: return "недавно"
    try:
        if isinstance(date_str, str): d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        else: d = date_str
        days = (datetime.now() - d).days
        if days < 30: return f"{days} дн."
        months = days // 30
        remaining = days % 30
        if months < 12: return f"{months} мес. {remaining} дн."
        years = months // 12
        months = months % 12
        return f"{years} г. {months} мес."
    except: return "недавно"


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
        if not r: return None
        expires_at, emoji = r
        try:
            exp_dt = datetime.strptime(expires_at[:19], "%Y-%m-%d %H:%M:%S")
            if exp_dt < datetime.now():
                c.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
                conn.commit()
                return None
        except: pass
        return (expires_at, emoji)


def add_vip_months(user_id, months):
    current = get_vip(user_id)
    if current:
        try:
            exp_dt = datetime.strptime(current[0][:19], "%Y-%m-%d %H:%M:%S")
            if exp_dt < datetime.now(): exp_dt = datetime.now()
        except: exp_dt = datetime.now()
        emoji = current[1]
    else:
        exp_dt = datetime.now()
        emoji = None
    new_exp = exp_dt + timedelta(days=30 * months)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO vip_users (user_id, expires_at, emoji) VALUES (?, ?, ?)",
                  (user_id, new_exp.isoformat(), emoji))
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
        if not r: return 0
        try:
            exp_dt = datetime.strptime(r[0][:19], "%Y-%m-%d %H:%M:%S")
            delta = exp_dt - datetime.now()
            if delta.total_seconds() < 0: return 0
            return delta.days
        except: return 0


def get_vip_emoji(user_id):
    v = get_vip(user_id)
    if v and v[1]: return v[1]
    return ""


# ================= ПОГОДА =================
def get_weather(city: str):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(city)}&count=1&language=ru&format=json"
        with urlopen(geo_url, timeout=10) as response:
            geo_data = json.loads(response.read().decode("utf-8"))
        if not geo_data.get("results"): return None
        location = geo_data["results"][0]
        lat = location["latitude"]; lon = location["longitude"]
        name = location["name"]; country = location.get("country", "")
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


# ================= ПРОВЕРКА ССЫЛОК =================
LINK_PATTERN = re.compile(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)|\{(https?://[^\s\}]+)\}')
PLACEHOLDER = "[ссылка на проверке]"


def extract_links_from_text(text: str):
    if not text: return text, []
    protected = []
    def _protect(match):
        protected.append(match.group(0))
        return f"\x00LINKPROT{len(protected)-1}\x00"
    text = re.sub(r'<(tg-emoji|a|b|i|u|s|code|pre|blockquote|tg-spoiler)\b[^>]*>.*?</\1>',
                  _protect, text, flags=re.DOTALL)
    links = []
    def replacer(match):
        if match.group(1) and match.group(2):
            link_text = match.group(1); link_url = match.group(2)
        else:
            link_url = match.group(3); link_text = link_url
        links.append({"text": link_text, "url": link_url})
        return PLACEHOLDER
    cleaned = LINK_PATTERN.sub(replacer, text)
    for i, p in enumerate(protected):
        cleaned = cleaned.replace(f"\x00LINKPROT{i}\x00", p)
    return cleaned, links# ================= /START =================
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
            except: pass
    else:
        text += "  <i>пока нет</i>\n"

    text += (
        f"\n📄 <b>Соглашение:</b> <a href='{TERMS_URL}'>Прочитать</a>\n\n"
        f"{em('sos', '🆘')} <b>Поддержка:</b> {SUPPORT_CHAT_LINK}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить бота в чат", url=add_url)],
        [InlineKeyboardButton(text="🍬 Купить ириски", callback_data="buy_candies_menu")],
        [
            InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_CHAT_LINK),
            InlineKeyboardButton(text="📢 Канал", url=SUPPORT_CHANNEL_LINK)
        ],
        [InlineKeyboardButton(text="📄 Пользовательское соглашение", url=TERMS_URL)]
    ])

    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "buy_candies_menu")
async def buy_candies_menu(callback: types.CallbackQuery):
    price = get_stars_per_candy(callback.message.chat.id)
    await callback.message.answer(
        f"🍬 <b>Купить ириски за ⭐ Stars</b>\n\n"
        f"💰 Курс: <b>{price} ⭐ = 1 🍬</b>\n\n"
        f"📌 Напишите:\n"
        f"<code>.купитьириски 10</code> → {price * 10} ⭐",
        parse_mode="HTML", disable_web_page_preview=True
    )
    await callback.answer()


# ================= КОМАНДЫ =================
@cmd("команды")
@cmd("commands")
async def commands_link_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📖 Открыть команды", url=TELETYPE_URL)
    ]])
    await message.reply(
        f"📖 <b>Все команды бота Mos</b>\n\n"
        f"🔗 <a href='{TELETYPE_URL}'>Mos-command</a>",
        parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb
    )

# ================= ИНФОБОТ =================
@cmd("инфобот")
async def bot_info_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply(
            f"{em('cross', '❌')} Только владелец.\n🆔 Ваш ID: <code>{message.from_user.id}</code>\n👑 ID владельца: <code>{OWNER_ID}</code>",
            parse_mode="HTML", disable_web_page_preview=True
        )
    start = datetime.now()
    sent = await message.reply("🏓 Считаю...")
    ping_ms = int((datetime.now() - start).total_seconds() * 1000)
    try: await sent.delete()
    except: pass

    uptime = datetime.now() - BOT_START_TIME
    days = uptime.days
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    if days > 0: uptime_str = f"{days} д. {hours} ч."
    elif hours > 0: uptime_str = f"{hours} ч. {minutes} мин."
    else: uptime_str = f"{minutes} мин."

    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users"); total_users = c.fetchone()[0] or 0
        c.execute("SELECT SUM(count) FROM messages_stats"); total_messages = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(DISTINCT chat_id) FROM messages_stats"); total_chats = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM agents"); total_agents = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM antispam"); total_antispam = c.fetchone()[0] or 0

    try:
        db_size = os.path.getsize(DATABASE_PATH)
        if db_size < 1024: db_size_str = f"{db_size} Б"
        elif db_size < 1024 * 1024: db_size_str = f"{db_size / 1024:.1f} КБ"
        else: db_size_str = f"{db_size / (1024 * 1024):.2f} МБ"
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
    
@cmd("помощь")
async def help_cmd(message: types.Message):
    online, offline, statuses = get_agents_status()
    agents_text = ""
    if online:
        agents_text += f"{em('check', '✅')} <b>В сети:</b>\n"
        for uid in online:
            try:
                user = await bot.get_chat(uid)
                agents_text += f"  • {user_link(uid, user.first_name, user.username)}\n"
            except:
                agents_text += f"  • ID: <code>{uid}</code>\n"
    else:
        agents_text += f"{em('cross', '❌')} <b>В сети:</b> нет\n"
    if offline:
        agents_text += f"\n{em('cross', '❌')} <b>Не в сети:</b>\n"
        for uid in offline:
            try:
                user = await bot.get_chat(uid)
                status = statuses.get(uid, "")
                agents_text += f"  • {user_link(uid, user.first_name, user.username)} — <i>{status}</i>\n"
            except:
                agents_text += f"  • ID: <code>{uid}</code> — <i>{statuses.get(uid, '')}</i>\n"

    help_text = (
        f"{em('sos', '🆘')} <b>Помощь по боту {BOT_NAME}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{agents_text}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📖 <b>Команды:</b> <a href='{TELETYPE_URL}'>Mos-command</a>\n"
        f"📄 <b>Соглашение:</b> <a href='{TERMS_URL}'>Прочитать</a>\n"
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
        parse_mode="HTML", disable_web_page_preview=True
    )


# ================= ПОГОДА =================
@cmd("погода")
async def weather_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply(
            "🌤 <b>Погода</b>\n\n📌 Напиши: <code>.погода Москва</code>",
            parse_mode="HTML", disable_web_page_preview=True
        )
    city = args[1].strip()
    if not city:
        return await message.reply("❌ Укажи город.", parse_mode="HTML", disable_web_page_preview=True)

    msg = await message.reply(f"🌍 Ищу погоду в <b>{city}</b>...", parse_mode="HTML", disable_web_page_preview=True)
    weather = get_weather(city)
    if not weather:
        return await msg.edit_text(f"{em('cross', '❌')} Город <b>{city}</b> не найден.", parse_mode="HTML")

    code = weather["code"]
    weather_desc = get_weather_emoji(code) if code is not None else "🌡️ Погода"
    text = (
        f"🌍 <b>{weather['name']}</b>"
        + (f", {weather['country']}" if weather.get('country') else "")
        + f"\n\n{weather_desc}\n"
        f"🌡 Температура: <b>{weather['temperature']}°C</b>\n"
        f"💧 Влажность: <b>{weather['humidity']}%</b>\n"
        f"💨 Ветер: <b>{weather['wind']} м/с</b>"
    )
    try: await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    except: await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


# ================= МОЙ ПОЛ =================
@dp.message(lambda m: m.text and re.match(r'^мой\s+пол\s+\S+', m.text.strip(), re.IGNORECASE))
async def set_gender_cmd(message: types.Message):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("📌 <code>мой пол М</code> или <code>мой пол Ж</code>", parse_mode="HTML")
    v = parts[2].strip().lower()
    if v in ["м", "муж", "мужской"]: v = "Мужской"
    elif v in ["ж", "жен", "женский"]: v = "Женский"
    else: v = "Другой"
    update_user_profile(message.from_user.id, "gender", v)
    await message.reply(f"✅ Пол: <b>{v}</b>", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-мой пол")
async def remove_gender_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "gender", None)
    await message.reply("✅ Удалён.", parse_mode="HTML", disable_web_page_preview=True)


# ================= МОЙ ДР =================
@dp.message(lambda m: m.text and re.match(r'^мой\s+др\s+\S+', m.text.strip(), re.IGNORECASE))
async def set_birth_cmd(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) < 3:
        return await message.reply("📌 <code>мой др 01.01.2000</code>", parse_mode="HTML")
    date = parts[2].strip()
    vis = parts[3].lower() if len(parts) >= 4 else "месяц"
    update_user_profile(message.from_user.id, "birth_date", date)
    update_user_profile(message.from_user.id, "birth_visibility", vis)
    await message.reply(f"✅ ДР: <b>{date}</b>", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-мой др")
async def remove_birth_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "birth_date", None)
    await message.reply("✅ Удалён.", parse_mode="HTML", disable_web_page_preview=True)


# ================= МОЙ ГОРОД =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("!мой город"))
async def set_city_cmd(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return
    update_user_profile(message.from_user.id, "city", args[2].strip()[:50])
    await message.reply(f"✅ Город: <b>{args[2].strip()[:50]}</b>", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-мой город")
async def remove_city_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "city", None)
    await message.reply("✅ Удалён.", parse_mode="HTML", disable_web_page_preview=True)


# ================= ПРОФИЛЬ =================
@cmd("профиль")
async def profile_cmd(message: types.Message):
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
    if not target: target = message.from_user

    today_count, all_count = get_user_stats(target.id, message.chat.id)
    in_antispam = is_in_antispam(target.id)
    in_ignore = is_ignored(message.chat.id, target.id)
    if in_antispam and in_ignore: status = f"{em('ban', '🚫')} В АС + {em('mute', '🔇')} В игноре"
    elif in_antispam: status = f"{em('ban', '🚫')} В антиспаме"
    elif in_ignore: status = f"{em('mute', '🔇')} В игноре"
    else: status = f"{em('check', '✅')} Чист"

    role_line = ""
    if target.id == OWNER_ID: role_line = "👑 <b>Владелец бота</b>"
    elif get_rank(message.chat.id, target.id) == 5: role_line = "⚜️ <b>Владелец чата</b>"
    elif is_bot_promoted(target.id, message.chat.id): role_line = "🛡 <b>Telegram-админ</b>"
    elif is_agent(target.id): role_line = "🛡 <b>Агент поддержки Mos</b>"

    rank = get_rank(message.chat.id, target.id)
    rank_name = RANK_NAMES.get(rank, "👤 Участник")

    nick = get_user_nick(target.id, message.chat.id)
    display_name = nick or target.first_name
    rank_text = get_user_rank_text(target.id, message.chat.id)

    cit = get_citizenship_info(target.id)
    cit_line = ""
    if cit:
        cit_chat_id, cit_date = cit
        try:
            cit_chat = await bot.get_chat(cit_chat_id)
            cit_title = cit_chat.title or f"Чат {cit_chat_id}"
        except: cit_title = f"Чат {cit_chat_id}"
        cit_line = f"🏠 Гражданин «{cit_title}» {format_citizenship_duration(cit_date)}"

    vip_emoji = get_vip_emoji(target.id)

    user_ach = get_user_achievements(target.id, message.chat.id)
    ach_text = ""
    if user_ach:
        ach_text = " ".join([f"{a[2]}{a[1]}" for a in user_ach])

    about = get_user_about(target.id)

    lines = []
    lines.append(f"{em('user', '👤')} <b>Профиль {vip_emoji}{display_name}{vip_emoji}</b>")
    lines.append("")
    if role_line: lines.append(role_line)
    lines.append(f"{em('id', '🆔')} ID: <code>{target.id}</code>")
    if nick and nick != target.first_name: lines.append(f"📛 Имя: {target.first_name}")
    lines.append(f"🔤 Ник: {nick or display_name}")
    lines.append(f"📌 Звание: {rank_text or '—'}")
    lines.append(f"🏆 Ранг: {rank_name}")
    lines.append("")
    lines.append(f"{em('stats', '📊')} Сегодня: <b>{today_count}</b> • Всего: <b>{all_count}</b>")
    lines.append(f"{em('shield', '🛡')} Статус: {status}")
    if cit_line: lines.append(cit_line)
    if ach_text:
        lines.append("")
        lines.append(f"🎖 <b>Ачивки:</b> {ach_text}")
    if about:
        lines.append("")
        lines.append(f"✏️ <b>О себе:</b>")
        lines.append(about)

    text = "\n".join(lines)

    chart_buf = None
    try: chart_buf = generate_user_chat_activity_chart(target.id, message.chat.id, days=30)
    except: pass

    if chart_buf:
        await message.reply_photo(
            photo=types.BufferedInputFile(chart_buf.getvalue(), filename="user_chat_activity.png"),
            caption=text, parse_mode="HTML"
        )
    else:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


# ================= АНКЕТА =================
@cmd("анкета")
async def profile_full_cmd(message: types.Message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            try:
                if args[1].startswith('@'): target = await bot.get_chat(args[1])
                elif args[1].isdigit(): target = await bot.get_chat(int(args[1]))
            except: pass
    if not target: target = message.from_user

    register_user(target.id, target.first_name, target.username or "")
    user_info = get_user_info(target.id)
    if not user_info: first_seen = datetime.now()
    else:
        try: first_seen = datetime.strptime(user_info[0], "%Y-%m-%d %H:%M:%S")
        except: first_seen = datetime.now()

    profile = get_user_profile(target.id)
    gender, birth_date, city, bio, is_hidden, birth_visibility, motto, show_cit = profile

    viewer_id = message.from_user.id
    is_owner_viewer = (viewer_id == OWNER_ID)
    is_agent_viewer = is_agent(viewer_id)
    is_self = (viewer_id == target.id)
    can_see_full = is_owner_viewer or is_agent_viewer or is_self or (not is_hidden)
    if not can_see_full:
        return await message.reply(f"🔒 {mention(target)} скрыл анкету.", parse_mode="HTML", disable_web_page_preview=True)

    day, week, month, total = get_activity_stats(target.id)

    role_line = ""
    if target.id == OWNER_ID: role_line = "👑 <b>Владелец бота</b>"
    elif get_rank(message.chat.id, target.id) == 5: role_line = "⚜️ <b>Владелец чата</b>"
    elif is_bot_promoted(target.id, message.chat.id): role_line = "🛡 <b>Telegram-админ</b>"
    elif is_agent(target.id): role_line = "🛡 <b>Агент поддержки Mos</b>"

    user_ach = get_user_achievements(target.id, message.chat.id)
    ach_text = ""
    if user_ach:
        ach_text = " ".join([f"{a[2]}{a[1]}" for a in user_ach])

    cit_line = ""
    cit = get_citizenship_info(target.id)
    if cit and (show_cit or is_owner_viewer or is_agent_viewer or is_self):
        cit_chat_id, cit_date = cit
        try:
            cit_chat = await bot.get_chat(cit_chat_id)
            cit_title = cit_chat.title or "Чат"
        except: cit_title = "Чат"
        cit_line = f"\n🏠 Гражданин «{cit_title}» {format_citizenship_duration(cit_date)}"

    reg_date = first_seen.strftime("%d.%m.%Y")
    time_in = format_time_since(first_seen.strftime("%Y-%m-%d"))

    text = (
        f"👤 <b>Это {mention(target)}</b>\n"
        f"🆔 <code>{target.id}</code>\n"
    )
    if role_line: text += f"{role_line}\n"
    text += (
        f"\n⏱ В Mos с {reg_date} ({time_in})\n"
        f"👨 Пол: {gender or '—'}\n"
        f"📆 ДР: {birth_date or '—'}\n"
        f"🗺 Город: {city or '—'}\n"
        f"📊 Активность: {format_number(day)}|{format_number(week)}|{format_number(month)}|{format_number(total)}"
        f"{cit_line}"
    )
    if ach_text: text += f"\n\n🎖 <b>Ачивки:</b> {ach_text}"
    if motto: text += f"\n\n💭 {motto}"
    if bio: text += f"\n\n📝 {bio}"

    chart = None
    try: chart = generate_user_activity_chart(target.id, days=30)
    except: pass
    if chart:
        await message.reply_photo(photo=types.BufferedInputFile(chart.getvalue(), filename="anketa.png"), caption=text, parse_mode="HTML")
    else:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("мойид")
async def myid_cmd(message: types.Message):
    await message.reply(f"{em('id', '🆔')} Ваш ID: <code>{message.from_user.id}</code>", parse_mode="HTML", disable_web_page_preview=True)


@cmd("ид")
async def get_id_cmd(message: types.Message):
    target = None
    if message.reply_to_message: target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            arg = args[1]
            if arg.isdigit():
                user_id = int(arg)
                try: target = await bot.get_chat(user_id)
                except:
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        c = conn.cursor()
                        c.execute("SELECT first_name, username FROM users WHERE user_id = ?", (user_id,))
                        r = c.fetchone()
                        if r:
                            return await message.reply(f"{em('id', '🆔')} ID: <code>{user_id}</code>\n📛 {r[0]}", parse_mode="HTML", disable_web_page_preview=True)
                    return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML", disable_web_page_preview=True)
            elif arg.startswith('@'):
                try: target = await bot.get_chat(arg)
                except: return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML", disable_web_page_preview=True)
    if not target: target = message.from_user
    await message.reply(
        f"{em('id', '🆔')} <b>Информация</b>\n\n👤 Имя: {mention(target)}\n🆔 ID: <code>{target.id}</code>\n👤 Username: @{target.username if target.username else '—'}",
        parse_mode="HTML", disable_web_page_preview=True
    )


@cmd("чатид")
async def get_chat_id_cmd(message: types.Message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        fwd = message.reply_to_message.forward_from_chat
        return await message.reply(
            f"{em('id', '🆔')} <b>ID пересланного чата</b>\n\n📛 <b>{fwd.title or 'Без названия'}</b>\n🆔 <code>{fwd.id}</code>",
            parse_mode="HTML", disable_web_page_preview=True
        )
    await message.reply(
        f"{em('id', '🆔')} <b>Информация о чате</b>\n\n📛 <b>{message.chat.title or 'Личный чат'}</b>\n🆔 <code>{message.chat.id}</code>",
        parse_mode="HTML", disable_web_page_preview=True
    )


@cmd("топ")
async def top_cmd(message: types.Message):
    args = message.text.split()
    period = "today"; period_name = "за сегодня"
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
        except: name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{count}</b>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


# ================= КТО НЕ ПИСАЛ =================
@cmd("кто не писал")
@cmd("неактивные")
async def inactive_users_cmd(message: types.Message):
    chat_id = message.chat.id
    args = message.text.split()
    days = 7
    if len(args) >= 2 and args[1].isdigit():
        days = max(1, min(365, int(args[1])))

    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass

    if not is_creator and not has_permission(chat_id, message.from_user.id, 2):
        if not await is_tg_admin(chat_id, message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Нужен Ст. Модератор (2+) или ТГ-админ.", parse_mode="HTML", disable_web_page_preview=True)

    inactive = get_inactive_users(chat_id, days=days, limit=30)
    if not inactive:
        return await message.reply(f"{em('check', '✅')} <b>Все активны!</b>", parse_mode="HTML", disable_web_page_preview=True)

    text = f"💤 <b>Не писали {days}+ дней</b> ({len(inactive)}):\n\n"
    for i, (user_id, last_date) in enumerate(inactive, 1):
        try:
            last_dt = datetime.strptime(last_date[:10], "%Y-%m-%d").date()
            days_ago = (datetime.now().date() - last_dt).days
        except: days_ago = "?"
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT first_name, username FROM users WHERE user_id = ?", (user_id,))
            r = c.fetchone()
        if r: name_display = user_link(user_id, r[0], r[1])
        else: name_display = f"<code>{user_id}</code>"
        if days_ago == "?": time_str = "?"
        elif days_ago < 30: time_str = f"{days_ago} дн."
        elif days_ago < 365: time_str = f"{days_ago // 30} мес."
        else: time_str = f"{days_ago // 365} г."
        text += f"{i}. {name_display} — <i>{time_str} назад</i>\n"
    text += f"\n📌 Показаны первые 30."
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


# ================= ОБНОВИТЬ ЧАТ =================
@cmd("обновить чат")
@cmd("обновитьчат")
async def refresh_chat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True)

    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass

    if not is_creator and not has_permission(message.chat.id, message.from_user.id, 3):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True)

    status_msg = await message.reply("🔄 Обновляю...")
    try:
        chat = await bot.get_chat(message.chat.id)
        title = chat.title or "Без названия"
        description = chat.description or ""
        link = f"https://t.me/{chat.username}" if chat.username else None
        code = get_chat_code(message.chat.id)
        bot_is_admin = False
        try:
            bot_member = await bot.get_chat_member(message.chat.id, bot.id)
            bot_is_admin = bot_member.status in ["administrator", "creator"]
        except: pass
        admin_icon = "✅ Да" if bot_is_admin else "❌ Нет"
        link_text = f"<a href='{link}'>ссылка</a>" if link else "—"
        text = (
            f"{em('check', '✅')} <b>Чат обновлён!</b>\n\n"
            f"📛 <b>Название:</b> {title}\n"
            f"🆔 <b>ID:</b> <code>{message.chat.id}</code>\n"
            f"🔑 <b>Код:</b> <code>{code}</code>\n"
            f"🔗 <b>Ссылка:</b> {link_text}\n"
            f"👑 <b>Бот админ:</b> {admin_icon}\n"
            f"📝 <b>Описание:</b> {description[:200] or '—'}"
        )
        try: await status_msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
        except: await status_msg.edit_text(text)
    except Exception as e:
        await status_msg.edit_text(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")


# ================= ДК =================
@cmd("дк")
async def dk_main_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True)

    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass
    if message.from_user.id == OWNER_ID: is_creator = True

    if not is_creator and not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True)

    args = message.text.split(maxsplit=2)
    if len(args) < 2: return await _show_dk_list(message)

    if args[1].lower() in ["сброс", "reset"]:
        reset_command_access(message.chat.id)
        return await message.reply(f"{em('check', '✅')} Все ДК сброшены.", parse_mode="HTML", disable_web_page_preview=True)

    if len(args) < 3:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>.дк бан 3</code>\n<code>.дк бан все</code>\n"
            "<code>.дк бан выкл</code>\n<code>.дк бан создатель</code>\n"
            "<code>.дк сброс</code>",
            parse_mode="HTML", disable_web_page_preview=True
        )

    cmd_name = args[1].lower().strip()
    value = args[2].lower().strip()

    if cmd_name not in DEFAULT_ACCESS:
        return await message.reply(f"{em('cross', '❌')} Команда <code>{cmd_name}</code> не найдена.", parse_mode="HTML", disable_web_page_preview=True)

    if value in ["все", "all", "0"]: new_rank = 0
    elif value in ["выкл", "off", "отключить", "-1"]: new_rank = -1
    elif value in ["создатель", "creator", "владелецчата", "-2"]: new_rank = -2
    elif value.isdigit() and 0 <= int(value) <= 5: new_rank = int(value)
    else:
        return await message.reply("❌ Допустимые: <code>все</code>, <code>0-5</code>, <code>выкл</code>, <code>создатель</code>", parse_mode="HTML", disable_web_page_preview=True)

    if not is_creator:
        actor_rank = get_rank(message.chat.id, message.from_user.id)
        if new_rank > actor_rank and new_rank not in (-1, -2):
            return await message.reply(f"{em('cross', '❌')} Нельзя выше своего.", parse_mode="HTML", disable_web_page_preview=True)

    set_command_access(message.chat.id, cmd_name, new_rank)
    level_names = {-2: "👑 Только создатель", -1: "🔒 Отключено", 0: "🌐 Все", 1: "🛡 Мл. Модератор", 2: "🛡 Ст. Модератор", 3: "👑 Мл. Админ", 4: "👑 Ст. Админ", 5: "⚜️ Владелец"}
    return await message.reply(
        f"{em('check', '✅')} ДК обновлён\n📌 <code>{cmd_name}</code>\n🔒 {level_names.get(new_rank, str(new_rank))}",
        parse_mode="HTML", disable_web_page_preview=True
    )


async def _show_dk_list(message: types.Message):
    chat_id = message.chat.id
    access = get_all_access_for_chat(chat_id)
    groups = {-2: [], -1: [], 0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
    for cmd_name, rank in access.items():
        if rank in groups: groups[rank].append(cmd_name)
    level_names = {-2: "👑 Только создатель", -1: "🔒 Отключено", 0: "🌐 Все", 1: "🛡 Мл. Модератор", 2: "🛡 Ст. Модератор", 3: "👑 Мл. Админ", 4: "👑 Ст. Админ", 5: "⚜️ Владелец"}
    text = f"{em('shield', '🛡')} <b>Доступы к командам (ДК)</b>\n\n"
    for level in [-2, -1, 0, 1, 2, 3, 4, 5]:
        cmds = sorted(groups[level])
        if not cmds: continue
        text += f"{level_names[level]} ({len(cmds)}):\n"
        for cmd_name in cmds[:15]:
            text += f"  • <code>{cmd_name}</code>\n"
        if len(cmds) > 15: text += f"  ... +{len(cmds)-15} ещё\n"
        text += "\n"
    text += "<code>.дк бан 3</code> | <code>.дк бан все</code> | <code>.дк сброс</code>"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+команды", "+ команды", "+оповещения", "+ оповещения"])
async def enable_command_notify_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass
    if message.from_user.id == OWNER_ID: is_creator = True
    if not is_creator and not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True)
    if is_command_notify_enabled(message.chat.id):
        return await message.reply(f"ℹ️ Уже включены.", parse_mode="HTML", disable_web_page_preview=True)
    set_command_notify_enabled(message.chat.id, True)
    await message.reply(f"{em('check', '✅')} Оповещения включены!\n📌 Отключить: <code>-команды</code>", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-команды", "- команды", "-оповещения", "- оповещения"])
async def disable_command_notify_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass
    if message.from_user.id == OWNER_ID: is_creator = True
    if not is_creator and not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True)
    if not is_command_notify_enabled(message.chat.id):
        return await message.reply(f"ℹ️ Уже выключены.", parse_mode="HTML", disable_web_page_preview=True)
    set_command_notify_enabled(message.chat.id, False)
    await message.reply(f"{em('check', '✅')} Оповещения выключены!", parse_mode="HTML", disable_web_page_preview=True)


@cmd("оповещения")
@cmd("командыстатус")
async def command_notify_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    enabled = is_command_notify_enabled(message.chat.id)
    status = "🟢 включены" if enabled else "🔴 выключены"
    await message.reply(f"🔔 Оповещения: {status}\n\n<code>+команды</code> / <code>-команды</code>", parse_mode="HTML", disable_web_page_preview=True)


# ================= МОДЕРАЦИЯ =================
@cmd("бан")
async def ban_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    args = message.text.split()
    duration_seconds = None; duration_text = "навсегда"
    if len(args) >= 3 and args[1].isdigit():
        amount = int(args[1]); unit = args[2].lower().rstrip('.,!?')
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
    if len(parts) > 1: reason = parts[1].strip()
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
        response = (f"{em('ban', '🚫')} {mention(target)} бан {ban_type}\n"
                    f"👮 {mention(message.from_user)}\n📝 {reason}")
        if auto_added: response += f"\n\n☢️ Автоматически в антиспам!"
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
    try: await bot.unban_chat_member(message.chat.id, target.id)
    except: pass
    try:
        await bot.restrict_chat_member(message.chat.id, target.id, permissions=types.ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True,
            can_add_web_page_previews=True, can_send_polls=True, can_invite_users=True))
    except: pass
    clear_chat_ban(message.chat.id, target.id)
    await message.reply(f"{em('check', '✅')} {mention(target)} разбанен.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("мут")
async def mute_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True)
    args = message.text.split()
    duration_seconds = 1800; duration_text = "30 мин."
    if len(args) >= 3 and args[1].isdigit():
        amount = int(args[1]); unit = args[2].lower().rstrip('.,!?')
        if amount > 0:
            if unit in ['сек', 'секунд']: duration_seconds, duration_text = amount, f"{amount} сек."
            elif unit in ['мин', 'минут', 'м']: duration_seconds, duration_text = amount * 60, f"{amount} мин."
            elif unit in ['час', 'часа', 'часов', 'ч']: duration_seconds, duration_text = amount * 3600, f"{amount} ч."
            elif unit in ['день', 'дня', 'дней', 'д']: duration_seconds, duration_text = amount * 86400, f"{amount} дн."
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
    if len(parts) > 1: reason = parts[1].strip()
    try:
        await bot.restrict_chat_member(message.chat.id, target.id,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(seconds=duration_seconds))
        await message.reply(f"{em('mute', '🔇')} {mention(target)} замучен на <b>{duration_text}</b>\n👮 {mention(message.from_user)}\n📝 {reason}", parse_mode="HTML", disable_web_page_preview=True)
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
        await bot.restrict_chat_member(message.chat.id, target.id, permissions=types.ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
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
    if not has_permission(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: return
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']: return
        if bot_member.status == 'administrator' and not bot_member.can_delete_messages: return
    except: return
    args = message.text.split()
    count = 1
    if len(args) >= 2 and args[1].isdigit():
        count = max(1, min(100, int(args[1])))
    if count == 1:
        try: await message.reply_to_message.delete()
        except: pass
    else:
        for msg_id in range(message.reply_to_message.message_id, message.message_id + 1):
            if msg_id != message.message_id:
                try: await bot.delete_message(message.chat.id, msg_id)
                except: pass
    try: await message.delete()
    except: pass


# ================= ПИН =================
@cmd("пин")
@cmd("закрепить")
async def pin_message_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Нет прав.", disable_web_page_preview=True)
    if not message.reply_to_message:
        return await message.reply("📌 Ответьте на сообщение.", disable_web_page_preview=True)
    args = message.text.split()
    silent = len(args) >= 2 and args[1].lower() in ["тихо", "silent", "s", "тих"]
    try:
        await bot.pin_chat_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id, disable_notification=silent)
        try: await message.delete()
        except: pass
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} {e}", disable_web_page_preview=True)


@cmd("анпин")
@cmd("открепить")
async def unpin_message_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id): return
    try:
        if message.reply_to_message:
            await bot.unpin_chat_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
        else:
            await bot.unpin_all_chat_messages(chat_id=message.chat.id)
        await message.reply(f"{em('check', '✅')} Готово.", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} {e}", disable_web_page_preview=True)


# ================= ВАРНЫ =================
@cmd("варн")
async def warn_cmd(message: types.Message):
    actor_id = message.from_user.id
    actor_rank = get_rank(message.chat.id, actor_id)
    if actor_rank < 1:
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True)
    target_rank = get_rank(message.chat.id, target.id)
    if actor_rank < 5 and target_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    reason = "Без причины"
    parts = message.text.split('\n', 1)
    if len(parts) > 1: reason = parts[1].strip()
    add_warn(target.id, message.chat.id, reason, actor_id)
    warns_count = count_warns(target.id, message.chat.id)
    if warns_count >= 3:
        try:
            await bot.restrict_chat_member(message.chat.id, target.id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(seconds=3600))
            clear_warns(target.id, message.chat.id)
            return await message.reply(f"{em('pencil', '✏️')} {mention(target)} 3-й варн!\n{em('mute', '🔇')} Мут 1 час.", parse_mode="HTML", disable_web_page_preview=True)
        except: pass
    await message.reply(f"{em('pencil', '✏️')} {mention(target)} предупреждение!\n{em('stats', '📊')} {warns_count}/3", parse_mode="HTML", disable_web_page_preview=True)


@cmd("варны")
async def warns_list_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, reason, warned_at FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY warned_at DESC", (target.id, message.chat.id))
        warns = c.fetchall()
    if not warns:
        return await message.reply(f"{em('check', '✅')} Нет варнов.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"{em('pencil', '✏️')} <b>Варны {mention(target)}:</b> ({len(warns)}/3)\n\n"
    for i, (_, reason, warned_at) in enumerate(warns, 1):
        text += f"{i}. {reason}\n   {em('calendar', '🗓')} {warned_at[:10]}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("снятьварн")
async def unwarn_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target: return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM warns WHERE id = (SELECT id FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY warned_at DESC LIMIT 1)",
                  (target.id, message.chat.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Варн снят. Осталось: {count_warns(target.id, message.chat.id)}/3", parse_mode="HTML", disable_web_page_preview=True)


@cmd("сбросварнов")
async def clear_warns_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target: return
    count = count_warns(target.id, message.chat.id)
    clear_warns(target.id, message.chat.id)
    await message.reply(f"♻️ Сброшено варнов: {count}", parse_mode="HTML", disable_web_page_preview=True)


@cmd("наказания")
async def show_punishments(message: types.Message):
    if not await is_tg_admin(message.chat.id, message.from_user.id): return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True)
    user_id = target.id
    blocks = []
    try:
        member = await bot.get_chat_member(message.chat.id, user_id)
        if member.status == "kicked":
            ban_info = get_last_chat_ban(message.chat.id, user_id)
            if ban_info: blocks.append(f"{em('ban', '🚫')} <b>Забанен</b>\n📝 {ban_info[0]}")
            else: blocks.append(f"{em('ban', '🚫')} <b>Забанен</b>")
    except: pass
    if is_in_antispam(user_id):
        info = get_antispam_info(user_id)
        if info: blocks.append(f"{em('shield', '🛡')} <b>В антиспаме MOS</b>\n📝 {info[0]}")
    if not blocks:
        return await message.reply(f"{em('check', '✅')} {mention(target)} чист.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"{em('calendar', '🗓')} <b>Наказания {mention(target)}</b>\n\n" + "\n\n".join(blocks)
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("баны")
async def show_bans(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1): return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True)
    user_id = target.id
    name = user_link(user_id, target.first_name, target.username)
    bans = get_all_user_bans(user_id)
    text = f"{em('ban', '🚫')} <b>Баны {name}</b>\n{em('id', '🆔')} <code>{user_id}</code>\n\n"
    if is_in_antispam(user_id):
        info = get_antispam_info(user_id)
        if info: text += f"☢️ <b>В АНТИСПАМЕ</b>\n📝 {info[0]}\n\n"
    else: text += f"{em('check', '✅')} <b>Не в антиспаме</b>\n\n"
    text += f"{em('stats', '📊')} Банов: <b>{len(bans)}</b>\n\n"
    for i, (chat_id, reason, banned_by, banned_at, until_date) in enumerate(bans[:10], 1):
        text += f"<b>{i}.</b> 📝 {reason}\n   {em('calendar', '🗓')} {banned_at[:10]}\n\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


# ================= АГЕНТЫ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+агент"))
async def add_agent_cmd(message: types.Message):
    actor_id = message.from_user.id
    if actor_id != OWNER_ID and not has_agent_rank(actor_id, 4):
        return await message.reply(f"{em('cross', '❌')} Только Гл. Агент (4).", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("📌 <code>+Агент @user 2</code>", parse_mode="HTML", disable_web_page_preview=True)
    if target.id == OWNER_ID: return
    args = message.text.split()
    rank = 1
    for a in args[1:]:
        if a.isdigit(): rank = int(a); break
    if rank not in [1, 2, 3, 4]:
        return await message.reply(f"{em('cross', '❌')} Ранг 1-4.", parse_mode="HTML", disable_web_page_preview=True)
    set_agent_rank(target.id, rank, actor_id)
    rank_name = AGENT_RANKS.get(rank, "🛡 Агент")
    await message.reply(f"{em('check', '✅')} {mention(target)} теперь <b>{rank_name}</b>!", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-агент"))
async def remove_agent_cmd(message: types.Message):
    actor_id = message.from_user.id
    if actor_id != OWNER_ID and not has_agent_rank(actor_id, 4): return
    target, _ = await resolve_target(message)
    if not target: return
    remove_agent(target.id)
    await message.reply(f"{em('cross', '❌')} {mention(target)} не агент.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("агенты")
async def list_agents_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1): return
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
        except: name = f"ID {uid}"
        text += f"{AGENT_RANKS.get(rank, '🛡 Агент')} — {name}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-помощь")
async def hide_from_help_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_agent(user_id) and user_id != OWNER_ID: return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO hidden_agents (user_id) VALUES (?)", (user_id,))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Вы скрыты.\n↩️ <code>+помощь</code>", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "+помощь")
async def show_in_help_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_agent(user_id) and user_id != OWNER_ID: return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM hidden_agents WHERE user_id = ?", (user_id,))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Вы в списке.\n🙈 <code>-помощь</code>", parse_mode="HTML", disable_web_page_preview=True)


# ================= ПОВЫСИТЬ / ПОНИЗИТЬ =================
@cmd("повысить")
async def promote_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("📌 <code>.повысить @user 3</code>", parse_mode="HTML", disable_web_page_preview=True)
    if target.id == OWNER_ID: return
    current_rank = get_rank(message.chat.id, target.id)
    args = message.text.split()
    new_rank = current_rank + 1
    for a in args[1:]:
        if a.isdigit(): new_rank = int(a); break
    if new_rank > 5: new_rank = 5
    if message.from_user.id != OWNER_ID and new_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя ≥ твоего.", parse_mode="HTML", disable_web_page_preview=True)
    set_rank(message.chat.id, target.id, new_rank, message.from_user.id)
    await message.reply(f"🏆 {mention(target)}: {RANK_NAMES[new_rank]}", parse_mode="HTML", disable_web_page_preview=True)


@cmd("понизить")
async def demote_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True)
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("📌 <code>.понизить @user 1</code>", parse_mode="HTML", disable_web_page_preview=True)
    if target.id == OWNER_ID: return
    current_rank = get_rank(message.chat.id, target.id)
    args = message.text.split()
    new_rank = current_rank - 1
    for a in args[1:]:
        if a.isdigit(): new_rank = int(a); break
    if new_rank < 0: new_rank = 0
    if message.from_user.id != OWNER_ID and new_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя ≥ твоего.", parse_mode="HTML", disable_web_page_preview=True)
    if new_rank == 0:
        remove_rank(message.chat.id, target.id)
        return await message.reply(f"📉 {mention(target)} разжалован.", parse_mode="HTML", disable_web_page_preview=True)
    set_rank(message.chat.id, target.id, new_rank, message.from_user.id)
    await message.reply(f"📉 {mention(target)}: {RANK_NAMES[new_rank]}", parse_mode="HTML", disable_web_page_preview=True)


@cmd("разжаловать")
@cmd("снять")
async def demote_all_cmd(message: types.Message):
    actor_id = message.from_user.id
    actor_rank = get_rank(message.chat.id, actor_id)
    if actor_id != OWNER_ID and actor_rank < 3: return
    target, _ = await resolve_target(message)
    if not target or target.id == OWNER_ID: return
    remove_rank(message.chat.id, target.id)
    await message.reply(f"{em('cross', '❌')} {mention(target)} разжалован.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("админы")
async def list_admins_cmd(message: types.Message):
    admins = get_all_admins(message.chat.id)
    if not admins:
        return await message.reply("📭 Нет админов.", parse_mode="HTML", disable_web_page_preview=True)
    text = "🏆 <b>Админы:</b>\n\n"
    for user_id, rank in admins:
        try:
            user = await bot.get_chat(user_id)
            name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        text += f"{RANK_NAMES.get(rank, '👤')} — {name}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("восстановить")
async def restore_creator_cmd(message: types.Message):
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status != "creator":
            return await message.reply(f"{em('cross', '❌')} Только создатель.", parse_mode="HTML", disable_web_page_preview=True)
    except: return
    set_rank(message.chat.id, message.from_user.id, 5, message.from_user.id)
    await message.reply(f"{em('check', '✅')} Вы владелец чата!", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+админ"))
async def grant_admin_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3: return
    target, _ = await resolve_target(message)
    if not target or target.id == OWNER_ID: return
    try:
        await bot.promote_chat_member(
            chat_id=message.chat.id, user_id=target.id,
            can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_promote_members=True, can_change_info=True,
            can_invite_users=True, can_pin_messages=True
        )
        mark_bot_promoted(target.id, message.chat.id, message.from_user.id)
        await message.reply(f"{em('check', '✅')} {mention(target)} теперь <b>ТГ-админ</b>!", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)


# ================= АВТОМОДЕРАЦИЯ =================
def _fmt_time(minutes):
    if minutes >= 1440: return f"{minutes // 1440} дн."
    if minutes >= 60: return f"{minutes // 60} ч."
    return f"{minutes} мин."


async def _check_automod_perms(message):
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass
    if message.from_user.id == OWNER_ID: is_creator = True
    if not is_creator and not has_permission(message.chat.id, message.from_user.id, 3):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True)
            return False
    return True


ACTION_NAMES = {"delete": "🗑 удалить", "mute": "🔇 мут", "warn": "⚠️ варн", "ban": "🚫 бан"}


@cmd("автомод")
@cmd("автомодерация")
async def automod_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    s = get_automod_settings(message.chat.id)
    def st(v): return "🟢" if v else "🔴"
    def act(k): return ACTION_NAMES.get(s[f"{k}_action"], s[f"{k}_action"])
    text = (
        f"🛡 <b>Автомодерация</b>\n\n"
        f"🚫 Антимат: {st(s['antimat'])} | {act('antimat')} | мут: {_fmt_time(s['antimat_mute'])}\n\n"
        f"💧 Антифлуд: {st(s['antiflood'])} | {act('antiflood')} | мут: {_fmt_time(s['antiflood_mute'])}\n\n"
        f"🔠 Антикапс: {st(s['anticaps'])} | {act('anticaps')}\n\n"
        f"🎨 Антистикер: {st(s['antisticker'])} | {act('antisticker')}\n\n"
        f"<code>+антимат</code> / <code>-антимат</code>\n"
        f"<code>+антифлуд</code> / <code>-антифлуд</code>\n"
        f"<code>+антикапс</code> / <code>-антикапс</code>\n"
        f"<code>+антисticker</code> / <code>-антисticker</code>"
    )
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антимат", "+ антимат"])
async def enable_antimat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antimat", 1)
    await message.reply(f"{em('check', '✅')} Антимат вкл", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антимат", "- антимат"])
async def disable_antimat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antimat", 0)
    await message.reply(f"{em('check', '✅')} Антимат выкл", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антифлуд", "+ антифлуд"])
async def enable_antiflood_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antiflood", 1)
    await message.reply(f"{em('check', '✅')} Антифлуд вкл", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антифлуд", "- антифлуд"])
async def disable_antiflood_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antiflood", 0)
    await message.reply(f"{em('check', '✅')} Антифлуд выкл", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антикапс", "+ антикапс"])
async def enable_anticaps_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "anticaps", 1)
    await message.reply(f"{em('check', '✅')} Антикапс вкл", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антикапс", "- антикапс"])
async def disable_anticaps_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "anticaps", 0)
    await message.reply(f"{em('check', '✅')} Антикапс выкл", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антисticker", "+ антисticker"])
async def enable_antisticker_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antisticker", 1)
    await message.reply(f"{em('check', '✅')} Антистикер вкл", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антисticker", "- антисticker"])
async def disable_antisticker_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antisticker", 0)
    await message.reply(f"{em('check', '✅')} Антистикер выкл", parse_mode="HTML", disable_web_page_preview=True)


async def _set_automod_action(message, rule):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    args = message.text.split()
    s = get_automod_settings(message.chat.id)
    cur = s[f"{rule}_action"]
    if len(args) < 2:
        return await message.reply(f"🎯 Действие <b>{rule}</b>: {ACTION_NAMES.get(cur, cur)}\n<code>.{rule}действие мут/варн/бан</code>", parse_mode="HTML", disable_web_page_preview=True)
    action = args[1].lower()
    mapping = {"удалить": "delete", "delete": "delete", "мут": "mute", "mute": "mute", "варн": "warn", "warn": "warn", "бан": "ban", "ban": "ban"}
    if action not in mapping: return
    set_automod_setting(message.chat.id, f"{rule}_action", mapping[action])
    await message.reply(f"{em('check', '✅')} <b>{rule}</b>: {ACTION_NAMES[mapping[action]]}", parse_mode="HTML", disable_web_page_preview=True)


@cmd("антиматдействие")
async def am_action_cmd(message): await _set_automod_action(message, "antimat")

@cmd("антифлуддействие")
async def afl_action_cmd(message): await _set_automod_action(message, "antiflood")

@cmd("антикапсдействие")
async def ac_action_cmd(message): await _set_automod_action(message, "anticaps")

@cmd("антисtickerдействие")
async def ast_action_cmd(message): await _set_automod_action(message, "antisticker")


async def _set_automod_time(message, rule, kind):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    args = message.text.split()
    s = get_automod_settings(message.chat.id)
    field = f"{rule}_{kind}"
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply(f"⏱ {_fmt_time(s[field])}\n<code>.{rule}{kind} 60</code>", parse_mode="HTML", disable_web_page_preview=True)
    minutes = int(args[1])
    if minutes < 1 or minutes > 525600: return
    set_automod_setting(message.chat.id, field, minutes)
    await message.reply(f"{em('check', '✅')} {rule} {kind}: <b>{_fmt_time(minutes)}</b>", parse_mode="HTML", disable_web_page_preview=True)


@cmd("антиматмут")
async def am_mute_cmd(message): await _set_automod_time(message, "antimat", "mute")

@cmd("антиматбан")
async def am_ban_cmd(message): await _set_automod_time(message, "antimat", "ban")

@cmd("антифлудмут")
async def afl_mute_cmd(message): await _set_automod_time(message, "antiflood", "mute")

@cmd("антифлудбан")
async def afl_ban_cmd(message): await _set_automod_time(message, "antiflood", "ban")

@cmd("антикапсмут")
async def ac_mute_cmd(message): await _set_automod_time(message, "anticaps", "mute")

@cmd("антисtickermut")
async def ast_mute_cmd(message): await _set_automod_time(message, "antisticker", "mute")# ================= АЧИВКИ =================
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
        text += "\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


# ================= ИРИСКИ =================
@cmd("мешок")
async def my_candies_cmd(message: types.Message):
    if message.reply_to_message: target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            try:
                if args[1].startswith('@'): target = await bot.get_chat(args[1])
                elif args[1].isdigit(): target = await bot.get_chat(int(args[1]))
            except: target = message.from_user
        else: target = message.from_user
    await message.reply(
        f"🎒 <b>Мешок {mention(target)}</b>\n\n🍬 Ириски: <b>{get_balance(target.id)}</b>\n☢️ Коины: <b>{get_coins(target.id)}</b> i¢",
        parse_mode="HTML", disable_web_page_preview=True
    )


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


@cmd("перевод")
@cmd("перевести")
async def transfer_candies_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("📌 <code>.перевод @user 100</code>", parse_mode="HTML", disable_web_page_preview=True)
    target = None; amount_arg = None
    if message.reply_to_message and len(args) == 2:
        target = message.reply_to_message.from_user; amount_arg = args[1]
    else:
        target_arg = args[1]
        amount_arg = args[2] if len(args) >= 3 else None
        if not amount_arg: return
        if target_arg.startswith('@'):
            try: target = await bot.get_chat(target_arg)
            except: return
        elif target_arg.isdigit():
            try: target = await bot.get_chat(int(target_arg))
            except: return
    if not target: return
    if target.id == user_id or target.id == bot.id: return
    try: amount = int(amount_arg)
    except: return
    if amount < 1 or amount > 100000: return
    if get_balance(user_id) < amount: return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        c.execute("INSERT OR IGNORE INTO candies (user_id, balance) VALUES (?, 0)", (target.id,))
        c.execute("UPDATE candies SET balance = balance + ? WHERE user_id = ?", (amount, target.id))
        conn.commit()
    await message.reply(
        f"{em('check', '✅')} <b>Перевод!</b>\n\n👤 Кому: {mention(target)}\n💰 Сумма: <b>{amount}</b> 🍬",
        parse_mode="HTML", disable_web_page_preview=True
    )


# ================= КОИНЫ =================
@cmd("коины")
@cmd("баланс")
async def coins_balance_cmd(message: types.Message):
    user_id = message.from_user.id
    apply_tax(user_id)
    info = get_coins_info(user_id)
    balance, last_farm, total_farmed, last_tax = info
    text = f"☢️ <b>Mos-коины</b>\n\n💰 Баланс: <b>{balance}</b> i¢\n📈 Всего: <b>{total_farmed}</b> i¢\n"
    if last_farm:
        try:
            last_farm_dt = datetime.strptime(last_farm[:19], "%Y-%m-%d %H:%M:%S")
            hours = (datetime.now() - last_farm_dt).total_seconds() / 3600
            if hours < 4: text += f"\n⛏ Ферма через: <b>{int((4 - hours) * 60)} мин.</b>"
            else: text += f"\n⛏ Ферма готова!"
        except: pass
    else: text += f"\n⛏ Ферма доступна!"
    text += f"\n\n💱 <code>Купить коины 10</code>\n💸 <code>Бкоин 100</code>"
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
    add_coins(user_id, reward, "ферма"); update_farm_time(user_id, total_farmed)
    await message.reply(f"⛏ <b>Урожай!</b>\n💰 +{reward} i¢", parse_mode="HTML", disable_web_page_preview=True)


@cmd("купить коины")
async def buy_coins_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 3 or not args[-1].isdigit(): return
    candies_amount = int(args[-1])
    if candies_amount <= 0: return
    user_id = message.from_user.id
    if get_balance(user_id) < candies_amount: return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (candies_amount, user_id))
        conn.commit()
    coins_amount = candies_amount * 100
    add_coins(user_id, coins_amount, f"обмен")
    await message.reply(f"💱 Обмен!\n💸 -{candies_amount} 🍬\n💰 +{coins_amount} i¢", parse_mode="HTML", disable_web_page_preview=True)


@cmd("бкоин")
async def bkoin_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[-1].isdigit(): return
    amount = int(args[-1])
    if amount < 1: return
    user_id = message.from_user.id
    if get_coins(user_id) < amount: return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE coins SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        c.execute("INSERT INTO coin_log (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, -amount, "взнос"))
        conn.commit()
    add_chat_coins(message.chat.id, amount)
    total = get_chat_coins(message.chat.id)
    text = f"💸 Взнос: <b>{amount}</b> i¢\n🏦 Счёт чата: <b>{total}</b> i¢"
    if total >= 35000: text += f"\n\n✅ <b>Можно в каталог!</b>"
    else: text += f"\n\n📊 До каталога: <b>{35000 - total}</b> i¢"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("коинытоп")
async def coins_top_cmd(message: types.Message):
    top = get_coins_top(limit=10)
    if not top: return
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


# ================= STARS =================
@cmd("купитьириски")
@cmd("купить-ириски")
@cmd("buycandies")
async def buy_candies_stars_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        price = get_stars_per_candy(message.chat.id)
        return await message.reply(
            f"🍬 <b>Покупка ирисок</b>\n\n💰 Курс: <b>{price} ⭐ = 1 🍬</b>\n\n📌 <code>.купитьириски 10</code>",
            parse_mode="HTML", disable_web_page_preview=True
        )
    amount = int(args[1])
    if amount < 1 or amount > 10000: return
    price = get_stars_per_candy(message.chat.id); total_stars = amount * price
    payment_id = create_stars_payment(user_id=message.from_user.id, chat_id=message.chat.id, amount_candies=amount, stars=total_stars)
    try:
        await bot.send_invoice(
            chat_id=message.chat.id, title=f"🍬 {amount} ирисок",
            description=f"{amount} ирисок за {total_stars} ⭐",
            payload=f"candies_{payment_id}", provider_token="", currency="XTR",
            prices=[types.LabeledPrice(label=f"{amount} ирисок", amount=total_stars)],
            start_parameter=f"buy_candies_{payment_id}"
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)


@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    try: await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except: pass


@dp.message(lambda m: m.successful_payment is not None)
async def successful_payment_handler(message: types.Message):
    payment = message.successful_payment
    try: payment_id = int(payment.invoice_payload.split("_")[1])
    except: return
    result = complete_stars_payment(payment_id)
    if not result: return
    user_id, chat_id, amount_candies, stars_paid = result
    await message.reply(
        f"{em('check', '✅')} <b>Покупка успешна!</b>\n\n🍬 +{amount_candies}\n⭐ {stars_paid}",
        parse_mode="HTML", disable_web_page_preview=True
    )


# ================= РЫБАЛКА =================
@cmd("рыбалка")
@cmd("рыба")
@cmd("рыбачить")
async def fishing_cmd(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    info = get_fishing(user_id)
    (uid, level, xp, total_caught, total_empty, has_rod, bait_until, last_fish, inv, legendary) = info

    cooldown = format_fishing_cooldown(last_fish)
    if cooldown > 0:
        hours = cooldown // 3600; mins = (cooldown % 3600) // 60; secs = cooldown % 60
        parts = []
        if hours > 0: parts.append(f"{hours} ч.")
        if mins > 0: parts.append(f"{mins} мин.")
        if secs > 0 and hours == 0: parts.append(f"{secs} сек.")
        time_str = " ".join(parts) if parts else "1 сек."
        return await message.reply(f"⏳ Удочка не готова. Подожди <b>{time_str}</b>.", parse_mode="HTML", disable_web_page_preview=True)

    msg = await message.reply("🎣 Забрасываю удочку...")
    await asyncio.sleep(2)

    event = get_active_event(chat_id)
    event_bonus = 1.0; event_text = ""; rare_boost = 1.0
    if event:
        ev_key, ev_bonus, ev_exp = event
        ev_data = FISHING_EVENTS.get(ev_key, {})
        event_bonus = ev_bonus
        rare_boost = ev_data.get("rare_boost", 1.0)
        event_text = f"\n{ev_data.get('name', ev_key)} — бонус ×{event_bonus}"

    chance = 55 + (level - 1) * 5 + 10
    bait_active = is_bait_active(bait_until)
    if bait_active: chance += 15

    gear_bonus, gear_flat, has_boat, has_premium = get_fishing_gear_bonus(user_id)
    chance = int(chance * (1 + gear_bonus))
    chance = min(chance, 98)

    roll = random.randint(1, 100)
    if roll <= chance:
        legendary_chance = 0
        if has_boat: legendary_chance += 15
        legendary_chance = int(legendary_chance * rare_boost)
        is_legendary = random.randint(1, 100) <= legendary_chance

        if is_legendary:
            total_weight = sum(f[4] for f in LEGENDARY_FISH)
            pick = random.uniform(0, total_weight); cumulative = 0
            chosen = LEGENDARY_FISH[0]
            for fish in LEGENDARY_FISH:
                cumulative += fish[4]
                if pick <= cumulative: chosen = fish; break
            fish_name, fish_emoji, min_r, max_r, _ = chosen
            update_legendary_count(user_id)
            legendary_text = "\n\n💎 <b>ЛЕГЕНДАРНАЯ РЫБА!</b>"
        else:
            total_weight = sum(f[4] for f in FISH_LIST)
            pick = random.uniform(0, total_weight); cumulative = 0
            chosen = FISH_LIST[0]
            for fish in FISH_LIST:
                cumulative += fish[4]
                if pick <= cumulative: chosen = fish; break
            fish_name, fish_emoji, min_r, max_r, _ = chosen
            legendary_text = ""

        add_fish_to_storage(user_id, fish_name, fish_emoji, 1)

        xp_gain = random.randint(5, 15)
        new_xp = xp + xp_gain
        new_level = level
        while new_xp >= xp_needed_for_level(new_level):
            new_xp -= xp_needed_for_level(new_level)
            new_level += 1

        update_fishing(user_id, level=new_level, xp=new_xp, total_caught=total_caught + 1)
        set_fishing_last_fish(user_id)
        log_fishing(user_id, chat_id, "caught", fish_name, 0)

        tour = get_active_tournament(chat_id)
        if tour: update_tournament_score(chat_id, user_id, 1)

        new_ach = check_fishing_achievements(user_id, chat_id)
        ach_text = ""
        if new_ach: ach_text = "\n\n🎖 <b>Новые ачивки:</b>\n" + "\n".join(f"  • {a}" for a in new_ach)

        level_up_text = ""
        if new_level > level: level_up_text = f"\n\n🎉 <b>Уровень повышен!</b> Теперь <b>{new_level}</b>"
        bait_text = ""
        if bait_active: bait_text = "\n🍯 Прикормка активна"

        fish_price = get_fish_price(fish_name)
        await msg.edit_text(
            f"🎣 <b>Улов!</b>\n\n{fish_emoji} <b>{fish_name}</b>\n"
            f"💵 Продажа: <b>{fish_price} 🍬</b>\n✨ Опыт: <b>+{xp_gain}</b> XP\n\n"
            f"📊 Уровень: <b>{new_level}</b> | XP: <b>{new_xp}/{xp_needed_for_level(new_level)}</b>\n"
            f"📦 В садке! Продай: <code>.продать</code>\n"
            f"🐟 Всего поймано: <b>{total_caught + 1}</b>"
            f"{level_up_text}{bait_text}{legendary_text}{event_text}{ach_text}",
            parse_mode="HTML"
        )
    else:
        update_fishing(user_id, total_empty=total_empty + 1)
        set_fishing_last_fish(user_id)
        log_fishing(user_id, chat_id, "empty")
        phrases = ["🐟 Рыба ушла...", "🌊 Ничего не поймал.", "🪝 Пустой крючок...", "💧 Только водоросли.", "🎣 Попробуй ещё раз!"]
        phrase = random.choice(phrases)
        await msg.edit_text(
            f"{phrase}\n\n📊 Уровень: <b>{level}</b> | XP: <b>{xp}/{xp_needed_for_level(level)}</b>\n📉 Пустых: <b>{total_empty + 1}</b>",
            parse_mode="HTML"
        )


@cmd("садок")
@cmd("моя рыба")
@cmd("рыбасадок")
async def fish_storage_cmd(message: types.Message):
    user_id = message.from_user.id
    storage = get_fish_storage(user_id)
    if not storage:
        return await message.reply("🎣 <b>Садок пуст</b>\n\nПоймай: <code>.рыбалка</code>", parse_mode="HTML", disable_web_page_preview=True)
    text = "🎒 <b>Твой садок</b>\n\n"
    total_price = 0; total_count = 0
    sorted_fish = sorted(storage.items(), key=lambda x: get_fish_price(x[0]), reverse=True)
    for fish_name, data in sorted_fish:
        qty = data["quantity"]; emoji = data["emoji"]; price = get_fish_price(fish_name)
        total_price += price * qty; total_count += qty
        text += f"{emoji} <b>{fish_name}</b> × <b>{qty}</b> — {price} 🍬/шт\n"
    text += f"\n💰 <b>Всего:</b> {total_count} рыб на <b>{total_price}</b> 🍬"
    text += f"\n\n<code>.продать все</code>\n<code>.продать Щука</code>"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("продать")
async def sell_fish_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("📌 <code>.продать все</code>\n📌 <code>.продать Щука 5</code>", parse_mode="HTML", disable_web_page_preview=True)
    storage = get_fish_storage(user_id)
    if not storage:
        return await message.reply("🎣 Садок пуст", parse_mode="HTML", disable_web_page_preview=True)
    query = args[1].strip()
    if query.lower() in ["все", "всё", "all", "*"]:
        total_price = 0; total_count = 0; sold_list = []
        for fish_name, data in storage.items():
            qty = data["quantity"]; price = get_fish_price(fish_name)
            total_price += price * qty; total_count += qty
            sold_list.append(f"{data['emoji']} {fish_name} × {qty}")
            remove_fish_from_storage(user_id, fish_name, qty)
        add_candies(user_id, total_price, 0)
        text = f"{em('check', '✅')} <b>Продано!</b>\n\n"
        for s in sold_list[:20]: text += f"  • {s}\n"
        if len(sold_list) > 20: text += f"  ... +{len(sold_list)-20} ещё\n"
        text += f"\n💰 +{total_price} 🍬\n📊 Всего: {total_count} рыб\n💼 Баланс: <b>{get_balance(user_id)}</b> 🍬"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)
    parts = query.split()
    fish_name_query = parts[0]
    matched_fish = None
    for fish_name in storage.keys():
        if fish_name_query.lower() in fish_name.lower() or fish_name.lower() in fish_name_query.lower():
            matched_fish = fish_name; break
    if not matched_fish:
        return await message.reply(f"{em('cross', '❌')} Не найдена.\n<code>.садок</code>", parse_mode="HTML", disable_web_page_preview=True)
    available = storage[matched_fish]["quantity"]
    emoji = storage[matched_fish]["emoji"]; price = get_fish_price(matched_fish)
    if len(parts) >= 2 and parts[1].isdigit():
        qty = min(int(parts[1]), available)
        if qty < 1: qty = 1
    else: qty = available
    total_price = price * qty
    remove_fish_from_storage(user_id, matched_fish, qty)
    add_candies(user_id, total_price, 0)
    await message.reply(
        f"{em('check', '✅')} <b>Продано!</b>\n\n{emoji} <b>{matched_fish}</b> × <b>{qty}</b>\n💰 +{total_price} 🍬\n📊 Осталось: <b>{available - qty}</b>",
        parse_mode="HTML", disable_web_page_preview=True
    )


@cmd("рыбтоп")
async def fishing_top_cmd(message: types.Message):
    top = get_fishing_top(limit=10)
    if not top:
        return await message.reply("📭 Никто не рыбачил.", parse_mode="HTML", disable_web_page_preview=True)
    text = "🏆 <b>Топ рыбаков:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, caught, level) in enumerate(top, 1):
        try:
            user = await bot.get_chat(user_id)
            name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{caught}</b> 🐟 (ур. {level})\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("моя рыбалка")
@cmd("рыбстата")
async def fishing_stats_cmd(message: types.Message):
    info = get_fishing(message.from_user.id)
    (uid, level, xp, total_caught, total_empty, has_rod, bait_until, last_fish, inv, legendary) = info
    xp_needed = xp_needed_for_level(level)
    bait_active = is_bait_active(bait_until)
    bait_text = "✅ Активна" if bait_active else "❌ Нет"
    total = total_caught + total_empty
    success_rate = int(total_caught / total * 100) if total > 0 else 0
    cooldown = format_fishing_cooldown(last_fish)
    if cooldown > 0:
        hours = cooldown // 3600; mins = (cooldown % 3600) // 60
        parts = []
        if hours > 0: parts.append(f"{hours} ч.")
        if mins > 0: parts.append(f"{mins} мин.")
        cooldown_text = "⏳ " + " ".join(parts)
    else: cooldown_text = "✅ Готово"
    await message.reply(
        f"🎣 <b>Твоя рыбалка</b>\n\n📊 Уровень: <b>{level}</b>\n✨ XP: <b>{xp}/{xp_needed}</b>\n"
        f"🐟 Поймано: <b>{total_caught}</b>\n📉 Пустых: <b>{total_empty}</b>\n🎯 Успешность: <b>{success_rate}%</b>\n"
        f"💎 Легендарных: <b>{legendary or 0}</b>\n\n🍯 Прикормка: {bait_text}\n⏰ Кулдаун: {cooldown_text}",
        parse_mode="HTML", disable_web_page_preview=True
    )


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+прикормка"))
async def buy_bait_cmd(message: types.Message):
    user_id = message.from_user.id
    info = get_fishing(user_id)
    if is_bait_active(info[6]):
        return await message.reply("🍯 Уже активна.", parse_mode="HTML", disable_web_page_preview=True)
    price = 20
    if get_balance(user_id) < price:
        return await message.reply(f"❌ Нужно <b>{price}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        conn.commit()
    set_fishing_bait(user_id)
    await message.reply(f"✅ <b>Прикормка куплена!</b>\n🍯 {BAIT_DURATION_HOURS} ч.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("магазин снастей")
@cmd("снасти")
async def fishing_shop_cmd(message: types.Message):
    text = "🛒 <b>Магазин снастей</b>\n\n"
    for key, gear in FISHING_GEAR.items():
        text += f"<b>{gear['name']}</b> — <b>{gear['price']}</b> 🍬\n   <i>{gear['desc']}</i>\n   Купить: <code>.купить {key}</code>\n\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!]?\s*купить\s+\S+', m.text.strip(), re.IGNORECASE)
    and not re.match(r'^\s*[.\/!]?\s*купить\s+вип\b', m.text.strip(), re.IGNORECASE))
async def fishing_buy_cmd(message: types.Message):
    if not await check_command_access(message, "купить"):
        return
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("📌 <code>.магазин снастей</code>", parse_mode="HTML", disable_web_page_preview=True)
    query = " ".join(args[1:]).lower()
    gear_key = None
    for k, g in FISHING_GEAR.items():
        if query == k or query in g["name"].lower():
            gear_key = k; break
    if not gear_key:
        return await message.reply("❌ Не найдено. <code>.магазин снастей</code>", parse_mode="HTML", disable_web_page_preview=True)
    gear = FISHING_GEAR[gear_key]
    price = gear["price"]
    user_id = message.from_user.id
    if get_balance(user_id) < price:
        return await message.reply(f"❌ Нужно <b>{price}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True)
    inv = get_fishing_inventory(user_id)
    if inv.get(gear_key, 0) > 0:
        return await message.reply(f"⚠️ Уже есть <b>{gear['name']}</b>.", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        conn.commit()
    add_to_fishing_inventory(user_id, gear_key, 1)
    await message.reply(f"{em('check', '✅')} <b>Куплено!</b>\n\n{gear['name']} — {price} 🍬", parse_mode="HTML", disable_web_page_preview=True)


@cmd("инвентарь")
@cmd("инв")
async def fishing_inventory_cmd(message: types.Message):
    user_id = message.from_user.id
    inv = get_fishing_inventory(user_id)
    text = "🎒 <b>Твой инвентарь</b>\n\n"
    if not inv:
        text += "<i>Пусто. <code>.магазин снастей</code></i>\n"
    else:
        for key, count in inv.items():
            gear = FISHING_GEAR.get(key)
            if not gear: continue
            cnt = f" (x{count})" if count > 1 else ""
            text += f"{gear['name']}{cnt}\n   <i>{gear['desc']}</i>\n"
    gear_bonus, gear_flat, has_boat, has_premium = get_fishing_gear_bonus(user_id)
    text += f"\n📊 <b>Бонусы:</b>\n• К улову: +{int(gear_bonus*100)}%\n• К награде: +{gear_flat} 🍬\n"
    if has_boat: text += "• 🚤 Шанс легендарки +15%\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("мои рыбные ачивки")
@cmd("рыбные ачивки")
async def fishing_ach_cmd(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT achievement FROM fishing_achievements WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        have = {r[0] for r in c.fetchall()}
    text = "🎖 <b>Твои ачивки рыбалки</b>\n\n"
    for key, ach in FISHING_ACHIEVEMENTS.items():
        mark = "✅" if key in have else "🔒"
        text += f"{mark} {ach['name']}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("событие")
@cmd("погода рыбалки")
async def fishing_event_cmd(message: types.Message):
    chat_id = message.chat.id
    event = get_active_event(chat_id)
    if not event:
        return await message.reply("☀️ <b>Сейчас штиль</b>", parse_mode="HTML", disable_web_page_preview=True)
    ev_key, bonus, expires = event
    ev_data = FISHING_EVENTS.get(ev_key, {})
    try:
        exp_dt = datetime.strptime(expires[:19], "%Y-%m-%d %H:%M:%S")
        left = int((exp_dt - datetime.now()).total_seconds() / 60)
    except: left = 0
    text = f"{ev_data.get('name', ev_key)}\n📈 Бонус: <b>×{bonus}</b>\n⏰ Осталось: <b>{left} мин.</b>"
    if ev_data.get("rare_boost"): text += f"\n💎 Шанс редких ×{ev_data['rare_boost']}"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("турнир")
async def fishing_tournament_cmd(message: types.Message):
    args = message.text.split(); chat_id = message.chat.id
    if len(args) >= 2 and args[1].lower() in ["участвовать", "join"]:
        tour = get_active_tournament(chat_id)
        if not tour:
            return await message.reply("❌ Нет турнира.", parse_mode="HTML", disable_web_page_preview=True)
        join_tournament(chat_id, message.from_user.id)
        return await message.reply(f"{em('check', '✅')} Ты в турнире!", parse_mode="HTML", disable_web_page_preview=True)
    if len(args) >= 2 and args[1].lower() in ["стоп", "end"]:
        if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1) and not await is_tg_admin(chat_id, message.from_user.id): return
        winners = end_tournament(chat_id)
        if not winners: return
        text = "🏆 <b>ТУРНИР ЗАВЕРШЁН!</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, caught, prize) in enumerate(winners):
            try:
                u = await bot.get_chat(uid)
                name = user_link(uid, u.first_name, u.username)
            except: name = f"ID {uid}"
            text += f"{medals[i]} {name} — <b>{caught}</b> 🐟 (+{prize} 🍬)\n"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)
    if not await is_tg_admin(chat_id, message.from_user.id) and message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Только админ.", parse_mode="HTML", disable_web_page_preview=True)
    tour = get_active_tournament(chat_id)
    if tour:
        started_by, started_at, expires_at, prize = tour
        try:
            exp_dt = datetime.strptime(expires_at[:19], "%Y-%m-%d %H:%M:%S")
            left = int((exp_dt - datetime.now()).total_seconds() / 60)
        except: left = 0
        members = get_tournament_members(chat_id, limit=10)
        text = f"🏆 <b>Турнир</b>\n⏰ Осталось: <b>{left} мин.</b>\n💰 Приз: <b>{prize}</b> 🍬\n\n"
        if members:
            medals = ["🥇", "🥈", "🥉"]
            for i, (uid, caught) in enumerate(members):
                try:
                    u = await bot.get_chat(uid)
                    name = user_link(uid, u.first_name, u.username)
                except: name = f"ID {uid}"
                m = medals[i] if i < 3 else f"{i+1}."
                text += f"{m} {name} — <b>{caught}</b> 🐟\n"
        text += f"\n📌 <code>.турнир участвовать</code>"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)
    create_tournament(chat_id, message.from_user.id, prize=5000, duration_min=60)
    join_tournament(chat_id, message.from_user.id)
    await message.reply("🏆 <b>ТУРНИР ЗАПУЩЕН!</b>\n⏰ 1 час\n💰 5000/2500/1250 🍬\n📌 <code>.турнир участвовать</code>", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+событие", "+ событие"])
async def enable_events_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    if is_events_enabled(message.chat.id):
        return await message.reply("ℹ️ Уже включены.", parse_mode="HTML", disable_web_page_preview=True)
    set_events_enabled(message.chat.id, True)
    await message.reply(f"{em('check', '✅')} Уведомления о событиях включены!", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-событие", "- событие"])
async def disable_events_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    if not is_events_enabled(message.chat.id):
        return await message.reply("ℹ️ Уже выключены.", parse_mode="HTML", disable_web_page_preview=True)
    set_events_enabled(message.chat.id, False)
    await message.reply(f"{em('check', '✅')} Уведомления о событиях выключены!", parse_mode="HTML", disable_web_page_preview=True)


@cmd("события")
@cmd("уведомления")
async def events_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    enabled = is_events_enabled(message.chat.id)
    status = "🟢 включены" if enabled else "🔴 выключены"
    await message.reply(f"🌦 Уведомления о событиях: {status}\n\n<code>+событие</code> / <code>-событие</code>", parse_mode="HTML", disable_web_page_preview=True)


# ================= РП =================
@dp.message(lambda m: m.text and not m.text.startswith(('.', '+', '-', '!', '/', 'брак')))
async def standard_rp_handler(message: types.Message):
    if not message.text: return
    txt = message.text.strip()
    if not txt: return
    txt_lower = txt.lower()
    rp_data = None; rp_name = None
    if txt_lower in STANDARD_RP:
        rp_name = txt_lower; rp_data = STANDARD_RP[txt_lower]
    else:
        for name in sorted(STANDARD_RP.keys(), key=len, reverse=True):
            if txt_lower.startswith(name):
                rest = txt_lower[len(name):]
                if not rest or rest[0] == ' ':
                    rp_name = name; rp_data = STANDARD_RP[name]; break
    if not rp_data: return
    actor = message.from_user; target = None
    if message.reply_to_message: target = message.reply_to_message.from_user
    if not target:
        rest_text = txt[len(rp_name):].strip()
        if rest_text:
            try:
                target_arg = rest_text.split()[0]
                if target_arg.startswith('@'): target = await bot.get_chat(target_arg)
                elif target_arg.isdigit(): target = await bot.get_chat(int(target_arg))
            except: pass
    if not target:
        return await message.reply(
            f"{rp_data['emoji']} {rp_data['self_text'].format(actor=mention(actor), target=mention(actor))}",
            parse_mode="HTML", disable_web_page_preview=True
        )
    if target.is_bot: return
    await message.reply(
        f"{rp_data['emoji']} {rp_data['text'].format(actor=mention(actor), target=mention(target))}",
        parse_mode="HTML", disable_web_page_preview=True
    )


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+мрп"))
async def create_rp_cmd(message: types.Message):
    if not get_vip(message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Только VIP.", parse_mode="HTML", disable_web_page_preview=True)
    parts = message.text.split("/", 2)
    if len(parts) < 3:
        return await message.reply("📌 <code>+Мрп Название / 😀 / текст</code>", parse_mode="HTML", disable_web_page_preview=True)
    name = parts[0].replace("+Мрп", "").replace("+мрп", "").strip()[:30]
    emoji = parts[1].strip()[:5]
    first_slash = message.text.find("/")
    second_slash = message.text.find("/", first_slash + 1)
    text_html = _extract_html_after(message, second_slash + 1)[:300] if second_slash != -1 else ""
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO rp_commands (chat_id, name, emoji, text, created_by) VALUES (?, ?, ?, ?, ?)",
                      (message.chat.id, name, emoji, text_html, message.from_user.id))
            conn.commit()
            await message.reply(f"{em('check', '✅')} РП: {emoji} <b>{name}</b>", parse_mode="HTML", disable_web_page_preview=True)
        except:
            await message.reply(f"{em('cross', '❌')} Уже есть.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("мрп")
async def list_rp_cmd(message: types.Message):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, emoji FROM rp_commands WHERE chat_id = ? AND created_by = ?", (message.chat.id, message.from_user.id))
        rows = c.fetchall()
    text = "🎭 <b>РП-команды</b>\n\n"
    if rows:
        text += "<b>Твои:</b>\n"
        for i, (rid, name, emoji) in enumerate(rows, 1):
            text += f"{i}. {emoji} <b>{name}</b>\n"
        text += "\n"
    text += f"<b>🌐 Стандартные ({len(STANDARD_RP)}):</b>\n  " + ", ".join(f"<code>{n}</code>" for n in list(STANDARD_RP.keys())[:30])
    text += f"\n\n📌 <code>.обнять @user</code> или ответом"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-мрп"))
async def delete_rp_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return
    name = args[1].strip()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM rp_commands WHERE chat_id = ? AND name = ? AND created_by = ?",
                  (message.chat.id, name, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Удалено.", parse_mode="HTML", disable_web_page_preview=True)


# ================= ПРАВИЛА =================
@cmd("правила")
@cmd("rules")
async def rules_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        rules = get_chat_rules(message.chat.id)
        if not rules:
            return await message.reply("📭 Правила не установлены.", parse_mode="HTML", disable_web_page_preview=True)
        return await message.reply(f"📜 <b>Правила:</b>\n\n{rules}", parse_mode="HTML", disable_web_page_preview=True)
    sub = args[1].strip().lower()
    if sub.startswith("установить"):
        if not has_permission(message.chat.id, message.from_user.id, 3): return
        parts = message.text.split("\n", 1)
        if len(parts) < 2: return
        nl_idx = message.text.find("\n")
        raw_text_html = _extract_html_after(message, nl_idx + 1)[:3500]
        cleaned_text, links = extract_links_from_text(raw_text_html)
        set_chat_rules(message.chat.id, cleaned_text, message.from_user.id)
        return await message.reply(f"{em('check', '✅')} Правила установлены!", parse_mode="HTML", disable_web_page_preview=True)
    if sub in ["сброс", "удалить"]:
        if not has_permission(message.chat.id, message.from_user.id, 3): return
        reset_chat_rules(message.chat.id)
        return await message.reply(f"{em('check', '✅')} Сброшено.", parse_mode="HTML", disable_web_page_preview=True)
    if sub in ["закрепить", "пин"]:
        if not has_permission(message.chat.id, message.from_user.id, 3): return
        rules = get_chat_rules(message.chat.id)
        if not rules: return
        try:
            msg = await message.reply(f"📜 <b>Правила:</b>\n\n{rules}", parse_mode="HTML", disable_web_page_preview=True)
            await bot.pin_chat_message(message.chat.id, msg.message_id, disable_notification=True)
        except: pass


# ================= ПРИВЕТСТВИЕ =================
@cmd("приветствие")
async def greeting_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    args = message.text.split(maxsplit=1)
    sub = args[1].strip().lower() if len(args) >= 2 else ""
    if not sub:
        current = get_greeting(message.chat.id)
        if not current:
            return await message.reply("📭 Не установлено.\n📌 <code>.приветствие установить</code>", parse_mode="HTML", disable_web_page_preview=True)
        return await message.reply(f"📜 <b>Текущее:</b>\n\n<code>{current}</code>", parse_mode="HTML", disable_web_page_preview=True)
    if sub.startswith("установить"):
        parts = message.text.split("\n", 1)
        if len(parts) < 2: return
        nl_idx = message.text.find("\n")
        raw_text_html = _extract_html_after(message, nl_idx + 1)[:1000]
        if not raw_text_html: return
        cleaned_text, links = extract_links_from_text(raw_text_html)
        set_greeting(message.chat.id, cleaned_text, message.from_user.id)
        return await message.reply(f"{em('check', '✅')} Установлено!\n\n{format_greeting(cleaned_text, message.from_user, message.chat)}", parse_mode="HTML", disable_web_page_preview=True)
    if sub in ["сброс", "удалить"]:
        reset_greeting(message.chat.id)
        return await message.reply(f"{em('check', '✅')} Сброшено.", parse_mode="HTML", disable_web_page_preview=True)


# ================= ФИЛЬТР ССЫЛОК =================
@cmd("фильтрссылок")
async def link_filter_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    args = message.text.split(maxsplit=1)
    sub = args[1].strip().lower() if len(args) >= 2 else ""
    if not sub:
        enabled = is_link_filter_enabled(message.chat.id)
        status = "🟢 включён" if enabled else "🔴 выключен"
        return await message.reply(f"🔗 <b>Фильтр ссылок:</b> {status}", parse_mode="HTML", disable_web_page_preview=True)
    if sub in ["вкл", "on", "+"]:
        set_link_filter(message.chat.id, True)
        return await message.reply(f"{em('check', '✅')} Включён", parse_mode="HTML", disable_web_page_preview=True)
    if sub in ["выкл", "off", "-"]:
        set_link_filter(message.chat.id, False)
        return await message.reply(f"{em('check', '✅')} Выключен", parse_mode="HTML", disable_web_page_preview=True)


# ================= КАПЧА =================
@dp.message(lambda m: m.text and m.text.lower().strip() in ["+капча", "+ капча"])
async def enable_captcha_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    if is_captcha_enabled(message.chat.id): return
    set_captcha_enabled(message.chat.id, True)
    await message.reply(f"{em('check', '✅')} Капча включена!", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-капча", "- капча"])
async def disable_captcha_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    if not is_captcha_enabled(message.chat.id): return
    set_captcha_enabled(message.chat.id, False)
    await message.reply(f"{em('check', '✅')} Капча выключена!", parse_mode="HTML", disable_web_page_preview=True)


@cmd("капча")
async def captcha_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    enabled = is_captcha_enabled(message.chat.id)
    status = "🟢 включена" if enabled else "🔴 выключена"
    await message.reply(f"🤖 Капча: {status}", parse_mode="HTML", disable_web_page_preview=True)


# ================= ГРАЖДАНСТВО =================
@dp.message(lambda m: m.text and m.text.lower().strip() == "+гражданство")
async def become_citizen_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    user_id = message.from_user.id; chat_id = message.chat.id
    current = get_citizenship_info(user_id)
    if current:
        if current[0] == chat_id: return
        return await message.reply("⚠️ Уже гражданин другого чата. <code>-гражданство</code>", parse_mode="HTML", disable_web_page_preview=True)
    set_citizenship(user_id, chat_id)
    await message.reply(f"🏠 {mention(message.from_user)} стал гражданином чата!", parse_mode="HTML", disable_web_page_preview=True)


@cmd("гражданство")
async def citizenship_info_cmd(message: types.Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    info = get_citizenship_info(target.id)
    if not info:
        return await message.reply(f"ℹ️ {mention(target)} не гражданин.", parse_mode="HTML", disable_web_page_preview=True)
    chat_id, became_at = info
    try:
        chat = await bot.get_chat(chat_id)
        title = chat.title or f"Чат"
    except: title = "Чат"
    duration = format_citizenship_duration(became_at)
    await message.reply(f"🏠 {mention(target)}\n🏠 {title}\n⏳ {duration}", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-гражданство")
async def leave_citizenship_cmd(message: types.Message):
    info = get_citizenship_info(message.from_user.id)
    if not info: return
    remove_citizenship(message.from_user.id)
    await message.reply("👋 Вы больше не гражданин.", parse_mode="HTML", disable_web_page_preview=True)


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
        text += f"{i}. {name} — {format_citizenship_duration(became_at)}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


# ================= НИК / ЗВАНИЕ / ДЕВИЗ / О СЕБЕ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+ник"))
async def set_nick_cmd(message: types.Message):
    if not message.text: return
    idx = message.text.lower().find("+ник")
    if idx == -1: return
    nick_html = _extract_html_after(message, idx + len("+ник"))[:300]
    if not nick_html: return
    set_user_nick(message.from_user.id, message.chat.id, nick_html)
    await message.reply(f"✅ Ник: <b>{nick_html}</b>", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-ник")
async def remove_nick_cmd(message: types.Message):
    remove_user_nick(message.from_user.id, message.chat.id)
    await message.reply("✅ Ник удалён.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("ник")
async def show_my_nick_cmd(message: types.Message):
    nick = get_user_nick(message.from_user.id, message.chat.id)
    if not nick: return await message.reply("📭 Нет ника.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"🔤 {nick}", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+звание"))
async def set_rank_text_cmd(message: types.Message):
    if not message.text: return
    idx = message.text.lower().find("+звание")
    if idx == -1: return
    rank_html = _extract_html_after(message, idx + len("+звание"))[:300]
    if not rank_html: return
    set_user_rank_text(message.from_user.id, message.chat.id, rank_html)
    await message.reply(f"✅ Звание: <b>{rank_html}</b>", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-звание")
async def remove_rank_text_cmd(message: types.Message):
    remove_user_rank_text(message.from_user.id, message.chat.id)
    await message.reply("✅ Удалено.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("звание")
async def show_my_rank_text_cmd(message: types.Message):
    rank_text = get_user_rank_text(message.from_user.id, message.chat.id)
    if not rank_text: return await message.reply("📭 Нет звания.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"📌 {rank_text}", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+о себе"))
async def set_about_cmd(message: types.Message):
    if not message.text: return
    nl_idx = message.text.find("\n")
    if nl_idx == -1: return
    raw_html = _extract_html_after(message, nl_idx + 1)[:500]
    cleaned, links = extract_links_from_text(raw_html)
    set_user_about(message.from_user.id, cleaned)
    await message.reply("✅ Сохранено.", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-о себе")
async def remove_about_cmd(message: types.Message):
    remove_user_about(message.from_user.id)
    await message.reply("✅ Удалено.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("о себе")
async def show_my_about_cmd(message: types.Message):
    text = get_user_about(message.from_user.id)
    if not text: return await message.reply("📭 Нет описания.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"✏️ {text}", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+девиз"))
async def set_motto_cmd(message: types.Message):
    if not message.text: return
    idx = message.text.lower().find("+девиз")
    if idx == -1: return
    motto_html = _extract_html_after(message, idx + len("+девиз"))[:500]
    if not motto_html: return
    update_user_profile(message.from_user.id, "motto", motto_html)
    await message.reply("✅ Девиз установлен.", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-девиз")
async def remove_motto_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "motto", None)
    await message.reply("✅ Удалён.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("девиз")
async def show_motto_cmd(message: types.Message):
    profile = get_user_profile(message.from_user.id)
    motto = profile[6] if len(profile) > 6 else None
    if not motto: return await message.reply("📭 Нет девиза.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"💭 {motto}", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+анкета", "+ анкета"])
async def show_profile_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "is_hidden", 0)
    await message.reply("✅ Анкета открыта.", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-анкета", "- анкета"])
async def hide_profile_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "is_hidden", 1)
    await message.reply("✅ Анкета скрыта.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("моя стата")
async def my_stats_cmd(message: types.Message):
    try: chart_buf = generate_user_activity_chart(message.from_user.id, days=30)
    except: return
    if not chart_buf: return await message.reply("📭 Нет данных.", disable_web_page_preview=True)
    await message.reply_photo(photo=types.BufferedInputFile(chart_buf.getvalue(), filename="my_stats.png"),
                              caption="📊 Статистика за 30 дней", parse_mode="HTML")


# ================= VIP =================
@cmd("вип")
async def vip_info_cmd(message: types.Message):
    price = get_vip_price(message.chat.id)
    await message.reply(
        f"💎 <b>VIP-статус</b>\n\n💰 Цена: <b>{price}</b> 🍬 / мес\n\n"
        f"📌 <code>Купить вип</code>\n📌 <code>Мой вип</code>",
        parse_mode="HTML", disable_web_page_preview=True
    )


@cmd("купить вип")
async def buy_vip_cmd(message: types.Message):
    args = message.text.split()
    months = 1; target = message.from_user
    for a in args[2:]:
        if a.isdigit(): months = int(a)
        else:
            try: target = await bot.get_chat(a)
            except: pass
    if months < 1 or months > 12: return
    total = get_vip_price(message.chat.id) * months
    if get_balance(message.from_user.id) < total:
        return await message.reply(f"❌ Нужно {total} 🍬", parse_mode="HTML", disable_web_page_preview=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (total, message.from_user.id))
        conn.commit()
    new_exp = add_vip_months(target.id, months)
    await message.reply(f"💎 <b>VIP активирован!</b>\n📅 До: <b>{new_exp.strftime('%d.%m.%Y')}</b>", parse_mode="HTML", disable_web_page_preview=True)


@cmd("мой вип")
async def my_vip_cmd(message: types.Message):
    v = get_vip(message.from_user.id)
    if not v: return await message.reply("💎 Нет VIP.", parse_mode="HTML", disable_web_page_preview=True)
    days = get_vip_days_left(message.from_user.id)
    await message.reply(f"💎 <b>Ваш VIP</b>\n📅 Осталось: <b>{days} дн.</b>\n😎 Эмодзи: {v[1] or '—'}", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+вип эмодзи"))
async def set_vip_emoji_cmd(message: types.Message):
    if not get_vip(message.from_user.id): return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return
    set_vip_emoji(message.from_user.id, args[2].strip()[:10])
    await message.reply(f"{em('check', '✅')} Эмодзи: {args[2].strip()[:10]}", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip() == "-вип эмодзи")
async def remove_vip_emoji_cmd(message: types.Message):
    if not get_vip(message.from_user.id): return
    set_vip_emoji(message.from_user.id, None)
    await message.reply("✅ Убран.", parse_mode="HTML", disable_web_page_preview=True)


# ================= ЗАМЕТКИ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+заметка "))
async def create_note_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    parts = message.text.split("\n", 1)
    name = parts[0].replace("+Заметка", "").replace("+заметка", "").strip()
    if not name or len(parts) < 2: return
    nl_idx = message.text.find("\n")
    raw_body_html = _extract_html_after(message, nl_idx + 1)[:3500]
    cleaned_body, links = extract_links_from_text(raw_body_html)
    note_id = add_note(message.chat.id, name, cleaned_body, message.from_user.id)
    if not note_id:
        return await message.reply(f"{em('cross', '❌')} Уже есть.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"{em('check', '✅')} Заметка <b>{name}</b> создана (ID: {note_id})", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-заметка "))
async def delete_note_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    arg = message.text[len("-Заметка"):].strip()
    if not arg: return
    note = get_note_by_number(message.chat.id, int(arg)) if arg.isdigit() else get_note_by_name(message.chat.id, arg)
    if not note:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    delete_note(message.chat.id, note[0])
    await message.reply(f"{em('check', '✅')} Удалена.", parse_mode="HTML", disable_web_page_preview=True)


@cmd("заметки")
async def list_notes_cmd(message: types.Message):
    notes = get_all_notes(message.chat.id)
    if not notes: return await message.reply("📭 Нет заметок.", parse_mode="HTML", disable_web_page_preview=True)
    text = f"📋 <b>Заметки</b>\n\n"
    for i, (nid, name) in enumerate(notes, 1):
        text += f"{i}. <b>{name}</b>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@cmd("заметка")
async def get_note_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("📌 <code>Заметка название</code>", parse_mode="HTML", disable_web_page_preview=True)
    arg = args[1].strip()
    note = get_note_by_number(message.chat.id, int(arg)) if arg.isdigit() else get_note_by_name(message.chat.id, arg)
    if not note:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    try: await message.reply(note[2], parse_mode="HTML", disable_web_page_preview=True)
    except: await message.reply(note[2], disable_web_page_preview=True)


# ================= СЕТКА =================
@cmd("создать сетку")
async def create_grid_cmd(message: types.Message):
    if message.chat.type != "private": return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return
    name = args[2].strip().replace(" ", "_")[:24]
    grid_id = create_grid(name, message.from_user.id)
    if not grid_id:
        return await message.reply("❌ Уже есть.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply(f"{em('check', '✅')} Сетка <b>{name}</b> (ID: {grid_id})", parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("сетка ") and m.chat.type != "private"
    and not m.text.lower().strip().startswith("сетка повысить")
    and not m.text.lower().strip().startswith("сетка понизить")
    and not m.text.lower().strip().startswith("сетка +админ")
    and not m.text.lower().strip().startswith("сетка -админ")
    and not m.text.lower().strip().startswith("сетка разжаловать")
    and not m.text.lower().strip().startswith("сетка инфо"))
async def set_grid_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return
    grid = get_grid_by_name(args[1].strip())
    if not grid:
        return await message.reply("❌ Не найдена.", parse_mode="HTML", disable_web_page_preview=True)
    grid_id, grid_name = grid
    add_chat_to_grid(grid_id, message.chat.id, hidden=0)
    await message.reply(f"{em('check', '✅')} Привязан к <b>{grid_name}</b>!", parse_mode="HTML", disable_web_page_preview=True)


@cmd("чаты")
async def list_grid_chats(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    chats = get_grid_chats(grid_id, include_hidden=False)
    text = "📋 <b>Чаты сетки:</b>\n\n"
    for chat_id, hidden, desc in chats:
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title or f"Чат"
            text += f"• {title}\n"
        except: pass
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("глобан"))
async def global_ban_cmd(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id: return
    if not is_grid_moderator(grid_id, message.from_user.id, 2): return
    target, _ = await resolve_target(message)
    if not target: return
    add_grid_ban(grid_id, target.id, "Global", message.from_user.id)
    chats = get_grid_chats(grid_id, include_hidden=True)
    success = 0
    for chat_id, hidden, desc in chats:
        try:
            await bot.ban_chat_member(chat_id, target.id); success += 1
        except: pass
    await message.reply(f"{em('ban', '🚫')} {mention(target)} забанен ({success}/{len(chats)}).", parse_mode="HTML", disable_web_page_preview=True)# ================= БРАКИ — ЕДИНЫЙ РОУТЕР =================
# Работает на: "брак" (ответом), "брак @user", "Брак" (любой регистр), ".брак"
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!]?\s*брак(\s|$)', m.text.strip(), re.IGNORECASE))
async def marriage_router(message: types.Message):
    txt = message.text.strip()
    # убираем префикс . / ! и слово "брак"
    txt = re.sub(r'^[.\/!]\s*', '', txt)
    rest = re.sub(r'^брак\s*', '', txt, count=1, flags=re.IGNORECASE).strip()

    # --- Ищем target ---
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif rest:
        # ищем @username в остатке
        for w in rest.split():
            if w.startswith("@"):
                try:
                    target = await bot.get_chat(w)
                    break
                except:
                    return await message.reply(f"{em('cross', '❌')} Пользователь <code>{w}</code> не найден.", parse_mode="HTML", disable_web_page_preview=True)
            if w.isdigit():
                try:
                    target = await bot.get_chat(int(w))
                    break
                except: pass

    # --- Нет target — инструкция ---
    if not target:
        return await message.reply(
            "💍 <b>Как жениться:</b>\n\n"
            "• Ответь на сообщение юзера: <code>брак</code>\n"
            "• Или напиши: <code>брак @username</code>",
            parse_mode="HTML", disable_web_page_preview=True
        )

    # --- Проверки ---
    if target.id == message.from_user.id:
        return await message.reply(f"{em('cross', '❌')} На себя нельзя.", parse_mode="HTML", disable_web_page_preview=True)
    if target.is_bot:
        return await message.reply(f"{em('cross', '❌')} Нельзя на бота.", parse_mode="HTML", disable_web_page_preview=True)

    if get_marriage(message.chat.id, message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Ты уже в браке.", parse_mode="HTML", disable_web_page_preview=True)
    if get_marriage(message.chat.id, target.id):
        return await message.reply(f"{em('cross', '❌')} {mention(target)} уже в браке.", parse_mode="HTML", disable_web_page_preview=True)

    # --- Восстановление после развода ---
    div = get_divorced_marriage(message.chat.id, message.from_user.id)
    if div:
        restore_marriage(div[0])
        return await message.reply("💞 <b>Брак восстановлен!</b>", parse_mode="HTML", disable_web_page_preview=True)

    # --- Предложение ---
    add_proposal(message.chat.id, message.from_user.id, target.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept:{message.from_user.id}:{target.id}:{message.chat.id}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"marry_reject:{message.from_user.id}:{target.id}:{message.chat.id}")
    ]])
    await message.reply(
        f"💍 <b>Предложение!</b>\n\n{mention(message.from_user)} → {mention(target)}\n\n{mention(target)}, ты согласен(на)?",
        parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb
    )


@dp.callback_query(lambda c: c.data and (c.data.startswith("marry_accept:") or c.data.startswith("marry_reject:")))
async def marriage_response(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) < 4:
        return await callback.answer("⚠️ Ошибка.", show_alert=True)
    action, from_id_str, to_id_str, chat_id_str = parts
    from_id = int(from_id_str); to_id = int(to_id_str); chat_id = int(chat_id_str)
    if callback.from_user.id != to_id:
        return await callback.answer("⛔ Это не тебе!", show_alert=True)
    if get_proposal(chat_id, from_id, to_id) is None:
        return await callback.answer("⚠️ Уже неактивно.", show_alert=True)
    try:
        fu = await bot.get_chat(from_id)
        tu = await bot.get_chat(to_id)
    except:
        return await callback.answer("❌ Ошибка загрузки.", show_alert=True)
    if action == "marry_accept":
        res = create_marriage(chat_id, from_id, fu.first_name, to_id, tu.first_name)
        if not res:
            return await callback.answer("❌ Кто-то уже в браке.", show_alert=True)
        remove_proposal(chat_id, from_id, to_id)
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except: pass
        await bot.send_message(chat_id,
            f"💍💐 <b>Свадьба!</b>\n\n{mention_by_id(from_id, fu.first_name, fu.username)} и {mention_by_id(to_id, tu.first_name, tu.username)} теперь в браке!",
            parse_mode="HTML", disable_web_page_preview=True)
        await callback.answer("💍 Вы в браке!")
    else:
        remove_proposal(chat_id, from_id, to_id)
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except: pass
        await bot.send_message(chat_id,
            f"💔 {mention_by_id(to_id, tu.first_name, tu.username)} отказал(а).",
            parse_mode="HTML", disable_web_page_preview=True)
        await callback.answer("❌ Отказано.")


@cmd("развод")
async def divorce_cmd(message: types.Message):
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar:
        return await message.reply("💔 Ты не в браке.", parse_mode="HTML", disable_web_page_preview=True)
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra = mar
    partner_id = u2_id if u1_id == message.from_user.id else u1_id
    partner_name = u2_name if u1_id == message.from_user.id else u1_name
    duration = format_marriage_duration(married_at, extra or 0)
    divorce_marriage(message.chat.id, message.from_user.id)
    await message.reply(
        f"💔 {mention(message.from_user)} и {mention_by_id(partner_id, partner_name)} развелись.\n📅 Длился: <b>{duration}</b>",
        parse_mode="HTML", disable_web_page_preview=True
    )


@cmd("мой брак")
@cmd("моя пара")
async def my_marriage_cmd(message: types.Message):
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar:
        return await message.reply("💔 Ты не в браке.", parse_mode="HTML", disable_web_page_preview=True)
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra = mar
    partner_id = u2_id if u1_id == message.from_user.id else u1_id
    partner_name = u2_name if u1_id == message.from_user.id else u1_name
    duration = format_marriage_duration(married_at, extra or 0)
    await message.reply(
        f"💍 <b>Ваш брак</b>\n\n👫 {mention(message.from_user)} 💞 {mention_by_id(partner_id, partner_name)}\n📅 {married_at[:10]}\n⏳ Вместе: <b>{duration}</b>",
        parse_mode="HTML", disable_web_page_preview=True
    )


@cmd("браки")
async def marriages_list_cmd(message: types.Message):
    pairs = get_all_marriages(message.chat.id)
    if not pairs:
        return await message.reply("📭 В этом чате пока нет браков.", parse_mode="HTML", disable_web_page_preview=True)
    text = "💍 <b>Браки в этом чате:</b>\n\n"
    for i, (u1_id, u1_name, u2_id, u2_name, married_at, extra) in enumerate(pairs, 1):
        duration = format_marriage_duration(married_at, extra or 0)
        text += f"{i}. {mention_by_id(u1_id, u1_name)} 💞 {mention_by_id(u2_id, u2_name)} — <i>{duration}</i>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


# ================= СЕТКА — ЕДИНЫЙ РОУТЕР =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!]?\s*сетка\b', m.text.strip(), re.IGNORECASE)
    and not m.text.lower().strip().startswith("сетка "))  # привязка чата без точки — отдельный хендлер выше
async def grid_command_router_dot(message: types.Message):
    """Роутер для команд сетки (когда есть префикс . / ! или это просто 'сетка <действие>')."""
    await _grid_router_impl(message)


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("сетка "))
async def grid_command_router_space(message: types.Message):
    """Роутер для 'сетка <действие>' (привязка чата отдельным хендлером выше)."""
    # Если это привязка — пропускаем (обрабатывается отдельным хендлером выше)
    txt = m.text.strip().lower()
    known_actions = ["инфо", "info", "+админ", "-админ", "разжаловать", "повысить", "понизить",
                     "+админка", "+adm", "-админка", "-adm", "снять", "+", "-"]
    parts = txt.split(maxsplit=1)
    if len(parts) >= 2:
        action = parts[1].split()[0].lower() if parts[1] else ""
        if action in known_actions:
            return await _grid_router_impl(m)
    return  # иначе — это привязка, обработана другим хендлером


async def _grid_router_impl(message: types.Message):
    if message.chat.type == "private":
        return await message.reply("⚠️ Команды сетки работают только в группе.", parse_mode="HTML", disable_web_page_preview=True)

    raw = message.text.strip()
    raw = re.sub(r'^[.\/!]\s*', '', raw)
    parts = raw.split()

    if len(parts) < 2:
        return await message.reply(
            "🕸 <b>Команды сетки:</b>\n\n"
            "• <code>сетка инфо</code>\n"
            "• <code>сетка +админ @user</code>\n"
            "• <code>сетка -админ @user</code>\n"
            "• <code>сетка разжаловать @user</code>\n"
            "• <code>сетка повысить @user 2</code>\n"
            "• <code>сетка понизить @user 1</code>",
            parse_mode="HTML", disable_web_page_preview=True
        )

    action = parts[1].lower()

    # --- ИНФО ---
    if action in ["инфо", "info"]:
        grid_id = get_chat_grid(message.chat.id)
        if not grid_id:
            return await message.reply("❌ Чат не привязан к сетке.", parse_mode="HTML", disable_web_page_preview=True)
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name, creator_id FROM grids WHERE id = ?", (grid_id,))
            g = c.fetchone()
            c.execute("SELECT chat_id, hidden FROM grid_chats WHERE grid_id = ?", (grid_id,))
            chats = c.fetchall()
            c.execute("SELECT user_id, rank, is_admin FROM grid_moderators WHERE grid_id = ?", (grid_id,))
            mods = c.fetchall()
        text = f"🕸 <b>Сетка #{grid_id}</b>\n"
        if g:
            text += f"📛 Название: <b>{g[0]}</b>\n👑 Создатель: <code>{g[1]}</code>\n"
        text += f"🗂 Чатов: <b>{len(chats)}</b>\n🛡 Модераторов: <b>{len(mods)}</b>\n\n"
        if mods:
            text += "<b>Модераторы:</b>\n"
            for uid, rank, is_admin in mods[:15]:
                try:
                    u = await bot.get_chat(uid)
                    name = user_link(uid, u.first_name, u.username)
                except: name = f"<code>{uid}</code>"
                badge = "👑" if is_admin else "🛡"
                text += f"{badge} {name} — ранг {rank}\n"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не привязан к сетке.", parse_mode="HTML", disable_web_page_preview=True)

    actor_id = message.from_user.id

    # --- +АДМИН ---
    if action in ["+админ", "+админка", "+adm"]:
        if actor_id != OWNER_ID and not is_grid_moderator(grid_id, actor_id, 5):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 5 в сетке.", parse_mode="HTML", disable_web_page_preview=True)
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка +админ @user</code>", parse_mode="HTML", disable_web_page_preview=True)
        if target.id == OWNER_ID: return
        try:
            bm = await bot.get_chat_member(message.chat.id, bot.id)
            if bm.status not in ["administrator", "creator"]:
                return await message.reply(f"{em('cross', '❌')} Я не админ здесь.", parse_mode="HTML", disable_web_page_preview=True)
            if bm.status == "administrator" and not getattr(bm, "can_promote_members", False):
                return await message.reply(f"{em('cross', '❌')} У меня нет права «Назначать админов».", parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            return await message.reply(f"{em('cross', '❌')} Ошибка прав: {e}", parse_mode="HTML", disable_web_page_preview=True)
        try:
            await bot.promote_chat_member(
                chat_id=message.chat.id, user_id=target.id,
                can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
                can_restrict_members=True, can_promote_members=False, can_change_info=True,
                can_invite_users=True, can_pin_messages=True
            )
        except Exception as e:
            return await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True)
        add_grid_moderator(grid_id, target.id, rank=4, is_admin=1)
        mark_bot_promoted(target.id, message.chat.id, actor_id)
        return await message.reply(f"{em('check', '✅')} {mention(target)} — <b>ТГ-админ</b> + админ сетки.", parse_mode="HTML", disable_web_page_preview=True)

    # --- -АДМИН ---
    if action in ["-админ", "-админка", "-adm"]:
        if actor_id != OWNER_ID and not is_grid_moderator(grid_id, actor_id, 5):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 5 в сетке.", parse_mode="HTML", disable_web_page_preview=True)
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка -админ @user</code>", parse_mode="HTML", disable_web_page_preview=True)
        if target.id == OWNER_ID: return
        results = []
        try:
            await bot.promote_chat_member(
                chat_id=message.chat.id, user_id=target.id,
                can_manage_chat=False, can_delete_messages=False, can_manage_video_chats=False,
                can_restrict_members=False, can_promote_members=False, can_change_info=False,
                can_invite_users=False, can_pin_messages=False
            )
            results.append("✅ ТГ-права сняты")
        except Exception as e: results.append(f"⚠️ ТГ: {e}")
        remove_grid_moderator(grid_id, target.id)
        unmark_bot_promoted(target.id, message.chat.id)
        results.append("✅ Убран из админов сетки")
        return await message.reply(f"{em('check', '✅')} <b>Снято с {mention(target)}:</b>\n\n" + "\n".join(results), parse_mode="HTML", disable_web_page_preview=True)

    # --- РАЗЖАЛОВАТЬ ---
    if action in ["разжаловать", "снять"]:
        if actor_id != OWNER_ID and not is_grid_moderator(grid_id, actor_id, 3):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 3.", parse_mode="HTML", disable_web_page_preview=True)
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка разжаловать @user</code>", parse_mode="HTML", disable_web_page_preview=True)
        if target.id == OWNER_ID: return
        remove_grid_moderator(grid_id, target.id)
        try:
            await bot.promote_chat_member(
                chat_id=message.chat.id, user_id=target.id,
                can_manage_chat=False, can_delete_messages=False, can_manage_video_chats=False,
                can_restrict_members=False, can_promote_members=False, can_change_info=False,
                can_invite_users=False, can_pin_messages=False
            )
        except: pass
        unmark_bot_promoted(target.id, message.chat.id)
        try: remove_grid_user_rank(grid_id, target.id)
        except: pass
        return await message.reply(f"{em('cross', '❌')} {mention(target)} <b>разжалован</b> в сетке.", parse_mode="HTML", disable_web_page_preview=True)

    # --- ПОВЫСИТЬ ---
    if action in ["повысить", "+"]:
        if actor_id != OWNER_ID and not is_grid_moderator(grid_id, actor_id, 4):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 4.", parse_mode="HTML", disable_web_page_preview=True)
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка повысить @user 2</code>", parse_mode="HTML", disable_web_page_preview=True)
        if target.id == OWNER_ID: return
        new_rank = 1
        for p in parts:
            if p.isdigit(): new_rank = int(p); break
        new_rank = max(1, min(4, new_rank))
        try: set_grid_user_rank(grid_id, target.id, new_rank, actor_id)
        except: pass
        add_grid_moderator(grid_id, target.id, rank=new_rank, is_admin=0)
        return await message.reply(f"🏆 {mention(target)} повышен до ранга <b>{new_rank}</b>", parse_mode="HTML", disable_web_page_preview=True)

    # --- ПОНИЗИТЬ ---
    if action in ["понизить", "-"]:
        if actor_id != OWNER_ID and not is_grid_moderator(grid_id, actor_id, 4):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 4.", parse_mode="HTML", disable_web_page_preview=True)
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка понизить @user 1</code>", parse_mode="HTML", disable_web_page_preview=True)
        if target.id == OWNER_ID: return
        new_rank = 1
        for p in parts:
            if p.isdigit(): new_rank = int(p); break
        new_rank = max(1, min(4, new_rank))
        try: set_grid_user_rank(grid_id, target.id, new_rank, actor_id)
        except: pass
        add_grid_moderator(grid_id, target.id, rank=new_rank, is_admin=0)
        return await message.reply(f"📉 {mention(target)} понижен до ранга <b>{new_rank}</b>", parse_mode="HTML", disable_web_page_preview=True)

    return await message.reply(
        f"❓ Неизвестно: <code>{action}</code>\n\n"
        "• <code>сетка инфо</code>\n"
        "• <code>сетка +админ @user</code>\n"
        "• <code>сетка -админ @user</code>\n"
        "• <code>сетка разжаловать @user</code>\n"
        "• <code>сетка повысить @user 2</code>\n"
        "• <code>сетка понизить @user 1</code>",
        parse_mode="HTML", disable_web_page_preview=True
    )


# ================= РЕПОРТЫ =================
REPORT_COMMAND_RE = re.compile(r'^[.!\/]\s*репорт\b', re.IGNORECASE)

@dp.message(lambda m: m.text and REPORT_COMMAND_RE.match(m.text.strip()))
async def report_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not message.reply_to_message:
        return await message.reply(f"{em('cross', '❌')} Ответьте на сообщение.\n📌 <code>.репорт [причина]</code>", parse_mode="HTML", disable_web_page_preview=True)
    target_msg = message.reply_to_message
    target = target_msg.from_user
    if target.id == bot.id or target.id == message.from_user.id or target.is_bot: return
    txt_clean = REPORT_COMMAND_RE.sub('', message.text.strip(), count=1).strip()
    reason = txt_clean if txt_clean else "без причины"
    report_chat_id = get_report_chat(message.chat.id)
    message_text = target_msg.text or target_msg.caption or "[не текст]"
    report_id = create_report(source_chat_id=message.chat.id, reporter=message.from_user, target=target, target_message_id=target_msg.message_id, message_text=message_text, reason=reason, forward_chat_id=report_chat_id)
    chat_title = message.chat.title or "чат"
    header = (
        f"🔔 <b>РЕПОРТ</b>\n\n"
        f"👤 От: {user_link(message.from_user.id, message.from_user.first_name, message.from_user.username)}\n"
        f"🎯 На: {user_link(target.id, target.first_name, target.username)}\n"
        f"🏠 Чат: {chat_title}\n"
        f"📝 {reason}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Проверен", callback_data=f"report_done:{report_id}")]])
    if report_chat_id:
        try:
            fwd = await bot.forward_message(chat_id=report_chat_id, from_chat_id=message.chat.id, message_id=target_msg.message_id)
            sent = await bot.send_message(report_chat_id, header, parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb, reply_to_message_id=fwd.message_id)
            set_report_forward_message(report_id, sent.message_id)
        except: pass
    await message.reply(f"✅ Жалоба отправлена. Спасибо!", parse_mode="HTML", disable_web_page_preview=True)


@dp.callback_query(lambda c: c.data and c.data.startswith("report_done:"))
async def report_done_handler(callback: types.CallbackQuery):
    report_id = int(callback.data.split(":")[1])
    report = get_report(report_id)
    if not report or report[13] == "reviewed": return await callback.answer("⚠️ Уже", show_alert=True)
    mark_report_reviewed(report_id, callback.from_user.id)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.answer("✅ Проверен")


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+репорты"))
async def set_report_chat_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not has_agent_rank(message.from_user.id, 1): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return
    report_chat_id = get_chat_by_code(args[1].strip().upper())
    if not report_chat_id: return
    set_report_chat(message.chat.id, report_chat_id, message.from_user.id)
    await message.reply(f"{em('check', '✅')} Репорты привязаны.", parse_mode="HTML", disable_web_page_preview=True)


# ================= БЭКАП / ИМПОРТ =================
@cmd("бэкап")
async def backup_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    try:
        with open(DATABASE_PATH, "rb") as f:
            data = f.read()
        await message.reply_document(types.BufferedInputFile(data, filename=f"bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"), caption="💾 Бэкап")
    except Exception as e:
        await message.reply(f"❌ {e}", disable_web_page_preview=True)


@dp.message(lambda m: m.text and m.text.strip().lower() in [".импорт", "/импорт", "!импорт"])
async def import_db_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Только владелец бота.", parse_mode="HTML", disable_web_page_preview=True)
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply(f"{em('cross', '❌')} <b>Ответьте на .db файл командой .импорт</b>", parse_mode="HTML", disable_web_page_preview=True)
    doc = message.reply_to_message.document
    if not doc.file_name.lower().endswith(".db"):
        return await message.reply(f"{em('cross', '❌')} Только <code>.db</code>.", parse_mode="HTML", disable_web_page_preview=True)
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        return await message.reply(f"{em('cross', '❌')} Файл больше 20 МБ.", parse_mode="HTML", disable_web_page_preview=True)
    status_msg = await message.reply("📥 Скачиваю...")
    temp_path = f"temp_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, temp_path)
        import sqlite3 as _sql
        try:
            with _sql.connect(temp_path) as test_conn:
                tc = test_conn.cursor()
                tc.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in tc.fetchall()]
        except Exception as e:
            os.remove(temp_path)
            return await status_msg.edit_text(f"{em('cross', '❌')} Файл повреждён: <code>{e}</code>", parse_mode="HTML")
        missing = [t for t in ["users", "messages_stats", "admins"] if t not in tables]
        if missing:
            os.remove(temp_path)
            return await status_msg.edit_text(f"{em('cross', '❌')} Не база Mos-бота. Нет: <code>{', '.join(missing)}</code>", parse_mode="HTML")
        os.makedirs("backups", exist_ok=True)
        old_backup = f"backups/old_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil
        if os.path.exists(DATABASE_PATH): shutil.copy2(DATABASE_PATH, old_backup)
        with _sql.connect(temp_path) as test_conn:
            tc = test_conn.cursor()
            try: tc.execute("SELECT COUNT(*) FROM users"); users_count = tc.fetchone()[0]
            except: users_count = "?"
            try: tc.execute("SELECT COUNT(*) FROM messages_stats"); messages_count = tc.fetchone()[0]
            except: messages_count = "?"
        shutil.move(temp_path, DATABASE_PATH)
        try: init_db()
        except: pass
        size_mb = doc.file_size / (1024 * 1024) if doc.file_size else 0
        await status_msg.edit_text(
            f"{em('check', '✅')} <b>База импортирована!</b>\n\n"
            f"👥 Пользователей: <b>{users_count}</b>\n💬 Сообщений: <b>{messages_count}</b>\n💾 Размер: <b>{size_mb:.2f} МБ</b>\n\n"
            f"⚠️ <b>ПЕРЕЗАПУСТИТЕ БОТА</b>",
            parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        await status_msg.edit_text(f"{em('cross', '❌')} Ошибка: <code>{e}</code>", parse_mode="HTML")


# ================= ОБРАБОТКА ВСЕХ СООБЩЕНИЙ =================
@dp.message()
async def all_messages(message: types.Message):
    if not message.from_user or message.from_user.is_bot: return

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
                try: await message.delete()
                except: pass
                try:
                    await bot.ban_chat_member(message.chat.id, message.from_user.id)
                    add_chat_ban(message.chat.id, message.from_user.id, "спам", message.from_user.id, None)
                except: pass
                try:
                    sent = await message.answer(f"{em('ban', '🚫')} {mention(message.from_user)} — <b>ссылки запрещены!</b>", parse_mode="HTML")
                    asyncio.create_task(delete_later(sent, 30))
                except: pass
                return

    # ===== АВТОМОДЕРАЦИЯ =====
    if message.chat.type in ["group", "supergroup"]:
        user_id = message.from_user.id
        chat_id = message.chat.id
        is_staff = user_id == OWNER_ID or has_agent_rank(user_id, 1) or get_rank(chat_id, user_id) >= 3
        if not is_staff:
            s = get_automod_settings(chat_id)
            if s["antimat"]:
                text_to_check = (message.text or message.caption or "").lower()
                if text_to_check and has_bad_words(text_to_check):
                    try: await message.delete()
                    except: pass
                    result = await apply_automod_punishment(chat_id, user_id, "antimat", s)
                    if result:
                        try:
                            sent = await message.answer(f"{em('ban', '🚫')} {mention(message.from_user)} — <b>мат!</b>\n{result}", parse_mode="HTML")
                            asyncio.create_task(delete_later(sent, 30))
                        except: pass
                    return
            if s["antiflood"]:
                if check_flood(user_id, chat_id, "text", limit=5, seconds=5):
                    result = await apply_automod_punishment(chat_id, user_id, "antiflood", s)
                    if result:
                        try:
                            sent = await message.answer(f"{em('mute', '🔇')} {mention(message.from_user)} — <b>флуд!</b>\n{result}", parse_mode="HTML")
                            asyncio.create_task(delete_later(sent, 30))
                        except: pass
                    return
            if s["anticaps"]:
                text_to_check = message.text or message.caption or ""
                if is_caps(text_to_check):
                    try: await message.delete()
                    except: pass
                    result = await apply_automod_punishment(chat_id, user_id, "anticaps", s)
                    if result:
                        try:
                            sent = await message.answer(f"{em('cross', '❌')} {mention(message.from_user)} — <b>капс!</b>\n{result}", parse_mode="HTML")
                            asyncio.create_task(delete_later(sent, 15))
                        except: pass
                    return
            if s["antisticker"] and message.sticker:
                if check_sticker_spam(user_id, chat_id, limit=5, seconds=10):
                    try: await message.delete()
                    except: pass
                    result = await apply_automod_punishment(chat_id, user_id, "antisticker", s)
                    if result:
                        try:
                            sent = await message.answer(f"{em('mute', '🔇')} {mention(message.from_user)} — <b>стикеры!</b>\n{result}", parse_mode="HTML")
                            asyncio.create_task(delete_later(sent, 30))
                        except: pass
                    return

    # ===== ОБЫЧНАЯ ЛОГИКА =====
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status == "creator":
            if get_rank(message.chat.id, message.from_user.id) < 5:
                set_rank(message.chat.id, message.from_user.id, 5, message.from_user.id)
    except: pass

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

    if is_ignored(message.chat.id, message.from_user.id):
        try: await message.delete()
        except: pass


# ================= ВХОД В ЧАТ =================
@dp.chat_member()
async def on_join(event: types.ChatMemberUpdated):
    if event.new_chat_member.status != "member": return
    user = event.new_chat_member.user
    chat_id = event.chat.id

    if is_antispam_enabled(chat_id) and is_in_antispam(user.id):
        try:
            await bot.ban_chat_member(chat_id, user.id)
            await bot.send_message(chat_id, f"{em('ban', '🚫')} {mention(user)} в антиспаме", parse_mode="HTML")
        except: pass
        return

    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            greeting = get_greeting(chat_id)
            if greeting:
                await bot.send_message(chat_id, format_greeting(greeting, user, event.chat), parse_mode="HTML")
            return
    except: return

    if not is_captcha_enabled(chat_id):
        greeting = get_greeting(chat_id)
        if greeting:
            try: await bot.send_message(chat_id, format_greeting(greeting, user, event.chat), parse_mode="HTML")
            except: pass
        return

    try:
        await bot.restrict_chat_member(chat_id=chat_id, user_id=user.id,
            permissions=types.ChatPermissions(can_send_messages=False))
    except: pass

    captcha_type = _random.choice(["emoji", "math", "odd"])
    if captcha_type == "emoji":
        rd = _random.choice(CAPTCHA_EMOJI_ROUNDS)
        options = rd["options"][:]; _random.shuffle(options)
        answer = rd["answer"]
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=opt, callback_data=f"captcha_answer:{user.id}:{chat_id}:{opt}")
            for opt in options
        ]])
        text_captcha = f"👋 {mention(user)}!\n\n🤖 <b>Проверка</b>\n\n❓ {rd['question']}"
    elif captcha_type == "math":
        a = _random.randint(2, 15); b = _random.randint(2, 15)
        op = _random.choice(["+", "-", "*"])
        if op == "+": answer = str(a + b); q = f"{a} + {b}"
        elif op == "-":
            if a < b: a, b = b, a
            answer = str(a - b); q = f"{a} − {b}"
        else: answer = str(a * b); q = f"{a} × {b}"
        wrong = set(); ans_int = int(answer)
        while len(wrong) < 3:
            delta = _random.randint(-5, 5)
            if delta == 0: continue
            w = ans_int + delta
            if w > 0 and w != ans_int: wrong.add(str(w))
        options = list(wrong) + [answer]; _random.shuffle(options)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=opt, callback_data=f"captcha_answer:{user.id}:{chat_id}:{opt}")
            for opt in options
        ]])
        text_captcha = f"👋 {mention(user)}!\n\n🤖 <b>Проверка</b>\n\n❓ {q}"
    else:
        emojis, odd = _make_odd_one_out()
        rows = []; row = []
        for i, e in enumerate(emojis):
            row.append(InlineKeyboardButton(text=e, callback_data=f"captcha_answer:{user.id}:{chat_id}:{i}"))
            if len(row) == 3: rows.append(row); row = []
        if row: rows.append(row)
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        answer = str(emojis.index(odd))
        text_captcha = f"👋 {mention(user)}!\n\n🤖 <b>Найди отличающийся</b>"

    try:
        msg = await bot.send_message(chat_id, text_captcha, reply_markup=kb, parse_mode="HTML")
        save_captcha(user.id, chat_id, msg.message_id, captcha_type, answer)
        asyncio.create_task(captcha_timeout(user.id, chat_id))
    except: pass


async def captcha_timeout(user_id, chat_id):
    await asyncio.sleep(120)
    cap = get_captcha(user_id, chat_id)
    if cap:
        try:
            await bot.ban_chat_member(chat_id, user_id)
            await bot.unban_chat_member(chat_id, user_id)
        except: pass
        if cap[0]:
            try: await bot.delete_message(chat_id, cap[0])
            except: pass
        remove_captcha(user_id, chat_id)


@dp.callback_query(lambda c: c.data and c.data.startswith("captcha_answer:"))
async def captcha_answer_handler(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) < 4: return await callback.answer("⚠️", show_alert=True)
    target_user_id = int(parts[1]); chat_id = int(parts[2]); given = parts[3]
    if callback.from_user.id != target_user_id:
        return await callback.answer("⛔ Не твоя!", show_alert=True)
    cap = get_captcha(target_user_id, chat_id)
    if not cap: return await callback.answer("⚠️ Неактивна.", show_alert=True)
    _, _, correct = cap
    if given != correct:
        try:
            await bot.ban_chat_member(chat_id, target_user_id)
            await bot.unban_chat_member(chat_id, target_user_id)
        except: pass
        remove_captcha(target_user_id, chat_id)
        try: await callback.message.delete()
        except: pass
        return await callback.answer("❌ Неверно!", show_alert=True)
    try:
        await bot.restrict_chat_member(chat_id=chat_id, user_id=target_user_id,
            permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_send_polls=True, can_invite_users=True))
    except: pass
    remove_captcha(target_user_id, chat_id)
    try: await callback.message.delete()
    except: pass
    greeting = get_greeting(chat_id)
    if greeting:
        try:
            chat = await bot.get_chat(chat_id)
            await bot.send_message(chat_id, format_greeting(greeting, callback.from_user, chat), parse_mode="HTML")
        except: pass
    else:
        await bot.send_message(chat_id, f"👋 Привет, {mention(callback.from_user)}!", parse_mode="HTML")
    await callback.answer("✅ Пройдена!")


# ================= ЗАЯВКИ =================
@dp.chat_join_request()
async def on_join_request(request: types.ChatJoinRequest):
    chat_id = request.chat.id; user = request.from_user
    if is_antispam_enabled(chat_id) and is_in_antispam(user.id):
        try: await request.decline()
        except: pass
        return
    try: await request.approve()
    except: pass


# ================= /MY_BANS =================
@dp.message(Command("my_bans"))
async def my_bans_cmd(message: types.Message):
    if message.chat.type != "private": return
    user_id = message.from_user.id
    bans = []
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT reason, banned_at FROM chat_bans WHERE user_id = ? AND (until_date IS NULL OR until_date > ?)",
                  (user_id, datetime.now().isoformat()))
        for reason, banned_at in c.fetchall():
            bans.append(f"🚫 {reason} ({banned_at[:10]})")
    if is_in_antispam(user_id):
        info = get_antispam_info(user_id)
        bans.append(f"☢️ Антиспам: {info[0] if info else '?'}")
    if not bans:
        return await message.reply("✅ У вас нет банов.", parse_mode="HTML", disable_web_page_preview=True)
    await message.reply("📋 <b>Ваши баны:</b>\n\n" + "\n".join(bans), parse_mode="HTML", disable_web_page_preview=True)


# ================= БОТ ДОБАВЛЕН =================
@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    if event.new_chat_member.status not in ["member", "administrator"]: return
    chat_id = event.chat.id; chat_type = event.chat.type
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.status == "creator":
                set_rank(chat_id, admin.user.id, 5, admin.user.id)
                break
    except: pass
    if chat_type in ["group", "supergroup"]:
        try:
            await bot.send_message(chat_id, f"👋 Я <b>{BOT_NAME}</b>!\n⚙️ Дайте права администратора.\n🆘 {SUPPORT_CHAT_LINK}", parse_mode="HTML")
        except: pass


# ================= BUSINESS =================
@dp.business_connection()
async def on_business_connection(connection: types.BusinessConnection):
    if connection.is_enabled:
        save_business_connection(connection.user.id, connection.id)


# ================= ФОНОВЫЕ ЗАДАЧИ =================
async def auto_unban_loop():
    while True:
        try:
            expired = get_expired_bans()
            for chat_id, user_id in expired:
                try:
                    await bot.unban_chat_member(chat_id, user_id)
                    clear_chat_ban(chat_id, user_id)
                except: pass
        except: pass
        await asyncio.sleep(300)


async def auto_backup_loop():
    while True:
        try:
            now = datetime.now(timezone.utc) + timedelta(hours=3)
            if (now.hour == 9 and now.minute < 5) or (now.hour == 21 and now.minute < 5):
                period = "morning" if now.hour == 9 else "evening"
                marker = f"backups/.last_sent_{period}_{now.date().isoformat()}"
                os.makedirs("backups", exist_ok=True)
                if not os.path.exists(marker):
                    import shutil
                    ts = now.strftime("%Y%m%d_%H%M%S")
                    shutil.copy2(DATABASE_PATH, f"backups/bot_{ts}.db")
                    with open(DATABASE_PATH, "rb") as f:
                        data = f.read()
                    try:
                        await bot.send_document(OWNER_ID, types.BufferedInputFile(data, filename=f"mos_backup_{ts}.db"),
                            caption=f"💾 <b>Бэкап {period}</b>", parse_mode="HTML")
                    except: pass
                    with open(marker, "w") as f: f.write(str(now))
        except: pass
        await asyncio.sleep(300)


async def auto_fishing_events_loop():
    while True:
        try:
            await asyncio.sleep(1800)
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT DISTINCT chat_id FROM messages_stats WHERE date >= ? AND chat_id < 0",
                    ((datetime.now().date() - timedelta(days=3)).isoformat(),))
                chats = [r[0] for r in c.fetchall()]
            for chat_id in chats:
                if chat_id >= 0: continue
                if not is_events_enabled(chat_id): continue
                try:
                    chat = await bot.get_chat(chat_id)
                    if chat.type not in ["group", "supergroup"]: continue
                except: continue
                if random.randint(1, 100) <= 30:
                    ev_key = random.choice(list(FISHING_EVENTS.keys()))
                    ev = FISHING_EVENTS[ev_key]
                    set_event(chat_id, ev_key, ev["bonus"], ev["duration"])
                    try:
                        await bot.send_message(chat_id, f"🌦 <b>Событие!</b>\n\n{ev['name']}\n📈 ×{ev['bonus']}\n⏰ {ev['duration']} мин.", parse_mode="HTML")
                    except: pass
        except Exception as e:
            print(f"❌ events: {e}")
        await asyncio.sleep(60)


async def auto_tournament_end_loop():
    while True:
        try:
            await asyncio.sleep(60)
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT chat_id FROM fishing_tournaments WHERE expires_at <= ?", (datetime.now().isoformat(),))
                expired = [r[0] for r in c.fetchall()]
            for chat_id in expired:
                winners = end_tournament(chat_id)
                if winners:
                    text = "🏆 <b>ТУРНИР ЗАВЕРШЁН!</b>\n\n"
                    medals = ["🥇", "🥈", "🥉"]
                    for i, (uid, caught, prize) in enumerate(winners):
                        try:
                            u = await bot.get_chat(uid)
                            name = user_link(uid, u.first_name, u.username)
                        except: name = f"ID {uid}"
                        text += f"{medals[i]} {name} — <b>{caught}</b> 🐟 (+{prize} 🍬)\n"
                    try: await bot.send_message(chat_id, text, parse_mode="HTML")
                    except: pass
        except: pass
        await asyncio.sleep(30)


# ================= ЗАПУСК =================
async def main():
    init_db()
    print("✅ Бот запущен!")
    asyncio.create_task(auto_unban_loop())
    asyncio.create_task(auto_backup_loop())
    asyncio.create_task(auto_fishing_events_loop())
    asyncio.create_task(auto_tournament_end_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
