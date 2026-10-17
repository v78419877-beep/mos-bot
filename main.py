import asyncio
from aiogram.dispatcher.event.bases import SkipHandler
import sqlite3
import random
import string
import os
import re
import json
import logging
import traceback
import aiohttp
from urllib.parse import quote
from urllib.request import urlopen
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO

# ================= НОВОЕ: ZvenoAI + dotenv =================
from dotenv import load_dotenv
load_dotenv()
from openai import AsyncOpenAI, APIError

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = 7305320918
DATABASE_PATH = os.environ.get("DATABASE_PATH", "bot.db")
BOT_NAME = "Mos | Чат-менеджер"
SUPPORT_CHAT_LINK = "https://t.me/mospodd"
SUPPORT_CHANNEL_LINK = "https://t.me/moskanalp"
FISHING_CHANNEL_ID = -1004491497040
FISHING_REQUIRE_SUBSCRIPTION = True
MODERATION_CHAT_ID = -1004438332613
SUPPORT_CHAT_ID = -1004438332613
TELETYPE_URL = "https://teletype.in/@sirenie3/Mos-command"
TERMS_URL = "https://teletype.in/@sirenie3/POLSVATELCKOEMOS"

BOT_START_TIME = datetime.now()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= ХЕЛПЕРЫ =================
def _match_command(message: types.Message, name_lower: str,
                   allow_args: bool = False,
                   args_pattern: str = None,
                   require_prefix: bool = False) -> bool:
    if not message.text:
        return False
    txt = message.text
    if not txt:
        return False
    txt_stripped = txt.lstrip()
    if not txt_stripped:
        return False
    had_prefix = txt_stripped[0] in ".!/+-"
    if had_prefix:
        txt_stripped = txt_stripped[1:].lstrip()
    if not txt_stripped:
        return False
    if require_prefix and not had_prefix:
        return False
    first_line = txt_stripped.split("\n", 1)[0].strip()
    if not first_line:
        return False
    first_line_lower = first_line.lower()
    name_lower_clean = name_lower.lower().strip()
    words_needed = name_lower_clean.split()
    words_have = first_line_lower.split()
    if len(words_have) < len(words_needed):
        return False
    if words_have[:len(words_needed)] != words_needed:
        return False
    tail = words_have[len(words_needed):]
    if not tail:
        return True
    if not allow_args:
        return False
    if args_pattern:
        rest_text = " ".join(tail)
        return bool(re.match(args_pattern, rest_text, re.IGNORECASE))
    return True


def cmd(name: str, allow_args: bool = False, args_pattern: str = None, require_prefix: bool = False):
    name_lower = name.lower().strip()
    def decorator(func):
        @dp.message(lambda m: _match_command(m, name_lower, allow_args, args_pattern, require_prefix))
        async def handler(message: types.Message):
            try:
                if not await check_command_access(message, name_lower): return
            except Exception as e:
                print(f"❌ check_command_access '{name_lower}': {e}")
                return
            return await func(message)
        return handler
    return decorator


def mod_cmd(name: str, allow_args: bool = False, args_pattern: str = None, require_prefix: bool = True):
    name_lower = name.lower().strip()
    def decorator(func):
        @dp.message(lambda m: _match_command(m, name_lower, allow_args, args_pattern, require_prefix))
        async def handler(message: types.Message):
            try:
                if not await check_command_access(message, name_lower):
                    return
            except Exception as e:
                try:
                    await message.reply(f"❌ Ошибка доступа: <code>{e}</code>", parse_mode="HTML")
                except: pass
                return
            try:
                return await func(message)
            except Exception as e:
                tb = traceback.format_exc()
                print(f"   ❌ ВНУТРЕННЯЯ ОШИБКА: {tb}")
                try:
                    await message.reply(
                        f"❌ <b>Ошибка в команде</b> <code>{name_lower}</code>\n\n"
                        f"<code>{type(e).__name__}: {e}</code>",
                        parse_mode="HTML", disable_web_page_preview=True
                    )
                except: pass
        return handler
    return decorator


def _reply_kwargs(message: types.Message) -> dict:
    if message.reply_to_message:
        return {"reply_to_message_id": message.reply_to_message.message_id}
    return {}


# ================= ЭМОДЗИ (С ПАТЧЕМ ПРЕМИУМ) =================
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

_VERIFIED_EMOJI_IDS: set = set()

_EMOJI_FALLBACKS = {
    "mute": "🔇", "pencil": "✏️", "wave": "👋", "stats": "📊",
    "ban": "🚫", "id": "🆔", "check": "✅", "ping": "🏓",
    "cross": "❌", "calendar": "🗓", "alien": "👽", "sos": "🆘",
    "gear": "⚙️", "shield": "🛡", "key": "🔑", "user": "👤",
    "write": "✍️", "pin": "📌", "announce": "📢", "artist": "🎨",
    "like": "👍", "dislike": "👎", "heart": "❤️", "education": "🎓",
    "art": "🎭", "broom": "🧹", "briefcase": "💼", "wrench": "🔧",
    "crop": "✂️", "notify": "🔔", "sport": "⚽", "mask": "🎭",
    "qr": "📱", "eye": "👁", "people": "👥", "envelope": "✉️",
    "card": "💳", "lab": "🔬", "medicine": "💊", "audio": "🎵",
    "video": "🎬", "verified": "✔️", "wallet": "👛", "music": "🎶",
}


def register_premium_emoji(emoji_id: str, fallback: str = ""):
    if not emoji_id:
        return
    eid = str(emoji_id)
    if eid in _VERIFIED_EMOJI_IDS:
        return
    _VERIFIED_EMOJI_IDS.add(eid)
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS premium_emojis (
                emoji_id TEXT PRIMARY KEY, fallback TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            c.execute("INSERT OR IGNORE INTO premium_emojis (emoji_id, fallback) VALUES (?, ?)",
                      (eid, fallback or ""))
            conn.commit()
    except Exception:
        pass


def em(name, fallback=None):
    eid = EMOJI.get(name)
    if not eid:
        return fallback or _EMOJI_FALLBACKS.get(name, "🔹")
    fb = fallback or _EMOJI_FALLBACKS.get(name, "🔹")
    if str(eid) not in _VERIFIED_EMOJI_IDS:
        return fb
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'


def mention(user):
    if getattr(user, 'username', None):
        return f'<a href="https://t.me/{user.username}">{user.first_name}</a>'
    return f'<b>{user.first_name}</b>'


def mention_by_id(user_id, first_name, username=None):
    if username: return f'<a href="https://t.me/{username}">{first_name}</a>'
    return f'<b>{first_name}</b>'


def user_link(user_id, first_name="Пользователь", username=None):
    if username: return f'<a href="https://t.me/{username}">{first_name}</a>'
    return f'<b>{first_name}</b>'


def html_escape_text(text: str) -> str:
    if not text: return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ================= РЕНДЕР ENTITIES → HTML =================
class _SimpleEntity:
    """Заглушка вместо types.MessageEntity — тот ломается в новых aiogram."""
    __slots__ = ("type", "offset", "length", "url", "language", "custom_emoji_id")
    def __init__(self, type, offset, length, url=None, language=None, custom_emoji_id=None):
        self.type = type
        self.offset = offset
        self.length = length
        self.url = url
        self.language = language
        self.custom_emoji_id = custom_emoji_id


def _render_entities_html(text: str, entities: list) -> str:
    if not text:
        return ""
    if not entities:
        return html_escape_text(text)

    sorted_ents = sorted(entities, key=lambda e: (e.offset, -e.length))

    def render_range(start, end, ent_list):
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
            inner_text = render_range(e.offset, e.offset + e.length, [x for x in inner if x is not e])
            etype = e.type
            if etype == "bold":
                result.append(f"<b>{inner_text}</b>")
            elif etype == "italic":
                result.append(f"<i>{inner_text}</i>")
            elif etype == "underline":
                result.append(f"<u>{inner_text}</u>")
            elif etype == "strikethrough":
                result.append(f"<s>{inner_text}</s>")
            elif etype == "spoiler":
                result.append(f"<tg-spoiler>{inner_text}</tg-spoiler>")
            elif etype == "code":
                result.append(f"<code>{html_escape_text(raw)}</code>")
            elif etype == "pre":
                lang = getattr(e, "language", None)
                if lang:
                    result.append(f'<pre><code class="language-{lang}">{html_escape_text(raw)}</code></pre>')
                else:
                    result.append(f"<pre>{html_escape_text(raw)}</pre>")
            elif etype == "blockquote":
                result.append(f"<blockquote>{inner_text}</blockquote>")
            elif etype == "expandable_blockquote":
                result.append(f"<blockquote expandable>{inner_text}</blockquote>")
            elif etype == "text_link":
                url = getattr(e, "url", "") or ""
                result.append(f'<a href="{url}">{inner_text}</a>')
            elif etype == "url":
                url = text[e.offset:e.offset + e.length]
                result.append(f'<a href="{url}">{html_escape_text(url)}</a>')
            elif etype == "custom_emoji":
                emoji_id = getattr(e, "custom_emoji_id", None) or ""
                if emoji_id and raw:
                    register_premium_emoji(emoji_id, raw)
                    result.append(f'<tg-emoji emoji-id="{emoji_id}">{raw}</tg-emoji>')
                else:
                    result.append(raw if raw else "")
            else:
                result.append(inner_text)
            pos = e.offset + e.length
        if pos < end:
            result.append(html_escape_text(text[pos:end]))
        return "".join(result)

    return render_range(0, len(text), sorted_ents).strip()


def entities_to_html(message: types.Message) -> str:
    if not message.text:
        return ""
    return _render_entities_html(message.text, message.entities or [])


def entities_to_html_from(message: types.Message, char_index: int) -> str:
    if not message.text:
        return ""
    text = message.text
    entities = message.entities or []
    if not entities:
        return html_escape_text(text[char_index:])

    fragment = text[char_index:]
    frag_len = len(fragment)
    shifted = []
    for e in entities:
        if e.offset + e.length <= char_index:
            continue
        new_off = max(0, e.offset - char_index)
        if e.offset < char_index:
            new_len = e.offset + e.length - char_index
        else:
            new_len = e.length
        if new_off + new_len > frag_len:
            new_len = frag_len - new_off
        if new_len <= 0:
            continue
        shifted.append(_SimpleEntity(
            type=e.type, offset=new_off, length=new_len,
            url=getattr(e, "url", None),
            language=getattr(e, "language", None),
            custom_emoji_id=getattr(e, "custom_emoji_id", None),
        ))
    return _render_entities_html(fragment, shifted)


def _extract_html_after(message: types.Message, char_index: int) -> str:
    return entities_to_html_from(message, char_index)

# ================= РАНГИ =================
RANK_NAMES = {0: "👤 Участник", 1: "🛡️ Мл. Модератор", 2: "🛡️ Ст. Модератор",
              3: "👑 Мл. Админ", 4: "👑 Ст. Админ", 5: "⚜️ Владелец"}

RANK_ICONS = {0: "👤", 1: "🛡️", 2: "🛡️", 3: "👑", 4: "👑", 5: "⚜️"}

AGENT_RANKS = {1: "🛡 Мл. Агент", 2: "🛡 Агент", 3: "🛡 Ст. Агент", 4: "⚜️ Гл. Агент"}


# ================= НАЗВАНИЯ МОДЕРАТОРОВ =================
DEFAULT_MODERATOR_TITLES = {
    0: {"nom": "Участник",      "gen": "Участника",      "dat": "Участнику",      "ins": "Участником",      "plu": "Участники"},
    1: {"nom": "Мл. Модератор", "gen": "Мл. Модератора", "dat": "Мл. Модератору", "ins": "Мл. Модератором", "plu": "Мл. Модераторы"},
    2: {"nom": "Ст. Модератор", "gen": "Ст. Модератора", "dat": "Ст. Модератору", "ins": "Ст. Модератором", "plu": "Ст. Модераторы"},
    3: {"nom": "Мл. Админ",     "gen": "Мл. Админа",     "dat": "Мл. Админу",     "ins": "Мл. Админом",     "plu": "Мл. Админы"},
    4: {"nom": "Ст. Админ",     "gen": "Ст. Админа",     "dat": "Ст. Админу",     "ins": "Ст. Админом",     "plu": "Ст. Админы"},
    5: {"nom": "Владелец",      "gen": "Владельца",      "dat": "Владельцу",      "ins": "Владельцем",      "plu": "Владельцы"},
}

DEFAULT_MODERATORS_HEADER = "🏆 Модераторы"


def get_moderator_title(chat_id: int, rank: int, case: str = "nom") -> str:
    case_map = {"nom": 2, "gen": 3, "dat": 4, "ins": 5, "plu": 6}
    col = case_map.get(case, 2)
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute(f"""SELECT title_nom, title_gen, title_dat, title_ins, title_plu
                          FROM moderator_titles WHERE chat_id = ? AND rank = ?""",
                      (chat_id, rank))
            r = c.fetchone()
            if r and r[col - 2]:
                return r[col - 2]
    except Exception:
        pass
    default = DEFAULT_MODERATOR_TITLES.get(rank, DEFAULT_MODERATOR_TITLES[0])
    return default.get(case, default["nom"])


def set_moderator_title(chat_id: int, rank: int, case: str, value: str):
    col_map = {"nom": "title_nom", "gen": "title_gen", "dat": "title_dat",
               "ins": "title_ins", "plu": "title_plu"}
    col = col_map.get(case)
    if not col: return False
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO moderator_titles (chat_id, rank) VALUES (?, ?)", (chat_id, rank))
        c.execute(f"UPDATE moderator_titles SET {col} = ? WHERE chat_id = ? AND rank = ?", (value, chat_id, rank))
        conn.commit()
    return True


def reset_moderator_titles(chat_id: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM moderator_titles WHERE chat_id = ?", (chat_id,))
        conn.commit()


def get_all_moderator_titles(chat_id: int) -> dict:
    result = {}
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("""SELECT rank, title_nom, title_gen, title_dat, title_ins, title_plu
                         FROM moderator_titles WHERE chat_id = ?""", (chat_id,))
            custom = {row[0]: row[1:] for row in c.fetchall()}
    except Exception:
        custom = {}
    for rank in range(6):
        base = dict(DEFAULT_MODERATOR_TITLES.get(rank, DEFAULT_MODERATOR_TITLES[0]))
        if rank in custom:
            vals = custom[rank]
            for i, key in enumerate(["nom", "gen", "dat", "ins", "plu"]):
                if vals[i]: base[key] = vals[i]
        result[rank] = base
    return result


def parse_title_template(text: str) -> dict:
    result = {}
    parts = re.split(r'[;|]', text)
    for p in parts:
        p = p.strip()
        if "=" not in p: continue
        k, v = p.split("=", 1)
        k = k.strip().lower()
        v = v.strip()
        key_map = {"и": "nom", "р": "gen", "д": "dat", "т": "ins", "мн": "plu",
                   "nom": "nom", "gen": "gen", "dat": "dat", "ins": "ins", "plu": "plu"}
        if k in key_map and v:
            result[key_map[k]] = v
    return result


def rank_display(chat_id: int, rank: int, case: str = "nom") -> str:
    icon = RANK_ICONS.get(rank, "👤")
    title = get_moderator_title(chat_id, rank, case)
    return f"{icon} {title}"


def get_moderators_header(chat_id: int) -> str:
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT header FROM chat_moderators_header WHERE chat_id = ?", (chat_id,))
            r = c.fetchone()
            if r and r[0]:
                return r[0]
    except Exception:
        pass
    return DEFAULT_MODERATORS_HEADER


def set_moderators_header(chat_id: int, header: str):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO chat_moderators_header (chat_id, header) VALUES (?, ?)",
                  (chat_id, header[:128]))
        conn.commit()


def reset_moderators_header(chat_id: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM chat_moderators_header WHERE chat_id = ?", (chat_id,))
        conn.commit()


def cleanup_zero_ranks():
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM admins WHERE rank <= 0")
            conn.commit()
    except Exception:
        pass


# ================= ДК =================
DEFAULT_ACCESS = {
    "брак": 0, "развод": 0, "профиль": 0, "анкета": 0, "мойид": 0, "пинг": 0, "помощь": 0,
    "команды": 0, "инфо": 0, "ид": 0, "чатид": 0, "топ": 0, "погода": 0, "лс": 0,
    "моя стата": 0, "мой брак": 0, "моя пара": 0, "браки": 0,
    "мой вип": 0, "ник": 0, "о себе": 0, "звание": 0, "девиз": 0,
    "гражданство": 0, "кто гражданин": 0, "мешок": 0,
    "мешки": 0, "перевод": 0, "коины": 0, "баланс": 0, "ферма": 0,
    "купить коины": 0, "бкоин": 0, "коинытоп": 0, "купитьириски": 0,
    "рыбалка": 0, "рыба": 0, "рыбачить": 0, "рыбтоп": 0,
    "моя рыбалка": 0, "рыбстата": 0, "магазин снастей": 0, "снасти": 0,
    "купить": 0, "улучшить": 0, "инвентарь": 0, "инв": 0,
    "мои рыбные ачивки": 0, "рыбные ачивки": 0,
    "событие": 0, "события": 0, "турнир": 0,
    "садок": 0, "моя рыба": 0, "рыбасадок": 0, "продать": 0,
    "ачивки": 0, "все ачивки": 0, "мои ачивки": 0, "твои ачивки": 0, "вип": 0, "купить вип": 0,
    "мрп": 0, "репорт": 0, "админы": 0, "ухожу в отставку": 0,
    "регион": 3, "рыбное место": 3, "локация": 3, "локации": 3,
    "translate": 0,
    "калькулятор": 0, "кальк": 0, "calc": 0,
    "курс": 0, "крипта": 0, "биржа": 0,
    "вики": 0, "wiki": 0,
    "праздники": 0, "праздник": 0, "holidays": 0,
    "запретить переводы": 0, "разрешить переводы": 0, "мои запреты": 0, "запреты": 0,
    "выдать ачивку": 3, "снять ачивку": 4, "создать ачивку": 4,
    "бан": 2, "разбан": 2, "мут": 1, "размут": 1, "кик": 1,
    "варн": 1, "варны": 1, "снятьварн": 2, "сбросварнов": 3,
    "наказания": 1, "баны": 1, "пин": 1, "закрепить": 1,
    "анпин": 1, "открепить": 1, "унпин": 1, "репорты": 3,
    "правила": 3, "приветствие": 3, "фильтрссылок": 3,
    "капча": 3, "автомод": 3, "автомодерация": 3,
    "капчавремя": 3, "капча время": 3,
    "обновить чат": 3, "обновитьчат": 3, "кто не писал": 2, "неактивные": 2,
    "повысить": 3, "понизить": 3, "разжаловать": 3, "снять": 3, "восстановить": 3,
    "агенты": 4, "скрытые": 5, "совладельцы": 5,
    "создать сетку": 5, "чаты": 1, "глобан": 2, "глоразбан": 2,
    "заметка": 3, "заметки": 3, "пополнить": 3,
    "инфобот": -2, "бэкап": -2, "импорт": -2,
    "дк": 3, "дк список": 3, "дк сброс": 3,
    "топ браков": 0,
    "поженить пару": 3,
    "развести пару": 3,
    "сброс браков": 4,
    "развести вышедших": 3,
    "антиспам": 3,
    "мос": 0,
    "модераторы": 4,
    "названия": 4,
    "названия рангов": 4,
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
    "локации": "локация",
    "кто админ": "админы", "ктоадмин": "админы",
    "названия рангов": "модераторы",
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
        c.execute("""CREATE TABLE IF NOT EXISTS coowners (
            user_id INTEGER PRIMARY KEY, added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS bot_ignore (
            user_id INTEGER PRIMARY KEY, added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS hidden_achievements (
            user_id INTEGER PRIMARY KEY, hidden_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("CREATE TABLE IF NOT EXISTS antispam (user_id INTEGER PRIMARY KEY, reason TEXT, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS ignore_list (user_id INTEGER, chat_id INTEGER, reason TEXT, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_codes (chat_id INTEGER PRIMARY KEY, code TEXT UNIQUE)")
        c.execute("""CREATE TABLE IF NOT EXISTS messages_stats (
            user_id INTEGER, chat_id INTEGER, date DATE,
            count INTEGER DEFAULT 1,
            last_message_at TIMESTAMP,
            UNIQUE(user_id, chat_id, date)
        )""")
        try:
            c.execute("PRAGMA table_info(messages_stats)")
            cols = [row[1] for row in c.fetchall()]
            if "last_message_at" not in cols:
                c.execute("ALTER TABLE messages_stats ADD COLUMN last_message_at TIMESTAMP")
                c.execute("UPDATE messages_stats SET last_message_at = date || ' 12:00:00' WHERE last_message_at IS NULL")
                conn.commit()
        except Exception as e:
            print(f"⚠️ Миграция messages_stats: {e}")
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_stats_chat_date ON messages_stats(chat_id, date)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_stats_user_chat ON messages_stats(user_id, chat_id)")
        except Exception as e:
            print(f"⚠️ Индексы: {e}")

        c.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER, chat_id INTEGER, rank INTEGER DEFAULT 1, added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS bot_promoted (user_id INTEGER, chat_id INTEGER, promoted_by INTEGER, promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, chat_id))")
        c.execute("""CREATE TABLE IF NOT EXISTS warn_settings (
            chat_id INTEGER PRIMARY KEY,
            warn_limit INTEGER DEFAULT 3,
            action TEXT DEFAULT 'mute',
            duration_text TEXT DEFAULT '1 час',
            duration_seconds INTEGER DEFAULT 3600
        )""")
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
            chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0, timeout INTEGER DEFAULT 120)""")
        try:
            c.execute("PRAGMA table_info(captcha_settings)")
            cols = [row[1] for row in c.fetchall()]
            if "timeout" not in cols:
                c.execute("ALTER TABLE captcha_settings ADD COLUMN timeout INTEGER DEFAULT 120")
                c.execute("UPDATE captcha_settings SET timeout = 120 WHERE timeout IS NULL")
                conn.commit()
        except Exception as e:
            print(f"⚠️ Миграция captcha_settings: {e}")
        c.execute("""CREATE TABLE IF NOT EXISTS command_notify_settings (
            chat_id INTEGER PRIMARY KEY, notify_enabled INTEGER DEFAULT 1)""")
        c.execute("CREATE TABLE IF NOT EXISTS business_connections (user_id INTEGER PRIMARY KEY, connection_id TEXT, connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS chat_bans (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER, reason TEXT, banned_by INTEGER, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, until_date TIMESTAMP, was_antispam INTEGER DEFAULT 0)")
        try:
            c.execute("PRAGMA table_info(chat_bans)")
            cols = [row[1] for row in c.fetchall()]
            if "was_antispam" not in cols:
                c.execute("ALTER TABLE chat_bans ADD COLUMN was_antispam INTEGER DEFAULT 0")
                conn.commit()
        except Exception as e:
            print(f"⚠️ Миграция chat_bans: {e}")
        c.execute("""CREATE TABLE IF NOT EXISTS chat_mutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, user_id INTEGER, reason TEXT,
            muted_by INTEGER, muted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            until_date TIMESTAMP)""")
        c.execute("CREATE TABLE IF NOT EXISTS grids (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, creator_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS grid_chats (grid_id INTEGER, chat_id INTEGER, hidden INTEGER DEFAULT 0, description TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, chat_id))")
        c.execute("CREATE TABLE IF NOT EXISTS grid_moderators (grid_id INTEGER, user_id INTEGER, rank INTEGER DEFAULT 1, is_admin INTEGER DEFAULT 0, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(grid_id, user_id))")
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
        c.execute("CREATE TABLE IF NOT EXISTS global_rp_commands (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, emoji TEXT, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, name))")
        c.execute("CREATE TABLE IF NOT EXISTS chat_antispam_settings (chat_id INTEGER PRIMARY KEY, antispam_enabled INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS stars_settings (chat_id INTEGER PRIMARY KEY, stars_per_candy INTEGER DEFAULT 2)")
        c.execute("CREATE TABLE IF NOT EXISTS stars_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, amount_candies INTEGER, stars_paid INTEGER, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS antispam_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, reason TEXT, admin_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS link_filter (chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS hidden_agents (user_id INTEGER PRIMARY KEY, hidden_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS global_settings (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("""CREATE TABLE IF NOT EXISTS transfer_blocks (
            blocker_id INTEGER, blocked_id INTEGER,
            added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(blocker_id, blocked_id))""")
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
            expires_at TIMESTAMP, prize INTEGER DEFAULT 100)""")
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
        c.execute("""CREATE TABLE IF NOT EXISTS daily_rewards (
            user_id INTEGER, date TEXT, UNIQUE(user_id, date))""")
        c.execute("""CREATE TABLE IF NOT EXISTS marriage_settings (
            chat_id INTEGER PRIMARY KEY,
            prolong_price INTEGER DEFAULT 50,
            divorce_mode TEXT DEFAULT 'выключить'
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            added_by INTEGER DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, name)
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_holidays_date ON holidays(date)")
        c.execute("""CREATE TABLE IF NOT EXISTS moderator_titles (
            chat_id INTEGER, rank INTEGER,
            title_nom TEXT, title_gen TEXT, title_dat TEXT,
            title_ins TEXT, title_plu TEXT,
            PRIMARY KEY (chat_id, rank)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS chat_moderators_header (
            chat_id INTEGER PRIMARY KEY, header TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS greeting_autodelete (
            chat_id INTEGER PRIMARY KEY,
            seconds INTEGER DEFAULT 0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS short_about_settings (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS premium_emojis (
            emoji_id TEXT PRIMARY KEY, fallback TEXT,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS ai_chats (
            chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 1
        )""")
        conn.commit()# ================= ХЕЛПЕРЫ ПРАВ =================
def _admin_rights_kwargs(**overrides):
    base = {
        "is_anonymous": False,
        "can_manage_chat": False,
        "can_delete_messages": False,
        "can_manage_video_chats": False,
        "can_restrict_members": False,
        "can_promote_members": False,
        "can_change_info": False,
        "can_invite_users": False,
        "can_pin_messages": False,
        "can_manage_topics": False,
        "can_post_messages": False,
        "can_edit_messages": False,
        "can_post_stories": False,
        "can_edit_stories": False,
        "can_delete_stories": False,
    }
    base.update(overrides)
    try:
        valid = set(types.ChatAdministratorRights.model_fields.keys())
    except Exception:
        valid = set(base.keys())
    return {k: v for k, v in base.items() if k in valid}


def full_admin_rights() -> types.ChatAdministratorRights:
    return types.ChatAdministratorRights(**_admin_rights_kwargs(
        can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
        can_restrict_members=True, can_change_info=True, can_invite_users=True,
        can_pin_messages=True, can_manage_topics=True,
    ))


def empty_admin_rights() -> types.ChatAdministratorRights:
    return types.ChatAdministratorRights(**_admin_rights_kwargs())


# ================= ХЕЛПЕРЫ ВРЕМЕНИ =================
def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _parse_dt(s: str) -> datetime:
    if not s: return datetime.now()
    s = s.replace("T", " ")[:19]
    try: return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except: return datetime.now()


def _fmt_added_dt(s: str) -> str:
    if not s: return "?"
    try:
        dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
            return dt.strftime("%d.%m.%Y")
        except:
            return s[:19]


def format_last_seen(last_seen_str):
    if not last_seen_str:
        return "нет данных"
    try:
        if isinstance(last_seen_str, str):
            ls = datetime.strptime(last_seen_str[:19], "%Y-%m-%d %H:%M:%S")
        else:
            ls = last_seen_str
    except Exception:
        return "нет данных"
    delta = (datetime.now() - ls).total_seconds()
    if delta < 0: delta = 0
    if delta < 60:
        return "только что"
    if delta < 3600:
        return f"{int(delta // 60)} мин назад"
    if delta < 86400:
        return f"{int(delta // 3600)} ч назад"
    if delta < 86400 * 7:
        return f"{int(delta // 86400)} дн назад"
    return ls.strftime("%d.%m.%Y")


def format_citizenship_short(became_at_str):
    if not became_at_str:
        return "недавно"
    try:
        became_at = datetime.strptime(became_at_str[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            became_at = datetime.strptime(became_at_str[:10], "%Y-%m-%d")
        except Exception:
            return "недавно"
    delta = (datetime.now() - became_at).total_seconds()
    if delta < 0: delta = 0

    def _plural(n, one, few, many):
        n10, n100 = n % 10, n % 100
        if n10 == 1 and n100 != 11: return one
        if 2 <= n10 <= 4 and not (12 <= n100 <= 14): return few
        return many

    if delta < 60:
        n = int(delta)
        return f"{n} {_plural(n, 'секунда', 'секунды', 'секунд')}"
    if delta < 3600:
        n = int(delta // 60)
        return f"{n} {_plural(n, 'минута', 'минуты', 'минут')}"
    if delta < 86400:
        n = int(delta // 3600)
        return f"{n} {_plural(n, 'час', 'часа', 'часов')}"
    if delta < 86400 * 30:
        n = int(delta // 86400)
        return f"{n} {_plural(n, 'день', 'дня', 'дней')}"
    if delta < 86400 * 365:
        n = int(delta // (86400 * 30))
        return f"{n} {_plural(n, 'месяц', 'месяца', 'месяцев')}"
    n = int(delta // (86400 * 365))
    return f"{n} {_plural(n, 'год', 'года', 'лет')}"


# ================= ЕДИНЫЙ СТИЛЬ ОТВЕТОВ =================
def mod_action_text(action_emoji: str, action_title: str, target_mention: str,
                    moderator_mention: str, duration: str = None,
                    reason: str = None, extra: str = None) -> str:
    lines = [f"{action_emoji} <b>{action_title}</b>", ""]
    lines.append(f"👤 Пользователь: {target_mention}")
    if duration:
        lines.append(f"⏱ Срок: <b>{duration}</b>")
    if reason and reason.strip().lower() not in ["без причины", "без причины."]:
        lines.append(f"📝 Причина: <i>{reason}</i>")
    lines.append(f"👮 Модератор: {moderator_mention}")
    if extra:
        lines.append("")
        lines.append(extra)
    return "\n".join(lines)


def mod_error_text(title: str, details: str = None) -> str:
    text = f"❌ <b>{title}</b>"
    if details:
        text += f"\n\n{details}"
    return text


# ================= СОВЛАДЕЛЬЦЫ =================
def is_coowner(user_id: int) -> bool:
    if user_id == OWNER_ID: return True
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM coowners WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None


def add_coowner(user_id: int, added_by: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO coowners (user_id, added_by) VALUES (?, ?)", (user_id, added_by))
        conn.commit()


def remove_coowner(user_id: int) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM coowners WHERE user_id = ?", (user_id,))
        conn.commit()
        return c.rowcount > 0


def get_coowners():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, added_at FROM coowners ORDER BY added_at ASC")
        return c.fetchall()


# ================= РАНГИ =================
def get_rank(chat_id, user_id):
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
        c.execute("""SELECT user_id, rank FROM admins WHERE chat_id = ? AND rank > 0 ORDER BY rank DESC""", (chat_id,))
        return c.fetchall()


def has_permission(chat_id, user_id, required_rank):
    if user_id == OWNER_ID or is_coowner(user_id):
        return True
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
    if user_id == OWNER_ID or is_coowner(user_id):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status == "creator":
            return True
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
        await message.reply(f"{em('cross', '❌')} Недостаточно прав.\n🔒 Нужен: <b>{rank_display(chat_id, access)}</b>", parse_mode="HTML")
    return False


# ================= АГЕНТЫ =================
def is_agent(user_id):
    if user_id == OWNER_ID or is_coowner(user_id): return False
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM agents WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None


def get_agent_rank(user_id):
    if user_id == OWNER_ID or is_coowner(user_id): return 0
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
    if user_id == OWNER_ID or is_coowner(user_id): return True
    return get_agent_rank(user_id) >= min_rank


def get_hidden_agents():
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM hidden_agents")
        return [r[0] for r in c.fetchall()]


# ================= АНТИСПАМ =================
def get_all_known_chats() -> list:
    chats = set()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id FROM chat_codes")
        for (cid,) in c.fetchall():
            if cid and cid < 0: chats.add(cid)
        c.execute("SELECT chat_id FROM grid_chats")
        for (cid,) in c.fetchall():
            if cid and cid < 0: chats.add(cid)
        c.execute("SELECT DISTINCT chat_id FROM messages_stats WHERE chat_id < 0")
        for (cid,) in c.fetchall():
            if cid and cid < 0: chats.add(cid)
    return list(chats)


def is_bot_ignored(user_id: int) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM bot_ignore WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None


def add_bot_ignore(user_id: int, added_by: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO bot_ignore (user_id, added_by) VALUES (?, ?)", (user_id, added_by))
        conn.commit()


def remove_bot_ignore(user_id: int) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM bot_ignore WHERE user_id = ?", (user_id,))
        conn.commit()
        return c.rowcount > 0


def are_achievements_hidden(user_id: int) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM hidden_achievements WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None


def hide_achievements(user_id: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO hidden_achievements (user_id) VALUES (?)", (user_id,))
        conn.commit()


def show_achievements(user_id: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM hidden_achievements WHERE user_id = ?", (user_id,))
        conn.commit()


def is_in_antispam(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM antispam WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None


def log_antispam_action(user_id, action, reason, admin_id, removed_by=None):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO antispam_history (user_id, action, reason, admin_id) VALUES (?, ?, ?, ?)",
            (user_id, action, reason, removed_by if removed_by is not None else admin_id)
        )
        conn.commit()


def add_user_to_antispam(user_id: int, reason: str, added_by: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO antispam (user_id, reason, added_by, added_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                  (user_id, reason, added_by))
        conn.commit()
    log_antispam_action(user_id, "add", reason, added_by)


def remove_user_from_antispam(user_id: int, removed_by: int = 0) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT reason, added_by, added_at FROM antispam WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        c.execute("DELETE FROM antispam WHERE user_id = ?", (user_id,))
        conn.commit()
    if row:
        reason, added_by, added_at = row
        log_antispam_action(user_id, "remove", reason or "", removed_by, removed_by=removed_by)
        return True
    return False


def get_antispam_info(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT reason, added_by, added_at FROM antispam WHERE user_id = ?", (user_id,))
        return c.fetchone()


def get_antispam_history(user_id, limit=10):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT action, reason, admin_id, created_at 
                     FROM antispam_history WHERE user_id = ? 
                     ORDER BY created_at DESC LIMIT ?""", (user_id, limit))
        return c.fetchall()


def is_ignored(chat_id, user_id):
    if is_bot_ignored(user_id): return True
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM ignore_list WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        if c.fetchone(): return True
    return False


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


# ================= ДОП. ХЕЛПЕРЫ =================
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


async def is_tg_admin(chat_id, user_id):
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        return m.status in ['creator', 'administrator']
    except: return False


class _FakeUser:
    def __init__(self, user_id, first_name, username=None):
        self.id = user_id
        self.first_name = first_name
        self.username = username
        self.is_bot = False


async def resolve_target(message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user, None
    if not message.text: return None, None
    args = message.text.split()
    for a in args[1:]:
        raw = a.strip().rstrip('.,;:!?')
        if not raw: continue
        if raw.startswith('@'):
            username = raw[1:]
            try:
                return await bot.get_chat(f"@{username}"), raw
            except Exception as e:
                pass
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT user_id, first_name, username FROM users WHERE LOWER(username) = LOWER(?)", (username,))
                r = c.fetchone()
                if r:
                    try: return await bot.get_chat(r[0]), raw
                    except:
                        return _FakeUser(r[0], r[1], r[2]), raw
            continue
        if raw.lstrip('-').isdigit():
            user_id = int(raw)
            if 0 < user_id < 100000:
                continue
            try:
                return await bot.get_chat(user_id), raw
            except Exception as e:
                pass
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT first_name, username FROM users WHERE user_id = ?", (user_id,))
                r = c.fetchone()
            if r:
                return _FakeUser(user_id, r[0] or str(user_id), r[1]), raw
            return _FakeUser(user_id, f"ID {user_id}"), raw
        if 3 <= len(raw) <= 32 and re.match(r'^[a-zA-Z][a-zA-Z0-9_]+$', raw):
            try:
                return await bot.get_chat(f"@{raw}"), raw
            except Exception as e:
                pass
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT user_id, first_name FROM users WHERE LOWER(username) = LOWER(?)", (raw,))
                r = c.fetchone()
                if r:
                    try: return await bot.get_chat(r[0]), raw
                    except: return _FakeUser(r[0], r[1], raw), raw
            continue
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
    except: pass# ================= ФИЛЬТР ССЫЛОК =================
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
    return False


# ================= АВТОМОДЕРАЦИЯ =================
BAD_WORDS = [
    "блять", "блядь", "блят", "бля", "сука", "сучка", "сучонок",
    "хуй", "хуя", "хую", "хуе", "хуё", "хуи", "хуйн", "хуйня", "хуёв",
    "пизда", "пизду", "пизде", "пизды", "пиздец", "пизд",
    "ебать", "ебал", "еба", "ебёт", "ебет", "ебан", "ебану", "ебуч",
    "ёбаный", "ебаный", "ёбн", "ёб", "ёпт",
    "мудак", "мудила", "мудозвон", "гандон", "гондон",
    "долбоеб", "долбоёб", "долбаеб", "долбаёб",
    "уебан", "уёбан", "уёбище", "уебище",
    "залупа", "залупу", "залупе",
    "манда", "манду", "манде", "мандавошка",
    "нах", "нахуй", "нахуя", "похуй", "похую", "похуист",
    "охуе", "ахуе", "охуи",
    "пидор", "пидар", "пидр", "пидарас", "пидорас",
    "шлюха", "шлюх", "шалава",
    "хер", "херн", "херов", "херня",
    "жопа", "жоп", "жопу", "срать", "сру", "срака", "срак",
    "пердеть", "перд", "пердёж", "член",
    "яйца", "яиц", "яйцо", "сперм", "сперма", "минет", "миньет",
    "трахать", "трахал", "трах", "еби", "ёби",
    "сук", "падла", "падлю",
    "казел", "козел", "козёл", "быдло", "быдл",
    "гнида", "гнид", "тварь", "твар",
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


# ================= БАНЫ / МУТЫ =================
def get_all_user_bans(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT chat_id, reason, banned_by, banned_at, until_date, was_antispam 
            FROM chat_bans WHERE user_id = ? ORDER BY banned_at DESC LIMIT 20""", (user_id,))
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
    add_user_to_antispam(user_id, "автоматическая блокировка спамера", 0)
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


# ================= НАСТРОЙКИ ВАРНОВ =================
def get_warn_settings(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT warn_limit, action, duration_text, duration_seconds FROM warn_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if not r:
            c.execute("INSERT INTO warn_settings (chat_id) VALUES (?)", (chat_id,))
            conn.commit()
            return (3, 'mute', '1 час', 3600)
        return r


def set_warn_setting(chat_id, field, value):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO warn_settings (chat_id) VALUES (?)", (chat_id,))
        c.execute(f"UPDATE warn_settings SET {field} = ? WHERE chat_id = ?", (value, chat_id))
        conn.commit()


def parse_warn_duration(text: str):
    text = text.lower().strip().rstrip('.')
    if text in ["навсегда", "вечно", "forever", "перм", "∞"]:
        return (None, "навсегда")
    m = re.match(
        r'^(\d+)\s*(сек|секунд|секунды|секунда|с|мин|минут|минуты|минута|м|'
        r'час|часа|часов|ч|день|дня|дней|д|нед|неделя|недели|недель|'
        r'месяц|месяца|месяцев|мес|год|года|лет)$',
        text
    )
    if not m:
        return (False, None)
    amount = int(m.group(1))
    unit = m.group(2)
    if unit in ['сек', 'секунд', 'секунды', 'секунда', 'с']:
        return (amount, f"{amount} сек.")
    elif unit in ['мин', 'минут', 'минуты', 'минута', 'м']:
        return (amount * 60, f"{amount} мин.")
    elif unit in ['час', 'часа', 'часов', 'ч']:
        return (amount * 3600, f"{amount} ч.")
    elif unit in ['день', 'дня', 'дней', 'д']:
        return (amount * 86400, f"{amount} дн.")
    elif unit in ['нед', 'неделя', 'недели', 'недель']:
        return (amount * 604800, f"{amount} нед.")
    elif unit in ['месяц', 'месяца', 'месяцев', 'мес']:
        return (amount * 30 * 86400, f"{amount} мес.")
    elif unit in ['год', 'года', 'лет']:
        return (amount * 365 * 86400, f"{amount} г.")
    return (False, None)


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


# ================= ТОП / АКТИВНОСТЬ =================
def get_top_users(chat_id, period="today", limit=10):
    now = datetime.now()
    if period in ("today", "24h", "day", "день"):
        cutoff_date = (now - timedelta(hours=24)).date().isoformat()
        query = """SELECT user_id, SUM(count) as cnt FROM messages_stats
                   WHERE chat_id = ? AND date >= ?
                   GROUP BY user_id ORDER BY cnt DESC LIMIT ?"""
        params = (chat_id, cutoff_date, limit)
    elif period in ("week", "7d", "неделя"):
        cutoff_date = (now - timedelta(days=7)).date().isoformat()
        query = """SELECT user_id, SUM(count) as cnt FROM messages_stats
                   WHERE chat_id = ? AND date >= ?
                   GROUP BY user_id ORDER BY cnt DESC LIMIT ?"""
        params = (chat_id, cutoff_date, limit)
    elif period in ("month", "30d", "месяц"):
        cutoff_date = (now - timedelta(days=30)).date().isoformat()
        query = """SELECT user_id, SUM(count) as cnt FROM messages_stats
                   WHERE chat_id = ? AND date >= ?
                   GROUP BY user_id ORDER BY cnt DESC LIMIT ?"""
        params = (chat_id, cutoff_date, limit)
    else:
        query = """SELECT user_id, SUM(count) as total FROM messages_stats
                   WHERE chat_id = ?
                   GROUP BY user_id ORDER BY total DESC LIMIT ?"""
        params = (chat_id, limit)

    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
    return [(r[0], r[1] or 0) for r in rows]


def get_inactive_users(chat_id, days=7, limit=30):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT user_id, MAX(COALESCE(last_message_at, date || ' 12:00:00')) as last_seen
            FROM messages_stats
            WHERE chat_id = ?
            GROUP BY user_id
            HAVING last_seen < ?
            ORDER BY last_seen ASC
            LIMIT ?
        """, (chat_id, cutoff, limit))
        return c.fetchall()


def get_last_seen_in_chat(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT MAX(COALESCE(last_message_at, date || ' 12:00:00'))
            FROM messages_stats
            WHERE user_id = ? AND chat_id = ?
        """, (user_id, chat_id))
        r = c.fetchone()
        return r[0] if r and r[0] else None


def get_activity_extended(user_id, chat_id):
    now = datetime.now()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT SUM(count) FROM messages_stats
            WHERE user_id = ? AND chat_id = ? AND date >= ?""",
            (user_id, chat_id, (now - timedelta(hours=24)).date().isoformat()))
        day = c.fetchone()[0] or 0
        c.execute("""SELECT SUM(count) FROM messages_stats
            WHERE user_id = ? AND chat_id = ? AND date >= ?""",
            (user_id, chat_id, (now - timedelta(days=7)).date().isoformat()))
        week = c.fetchone()[0] or 0
        c.execute("""SELECT SUM(count) FROM messages_stats
            WHERE user_id = ? AND chat_id = ? AND date >= ?""",
            (user_id, chat_id, (now - timedelta(days=30)).date().isoformat()))
        month = c.fetchone()[0] or 0
        c.execute("""SELECT SUM(count) FROM messages_stats
            WHERE user_id = ? AND chat_id = ?""", (user_id, chat_id))
        total = c.fetchone()[0] or 0
    return day, week, month, total


def get_activity_extended_global(user_id):
    now = datetime.now()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT SUM(count) FROM messages_stats
            WHERE user_id = ? AND date >= ?""",
            (user_id, (now - timedelta(hours=24)).date().isoformat()))
        day = c.fetchone()[0] or 0
        c.execute("""SELECT SUM(count) FROM messages_stats
            WHERE user_id = ? AND date >= ?""",
            (user_id, (now - timedelta(days=7)).date().isoformat()))
        week = c.fetchone()[0] or 0
        c.execute("""SELECT SUM(count) FROM messages_stats
            WHERE user_id = ? AND date >= ?""",
            (user_id, (now - timedelta(days=30)).date().isoformat()))
        month = c.fetchone()[0] or 0
        c.execute("""SELECT SUM(count) FROM messages_stats
            WHERE user_id = ?""", (user_id,))
        total = c.fetchone()[0] or 0
    return day, week, month, total# ================= ИРИСКИ =================
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


# ================= ЗАПРЕТ ПЕРЕВОДОВ =================
def add_transfer_block(blocker_id: int, blocked_id: int, added_by: int) -> bool:
    if blocker_id == blocked_id: return False
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT OR IGNORE INTO transfer_blocks (blocker_id, blocked_id, added_by) VALUES (?, ?, ?)",
                      (blocker_id, blocked_id, added_by))
            conn.commit()
            return c.rowcount > 0
        except: return False


def remove_transfer_block(blocker_id: int, blocked_id: int) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM transfer_blocks WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
        conn.commit()
        return c.rowcount > 0


def is_transfer_blocked(blocker_id: int, blocked_id: int) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM transfer_blocks WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
        return c.fetchone() is not None


def get_transfer_blocks(blocker_id: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT blocked_id, added_at FROM transfer_blocks WHERE blocker_id = ? ORDER BY added_at DESC", (blocker_id,))
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


# ================= АГЕНТЫ СТАТУС =================
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
            c.execute("INSERT INTO users (user_id, first_name, username, first_seen) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                      (user_id, first_name, username))
            conn.commit()
        else:
            c.execute("UPDATE users SET first_name = ?, username = ? WHERE user_id = ?",
                      (first_name, username, user_id))
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


# ================= CHAT BANS / MUTES =================
def add_chat_ban(chat_id, user_id, reason, banned_by, until_date=None, was_antispam=0):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO chat_bans (chat_id, user_id, reason, banned_by, until_date, was_antispam) VALUES (?, ?, ?, ?, ?, ?)",
                  (chat_id, user_id, reason, banned_by, until_date, was_antispam))
        conn.commit()


def add_chat_mute(chat_id, user_id, reason, muted_by, until_date):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO chat_mutes (chat_id, user_id, reason, muted_by, until_date) VALUES (?, ?, ?, ?, ?)",
                  (chat_id, user_id, reason, muted_by, until_date))
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
        c.execute("SELECT chat_id, user_id, reason, banned_by FROM chat_bans WHERE until_date IS NOT NULL AND until_date <= ?", (now,))
        return c.fetchall()


def get_expired_mutes():
    now = datetime.now().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, user_id, reason FROM chat_mutes WHERE until_date IS NOT NULL AND until_date <= ?", (now,))
        return c.fetchall()


def clear_chat_mute(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM chat_mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        conn.commit()


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
    chat_title = html_escape_text(chat.title or "чат")
    first_name = html_escape_text(user.first_name or "Пользователь")

    username = getattr(user, "username", None)
    user_id = getattr(user, "id", 0)
    if username:
        nick_link = f'<a href="https://t.me/{username}">{first_name}</a>'
    else:
        nick_link = f'<a href="tg://user?id={user_id}">{first_name}</a>'

    has_nick_placeholder = "{ник}" in text
    no_nick = "{без_ника}" in text

    first_line = text.split("\n", 1)[0]
    first_line_has_nick = ("{ник}" in first_line or "{имя}" in first_line
                           or "{юзер}" in first_line or "{name}" in first_line)

    result = text
    result = result.replace("{без_ника}", "")
    result = result.replace("{ник}", nick_link)
    result = result.replace("{имя}", first_name)
    result = result.replace("{юзер}", f"@{username}" if username else first_name)
    result = result.replace("{чат}", chat_title)
    result = result.replace("{айди}", str(user_id))
    result = result.replace("{name}", first_name).replace("{first_name}", first_name)
    result = result.replace("{chat}", chat_title)
    result = result.replace("{rules}", "правила")
    result = result.replace("{link}", SUPPORT_CHAT_LINK)

    if has_nick_placeholder or no_nick or first_line_has_nick:
        return result

    return f"{nick_link}\n\n{result}"


# ================= АВТОУДАЛЕНИЕ ПРИВЕТСТВИЙ =================
def get_greeting_autodelete(chat_id) -> int:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT seconds FROM greeting_autodelete WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        return int(r[0]) if r and r[0] else 0


def set_greeting_autodelete(chat_id, seconds: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO greeting_autodelete (chat_id, seconds) VALUES (?, ?)",
                  (chat_id, int(seconds)))
        conn.commit()


def parse_autodelete_duration(text: str):
    text = text.lower().strip().rstrip('.')
    if text in ["выкл", "выключить", "off", "0"]:
        return (0, "выключено")
    m = re.match(
        r'^(\d+)\s*'
        r'(с|сек|секунд|секунды|секунда|'
        r'м|мин|минут|минуты|минута|'
        r'ч|час|часа|часов|'
        r'д|день|дня|дней)$',
        text
    )
    if not m:
        return (False, None)
    amount = int(m.group(1)); unit = m.group(2)
    if unit in ['с', 'сек', 'секунд', 'секунды', 'секунда']:
        seconds, human = amount, f"{amount} сек."
    elif unit in ['м', 'мин', 'минут', 'минуты', 'минута']:
        seconds, human = amount * 60, f"{amount} мин."
    elif unit in ['ч', 'час', 'часа', 'часов']:
        seconds, human = amount * 3600, f"{amount} ч."
    elif unit in ['д', 'день', 'дня', 'дней']:
        seconds, human = amount * 86400, f"{amount} дн."
    else:
        return (False, None)
    if seconds < 5 or seconds > 86400:
        return (False, None)
    return (seconds, human)


def _humanize_seconds(seconds: int) -> str:
    if seconds < 60: return f"{seconds} сек."
    if seconds < 3600: return f"{seconds // 60} мин."
    if seconds < 86400:
        h = seconds // 3600; m = (seconds % 3600) // 60
        return f"{h} ч. {m} мин." if m else f"{h} ч."
    return f"{seconds // 86400} дн."


def _schedule_greeting_delete(chat_id: int, message: types.Message):
    seconds = get_greeting_autodelete(chat_id)
    if seconds > 0:
        asyncio.create_task(delete_later(message, seconds))


# ================= КОРОТКО ПРО =================
def is_short_about_enabled(chat_id) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT enabled FROM short_about_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        return bool(r[0]) if r else False


def set_short_about_enabled(chat_id, enabled: bool):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO short_about_settings (chat_id, enabled) VALUES (?, ?)",
                  (chat_id, 1 if enabled else 0))
        conn.commit()


def get_universe_start(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT first_seen FROM users WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        if r and r[0]:
            return r[0]
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)",
                  (user_id, "", ""))
        c.execute("SELECT first_seen FROM users WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return r[0] if r and r[0] else None


def build_short_about_text(target, chat_id: int) -> str:
    user_id = target.id
    start = get_universe_start(user_id)
    if start:
        try:
            d = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                d = datetime.strptime(start[:10], "%Y-%m-%d")
            except Exception:
                d = None
        if d:
            delta = (datetime.now() - d).total_seconds()
            if delta < 60:
                universe_line = "🕰 Во вселенной <b>Mos</b>: появился только что"
            else:
                date_str = d.strftime("%d.%m.%Y")
                duration = format_citizenship_duration(start)
                universe_line = f"🕰 Во вселенной <b>Mos</b>: с <b>{date_str}</b> ({duration})"
        else:
            universe_line = "🕰 Во вселенной <b>Mos</b>: появился только что"
    else:
        universe_line = "🕰 Во вселенной <b>Mos</b>: появился только что"

    lines = [universe_line]
    day_g, week_g, month_g, total_g = get_activity_extended_global(user_id)
    lines.append(
        f"🗣 Активность: <b>{day_g}</b> | <b>{week_g}</b> | <b>{month_g}</b> | <b>{total_g}</b> "
        f"<i>(день|нед|мес|всего)</i>"
    )

    profile = get_user_profile(user_id)
    is_hidden = profile[4] if profile and len(profile) > 4 else 1
    gender = profile[0] if profile and len(profile) > 0 else None
    if not is_hidden and gender:
        lines.append(f"ℹ️ Пол: <b>{html_escape_text(str(gender).lower())}</b>")

    header = f"📇 <b>Коротко про</b> {mention(target)}"
    return header + "\n\n" + "\n".join(lines)


async def _send_short_about_if_enabled(chat_id: int, user, delay: float = 0.7):
    if not is_short_about_enabled(chat_id):
        return
    try:
        if delay > 0:
            await asyncio.sleep(delay)
        text = build_short_about_text(user, chat_id)
        await bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"⚠️ short_about: {e}")


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
            (user_id, chat_id, message_id, captcha_type, answer, created_at) 
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (user_id, chat_id, message_id, captcha_type, answer))
        conn.commit()


def get_captcha(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT message_id, captcha_type, answer FROM captcha WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        return c.fetchone()


def get_captcha_created_at(user_id, chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT created_at FROM captcha WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        r = c.fetchone()
    if not r or not r[0]:
        return None
    try:
        return datetime.strptime(r[0][:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


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
            c.execute("INSERT INTO captcha_settings (chat_id, enabled) VALUES (?, 0)", (chat_id,))
            conn.commit()
            return False
        return bool(r[0])


def set_captcha_enabled(chat_id, enabled):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO captcha_settings (chat_id, enabled) VALUES (?, ?)", (chat_id, 1 if enabled else 0))
        conn.commit()


def get_captcha_timeout(chat_id) -> int:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT timeout FROM captcha_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if r is None or r[0] is None:
            c.execute("INSERT OR IGNORE INTO captcha_settings (chat_id, enabled, timeout) VALUES (?, 0, 120)", (chat_id,))
            conn.commit()
            return 120
        return int(r[0])


def set_captcha_timeout(chat_id, seconds: int):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO captcha_settings (chat_id, enabled, timeout) VALUES (?, 0, 120)", (chat_id,))
        c.execute("UPDATE captcha_settings SET timeout = ? WHERE chat_id = ?", (seconds, chat_id))
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
        conn.commit()


# ================= РЫБАЛКА — ПОДПИСКА =================
async def is_subscribed_to_fishing_channel(user_id: int) -> bool:
    if not FISHING_REQUIRE_SUBSCRIPTION:
        return True
    if user_id == OWNER_ID or is_coowner(user_id) or has_agent_rank(user_id, 1):
        return True
    if not FISHING_CHANNEL_ID:
        return True
    try:
        member = await bot.get_chat_member(FISHING_CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator", "restricted")
    except Exception as e:
        print(f"⚠️ is_subscribed_to_fishing_channel: {e}")
        return False# ================= РЫБАЛКА — ДАННЫЕ =================
LOCATIONS = {
    "pier": {"name": "🌊 Пирс", "emoji": "🌊", "desc": "Спокойное место для новичков", "min_level": 1, "vip_required": False, "rare_chance": 0, "legendary_chance": 0, "treasure_chance": 0},
    "rocks": {"name": "🪨 Камни", "emoji": "🪨", "desc": "Больше редкой рыбы, чем на пирсе", "min_level": 5, "vip_required": False, "rare_chance": 10, "legendary_chance": 2, "treasure_chance": 0},
    "sunset_cape": {"name": "🌅 Закатный мыс", "emoji": "🌅", "desc": "Здесь ловится мифическая рыба", "min_level": 15, "vip_required": False, "rare_chance": 20, "legendary_chance": 5, "treasure_chance": 5},
    "abyss": {"name": "🌌 Бездна", "emoji": "🌌", "desc": "Только для опытных. Опасно, но выгодно", "min_level": 20, "vip_required": False, "rare_chance": 35, "legendary_chance": 12, "treasure_chance": 10},
    "treasure_island": {"name": "🏝 Остров сокровищ", "emoji": "🏝", "desc": "Здесь ловятся сокровища и редчайшая рыба", "min_level": 30, "vip_required": True, "rare_chance": 50, "legendary_chance": 20, "treasure_chance": 25},
}

FISH_LIST = [
    ("Окунь","🐟",1,3,100,"river","any"),("Ёрш","🐡",2,4,80,"river","any"),("Пескарь","🐟",1,3,75,"river","any"),
    ("Плотва","🐟",2,5,70,"river","day"),("Краснопёрка","🐠",3,6,65,"river","day"),("Густера","🐟",3,7,60,"river","any"),
    ("Язь","🐟",5,10,45,"river","day"),("Лещ","🐠",4,9,50,"river","day"),("Линь","🐠",6,12,40,"river","any"),
    ("Голавль","🐟",6,11,42,"river","day"),("Жерех","🐡",8,14,32,"river","day"),("Щука","🐡",8,18,30,"river","any"),
    ("Судак","🐡",10,22,24,"river","night"),("Налим","🐡",12,24,18,"river","night"),("Сом","🦈",15,30,12,"river","night"),
    ("Форель","🐟",12,24,20,"river","day"),("Хариус","🐠",10,20,16,"river","day"),("Таймень","🐡",30,60,4,"river","any"),
    ("Ручьевая форель","🐟",14,28,14,"river","day"),("Карась","🐠",2,5,95,"lake","any"),("Карп","🐠",10,24,22,"lake","day"),
    ("Сазан","🐟",12,26,18,"lake","day"),("Толстолобик","🐡",14,28,15,"lake","day"),("Белый амур","🐟",16,32,12,"lake","day"),
    ("Линь-гигант","🐠",25,50,3,"lake","any"),("Угорь","🐍",18,34,10,"lake","night"),("Золотой карась","✨",40,80,2,"lake","any"),
    ("Сельдь","🐟",10,20,28,"sea","any"),("Скумбрия","🐠",15,28,22,"sea","day"),("Ставрида","🐟",12,22,24,"sea","any"),
    ("Камбала","🐠",16,30,18,"sea","night"),("Бычок","🐡",8,16,30,"sea","any"),("Пикша","🐟",18,34,16,"sea","any"),
    ("Треска","🐟",20,38,14,"sea","any"),("Морской окунь","🐠",22,40,12,"sea","day"),("Сайда","🐟",18,32,15,"sea","day"),
    ("Зубатка","🐡",25,45,8,"sea","night"),("Морской чёрт","🐡",45,90,2,"sea","night"),("Барракуда","🐡",35,70,3,"sea","any"),
    ("Мурена-детёныш","🐍",25,50,4,"sea","night"),("Морской конёк","🐠",20,40,8,"sea","day"),("Рыба-попугай","🦜",30,60,3,"sea","day"),
    ("Кальмар","🦑",30,60,6,"sea","night"),("Осьминог","🐙",45,90,2,"sea","night"),("Тунец","🐟",40,80,5,"ocean","any"),
    ("Меч-рыба","🗡",55,110,3,"ocean","day"),("Рыба-меч","🗡",60,120,2,"ocean","any"),("Марлин","🐟",70,140,1.5,"ocean","day"),
    ("Парусник","🐟",80,160,1.2,"ocean","day"),("Мурена","🐍",50,100,3,"ocean","night"),("Ильная рыба","🐟",45,90,1.8,"ocean","night"),
    ("Гигантский тресковый","🐟",50,100,2,"ocean","any"),("Королевский лосось","🐠",55,110,1,"ocean","day"),("Кета","🐡",45,90,1.2,"ocean","any"),
    ("Кижуч","🐟",55,110,1,"ocean","day"),("Нерка","🐟",60,120,0.8,"ocean","any"),("Призрачный карп","👻",100,200,0.3,"any","night"),
    ("Лунная рыба","🌙",150,300,0.2,"any","night"),("Рыба-дракончик","🐉",200,400,0.1,"any","any"),("Золотая рыбка","✨",250,500,0.05,"any","any"),
    ("Радужный лосось","🌈",180,360,0.1,"any","any"),("Стеклянная рыба","🔮",220,440,0.08,"any","any"),
    ("Электрический угорь","⚡",180,340,0.4,"river","any"),("Скат-электро","⚡",250,480,0.2,"sea","night"),("Рыба-молния","⚡",320,620,0.1,"any","any"),
    ("Удильщик","🎣",150,290,0.5,"ocean","night"),("Рыба-фонарь","🔦",120,240,0.6,"ocean","night"),("Гигантский кальмар","🦑",280,540,0.15,"ocean","night"),
    ("Плащеносец","🦎",200,400,0.2,"ocean","night"),("Древний латимерия","🦴",450,900,0.05,"any","any"),("Акула-молот","🦈",400,800,0.08,"ocean","day"),
    ("Акула-тигр","🦈",380,760,0.1,"ocean","any"),("Китовая акула","🦈",700,1400,0.02,"ocean","any"),("Русалочья рыбка","🧜",300,600,0.1,"sea","day"),
    ("Рыба-пегас","🦄",350,700,0.08,"any","day"),("Единороговая рыба","🦄",420,840,0.05,"any","any"),("Кристальная рыба","💎",380,760,0.06,"any","day"),
    ("Рыба-клоун","🐠",25,50,20,"sea","day"),("Хирург-рыба","🐠",30,60,15,"sea","day"),("Мурена-радуга","🐍",55,110,5,"sea","night"),
    ("Крылатка","🦁",80,160,3,"sea","any"),("Рыба-шар","🟠",40,80,10,"sea","any"),("Щука-гигант","🐡",120,240,1.5,"lake","any"),
    ("Сом-людоед","🐡",150,300,1.0,"river","night"),("Пирания","🐟",90,180,2.5,"river","any"),("Барракуда-гигант","🐡",180,360,1.2,"sea","night"),
    ("Майская рыба","🌸",60,120,5,"any","day"),("Осенний лосось","🍂",100,200,3,"river","any"),("Зимний сиг","❄️",80,160,4,"lake","any"),
    ("Летний окунь","☀️",50,100,8,"any","day"),("Рыба-хамелеон","🦎",150,300,1.5,"any","any"),("Стеклянный карп","🔮",180,360,1.0,"lake","any"),
    ("Стальная щука","⚙️",220,440,0.5,"river","any"),
]

LEGENDARY_FISH = [
    ("Мурена-гигант","🐍",250,500,25),("Акула","🦈",400,800,20),("Рыба-луна","🌕",500,1000,15),
    ("Голубой марлин","🐟",700,1400,12),("Гигантский сом","🐟",600,1200,10),("Кит-детёныш","🐋",900,1800,8),
    ("Кракен","🦑",1500,3000,5),("Морской дракон","🐲",2000,4000,3),("Император-краб","🦀",2500,5000,2.5),
    ("Древний осьминог","🐙",3000,6000,2),("Хранитель глубин","🌊",4000,8000,1.5),("Левиафан","🐉",6000,12000,1),
    ("Рыба-феникс","🔥",8000,16000,0.5),("Космический кит","🌌",10000,20000,0.3),("Рыба-бог","⚡",15000,30000,0.15),
    ("Император морей","🔱",20000,40000,0.1),("Посейдон","🌊",30000,60000,0.05),("Аватар моря","🌊",50000,100000,0.03),
    ("Рыба-титан","🗿",70000,140000,0.02),("Рыба-хаос","🌀",100000,200000,0.01),("Дух океана","👻",150000,300000,0.005),
]

THINGS_LIST = [
    ("Ржавый ключ","🗝",60,1,"candies"),("Пустая бутылка","🍾",80,2,"candies"),("Старый ботинок","👟",70,3,"candies"),
    ("Консервная банка","🥫",75,2,"candies"),("Кусок водоросли","🌿",65,1,"candies"),("Морской мусор","🗑",45,0,"candies"),
    ("Пакет","🛍",55,1,"candies"),("Ржавая цепь","⛓",30,8,"candies"),("Пустая ракушка","🐚",40,2,"candies"),
    ("Ржавый крючок","🪝",30,5,"candies"),("Морская ракушка","🐚",55,4,"candies"),("Морская звезда","⭐",25,12,"candies"),
    ("Медуза","🎐",35,6,"candies"),("Морское стекло","🔷",15,50,"candies"),("Коралловый обломок","🪸",20,35,"candies"),
    ("Чешуйка русалки","🧜‍♀️",5,200,"candies"),("Потерянная монета","🪙",50,15,"candies"),("Мелкая монетка","💰",40,25,"candies"),
    ("Старинная монета","🪙",15,80,"candies"),("Золотой слиток","🥇",8,800,"candies"),("Старое письмо","📜",15,30,"candies"),
    ("Древняя карта","🗺",20,40,"candies"),("Старинный пергамент","📜",6,150,"candies"),("Карта сокровищ","🗺",0.3,3000,"candies"),
    ("Морской жемчуг","🦪",10,60,"candies"),("Светящийся жемчуг","🔮",8,100,"candies"),("Розовый жемчуг","🩷",5,250,"pearl"),
    ("Чёрный жемчуг","🖤",2,500,"pearl"),("Драгоценный камень","💠",6,120,"candies"),("Сапфир","🔷",3,350,"candies"),
    ("Изумруд","💚",3,350,"candies"),("Алмаз","💎",1,700,"candies"),("Старый череп","💀",12,25,"candies"),
    ("Ржавый нож","🔪",22,10,"candies"),("Сломанный компас","🧭",18,35,"candies"),("Полузатонувший сундук","🗃",5,200,"candies"),
    ("Сундук с сокровищами","🎁",2.5,500,"candies"),("Затонувший клад","🏴‍☠️",0.8,1500,"candies"),("Реликвия древних","🏺",0.5,2000,"candies"),
    ("Ржавый якорь","⚓",25,20,"candies"),("Рыбий жир","🧴",20,30,"candies"),("Бутылка рома","🥃",8,100,"candies"),
    ("Золотая маска","🎭",0.5,2500,"candies"),("Корона глубин","👑",0.3,3000,"candies"),("Кристалл силы","💠",0.4,2200,"candies"),
    ("Прикормка (+1 ч)","🍯",3,0,"gear_bait"),("Счастливая монета","🍀",1.5,0,"gear_lucky"),
    ("Крепкий крючок","🪝",2,0,"gear_hook"),("Обломок лодки","🛶",0.5,0,"gear_boat"),("Осколок поплавка","🔮",1,0,"gear_float"),
]

FISHING_GEAR = {
    "hook": {"name": "🪝 Крючок", "base_price": 500, "max_level": 5, "bonus_per_level": 0.05, "flat_per_level": 0, "desc": "+5% к улову за уровень"},
    "spinning": {"name": "🎣 Спиннинг", "base_price": 1500, "max_level": 5, "bonus_per_level": 0.10, "flat_per_level": 0, "desc": "+10% к улову за уровень"},
    "bucket": {"name": "🪣 Ведро", "base_price": 2000, "max_level": 5, "bonus_per_level": 0.0, "flat_per_level": 1, "desc": "+1 🍬 к награде за уровень"},
    "boat": {"name": "🚤 Лодка", "base_price": 5000, "max_level": 3, "bonus_per_level": 0.0, "flat_per_level": 0, "rare_per_level": 10, "desc": "+10% к шансу редкой рыбы за уровень"},
    "premium_rod": {"name": "🎣 Премиум-удочка", "base_price": 10000, "max_level": 3, "bonus_per_level": 0.10, "flat_per_level": 0, "legendary_per_level": 10, "desc": "+10% к улову и +10% к шансу легендарки за уровень"},
    "magic_float": {"name": "🔮 Магический поплавок", "base_price": 25000, "max_level": 5, "bonus_per_level": 0.0, "flat_per_level": 0, "legendary_per_level": 2, "desc": "+2% к шансу легендарки за уровень"},
}

FISHING_EVENTS = {
    "rain":{"name":"🌧 Дождь","bonus":1.2,"duration":30},"heavy_rain":{"name":"⛈ Сильный дождь","bonus":1.1,"duration":20,"rare_boost":1.2},
    "storm":{"name":"🌩 Гроза","bonus":0.8,"duration":15},"fog":{"name":"🌫 Туман","bonus":0.9,"duration":20},"snow":{"name":"❄️ Снег","bonus":1.15,"duration":40},
    "hail":{"name":"🌨 Град","bonus":0.7,"duration":10},"wind":{"name":"💨 Ветер","bonus":1.1,"duration":25},"calm":{"name":"☀️ Штиль","bonus":1.0,"duration":30},
    "sunrise":{"name":"🌅 Рассвет","bonus":1.25,"duration":25,"rare_boost":1.3},"sunset":{"name":"🌇 Закат","bonus":1.35,"duration":30,"rare_boost":1.4},
    "night":{"name":"🌙 Ночь","bonus":1.3,"duration":45,"rare_boost":2.0},"midnight":{"name":"🌑 Полночь","bonus":1.5,"duration":20,"rare_boost":2.5},
    "twilight":{"name":"🌆 Сумерки","bonus":1.2,"duration":20},"full_moon":{"name":"🌕 Полнолуние","bonus":1.4,"duration":40,"rare_boost":3.0},
    "new_moon":{"name":"🌑 Новолуние","bonus":1.35,"duration":40,"rare_boost":2.5},"eclipse":{"name":"🌒 Затмение","bonus":1.7,"duration":15,"rare_boost":2.5},
    "meteor":{"name":"☄️ Метеоритный дождь","bonus":1.6,"duration":20,"rare_boost":2.0},"aurora":{"name":"🌌 Северное сияние","bonus":1.8,"duration":30,"rare_boost":2.5},
    "school":{"name":"🐟 Стая","bonus":1.2,"duration":20},"migration":{"name":"🐟 Миграция","bonus":1.8,"duration":20,"rare_boost":1.5},
    "boil":{"name":"🫧 Кипение воды","bonus":1.5,"duration":15},"spawning":{"name":"🥚 Нерест","bonus":2.0,"duration":15,"rare_boost":1.5},
    "magic_hour":{"name":"✨ Магический час","bonus":2.5,"duration":10,"rare_boost":3.0},"portal":{"name":"🌀 Портал","bonus":3.0,"duration":5,"rare_boost":5.0},
    "sea_spirit":{"name":"🧜 Дух моря","bonus":2.2,"duration":15,"rare_boost":3.5},"magnetic":{"name":"🧲 Магнитная буря","bonus":1.3,"duration":25,"rare_boost":1.8},
    "blackout":{"name":"⚡ Энергетическая буря","bonus":1.4,"duration":15},
}

FISHING_ACHIEVEMENTS = {
    "first_fish":{"name":"🥇 Первый улов","check":lambda u: u["total_caught"]>=1},
    "ten_fish":{"name":"🎣 10 рыб","check":lambda u: u["total_caught"]>=10},
    "hundred_fish":{"name":"🎣 100 рыб","check":lambda u: u["total_caught"]>=100},
    "five_hundred":{"name":"🐟 500 рыб","check":lambda u: u["total_caught"]>=500},
    "thousand_fish":{"name":"🏆 1000 рыб","check":lambda u: u["total_caught"]>=1000},
    "level_5":{"name":"📈 Рыбак-новичок","check":lambda u: u["level"]>=5},
    "level_10":{"name":"📈 Рыбак-любитель","check":lambda u: u["level"]>=10},
    "level_25":{"name":"📈 Рыбак-знаток","check":lambda u: u["level"]>=25},
    "level_50":{"name":"🏆 Рыбак-профи","check":lambda u: u["level"]>=50},
    "level_100":{"name":"👑 Рыбак-легенда","check":lambda u: u["level"]>=100},
    "legendary":{"name":"💎 Легендарная рыба","check":lambda u: u["legendary_caught"]>=1},
    "legendary_10":{"name":"💎 10 легендарок","check":lambda u: u["legendary_caught"]>=10},
    "legendary_50":{"name":"💎 50 легендарок","check":lambda u: u["legendary_caught"]>=50},
}

BAIT_DURATION_HOURS = 1
FISH_COOLDOWN_BASE = 7200
FISH_COOLDOWN_MIN = 900
LEVEL_XP_BASE = 50
TOURNAMENT_DURATION_MIN = 60


# ================= РЫБАЛКА — ФУНКЦИИ =================
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


def get_user_fish_cooldown(user_id) -> int:
    inv = get_fishing_inventory(user_id)
    cooldown = FISH_COOLDOWN_BASE
    hook_level = inv.get("hook", 0)
    if isinstance(hook_level, int) and hook_level > 0: cooldown -= hook_level * 600
    spinning_level = inv.get("spinning", 0)
    if isinstance(spinning_level, int) and spinning_level > 0: cooldown -= spinning_level * 300
    premium_level = inv.get("premium_rod", 0)
    if isinstance(premium_level, int) and premium_level > 0: cooldown -= premium_level * 180
    float_level = inv.get("magic_float", 0)
    if isinstance(float_level, int) and float_level > 0: cooldown -= float_level * 180
    return max(FISH_COOLDOWN_MIN, cooldown)


def format_fishing_cooldown(last_fish_str, cooldown_seconds: int = None):
    if not last_fish_str: return 0
    try:
        last = datetime.strptime(last_fish_str[:19], "%Y-%m-%d %H:%M:%S")
    except: return 0
    if cooldown_seconds is None: cooldown_seconds = FISH_COOLDOWN_BASE
    delta = (datetime.now() - last).total_seconds()
    remaining = cooldown_seconds - delta
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
    gear = FISHING_GEAR.get(gear_key)
    if gear and "max_level" in gear:
        if gear_key not in inv:
            inv[gear_key] = 1
    else:
        inv[gear_key] = inv.get(gear_key, 0) + count
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO fishing (user_id) VALUES (?)", (user_id,))
        c.execute("UPDATE fishing SET inventory = ? WHERE user_id = ?", (json.dumps(inv), user_id))
        conn.commit()


def upgrade_fishing_gear(user_id, gear_key) -> tuple:
    gear = FISHING_GEAR.get(gear_key)
    if not gear: return False, "Снасть не найдена", 0
    inv = get_fishing_inventory(user_id)
    cur_level = inv.get(gear_key, 0)
    if cur_level <= 0: return False, "Сначала купи снасть", 0
    if cur_level >= gear["max_level"]: return False, f"Максимум — ур. {gear['max_level']}", cur_level
    upgrade_cost = int(gear["base_price"] * (cur_level + 1) * 0.6)
    if get_balance(user_id) < upgrade_cost:
        return False, f"Нужно <b>{upgrade_cost}</b> 🍬", cur_level
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (upgrade_cost, user_id))
        conn.commit()
    inv[gear_key] = cur_level + 1
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE fishing SET inventory = ? WHERE user_id = ?", (json.dumps(inv), user_id))
        conn.commit()
    return True, f"Улучшено до ур. {cur_level + 1} (-{upgrade_cost} 🍬)", cur_level + 1


def get_fishing_gear_bonus(user_id):
    inv = get_fishing_inventory(user_id)
    total_bonus = 0.0; flat = 0; boat_level = 0; legendary_bonus = 0; rare_bonus = 0; gear_info = []
    for key, level in inv.items():
        if not isinstance(level, int) or level <= 0: continue
        gear = FISHING_GEAR.get(key)
        if not gear: continue
        lvl_bonus = gear.get("bonus_per_level", 0) * level
        lvl_flat = gear.get("flat_per_level", 0) * level
        lvl_legendary = gear.get("legendary_per_level", 0) * level
        lvl_rare = gear.get("rare_per_level", 0) * level
        total_bonus += lvl_bonus; flat += lvl_flat; legendary_bonus += lvl_legendary; rare_bonus += lvl_rare
        if key == "boat": boat_level = level
        gear_info.append({"key": key, "name": gear["name"], "level": level, "max_level": gear["max_level"],
                          "bonus": lvl_bonus, "flat": lvl_flat, "legendary": lvl_legendary, "rare": lvl_rare})
    return total_bonus, flat, boat_level, legendary_bonus, rare_bonus, gear_info


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
            min_r, max_r, weight = fish[2], fish[3], fish[4]
            avg = (min_r + max_r) // 2
            base = max(1, avg // 10)
            if weight >= 50: return base
            elif weight >= 15: return base + 3
            elif weight >= 3: return base + 8
            elif weight >= 0.5: return base + 20
            else: return base + 50
    for fish in LEGENDARY_FISH:
        if fish[0] == fish_name:
            avg = (fish[2] + fish[3]) // 2
            return max(50, avg // 8)
    for thing in THINGS_LIST:
        if thing[0] == fish_name:
            return thing[3] if thing[3] > 0 else 0
    return 5


def get_active_tournament(chat_id):
    now = _fmt_dt(datetime.now())
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT started_by, started_at, expires_at, prize FROM fishing_tournaments WHERE chat_id = ? AND expires_at > ?", (chat_id, now))
        return c.fetchone()


def create_tournament(chat_id, user_id, prize=100, duration_min=60):
    expires = _fmt_dt(datetime.now() + timedelta(minutes=duration_min))
    started = _fmt_dt(datetime.now())
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM fishing_tournaments WHERE chat_id = ?", (chat_id,))
        c.execute("DELETE FROM fishing_tournament_members WHERE chat_id = ?", (chat_id,))
        c.execute("INSERT INTO fishing_tournaments (chat_id, started_by, started_at, expires_at, prize) VALUES (?, ?, ?, ?, ?)",
                  (chat_id, user_id, started, expires, prize))
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
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT started_by, started_at, expires_at, prize FROM fishing_tournaments WHERE chat_id = ?", (chat_id,))
        tour = c.fetchone()
        if not tour: return None
        c.execute("SELECT user_id, caught FROM fishing_tournament_members WHERE chat_id = ? ORDER BY caught DESC LIMIT 3", (chat_id,))
        members = c.fetchall()
        c.execute("SELECT COUNT(*) FROM fishing_tournament_members WHERE chat_id = ?", (chat_id,))
        participants = c.fetchone()[0] or 0
        c.execute("DELETE FROM fishing_tournaments WHERE chat_id = ?", (chat_id,))
        c.execute("DELETE FROM fishing_tournament_members WHERE chat_id = ?", (chat_id,))
        conn.commit()
    if not members: return None
    base = min(100, max(20, 20 + (participants - 1) * 10))
    prizes = [base, max(1, base // 2), max(1, base // 4)]
    winners = []
    for i, (uid, caught) in enumerate(members):
        add_candies(uid, prizes[i], 0)
        winners.append((uid, caught, prizes[i]))
    return winners


def get_chat_location(chat_id) -> str:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM global_settings WHERE key = ?", (f"location:{chat_id}",))
        r = c.fetchone()
        if r: return r[0]
        return "pier"


def set_chat_location(chat_id, loc: str):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)", (f"location:{chat_id}", loc))
        conn.commit()


def get_chat_region(chat_id) -> str:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM global_settings WHERE key = ?", (f"region:{chat_id}",))
        r = c.fetchone()
        if r: return r[0]
        reg = random.choice(["river", "lake", "sea", "ocean"])
        c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)", (f"region:{chat_id}", reg))
        conn.commit()
        return reg


def set_chat_region(chat_id, region: str):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)", (f"region:{chat_id}", region))
        conn.commit()# ================= СТАНДАРТНЫЕ РП =================
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


# ================= СЕТКА — БД =================
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
        if user_id == OWNER_ID or is_coowner(user_id): return True
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


def set_rank_in_grid_chats(grid_id: int, user_id: int, rank: int, added_by: int) -> int:
    ok = 0
    for chat_id, hidden, desc in get_grid_chats(grid_id, include_hidden=True):
        try:
            if rank <= 0: remove_rank(chat_id, user_id)
            else: set_rank(chat_id, user_id, rank, added_by)
            ok += 1
        except Exception as e:
            print(f"❌ set_rank_in_grid_chats {chat_id}: {e}")
    return ok


# ================= ЗАМЕТКИ — БД =================
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


# ================= БРАКИ — БД =================
def get_marriage(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, user1_id, user2_id, user1_name, user2_name, married_at, status, divorced_at, in_top, extra_days
            FROM marriages WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'""",
            (chat_id, user_id, user_id))
        return c.fetchone()


def get_marriage_by_users(chat_id, user1_id, user2_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, user1_id, user2_id, user1_name, user2_name, married_at, status, divorced_at, in_top, extra_days
            FROM marriages WHERE chat_id = ? AND ((user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)) AND status = 'active'""",
            (chat_id, user1_id, user2_id, user2_id, user1_id))
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


def reset_all_marriages(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM marriages WHERE chat_id = ?", (chat_id,))
        conn.commit()
        return c.rowcount


def get_top_marriages(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user1_id, user1_name, user2_id, user2_name, married_at, extra_days FROM marriages WHERE chat_id = ? AND status = 'active' AND in_top = 1 ORDER BY married_at ASC",
                  (chat_id,))
        return c.fetchall()


def set_marriage_top_status(chat_id, user_id, in_top):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriages SET in_top = ? WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'",
                  (1 if in_top else 0, chat_id, user_id, user_id))
        conn.commit()
        return c.rowcount > 0


def get_marriage_settings(chat_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT prolong_price, divorce_mode FROM marriage_settings WHERE chat_id = ?", (chat_id,))
        r = c.fetchone()
        if not r:
            c.execute("INSERT INTO marriage_settings (chat_id) VALUES (?)", (chat_id,))
            conn.commit()
            return (50, 'выключить')
        return r


def set_marriage_price(chat_id, price):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO marriage_settings (chat_id, prolong_price) VALUES (?, ?)", (chat_id, price))
        conn.commit()


def set_divorce_mode(chat_id, mode):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriage_settings SET divorce_mode = ? WHERE chat_id = ?", (mode, chat_id))
        conn.commit()


def add_marriage_days(chat_id, user_id, days):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE marriages SET extra_days = extra_days + ? WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'",
                  (days, chat_id, user_id, user_id))
        conn.commit()


def get_marriage_extra_days(chat_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT extra_days FROM marriages WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND status = 'active'",
                  (chat_id, user_id, user_id))
        r = c.fetchone()
        return r[0] if r else 0


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
    if not became_at_str: return "только что"
    try:
        became_at = datetime.strptime(became_at_str[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        try: became_at = datetime.strptime(became_at_str[:10], "%Y-%m-%d")
        except Exception: return "только что"
    delta = (datetime.now() - became_at).total_seconds()
    if delta < 0: delta = 0

    def _plural(n, one, few, many):
        n10, n100 = n % 10, n % 100
        if n10 == 1 and n100 != 11: return one
        if 2 <= n10 <= 4 and not (12 <= n100 <= 14): return few
        return many

    if delta < 60: return "только что"
    if delta < 3600:
        n = int(delta // 60)
        return f"{n} {_plural(n, 'минуту', 'минуты', 'минут')} назад"
    if delta < 86400:
        n = int(delta // 3600)
        return f"{n} {_plural(n, 'час', 'часа', 'часов')} назад"
    if delta < 86400 * 30:
        n = int(delta // 86400)
        return f"{n} {_plural(n, 'день', 'дня', 'дней')}"
    if delta < 86400 * 365:
        n = int(delta // (86400 * 30))
        return f"{n} {_plural(n, 'месяц', 'месяца', 'месяцев')}"
    n = int(delta // (86400 * 365))
    return f"{n} {_plural(n, 'год', 'года', 'лет')}"


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


def _get_profile_field(profile, index, default=None):
    try:
        if profile and len(profile) > index:
            val = profile[index]
            return val if val is not None else default
    except Exception:
        pass
    return default


def _fmt_activity_num(n: int) -> str:
    n = int(n or 0)
    if n < 1000: return str(n)
    if n < 10000:
        v = n / 1000
        s = f"{v:.1f}".rstrip("0").rstrip(".")
        return s.replace(".", ",") + "k"
    if n < 100000: return f"{n // 1000}k"
    if n < 1000000:
        v = n / 1000
        return f"{v:.0f}k"
    v = n / 1000000
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") + "M"


def _owner_status_line(user_id: int) -> str:
    if user_id == OWNER_ID: return "⚜️ Владелец бота"
    if is_coowner(user_id): return "⚜️ Совладелец бота"
    if is_agent(user_id): return "🛡 Агент поддержки Mos"
    return ""


async def _build_anketa_text(target, chat_id: int, viewer_id: int = None) -> str:
    user_id = target.id
    profile = get_user_profile(user_id)
    if not profile:
        return "❌ Анкета не найдена."

    gender = _get_profile_field(profile, 0)
    birth_date = _get_profile_field(profile, 1)
    city = _get_profile_field(profile, 2)
    bio = _get_profile_field(profile, 3)
    is_hidden = _get_profile_field(profile, 4, 1)
    birth_vis = _get_profile_field(profile, 5, 'месяц')
    motto = _get_profile_field(profile, 6)
    show_citizenship = _get_profile_field(profile, 7, 1)

    is_self = (viewer_id == user_id) if viewer_id else True
    is_staff = False
    if viewer_id:
        is_staff = (viewer_id == OWNER_ID or is_coowner(viewer_id) or has_agent_rank(viewer_id, 1))

    if is_hidden and not is_self and not is_staff:
        return (
            f"🔒 <b>Анкета скрыта</b>\n\n"
            f"👤 {mention(target)} закрыл(а) свою анкету.\n"
            f"<i>Он(а) может открыть её командой <code>+анкета</code>.</i>"
        )

    display_name = html_escape_text(target.first_name or "Пользователь")
    if getattr(target, "username", None):
        display_name = f'<a href="https://t.me/{target.username}">{display_name}</a>'
    else:
        display_name = f'<a href="tg://user?id={user_id}">{display_name}</a>'

    lines = []
    last_seen_raw = get_last_seen_in_chat(user_id, chat_id)
    last_seen_str = format_last_seen(last_seen_raw) if last_seen_raw else None
    suffix = f" (был {last_seen_str})" if last_seen_str and last_seen_str != "нет данных" else ""
    lines.append(f"👤 <b>Это {display_name}{suffix}</b>")

    status_line = _owner_status_line(user_id)
    id_line = f"🆔 <code>{user_id}</code>"
    if status_line:
        lines.append(f"{id_line} · {status_line}")
    else:
        lines.append(id_line)
    lines.append("")

    # 🕰 Во вселенной Mos — сколько юзер в боте
    universe_start = get_universe_start(user_id)
    if universe_start:
        duration_u = format_citizenship_duration(universe_start)
        lines.append(f"🕰 Во вселенной <b>Mos</b>: {duration_u}")
    else:
        lines.append(f"🕰 Во вселенной <b>Mos</b>: только что")

    # 🏠 Гражданин чата — только если есть citizenship
    cit = get_citizenship_info(user_id)
    if show_citizenship and cit:
        cit_chat_id, cit_date = cit
        try:
            d = datetime.strptime(cit_date[:19], "%Y-%m-%d %H:%M:%S")
            date_str = d.strftime("%d.%m.%Y")
        except Exception:
            date_str = cit_date[:10]
        duration = format_citizenship_duration(cit_date)
        try:
            cc_title = (await bot.get_chat(cit_chat_id)).title or "чат"
        except Exception:
            cc_title = "чат"
        lines.append(f"🏠 Гражданин чата «{cc_title}»: {date_str} ({duration})")

    if gender:
        lines.append(f"🙂‍↔️ Пол: <b>{html_escape_text(str(gender).lower())}</b>")
    else:
        lines.append("🙂‍↔️ Пол: <i>не указан</i>")

    if birth_date:
        bd_display = str(birth_date)
        try:
            parts = bd_display.split(".")
            if len(parts) == 3:
                if birth_vis == "год":
                    bd_display = f"{parts[2]} год"
                elif birth_vis == "месяц":
                    bd_display = f"{parts[1]}.{parts[2]}"
                else:
                    bd_display = f"{parts[0]}.{parts[1]}.{parts[2]}"
        except Exception:
            pass
        lines.append(f"🗓 Дата рождения: <b>{html_escape_text(bd_display)}</b>")
    else:
        lines.append("🗓 Дата рождения: <i>не указана</i>")

    if city:
        lines.append(f"🏙 Город: <b>{html_escape_text(str(city))}</b>")
    else:
        lines.append("🏙 Город: <i>не указан</i>")

    day, week, month, total = get_activity_extended_global(user_id)
    lines.append(
        f"📊 Активность (день|нед|мес|всего): "
        f"<b>{_fmt_activity_num(day)}</b> | "
        f"<b>{_fmt_activity_num(week)}</b> | "
        f"<b>{_fmt_activity_num(month)}</b> | "
        f"<b>{_fmt_activity_num(total)}</b>"
    )

    rank_text = get_user_rank_text(user_id, chat_id)
    if rank_text:
        lines.append(f"✨ Звание: <b>{rank_text}</b>")

    if motto:
        lines.append(f"💭 Девиз: {motto}")

    about = get_user_about(user_id)
    if about:
        lines.append(f"\n📝 <b>О себе:</b>\n{about}")

    return "\n".join(lines)


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
            exp_dt = _parse_dt(expires_at)
            if exp_dt < datetime.now():
                c.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
                conn.commit()
                return None
        except Exception as e:
            pass
        return (expires_at, emoji)


def add_vip_months(user_id, months):
    current = get_vip(user_id)
    if current:
        try:
            exp_dt = _parse_dt(current[0])
            if exp_dt < datetime.now(): exp_dt = datetime.now()
        except Exception as e:
            exp_dt = datetime.now()
        emoji = current[1]
    else:
        exp_dt = datetime.now()
        emoji = None
    new_exp = exp_dt + timedelta(days=30 * months)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO vip_users (user_id, expires_at, emoji) VALUES (?, ?, ?)",
                  (user_id, _fmt_dt(new_exp), emoji))
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
            exp_dt = _parse_dt(r[0])
            delta = exp_dt - datetime.now()
            if delta.total_seconds() < 0: return 0
            return int(delta.total_seconds() // 86400)
        except Exception as e:
            return 0


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


# ================= ПРАЗДНИКИ =================
CATEGORY_NAMES = {
    "global": "🌍 Глобальные",
    "folk": "🪆 Народные",
    "local": "📍 Праздники",
    "prof": "💼 Профессиональные",
    "fun": "😄 Забавные",
    "church": "⛪ Церковные",
}


def add_holiday(date_str, name, category, added_by=0) -> bool:
    if category not in CATEGORY_NAMES:
        category = "global"
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO holidays (date, name, category, added_by) VALUES (?, ?, ?, ?)",
                      (date_str, name, category, added_by))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def remove_holiday(holiday_id) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
        conn.commit()
        return c.rowcount > 0


def get_holidays_for_date(date_str_mm_dd) -> dict:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT category, name FROM holidays WHERE date = ? ORDER BY id ASC", (date_str_mm_dd,))
        rows = c.fetchall()
    result = {cat: [] for cat in CATEGORY_NAMES.keys()}
    for cat, name in rows:
        if cat in result:
            result[cat].append(name)
    return result


def get_all_holidays_count() -> int:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM holidays")
        return c.fetchone()[0] or 0


def get_all_holidays_text(date_obj=None) -> str:
    if date_obj is None:
        date_obj = datetime.now(timezone.utc) + timedelta(hours=3)
    date_mm_dd = date_obj.strftime("%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")
    holidays = get_holidays_for_date(date_mm_dd)
    text = f"🥳 <b>Праздники {date_display}</b>\n\n"
    total = 0
    for cat_key, cat_title in CATEGORY_NAMES.items():
        items = holidays.get(cat_key, [])
        if not items: continue
        text += f"<b>{cat_title}</b>\n"
        for i, name in enumerate(items, 1):
            text += f"{i}. {html_escape_text(name)}\n"
        text += "\n"
        total += len(items)
    if total == 0:
        text += "<i>Пока нет данных для этой даты.</i>\n"
        text += f"\n📊 Всего в базе: <b>{get_all_holidays_count()}</b> праздников"
    return text.strip()


# ================= MIDDLEWARE =================
class BotIgnoreMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            msg = event
            user = getattr(msg, "from_user", None)
            if user and not user.is_bot:
                if is_bot_ignored(user.id) and user.id != OWNER_ID and not is_coowner(user.id):
                    return
        except Exception as e:
            print(f"⚠️ BotIgnoreMiddleware: {e}")
        return await handler(event, data)


dp.message.middleware(BotIgnoreMiddleware())


# ================= ИИ (ZVENOAI) =================
ZVENOAI_API_KEY = os.environ.get("ZVENOAI_API_KEY", "")
ZVENOAI_MODEL = "deepseek/deepseek-v4-flash"

ai_client = None
if ZVENOAI_API_KEY:
    ai_client = AsyncOpenAI(
        api_key=ZVENOAI_API_KEY,
        base_url="https://api.zveno.ai/v1",
    )

AI_REPLY_CHANCE = 15
AI_REPLY_CHANCE_QUESTION = 40
AI_REPLY_COOLDOWN = 30
AI_REPLY_PER_USER = 120
AI_REPLY_MIN_LEN = 4
AI_MAX_HISTORY = 6

_ai_disabled_chats: set = set()
_last_ai_reply_time = 0.0
_user_last_ai_reply = {}
_chat_history: dict = {}

SYSTEM_PROMPT = (
    "Ты — Mos, дружелюбный чат-бот в Telegram. "
    "Отвечай КОРОТКО (1-2 предложения), живо, по-русски, без формальностей. "
    "Не используй markdown, списки, заголовки. Не пиши длинные тексты. "
    "Иногда используй эмодзи, но не перебарщивай."
)


def _should_ai_reply(message: types.Message) -> bool:
    global _last_ai_reply_time
    print(f"🔍 AI check: chat={message.chat.id} type={message.chat.type}")
    if not ai_client:
        print("🔍 AI: ai_client=None")
        return False
    if not message.from_user or message.from_user.is_bot:
        print("🔍 AI: no user or bot")
        return False
    if message.chat.type not in ["group", "supergroup"]:
        print("🔍 AI: not group")
        return False
    if message.chat.id in _ai_disabled_chats:
        print("🔍 AI: disabled")
        return False

    txt = (message.text or message.caption or "").strip()
    if not txt or len(txt) < AI_REPLY_MIN_LEN:
        print(f"🔍 AI: short text ({len(txt)})")
        return False
    if txt[0] in ".!/+-":
        print("🔍 AI: command")
        return False
    if has_link(txt):
        print("🔍 AI: link")
        return False

    first_line_lower = txt.split("\n", 1)[0].strip().lower()
    if first_line_lower in STANDARD_RP:
        print(f"🔍 AI: RP exact '{first_line_lower}'")
        return False
    for rp_name in STANDARD_RP.keys():
        if first_line_lower.startswith(rp_name + " ") or first_line_lower == rp_name:
            print(f"🔍 AI: RP startswith '{rp_name}'")
            return False

    now = datetime.now().timestamp()
    uid = message.from_user.id
    if now - _last_ai_reply_time < AI_REPLY_COOLDOWN:
        print(f"🔍 AI: global cd {int(now - _last_ai_reply_time)}/{AI_REPLY_COOLDOWN}")
        return False
    if now - _user_last_ai_reply.get(uid, 0) < AI_REPLY_PER_USER:
        print(f"🔍 AI: user cd {int(now - _user_last_ai_reply.get(uid, 0))}/{AI_REPLY_PER_USER}")
        return False

    chance = AI_REPLY_CHANCE_QUESTION if "?" in txt else AI_REPLY_CHANCE
    r = random.randint(1, 100)
    print(f"🔍 AI: chance={chance}% rolled={r} -> {'PASS' if r <= chance else 'FAIL'}")
    return r <= chance


async def _ai_reply(message: types.Message):
    global _last_ai_reply_time
    chat_id = message.chat.id
    uid = message.from_user.id
    txt = (message.text or message.caption or "").strip()

    history = _chat_history.get(chat_id, [])
    history.append({"role": "user", "content": txt})
    history = history[-AI_MAX_HISTORY * 2:]
    _chat_history[chat_id] = history

    try:
        print(f"🚀 AI: request → {ZVENOAI_MODEL}")
        response = await ai_client.chat.completions.create(
            model=ZVENOAI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            max_tokens=150,
            temperature=1.3,
        )
        reply_text = response.choices[0].message.content.strip()
        print(f"🚀 AI: response → {reply_text[:80]}")
        if not reply_text: return

        history.append({"role": "assistant", "content": reply_text})
        _chat_history[chat_id] = history[-AI_MAX_HISTORY * 2:]

        await message.reply(reply_text)
        _last_ai_reply_time = datetime.now().timestamp()
        _user_last_ai_reply[uid] = _last_ai_reply_time
    except APIError as e:
        print(f"❌ AI APIError: {e}")
    except Exception as e:
        print(f"❌ AI Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+ии", "+ии ответы"])
async def enable_ai_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    _ai_disabled_chats.discard(message.chat.id)
    await message.reply("✅ <b>ИИ включён</b> в этом чате.", parse_mode="HTML", **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-ии", "-ии ответы"])
async def disable_ai_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    _ai_disabled_chats.add(message.chat.id)
    await message.reply("❌ <b>ИИ выключен</b> в этом чате.", parse_mode="HTML", **_reply_kwargs(message))


@cmd("ии")
async def ai_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not ai_client:
        return await message.reply("❌ <b>ZvenoAI ключ не задан</b> в .env", parse_mode="HTML", **_reply_kwargs(message))
    enabled = message.chat.id not in _ai_disabled_chats
    status = "🟢 включён" if enabled else "🔴 выключен"
    await message.reply(
        f"🤖 <b>ИИ (DeepSeek через ZvenoAI)</b>: {status}\n\n"
        f"📌 <code>+ии</code> / <code>-ии</code>\n"
        f"<i>Модель: {ZVENOAI_MODEL}</i>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )# ================= MOS — ПИНГ =================
async def _measure_ping():
    start = datetime.now()
    try:
        await bot.get_me()
        tg_ping = int((datetime.now() - start).total_seconds() * 1000)
    except:
        tg_ping = -1
    start = datetime.now()
    try:
        test = await bot.send_message(OWNER_ID, "🏓", disable_notification=True)
        api_ping = int((datetime.now() - start).total_seconds() * 1000)
        try: await test.delete()
        except: pass
    except:
        api_ping = -1
    return tg_ping, api_ping


def _ping_status(ping_ms: int) -> str:
    if ping_ms < 0:   return "❌"
    if ping_ms < 100: return "🟢"
    if ping_ms < 200: return "🟢"
    if ping_ms < 400: return "🟡"
    if ping_ms < 800: return "🟠"
    return "🔴"


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*мос\s*$', m.text.strip(), re.IGNORECASE))
async def mos_cmd(message: types.Message):
    t0 = datetime.now()
    sent = await message.reply("🏓 <b>Мос на месте!</b>\n⏳ <i>измеряю пинг...</i>", parse_mode="HTML", **_reply_kwargs(message))
    response_ping = int((datetime.now() - t0).total_seconds() * 1000)
    tg_ping, api_ping = await _measure_ping()
    text = (
        f"🏓 <b>Мос на месте!</b>\n\n"
        f"⚡ <b>Пинг:</b> <code>{api_ping} мс</code> {_ping_status(api_ping)}\n"
        f"🌐 <b>Telegram API:</b> <code>{tg_ping} мс</code> {_ping_status(tg_ping)}\n"
        f"⏱ <b>Ответ бота:</b> <code>{response_ping} мс</code>"
    )
    try:
        await sent.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    except:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= /START =================
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
    hidden_agents = set(get_hidden_agents())
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT a.user_id, COALESCE(r.rank, 1) FROM agents a
                     LEFT JOIN agent_ranks r ON r.user_id = a.user_id
                     ORDER BY COALESCE(r.rank, 1) DESC LIMIT 50""")
        agents = c.fetchall()
    visible_agents = [(uid, rank) for uid, rank in agents if uid not in hidden_agents][:20]
    if visible_agents:
        for uid, rank in visible_agents:
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
        [InlineKeyboardButton(text="🍬 Купить mos-конфетки", callback_data="buy_candies_menu")],
        [InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_CHAT_LINK),
         InlineKeyboardButton(text="📢 Канал", url=SUPPORT_CHANNEL_LINK)],
        [InlineKeyboardButton(text="📄 Пользовательское соглашение", url=TERMS_URL)]
    ])
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "buy_candies_menu")
async def buy_candies_menu(callback: types.CallbackQuery):
    price = get_stars_per_candy(callback.message.chat.id)
    await callback.message.answer(
        f"🍬 <b>Купить mos-конфетки за ⭐ Stars</b>\n\n"
        f"💰 Курс: <b>{price} ⭐ = 1 🍬</b>\n\n"
        f"📌 Напишите:\n"
        f"<code>.купитьириски 10</code> → {price * 10} ⭐",
        parse_mode="HTML", disable_web_page_preview=True
    )
    await callback.answer()


# ================= ЛС =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*лс\b', m.text.strip(), re.IGNORECASE))
async def bot_dm_cmd(message: types.Message):
    try:
        me = await bot.get_me()
        bot_username = me.username
    except:
        return await message.reply("❌ Ошибка.", disable_web_page_preview=True, **_reply_kwargs(message))
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📩 Написать в ЛС", url=f"https://t.me/{bot_username}")
    ]])
    await message.reply(
        f"📩 <b>Личные сообщения Mos</b>\n\n👉 <a href='https://t.me/{bot_username}'>@{bot_username}</a>",
        parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb, **_reply_kwargs(message)
    )


# ================= КОМАНДЫ =================
@cmd("команды")
@cmd("commands")
async def commands_link_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📖 Открыть команды", url=TELETYPE_URL)
    ]])
    await message.reply(
        f"📖 <b>Все команды бота Mos</b>\n\n🔗 <a href='{TELETYPE_URL}'>Mos-command</a>",
        parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb, **_reply_kwargs(message)
    )


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
    await message.reply(help_text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("пинг")
async def ping_cmd(message: types.Message):
    await message.reply(
        f"{em('ping', '🏓')} Понг!",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("инфобот")
async def bot_info_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
        return
    start = datetime.now()
    sent = await message.reply("🏓 Считаю...", **_reply_kwargs(message))
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
    except: db_size_str = "—"
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
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("инфо")
async def info_cmd(message: types.Message):
    chat_id = message.chat.id
    chat_title = message.chat.title or "Без названия"
    code = get_chat_code(chat_id)
    link = await get_chat_link(chat_id)
    if link: link_text = f'<a href="{link}">Чат-ссылка</a>'
    else: link_text = "Ссылка недоступна"
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
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


# ================= ПОГОДА =================
@cmd("погода", allow_args=True, args_pattern=r"^.+$")
async def weather_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("🌤 <b>Погода</b>\n\n📌 Напиши: <code>.погода Москва</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    city = args[1].strip()
    if not city:
        return await message.reply("❌ Укажи город.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    msg = await message.reply(f"🌍 Ищу погоду в <b>{city}</b>...", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
    except: await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ПЕРЕВОДЧИК =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*(перевод|translate)\s+\S+', m.text.strip(), re.IGNORECASE))
async def translate_cmd(message: types.Message):
    txt = message.text.strip()
    body = re.sub(r'^[.\/!+-]?\s*(перевод|translate)\s+', '', txt, count=1, flags=re.IGNORECASE).strip()
    if not body:
        return await message.reply(
            "🌐 <b>Переводчик</b>\n\n"
            "📌 <code>.перевод en Привет мир</code>\n"
            "📌 <code>.перевод ru Hello world</code>\n\n"
            "🌍 Коды: <code>en, ru, de, fr, es, it, uk, pl, tr, zh, ja, ko, ar</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    parts = body.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("📌 Формат: <code>.перевод en текст</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    lang = parts[0].lower().strip()
    text_to_translate = parts[1].strip()[:1500]
    if len(lang) > 5 or not lang.isalpha():
        lang = "ru"; text_to_translate = body[:1500]
    msg = await message.reply("🌐 Перевожу...", **_reply_kwargs(message))
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": lang, "dt": "t", "q": text_to_translate}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return await msg.edit_text(f"{em('cross', '❌')} Ошибка перевода (код {resp.status})", parse_mode="HTML")
                data = await resp.json()
        translated = "".join(chunk[0] for chunk in data[0] if chunk and chunk[0])
        detected_src = data[2] if len(data) > 2 else "?"
        flags = {"ru":"🇷🇺","en":"🇬🇧","de":"🇩🇪","fr":"🇫🇷","es":"🇪🇸","it":"🇮🇹","uk":"🇺🇦","pl":"🇵🇱","tr":"🇹🇷","zh":"🇨🇳","ja":"🇯🇵","ko":"🇰🇷","ar":"🇸🇦","pt":"🇵🇹","nl":"🇳🇱"}
        src_flag = flags.get(detected_src, "🌐"); dst_flag = flags.get(lang, "🌐")
        out = (
            f"🌐 <b>Перевод</b>\n\n"
            f"{src_flag} <b>Оригинал:</b>\n<i>{html_escape_text(text_to_translate)}</i>\n\n"
            f"{dst_flag} <b>Перевод ({lang}):</b>\n<b>{html_escape_text(translated)}</b>"
        )
        try:
            await msg.edit_text(out, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            await message.reply(out, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except asyncio.TimeoutError:
        await msg.edit_text(f"{em('cross', '❌')} Таймаут. Попробуй позже.", parse_mode="HTML")
    except Exception as e:
        print(f"❌ translate: {e}")
        await msg.edit_text(f"{em('cross', '❌')} Ошибка: <code>{e}</code>", parse_mode="HTML")


# ================= КАЛЬКУЛЯТОР =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*(калькулятор|кальк|calc)\s+(.+)$', m.text.strip(), re.IGNORECASE))
async def calc_cmd(message: types.Message):
    txt = message.text.strip()
    expr = re.sub(r'^[.\/!+-]?\s*(калькулятор|кальк|calc)\s+', '', txt, count=1, flags=re.IGNORECASE).strip()
    if not expr:
        return await message.reply(
            "🧮 <b>Калькулятор</b>\n\n"
            "📌 <code>.кальк 2+2*2</code>\n"
            "📌 <code>.кальк (5+3)/2</code>\n"
            "📌 <code>.кальк sqrt(16)</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    safe_expr = expr.replace(",", ".").replace("^", "**")
    allowed = re.match(r'^[0-9+\-*/().\s%^*]*$', safe_expr)
    math_funcs_used = re.findall(r'\b(sqrt|abs|round|sin|cos|tan|log|log10|pi|e)\b', safe_expr)
    if not allowed and not math_funcs_used:
        return await message.reply(f"{em('cross', '❌')} Недопустимые символы.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    dangerous = ["__", "import", "exec", "eval", "open", "os.", "sys.", "subprocess", "lambda"]
    for bad in dangerous:
        if bad in safe_expr.lower():
            return await message.reply(f"{em('cross', '❌')} Запрещено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        import math
        safe_globals = {"__builtins__": {}, "sqrt": math.sqrt, "abs": abs, "round": round,
                        "sin": math.sin, "cos": math.cos, "tan": math.tan,
                        "log": math.log, "log10": math.log10, "pi": math.pi, "e": math.e}
        result = eval(safe_expr, safe_globals, {})
        result_str = str(result)
        if len(result_str) > 500: result_str = result_str[:500] + "..."
        await message.reply(
            f"🧮 <b>Калькулятор</b>\n\n📝 Пример: <code>{html_escape_text(expr)}</code>\n✅ Ответ: <b>{html_escape_text(result_str)}</b>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    except ZeroDivisionError:
        await message.reply(f"{em('cross', '❌')} Деление на ноль.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Не смог посчитать.\n<code>{html_escape_text(str(e))}</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= КУРСЫ ВАЛЮТ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*курс(\s+\S+)?\s*$', m.text.strip(), re.IGNORECASE))
async def currency_cmd(message: types.Message):
    args = message.text.split()
    msg = await message.reply("💱 Загружаю курсы...", **_reply_kwargs(message))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://open.er-api.com/v6/latest/USD", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return await msg.edit_text(f"{em('cross', '❌')} Не удалось загрузить курсы.", parse_mode="HTML")
                data = await resp.json()
        rates = data.get("rates", {})
        if not rates:
            return await msg.edit_text(f"{em('cross', '❌')} Пустой ответ API.", parse_mode="HTML")
        if len(args) == 1:
            popular = ["USD", "EUR", "GBP", "CNY", "JPY", "UAH", "KZT", "BYN", "TRY", "PLN"]
            base = "RUB"
            if base not in rates:
                return await msg.edit_text(f"{em('cross', '❌')} Нет курса к RUB.", parse_mode="HTML")
            rub_rate = rates[base]
            text = f"💱 <b>Курсы к RUB</b>\n\n"
            for cur in popular:
                if cur == base: continue
                if cur in rates:
                    val = rub_rate / rates[cur]
                    text += f"• 1 {cur} = <b>{val:.2f}</b> ₽\n"
            text += f"\n📌 <code>.курс usd rub 100</code> — конвертер"
            return await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
        try:
            from_cur = args[1].upper()
            to_cur = args[2].upper() if len(args) >= 3 else "RUB"
            amount = float(args[3].replace(",", ".")) if len(args) >= 4 else 1.0
        except (IndexError, ValueError):
            return await msg.edit_text("📌 <b>Формат:</b>\n<code>.курс usd rub 100</code>", parse_mode="HTML")
        if from_cur not in rates:
            return await msg.edit_text(f"{em('cross', '❌')} Валюта <code>{from_cur}</code> не найдена.", parse_mode="HTML")
        if to_cur not in rates:
            return await msg.edit_text(f"{em('cross', '❌')} Валюта <code>{to_cur}</code> не найдена.", parse_mode="HTML")
        result = amount * (rates[to_cur] / rates[from_cur])
        symbols = {"USD":"$","EUR":"€","GBP":"£","RUB":"₽","JPY":"¥","CNY":"¥","UAH":"₴","KZT":"₸","BYN":"Br","TRY":"₺","PLN":"zł","CHF":"₣","CAD":"C$","AUD":"A$"}
        s_from = symbols.get(from_cur, ""); s_to = symbols.get(to_cur, "")
        await msg.edit_text(
            f"💱 <b>Конвертер валют</b>\n\n<b>{amount:g}</b> {s_from}{from_cur} = <b>{result:.4f}</b> {s_to}{to_cur}\n\n<i>Источник: open.er-api.com</i>",
            parse_mode="HTML", disable_web_page_preview=True
        )
    except asyncio.TimeoutError:
        await msg.edit_text(f"{em('cross', '❌')} Таймаут. Попробуй позже.", parse_mode="HTML")
    except Exception as e:
        print(f"❌ currency: {e}")
        await msg.edit_text(f"{em('cross', '❌')} Ошибка: <code>{e}</code>", parse_mode="HTML")


# ================= КРИПТА =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*(крипта|крипт|crypto)\s+\S+', m.text.strip(), re.IGNORECASE))
async def crypto_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("₿ <b>Крипта</b>\n\n📌 <code>.крипта btc</code>\n📌 <code>.крипта eth</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    coin = args[1].lower()
    currency = args[2].lower() if len(args) >= 3 else "usd"
    msg = await message.reply("💎 Загружаю...", **_reply_kwargs(message))
    coin_map = {"btc":"bitcoin","bitcoin":"bitcoin","eth":"ethereum","ethereum":"ethereum","ton":"the-open-network","toncoin":"the-open-network","sol":"solana","solana":"solana","xrp":"ripple","ripple":"ripple","doge":"dogecoin","dogecoin":"dogecoin","bnb":"binancecoin","ada":"cardano","dot":"polkadot","matic":"matic-network","usdt":"tether","usdc":"usd-coin","trx":"tron","ltc":"litecoin","shib":"shiba-inu","avax":"avalanche-2","link":"chainlink","atom":"cosmos"}
    coin_id = coin_map.get(coin, coin)
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": currency, "include_24hr_change": "true"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return await msg.edit_text(f"{em('cross', '❌')} Не удалось получить курс.", parse_mode="HTML")
                data = await resp.json()
        if not data or coin_id not in data:
            return await msg.edit_text(f"{em('cross', '❌')} Монета <code>{coin}</code> не найдена.", parse_mode="HTML")
        info = data[coin_id]
        price = info.get(currency)
        change = info.get(f"{currency}_24h_change")
        if price is None:
            return await msg.edit_text(f"{em('cross', '❌')} Нет цены в {currency.upper()}.", parse_mode="HTML")
        if price >= 1000: price_str = f"{price:,.2f}".replace(",", " ")
        elif price >= 1: price_str = f"{price:.2f}"
        elif price >= 0.01: price_str = f"{price:.4f}"
        else: price_str = f"{price:.8f}"
        change_str = ""
        if change is not None:
            arrow = "📈" if change >= 0 else "📉"
            sign = "+" if change >= 0 else ""
            change_str = f"\n{arrow} Изм. 24ч: <b>{sign}{change:.2f}%</b>"
        coins_emoji = {"btc":"₿","eth":"Ξ","ton":"💎","sol":"◎","doge":"🐕","xrp":"💧","bnb":"🟡","ada":"🔷"}
        icon = coins_emoji.get(coin, "💰")
        await msg.edit_text(f"{icon} <b>{coin.upper()}</b> / {currency.upper()}\n\n💵 Цена: <b>{price_str}</b> {currency.upper()}{change_str}", parse_mode="HTML", disable_web_page_preview=True)
    except asyncio.TimeoutError:
        await msg.edit_text(f"{em('cross', '❌')} Таймаут.", parse_mode="HTML")
    except Exception as e:
        print(f"❌ crypto: {e}")
        await msg.edit_text(f"{em('cross', '❌')} Ошибка: <code>{e}</code>", parse_mode="HTML")


# ================= ВНУТРЕННИЙ КУРС =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*(курс коинов|курс ирисок|биржа)\s*$', m.text.strip(), re.IGNORECASE))
async def internal_rates_cmd(message: types.Message):
    chat_coins = get_chat_coins(message.chat.id)
    text = (
        "💱 <b>Внутренний курс Mos</b>\n\n"
        "🪙 1 🍬 = <b>100</b> i¢\n🍬 100 i¢ = <b>1</b> 🍬\n\n"
        f"🏦 Счёт этого чата: <b>{chat_coins}</b> i¢\n"
        f"💰 В mos-конфетках: ≈ <b>{chat_coins // 100}</b> 🍬\n\n"
        "📌 Обмен: <code>.купить коины 10</code> — 10 🍬 → 1000 i¢\n"
        "📌 Взнос: <code>.бкоин 100</code> — 100 i¢ в счёт чата"
    )
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= WIKIPEDIA =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*(вики|wiki)\s+\S+', m.text.strip(), re.IGNORECASE))
async def wiki_cmd(message: types.Message):
    txt = message.text.strip()
    body = re.sub(r'^[.\/!+-]?\s*(вики|wiki)\s+', '', txt, count=1, flags=re.IGNORECASE).strip()
    if not body:
        return await message.reply("📖 <b>Википедия</b>\n\n📌 <code>.вики Москва</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    parts = body.split(maxsplit=1)
    lang = "ru"; query = body
    if len(parts) >= 2 and len(parts[0]) == 2 and parts[0].isalpha():
        lang = parts[0].lower(); query = parts[1].strip()
    if not query:
        return await message.reply("❌ Пустой запрос.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    msg = await message.reply(f"🔎 Ищу в Википедии: <b>{html_escape_text(query)}</b>...", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        search_url = f"https://{lang}.wikipedia.org/w/api.php"
        search_params = {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 1, "utf8": 1}
        headers = {"User-Agent": "MosBot/1.0 (Telegram bot)"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(search_url, params=search_params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return await msg.edit_text(f"{em('cross', '❌')} Википедия не отвечает.", parse_mode="HTML")
                search_data = await resp.json()
        results = search_data.get("query", {}).get("search", [])
        if not results:
            return await msg.edit_text(f"{em('cross', '❌')} Ничего не найдено.", parse_mode="HTML")
        page_title = results[0]["title"]
        summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(page_title)}"
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(summary_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return await msg.edit_text(f"{em('cross', '❌')} Не удалось загрузить статью.", parse_mode="HTML")
                summary_data = await resp.json()
        extract = summary_data.get("extract", "").strip()
        if not extract:
            return await msg.edit_text(f"{em('cross', '❌')} Пустая статья.", parse_mode="HTML")
        if len(extract) > 1000: extract = extract[:1000].rsplit(" ", 1)[0] + "..."
        flags = {"ru":"🇷🇺","en":"🇬🇧","de":"🇩🇪","fr":"🇫🇷","es":"🇪🇸","it":"🇮🇹","uk":"🇺🇦","pl":"🇵🇱","tr":"🇹🇷","ja":"🇯🇵","zh":"🇨🇳","ko":"🇰🇷","ar":"🇸🇦","pt":"🇵🇹","nl":"🇳🇱"}
        flag = flags.get(lang, "🌐")
        page_url = summary_data.get("content_urls", {}).get("desktop", {}).get("page") or f"https://{lang}.wikipedia.org/wiki/{quote(page_title)}"
        thumbnail = summary_data.get("thumbnail", {}).get("source")
        out = f"📖 <b>{html_escape_text(page_title)}</b>\n{flag} <i>Википедия ({lang})</i>\n\n{html_escape_text(extract)}\n\n🔗 <a href='{page_url}'>Читать полностью</a>"
        if thumbnail:
            try:
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Читать в Википедии", url=page_url)]])
                try: await msg.delete()
                except: pass
                await message.reply_photo(photo=thumbnail, caption=out, parse_mode="HTML", reply_markup=kb, **_reply_kwargs(message))
                return
            except Exception:
                pass
        try:
            await msg.edit_text(out, parse_mode="HTML", disable_web_page_preview=False)
        except Exception:
            try: await msg.delete()
            except: pass
            await message.reply(out, parse_mode="HTML", disable_web_page_preview=False, **_reply_kwargs(message))
    except asyncio.TimeoutError:
        await msg.edit_text(f"{em('cross', '❌')} Таймаут. Попробуй позже.", parse_mode="HTML")
    except Exception as e:
        print(f"❌ wiki: {traceback.format_exc()}")
        try:
            await msg.edit_text(f"{em('cross', '❌')} Ошибка: <code>{type(e).__name__}: {e}</code>", parse_mode="HTML")
        except: pass


# ================= ПРАЗДНИКИ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*(праздники|праздник|holidays)\s*$', m.text.strip(), re.IGNORECASE))
async def holidays_cmd(message: types.Message):
    text = get_all_holidays_text()
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*(праздники|праздник)\s+(\d{1,2})[.\-](\d{1,2})\.?(\d{4})?\s*$', m.text.strip(), re.IGNORECASE))
async def holidays_date_cmd(message: types.Message):
    m = re.match(r'^\s*[.\/!+-]?\s*(праздники|праздник)\s+(\d{1,2})[.\-](\d{1,2})\.?(\d{4})?\s*$', message.text.strip(), re.IGNORECASE)
    day, month = int(m.group(2)), int(m.group(3))
    year = int(m.group(4)) if m.group(4) else (datetime.now(timezone.utc) + timedelta(hours=3)).year
    try:
        date_obj = datetime(year, month, day)
    except ValueError:
        return await message.reply(f"{em('cross', '❌')} Неверная дата.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = get_all_holidays_text(date_obj)
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


def is_holidays_enabled(chat_id) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM global_settings WHERE key = ?", (f"holidays:{chat_id}",))
        r = c.fetchone()
        return r is not None and r[0] == "1"


def set_holidays_enabled(chat_id, enabled: bool):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)",
                  (f"holidays:{chat_id}", "1" if enabled else "0"))
        conn.commit()


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+праздники", "+ праздники", "+праздник", "+ праздник"])
async def enable_holidays_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    user_id = message.from_user.id
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(message.chat.id, user_id, 3):
        if not await is_tg_admin(message.chat.id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if is_holidays_enabled(message.chat.id):
        return await message.reply("ℹ️ Уже включено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_holidays_enabled(message.chat.id, True)
    await message.reply(f"{em('check', '✅')} <b>Праздники включены!</b>\n\n🥳 Автопост в <b>00:00 МСК</b>.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-праздники", "- праздники", "-праздник", "- праздник"])
async def disable_holidays_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    user_id = message.from_user.id
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(message.chat.id, user_id, 3):
        if not await is_tg_admin(message.chat.id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not is_holidays_enabled(message.chat.id):
        return await message.reply("ℹ️ Уже выключено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_holidays_enabled(message.chat.id, False)
    await message.reply(f"{em('check', '✅')} Праздники выключены.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*праздник\s+добавить\s+(\d{1,2})[.\-](\d{1,2})\s*\|\s*(.+?)\s*\|\s*(\S+)\s*$', m.text.strip(), re.IGNORECASE))
async def add_holiday_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id) and not has_agent_rank(message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Только владелец/совладелец/агент 3+.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    m = re.match(r'^\s*[.\/!+-]?\s*праздник\s+добавить\s+(\d{1,2})[.\-](\d{1,2})\s*\|\s*(.+?)\s*\|\s*(\S+)\s*$', message.text.strip(), re.IGNORECASE)
    day, month = int(m.group(1)), int(m.group(2))
    name = m.group(3).strip(); category = m.group(4).strip().lower()
    cat_map = {"глобальные":"global","глобальный":"global","global":"global","народные":"folk","народный":"folk","folk":"folk","праздники":"local","праздник":"local","local":"local","профессиональные":"prof","профессия":"prof","prof":"prof","забавные":"fun","забавный":"fun","fun":"fun","церковные":"church","церковный":"church","church":"church"}
    if category not in cat_map:
        return await message.reply("❌ Категория не найдена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    date_mm_dd = f"{month:02d}-{day:02d}"
    if add_holiday(date_mm_dd, name, cat_map[category], message.from_user.id):
        await message.reply(f"{em('check', '✅')} Праздник добавлен!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    else:
        await message.reply(f"{em('cross', '❌')} Уже есть.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*праздник\s+удалить\s+\d+\s*$', m.text.strip(), re.IGNORECASE))
async def remove_holiday_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Только владелец/совладелец.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    m = re.match(r'^\s*[.\/!+-]?\s*праздник\s+удалить\s+(\d+)\s*$', message.text.strip(), re.IGNORECASE)
    if remove_holiday(int(m.group(1))):
        await message.reply(f"{em('check', '✅')} Удалён.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    else:
        await message.reply(f"{em('cross', '❌')} Не найден.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*праздник\s+список\s*$', m.text.strip(), re.IGNORECASE))
async def list_holidays_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id) and not has_agent_rank(message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Только для агентов.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, date, name, category FROM holidays ORDER BY date ASC, id ASC LIMIT 100")
        rows = c.fetchall()
    if not rows:
        return await message.reply("📭 Пусто.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"📋 <b>Праздники в базе</b> (всего: {get_all_holidays_count()}):\n\n"
    for hid, date_mm_dd, name, cat in rows:
        text += f"<code>#{hid}</code> {date_mm_dd} [{cat}] {name}\n"
    await message.reply(text[:4000], parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))# ================= АВТОУДАЛЕНИЕ ПРИВЕТСТВИЙ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*\+?\s*автоудаление\s+приветствий\b', m.text.strip(), re.IGNORECASE))
async def set_greeting_autodelete_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    user_id = message.from_user.id; chat_id = message.chat.id
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(chat_id, user_id, 3):
        if not await is_tg_admin(chat_id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    args = re.sub(r'^[.\/!+-]?\s*\+?\s*автоудаление\s+приветствий\s*', '', message.text.strip(), count=1, flags=re.IGNORECASE).strip()
    if not args:
        current = get_greeting_autodelete(chat_id)
        if current > 0:
            return await message.reply(f"🧹 <b>Автоудаление приветствий</b>: <b>{_humanize_seconds(current)}</b>\n\n📌 Изменить: <code>+Автоудаление приветствий 30с</code>\n📌 Отключить: <code>-Автоудаление приветствий</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        return await message.reply("🧹 <b>Автоудаление приветствий</b>: 🔴 выключено\n\n📌 Включить: <code>+Автоудаление приветствий 30с</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    seconds, human = parse_autodelete_duration(args)
    if seconds is False:
        return await message.reply("❌ Не понял срок.\nПримеры: <code>30с</code>, <code>5 мин</code>, <code>2 часа</code>, <code>1 день</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if seconds == 0:
        set_greeting_autodelete(chat_id, 0)
        return await message.reply(f"{em('cross', '❌')} Автоудаление приветствий выключено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_greeting_autodelete(chat_id, seconds)
    await message.reply(f"{em('check', '✅')} <b>Автоудаление приветствий включено!</b>\n\n⏱ Удаление через <b>{human}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-автоудаление приветствий")
async def disable_greeting_autodelete_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    user_id = message.from_user.id; chat_id = message.chat.id
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(chat_id, user_id, 3):
        if not await is_tg_admin(chat_id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if get_greeting_autodelete(chat_id) == 0:
        return await message.reply("ℹ️ Уже выключено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_greeting_autodelete(chat_id, 0)
    await message.reply(f"{em('cross', '❌')} Автоудаление приветствий выключено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*срок\s+приветствия\b', m.text.strip(), re.IGNORECASE))
async def greeting_autodelete_alias_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    user_id = message.from_user.id; chat_id = message.chat.id
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(chat_id, user_id, 3):
        if not await is_tg_admin(chat_id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    args = re.sub(r'^[.\/!+-]?\s*срок\s+приветствия\s*', '', message.text.strip(), count=1, flags=re.IGNORECASE).strip()
    if not args:
        current = get_greeting_autodelete(chat_id)
        if current > 0:
            return await message.reply(f"🧹 Автоудаление приветствий: <b>{_humanize_seconds(current)}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        return await message.reply("🧹 Автоудаление приветствий: 🔴 выключено", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    seconds, human = parse_autodelete_duration(args)
    if seconds is False:
        return await message.reply("❌ Не понял срок.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if seconds == 0:
        set_greeting_autodelete(chat_id, 0)
        return await message.reply(f"{em('cross', '❌')} Автоудаление приветствий выключено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_greeting_autodelete(chat_id, seconds)
    await message.reply(f"{em('check', '✅')} Автоудаление приветствий: <b>{human}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= КОРОТКО ПРО =================
@dp.message(lambda m: m.text and m.text.lower().strip() in ["+коротко про", "+короткопро"])
async def enable_short_about_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    user_id = message.from_user.id; chat_id = message.chat.id
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(chat_id, user_id, 3):
        if not await is_tg_admin(chat_id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if is_short_about_enabled(chat_id):
        return await message.reply("ℹ️ Уже включено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_short_about_enabled(chat_id, True)
    await message.reply(f"{em('check', '✅')} <b>Карточка «Коротко про» включена!</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-коротко про", "-короткопро"])
async def disable_short_about_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    user_id = message.from_user.id; chat_id = message.chat.id
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(chat_id, user_id, 3):
        if not await is_tg_admin(chat_id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not is_short_about_enabled(chat_id):
        return await message.reply("ℹ️ Уже выключено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_short_about_enabled(chat_id, False)
    await message.reply(f"{em('cross', '❌')} Карточка «Коротко про» выключена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= МОЙ ПОЛ / ДР / ГОРОД =================
@dp.message(lambda m: m.text and re.match(r'^\s*!?\s*мой\s+пол(\s+[МЖмж]|\s+(Мужской|Женский|Другой))?\s*$', m.text.strip(), re.IGNORECASE))
async def set_gender_cmd(message: types.Message):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("📌 <code>мой пол М</code> или <code>мой пол Ж</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    v = parts[2].strip().lower()
    if v in ["м", "муж", "мужской"]: v = "Мужской"
    elif v in ["ж", "жен", "женский"]: v = "Женский"
    else: v = "Другой"
    update_user_profile(message.from_user.id, "gender", v)
    await message.reply(f"✅ Пол: <b>{v}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-мой пол", ".мой пол", "/мой пол"])
async def remove_gender_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "gender", None)
    await message.reply("✅ Удалён.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*!?\s*мой\s+др\s+(\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4})(\s+(год|месяц|день))?\s*$', m.text.strip(), re.IGNORECASE))
async def set_birth_cmd(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) < 3:
        return await message.reply("📌 <code>мой др 01.01.2000</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    date = parts[2].strip()
    vis = parts[3].lower() if len(parts) >= 4 else "месяц"
    update_user_profile(message.from_user.id, "birth_date", date)
    update_user_profile(message.from_user.id, "birth_visibility", vis)
    await message.reply(f"✅ ДР: <b>{date}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-мой др", ".мой др", "/мой др"])
async def remove_birth_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "birth_date", None)
    await message.reply("✅ Удалён.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*!?\s*мой\s+город(\s+.+)?\s*$', m.text.strip(), re.IGNORECASE))
async def set_city_cmd(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("📌 <code>мой город Москва</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    update_user_profile(message.from_user.id, "city", args[2].strip()[:50])
    await message.reply(f"✅ Город: <b>{args[2].strip()[:50]}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-мой город", ".мой город", "/мой город"])
async def remove_city_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "city", None)
    await message.reply("✅ Удалён.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= АНКЕТА =================
@cmd("анкета", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
async def anketa_cmd(message: types.Message):
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            arg = args[1].strip()
            try:
                if arg.startswith("@"):
                    target = await bot.get_chat(arg)
                elif arg.lstrip("-").isdigit():
                    target = await bot.get_chat(int(arg))
            except Exception:
                with sqlite3.connect(DATABASE_PATH) as conn:
                    c = conn.cursor()
                    if arg.startswith("@"):
                        c.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (arg[1:],))
                    else:
                        c.execute("SELECT user_id FROM users WHERE user_id = ?", (int(arg) if arg.lstrip("-").isdigit() else 0,))
                    row = c.fetchone()
                if row:
                    try: target = await bot.get_chat(row[0])
                    except Exception: target = _FakeUser(row[0], f"ID {row[0]}")
                else:
                    return await message.reply(f"{em('cross', '❌')} Пользователь <code>{arg}</code> не найден.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not target:
        target = message.from_user

    text = await _build_anketa_text(target, message.chat.id, viewer_id=message.from_user.id)
    chart_buf = None
    try: chart_buf = generate_user_activity_chart(target.id, days=30)
    except Exception as e: print(f"⚠️ График анкеты: {e}")

    if chart_buf:
        try:
            await message.reply_photo(photo=types.BufferedInputFile(chart_buf.getvalue(), filename="anketa.png"),
                caption=text, parse_mode="HTML", **_reply_kwargs(message))
            return
        except Exception: pass
    try:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception:
        await message.reply(text, disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("моя анкета")
@cmd("моя профиль")
async def my_anketa_cmd(message: types.Message):
    text = await _build_anketa_text(message.from_user, message.chat.id, viewer_id=message.from_user.id)
    chart_buf = None
    try: chart_buf = generate_user_activity_chart(message.from_user.id, days=30)
    except Exception as e: print(f"⚠️ График анкеты: {e}")
    if chart_buf:
        try:
            await message.reply_photo(photo=types.BufferedInputFile(chart_buf.getvalue(), filename="anketa.png"),
                caption=text, parse_mode="HTML", **_reply_kwargs(message))
            return
        except Exception: pass
    try:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception:
        await message.reply(text, disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("твоя анкета", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
async def your_anketa_cmd(message: types.Message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            arg = args[1]
            try:
                if arg.startswith("@"): target = await bot.get_chat(arg)
                elif arg.lstrip("-").isdigit(): target = await bot.get_chat(int(arg))
            except Exception:
                with sqlite3.connect(DATABASE_PATH) as conn:
                    c = conn.cursor()
                    if arg.startswith("@"): c.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (arg[1:],))
                    else: c.execute("SELECT user_id FROM users WHERE user_id = ?", (int(arg) if arg.lstrip("-").isdigit() else 0,))
                    row = c.fetchone()
                if row:
                    try: target = await bot.get_chat(row[0])
                    except Exception: target = _FakeUser(row[0], f"ID {row[0]}")
                else:
                    return await message.reply(f"{em('cross', '❌')} Пользователь <code>{arg}</code> не найден.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not target:
        return await message.reply("📌 <b>Формат:</b>\n• <code>.твоя анкета</code> (ответом)\n• <code>.твоя анкета @user</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = await _build_anketa_text(target, message.chat.id, viewer_id=message.from_user.id)
    chart_buf = None
    try: chart_buf = generate_user_activity_chart(target.id, days=30)
    except Exception as e: print(f"⚠️ График анкеты: {e}")
    if chart_buf:
        try:
            await message.reply_photo(photo=types.BufferedInputFile(chart_buf.getvalue(), filename="anketa.png"),
                caption=text, parse_mode="HTML", **_reply_kwargs(message))
            return
        except Exception: pass
    try:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception:
        await message.reply(text, disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+био"))
async def set_bio_cmd(message: types.Message):
    if not message.text: return
    nl_idx = message.text.find("\n")
    if nl_idx == -1:
        idx = message.text.lower().find("+био")
        raw = message.text[idx + len("+био"):].strip()
        if not raw:
            return await message.reply("📌 <code>+био Твой текст</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        update_user_profile(message.from_user.id, "bio", html_escape_text(raw[:300]))
        return await message.reply("✅ Био сохранено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    raw_html = _extract_html_after(message, nl_idx + 1)[:300]
    if not raw_html:
        return await message.reply("❌ Пусто.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    update_user_profile(message.from_user.id, "bio", raw_html)
    await message.reply("✅ Био сохранено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-био")
async def remove_bio_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "bio", None)
    await message.reply("✅ Био удалено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ПРОФИЛЬ =================
@cmd("профиль", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
async def profile_cmd(message: types.Message):
    target = None
    arg_raw = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) >= 2:
            arg_raw = args[1].strip()
            try:
                if arg_raw.startswith("@"): target = await bot.get_chat(arg_raw)
                elif arg_raw.lstrip("-").isdigit(): target = await bot.get_chat(int(arg_raw))
            except Exception:
                return await message.reply(f"{em('cross', '❌')} Пользователь <code>{arg_raw}</code> не найден.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not target:
        target = message.from_user

    chat_id = message.chat.id
    user_id = target.id
    register_user(user_id, target.first_name, target.username or "")
    rank = get_rank(chat_id, user_id)
    rank_name = rank_display(chat_id, rank)

    member_status_icon = "🟢"; member_status_text = "Состоит в чате"
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        if m.status == "creator": member_status_icon, member_status_text = "👑", "Создатель чата"
        elif m.status == "administrator": member_status_icon, member_status_text = "🛡", "Администратор"
        elif m.status == "restricted": member_status_icon, member_status_text = "🔇", "Ограничен"
        elif m.status == "left": member_status_icon, member_status_text = "⚪", "Вышел из чата"
        elif m.status == "kicked": member_status_icon, member_status_text = "🚫", "Забанен"
    except Exception: pass

    in_antispam = is_in_antispam(user_id)
    in_ignore = is_ignored(chat_id, user_id)
    as_line = None
    if in_antispam:
        info = get_antispam_info(user_id)
        reason = info[0] if info else "не указана"
        as_line = f"☢️ В антиспаме: <i>{reason}</i>"

    warns_count = count_warns(user_id, chat_id)
    warn_line = f"❗ Предупреждения: <b>{warns_count}/3</b>" if warns_count > 0 else "❗ Предупреждения: нет"

    cit = get_citizenship_info(user_id)
    if cit:
        cit_chat_id, cit_date = cit
        short = format_citizenship_short(cit_date)
        try:
            d = datetime.strptime(cit_date[:19], "%Y-%m-%d %H:%M:%S"); date_str = d.strftime("%d.%m.%Y")
        except Exception: date_str = cit_date[:10]
        if cit_chat_id == chat_id:
            cit_line = f"🏠 Гражданство беседы: {date_str} ({short})"
        else:
            try:
                cc = await bot.get_chat(cit_chat_id); cc_title = cc.title or "другой чат"
            except Exception: cc_title = "другой чат"
            cit_line = f"🏠 Гражданство «{cc_title}»: {date_str} ({short})"
    else:
        cit_line = "🏠 Гражданство беседы: нет"

    last_seen = get_last_seen_in_chat(user_id, chat_id)
    last_seen_str = format_last_seen(last_seen)
    last_line = f"⏰ Последний актив: {last_seen_str}"
    day, week, month, total = get_activity_extended(user_id, chat_id)
    activity_line = f"📊 Актив (д|н|м|весь): {day} | {week} | {month} | {total}"

    nick = get_user_nick(user_id, chat_id)
    display_name = nick if nick else html_escape_text(target.first_name or "Пользователь")
    if getattr(target, "username", None):
        profile_link = f'<a href="https://t.me/{target.username}">{display_name}</a>'
    else:
        profile_link = f'<a href="tg://user?id={user_id}">{display_name}</a>'

    lines = [f"👤 Это пользователь {profile_link}", f"{member_status_icon} {member_status_text}"]
    status_line = _owner_status_line(user_id)
    if status_line: lines.append(status_line)
    lines.append("")
    lines.append(f"👑 Ранг: <b>[{rank}]</b> {rank_name}")
    lines.append(warn_line); lines.append(cit_line); lines.append(last_line); lines.append(activity_line)
    if as_line: lines.append(as_line)
    elif in_ignore: lines.append(f"{em('mute', '🔇')} В игноре")

    text = "\n".join(lines)
    chart_buf = None
    try: chart_buf = generate_user_chat_activity_chart(user_id, chat_id, days=30)
    except Exception as e: print(f"⚠️ График профиля: {e}")
    if chart_buf:
        try:
            await message.reply_photo(photo=types.BufferedInputFile(chart_buf.getvalue(), filename="profile.png"),
                caption=text, parse_mode="HTML", **_reply_kwargs(message))
        except Exception:
            await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    else:
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("мойид")
async def myid_cmd(message: types.Message):
    await message.reply(f"{em('id', '🆔')} Ваш ID: <code>{message.from_user.id}</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("ид", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
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
                            return await message.reply(f"{em('id', '🆔')} ID: <code>{user_id}</code>\n📛 {r[0]}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
                    return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
            elif arg.startswith('@'):
                try: target = await bot.get_chat(arg)
                except: return await message.reply(f"{em('cross', '❌')} Не найден", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not target: target = message.from_user
    await message.reply(
        f"{em('id', '🆔')} <b>Информация</b>\n\n👤 Имя: {mention(target)}\n🆔 ID: <code>{target.id}</code>\n👤 Username: @{target.username if target.username else '—'}",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("чатид")
async def get_chat_id_cmd(message: types.Message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        fwd = message.reply_to_message.forward_from_chat
        return await message.reply(
            f"{em('id', '🆔')} <b>ID пересланного чата</b>\n\n📛 <b>{fwd.title or 'Без названия'}</b>\n🆔 <code>{fwd.id}</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    await message.reply(
        f"{em('id', '🆔')} <b>Информация о чате</b>\n\n📛 <b>{message.chat.title or 'Личный чат'}</b>\n🆔 <code>{message.chat.id}</code>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


# ================= ТОП =================
@cmd("топ", allow_args=True,
     args_pattern=r"^(24ч|24h|день|сутки|д|today|day|неделя|неделю|нед|н|7д|7d|week|месяц|мес|м|30д|30d|month|вся|всё|все|all|\*)$")
async def top_cmd(message: types.Message):
    try:
        if message.chat.type not in ["group", "supergroup"]:
            return await message.reply("📊 Топ работает только в группах.", parse_mode="HTML", **_reply_kwargs(message))
        args = message.text.strip().split()
        if args and args[0] and args[0][0] in ".!/+-":
            args[0] = args[0][1:]
        period = "24h"; period_name = "за последние 24 часа"; period_icon = "🕐"
        if len(args) >= 2:
            p = args[1].lower().strip()
            if p in ["24ч", "24h", "день", "сутки", "д", "today", "day"]:
                period, period_name, period_icon = "24h", "за последние 24 часа", "🕐"
            elif p in ["неделя", "неделю", "нед", "н", "7д", "7d", "week"]:
                period, period_name, period_icon = "7d", "за неделю", "📆"
            elif p in ["месяц", "мес", "м", "30д", "30d", "month"]:
                period, period_name, period_icon = "30d", "за месяц", "🗓"
            elif p in ["вся", "всё", "все", "всё время", "all", "*"]:
                period, period_name, period_icon = "all", "за всё время", "🏆"
        top_users = get_top_users(message.chat.id, period, limit=10)
        header = (
            f"{em('stats', '📊')} <b>Топ {period_icon} {period_name}</b>\n"
            f"<i>Чат:</i> {message.chat.title or 'личка'}\n"
            f"<i>Обновлено:</i> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        )
        if not top_users:
            return await message.reply(header + "📭 <i>Пока нет данных за этот период.</i>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        total_msgs = sum(cnt or 0 for _, cnt in top_users)
        text = header
        medals = ["🥇", "🥈", "🥉"]
        max_count = top_users[0][1] or 1
        for i, (user_id, count) in enumerate(top_users, 1):
            try:
                user = await bot.get_chat(user_id)
                name = user_link(user_id, user.first_name, user.username)
            except: name = f"<code>{user_id}</code>"
            medal = medals[i-1] if i <= 3 else f"<b>{i}.</b>"
            bar_len = 10
            filled = int((count / max_count) * bar_len) if max_count else 0
            bar = "▰" * filled + "▱" * (bar_len - filled)
            text += f"{medal} {name}\n    <code>{bar}</code> <b>{count}</b>\n\n"
        text += (
            f"━━━━━━━━━━━━━━━\n"
            f"📈 Всего сообщений: <b>{total_msgs}</b>\n"
            f"👥 Участников: <b>{len(top_users)}</b>\n"
            f"🕐 Живая статистика <b>24/7</b>"
        )
        await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        print(f"❌ top_cmd ошибка: {traceback.format_exc()}")
        try:
            await message.reply(f"❌ Ошибка топа: <code>{type(e).__name__}: {e}</code>", parse_mode="HTML", **_reply_kwargs(message))
        except: pass


# ================= КТО НЕ ПИСАЛ =================
@cmd("кто не писал", allow_args=True, args_pattern=r"^\d+$")
@cmd("неактивные", allow_args=True, args_pattern=r"^\d+$")
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
            return await message.reply(f"{em('cross', '❌')} Нужен Ст. Модератор (2+) или ТГ-админ.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    inactive = get_inactive_users(chat_id, days=days, limit=30)
    if not inactive:
        return await message.reply(f"{em('check', '✅')} <b>Все активны!</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ОБНОВИТЬ ЧАТ =================
@cmd("обновить чат")
@cmd("обновитьчат")
async def refresh_chat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass
    if not is_creator and not has_permission(message.chat.id, message.from_user.id, 3):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    status_msg = await message.reply("🔄 Обновляю...", **_reply_kwargs(message))
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
            f"📛 <b>Название:</b> {title}\n🆔 <b>ID:</b> <code>{message.chat.id}</code>\n"
            f"🔑 <b>Код:</b> <code>{code}</code>\n🔗 <b>Ссылка:</b> {link_text}\n"
            f"👑 <b>Бот админ:</b> {admin_icon}\n📝 <b>Описание:</b> {description[:200] or '—'}"
        )
        try: await status_msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
        except: await status_msg.edit_text(text)
    except Exception as e:
        await status_msg.edit_text(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML")


# ================= ДК =================
@cmd("дк", allow_args=True, args_pattern=r"^.+$")
async def dk_main_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    chat_id = message.chat.id
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass
    if message.from_user.id == OWNER_ID or is_coowner(message.from_user.id): is_creator = True
    if not is_creator and not has_permission(chat_id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    args = message.text.split(maxsplit=2)
    if len(args) < 2: return await _show_dk_list(message)
    if args[1].lower() in ["сброс", "reset"]:
        reset_command_access(chat_id)
        return await message.reply(f"{em('check', '✅')} Все ДК сброшены.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if len(args) < 3:
        return await message.reply(
            "📌 <b>Формат:</b>\n<code>.дк бан 3</code>\n<code>.дк бан все</code>\n<code>.дк бан выкл</code>\n<code>.дк бан создатель</code>\n<code>.дк сброс</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    cmd_name = args[1].lower().strip()
    value = args[2].lower().strip()
    if cmd_name not in DEFAULT_ACCESS:
        return await message.reply(f"{em('cross', '❌')} Команда <code>{cmd_name}</code> не найдена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if value in ["все", "all", "0"]: new_rank = 0
    elif value in ["выкл", "off", "отключить", "-1"]: new_rank = -1
    elif value in ["создатель", "creator", "владелецчата", "-2"]: new_rank = -2
    elif value.isdigit() and 0 <= int(value) <= 5: new_rank = int(value)
    else:
        return await message.reply("❌ Допустимые: <code>все</code>, <code>0-5</code>, <code>выкл</code>, <code>создатель</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not is_creator:
        actor_rank = get_rank(chat_id, message.from_user.id)
        if new_rank > actor_rank and new_rank not in (-1, -2):
            return await message.reply(f"{em('cross', '❌')} Нельзя выше своего.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_command_access(chat_id, cmd_name, new_rank)
    level_names = {
        -2: "👑 Только создатель", -1: "🔒 Отключено",
        0: f"🌐 {get_moderator_title(chat_id, 0, 'nom')}",
        1: rank_display(chat_id, 1), 2: rank_display(chat_id, 2), 3: rank_display(chat_id, 3),
        4: rank_display(chat_id, 4), 5: rank_display(chat_id, 5),
    }
    return await message.reply(
        f"{em('check', '✅')} ДК обновлён\n📌 <code>{cmd_name}</code>\n🔒 {level_names.get(new_rank, str(new_rank))}",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


async def _show_dk_list(message: types.Message):
    chat_id = message.chat.id
    access = get_all_access_for_chat(chat_id)
    groups = {-2: [], -1: [], 0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
    for cmd_name, rank in access.items():
        if rank in groups: groups[rank].append(cmd_name)
    level_names = {
        -2: "👑 Только создатель", -1: "🔒 Отключено", 0: "🌐 Все",
        1: rank_display(chat_id, 1), 2: rank_display(chat_id, 2), 3: rank_display(chat_id, 3),
        4: rank_display(chat_id, 4), 5: rank_display(chat_id, 5),
    }
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
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+команды", "+ команды", "+оповещения", "+ оповещения"])
async def enable_command_notify_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass
    if message.from_user.id == OWNER_ID or is_coowner(message.from_user.id): is_creator = True
    if not is_creator and not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if is_command_notify_enabled(message.chat.id):
        return await message.reply(f"ℹ️ Уже включены.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_command_notify_enabled(message.chat.id, True)
    await message.reply(f"{em('check', '✅')} Оповещения включены!\n📌 Отключить: <code>-команды</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-команды", "- команды", "-оповещения", "- оповещения"])
async def disable_command_notify_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_creator = (member.status == "creator")
    except: pass
    if message.from_user.id == OWNER_ID or is_coowner(message.from_user.id): is_creator = True
    if not is_creator and not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not is_command_notify_enabled(message.chat.id):
        return await message.reply(f"ℹ️ Уже выключены.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_command_notify_enabled(message.chat.id, False)
    await message.reply(f"{em('check', '✅')} Оповещения выключены!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("оповещения")
@cmd("командыстатус")
async def command_notify_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    enabled = is_command_notify_enabled(message.chat.id)
    status = "🟢 включены" if enabled else "🔴 выключены"
    await message.reply(f"🔔 Оповещения: {status}\n\n<code>+команды</code> / <code>-команды</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))# ================= МОДЕРАЦИЯ =================
@mod_cmd("бан", allow_args=True)
async def ban_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
        return await message.reply(f"{em('cross', '❌')} Максимум 366 дней.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Не могу найти юзера.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    reason = None
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        r = parts[1].strip()
        if r: reason = r
    try:
        if duration_seconds:
            until = datetime.now() + timedelta(seconds=duration_seconds)
            await bot.ban_chat_member(message.chat.id, target.id, until_date=until)
            add_chat_ban(message.chat.id, target.id, reason or "без причины", message.from_user.id, until.isoformat())
        else:
            await bot.ban_chat_member(message.chat.id, target.id)
            add_chat_ban(message.chat.id, target.id, reason or "без причины", message.from_user.id, None)
        auto_added = auto_add_to_antispam_if_needed(target.id)
        extra = "☢️ Автоматически добавлен в антиспам!" if auto_added else None
        response = mod_action_text("🚫", "Бан", mention(target), mention(message.from_user), duration_text, reason, extra)
        await message.reply(response, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        await message.reply(mod_error_text("Ошибка бана", f"<code>{e}</code>"), parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@mod_cmd("разбан", allow_args=True)
async def unban_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Не могу найти юзера.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try: await bot.unban_chat_member(message.chat.id, target.id)
    except: pass
    try:
        await bot.restrict_chat_member(message.chat.id, target.id, permissions=types.ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True,
            can_add_web_page_previews=True, can_send_polls=True, can_invite_users=True))
    except: pass
    clear_chat_ban(message.chat.id, target.id)
    response = mod_action_text("✅", "Разбан", mention(target), mention(message.from_user))
    await message.reply(response, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@mod_cmd("мут", allow_args=True)
async def mute_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
        return await message.reply(f"{em('cross', '❌')} Максимум 366 дней.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Не могу найти юзера.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    reason = None
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        r = parts[1].strip()
        if r: reason = r
    try:
        until = datetime.now() + timedelta(seconds=duration_seconds)
        await bot.restrict_chat_member(message.chat.id, target.id,
            permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
        add_chat_mute(message.chat.id, target.id, reason or "без причины", message.from_user.id, until.isoformat())
        response = mod_action_text("🔇", "Мут", mention(target), mention(message.from_user), duration_text, reason)
        await message.reply(response, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        await message.reply(mod_error_text("Ошибка мута", f"<code>{e}</code>"), parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@mod_cmd("размут", allow_args=True)
async def unmute_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Не могу найти юзера.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        await bot.restrict_chat_member(message.chat.id, target.id, permissions=types.ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        clear_chat_mute(message.chat.id, target.id)
        response = mod_action_text("🔈", "Размут", mention(target), mention(message.from_user))
        await message.reply(response, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        await message.reply(mod_error_text("Ошибка размута", f"<code>{e}</code>"), parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@mod_cmd("кик", allow_args=True)
async def kick_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Не могу найти юзера.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if get_rank(message.chat.id, target.id) >= get_rank(message.chat.id, message.from_user.id):
        if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
        response = mod_action_text("👢", "Кик", mention(target), mention(message.from_user))
        await message.reply(response, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        await message.reply(mod_error_text("Ошибка кика", f"<code>{e}</code>"), parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


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
@cmd("пин", allow_args=True, args_pattern=r"^(тихо|silent|s|тих)$")
@cmd("закрепить", allow_args=True, args_pattern=r"^(тихо|silent|s|тих)$")
async def pin_message_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        if not await is_tg_admin(message.chat.id, message.from_user.id):
            return await message.reply(f"{em('cross', '❌')} Нет прав.", disable_web_page_preview=True, **_reply_kwargs(message))
    if not message.reply_to_message:
        return await message.reply("📌 Ответьте на сообщение.", disable_web_page_preview=True, **_reply_kwargs(message))
    args = message.text.split()
    silent = len(args) >= 2 and args[1].lower() in ["тихо", "silent", "s", "тих"]
    try:
        await bot.pin_chat_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id, disable_notification=silent)
        try: await message.delete()
        except: pass
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} {e}", disable_web_page_preview=True, **_reply_kwargs(message))


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
        await message.reply(f"{em('check', '✅')} Готово.", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} {e}", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= НАСТРОЙКИ ВАРНОВ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*варн\s+(лимит|исход|наказание|настройки|статус|инфо|settings)\b', m.text.strip(), re.IGNORECASE))
async def warn_settings_cmd(message: types.Message):
    chat_id = message.chat.id; user_id = message.from_user.id
    is_creator = False
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        is_creator = (m.status == "creator")
    except: pass
    is_allowed = (is_creator or user_id == OWNER_ID or is_coowner(user_id) or has_agent_rank(user_id, 1)
                  or has_permission(chat_id, user_id, 3) or await is_tg_admin(chat_id, user_id))
    if not is_allowed:
        return await message.reply(f"{em('cross', '❌')} Нужен <b>Мл. Админ (3+)</b>, ТГ-админ или агент.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    args = message.text.split(maxsplit=2)
    if len(args) < 2: return
    sub = args[1].lower().strip()
    if sub in ["лимит", "limit"]:
        if len(args) < 3 or not args[2].strip().isdigit():
            limit, action, dur_text, dur_sec = get_warn_settings(chat_id)
            return await message.reply(f"📌 <b>Формат:</b> <code>.варн лимит 5</code>\n📊 Сейчас: <b>{limit}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        new_limit = int(args[2].strip())
        if new_limit < 1 or new_limit > 20:
            return await message.reply("❌ Лимит от <b>1</b> до <b>20</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        set_warn_setting(chat_id, "warn_limit", new_limit)
        return await message.reply(f"{em('check', '✅')} <b>Лимит варнов:</b> <b>{new_limit}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["исход", "наказание"]:
        rest = message.text.split(maxsplit=3)
        if len(rest) < 3:
            limit, action, dur_text, dur_sec = get_warn_settings(chat_id)
            action_name = {"mute": "🔇 Мут", "ban": "🚫 Бан", "kick": "👢 Кик"}.get(action, action)
            return await message.reply(
                f"⚙️ <b>Исход варнов</b>\n\n📊 Лимит: <b>{limit}</b>\n⚔️ Сейчас: <b>{action_name}</b> на <b>{dur_text}</b>\n\n"
                f"📌 <b>Формат:</b>\n<code>.варн исход мут 30 минут</code>\n<code>.варн исход бан 1 час</code>\n<code>.варн исход мут навсегда</code>\n<code>.варн исход бан навсегда</code>\n<code>.варн исход кик</code>",
                parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
            )
        action_raw = rest[2].lower().strip()
        if action_raw in ["кик", "kick"]:
            set_warn_setting(chat_id, "action", "kick")
            set_warn_setting(chat_id, "duration_text", "кик")
            set_warn_setting(chat_id, "duration_seconds", 0)
            return await message.reply(f"{em('check', '✅')} Исход варнов: <b>👢 Кик</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        action_map = {"мут": "mute", "mute": "mute", "бан": "ban", "ban": "ban"}
        if action_raw not in action_map:
            return await message.reply("❌ Действие: <code>мут</code>, <code>бан</code> или <code>кик</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if len(rest) < 4:
            return await message.reply("📌 Укажи время или <code>навсегда</code>:\n<code>.варн исход мут 30 минут</code>\n<code>.варн исход бан навсегда</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        action_db = action_map[action_raw]
        duration_text = rest[3].strip()
        seconds, text = parse_warn_duration(duration_text)
        if seconds is False:
            return await message.reply("❌ Не понял время.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        set_warn_setting(chat_id, "action", action_db)
        set_warn_setting(chat_id, "duration_text", text)
        if seconds is None: set_warn_setting(chat_id, "duration_seconds", 0)
        else: set_warn_setting(chat_id, "duration_seconds", seconds)
        action_name = "🔇 Мут" if action_db == "mute" else "🚫 Бан"
        return await message.reply(f"{em('check', '✅')} Исход варнов: <b>{action_name}</b> на <b>{text}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["настройки", "статус", "инфо", "settings"]:
        limit, action, dur_text, dur_sec = get_warn_settings(chat_id)
        action_name = {"mute": "🔇 Мут", "ban": "🚫 Бан", "kick": "👢 Кик"}.get(action, action)
        outcome = f"<b>{action_name}</b>" if action == "kick" else f"<b>{action_name}</b> на <b>{dur_text}</b>"
        return await message.reply(
            f"⚙️ <b>Настройки варнов</b>\n\n📊 Лимит: <b>{limit}</b>\n⚔️ Исход: {outcome}\n\n"
            f"📌 <code>.варн лимит 5</code>\n📌 <code>.варн исход мут 30 минут</code>\n📌 <code>.варн исход бан навсегда</code>\n📌 <code>.варн исход кик</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )


# ================= ВАРНЫ =================
@mod_cmd("варн", allow_args=True)
async def warn_cmd(message: types.Message):
    actor_id = message.from_user.id
    actor_rank = get_rank(message.chat.id, actor_id)
    if actor_rank < 1:
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте или укажите @user / ID", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target_rank = get_rank(message.chat.id, target.id)
    if actor_rank < 5 and target_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    reason = None
    parts = message.text.split('\n', 1)
    if len(parts) > 1:
        r = parts[1].strip()
        if r: reason = r
    add_warn(target.id, message.chat.id, reason or "без причины", actor_id)
    warns_count = count_warns(target.id, message.chat.id)
    warn_limit, action, dur_text, dur_sec = get_warn_settings(message.chat.id)
    first_msg = f"❗️ <b>Выдано предупреждение {warns_count}/{warn_limit}</b>\n\n🎯 Кому: {mention(target)}\n"
    if reason: first_msg += f"💬 Причина: <i>{reason}</i>\n"
    first_msg += f"👮 От: {mention(message.from_user)}"
    await message.reply(first_msg, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if warns_count >= warn_limit:
        try:
            if action == "mute":
                until = datetime.now() + timedelta(seconds=dur_sec) if dur_sec and dur_sec > 0 else None
                await bot.restrict_chat_member(message.chat.id, target.id,
                    permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
                punishment = (f"🔇 <b>Мут</b>\n\n👤 Пользователь: {mention(target)}\n⏱ Срок: <b>{dur_text}</b>\n"
                              f"📝 Причина: <i>лимит варнов</i>\n👮 Модератор: {mention(message.from_user)}")
            elif action == "ban":
                until = datetime.now() + timedelta(seconds=dur_sec) if dur_sec and dur_sec > 0 else None
                await bot.ban_chat_member(message.chat.id, target.id, until_date=until)
                add_chat_ban(message.chat.id, target.id, "лимит варнов", actor_id, until.isoformat() if until else None)
                punishment = (f"🚫 <b>Бан</b>\n\n👤 Пользователь: {mention(target)}\n⏱ Срок: <b>{dur_text}</b>\n"
                              f"📝 Причина: <i>лимит варнов</i>\n👮 Модератор: {mention(message.from_user)}")
            elif action == "kick":
                await bot.ban_chat_member(message.chat.id, target.id)
                await bot.unban_chat_member(message.chat.id, target.id)
                punishment = (f"👢 <b>Кик</b>\n\n👤 Пользователь: {mention(target)}\n"
                              f"📝 Причина: <i>лимит варнов</i>\n👮 Модератор: {mention(message.from_user)}")
            else:
                punishment = f"⚔️ <b>{action}</b> — {mention(target)}"
            clear_warns(target.id, message.chat.id)
            await message.reply(punishment, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        except Exception as e:
            print(f"⚠️ варн-исход ошибка: {e}")


@mod_cmd("варны", allow_args=True)
async def warns_list_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 1):
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, reason, warned_at FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY warned_at DESC", (target.id, message.chat.id))
        warns = c.fetchall()
    warn_limit, _, _, _ = get_warn_settings(message.chat.id)
    if not warns:
        return await message.reply(f"{em('check', '✅')} Нет варнов.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"{em('pencil', '✏️')} <b>Варны {mention(target)}:</b> ({len(warns)}/{warn_limit})\n\n"
    for i, (_, reason, warned_at) in enumerate(warns, 1):
        text += f"{i}. {reason}\n   {em('calendar', '🗓')} {warned_at[:10]}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@mod_cmd("снятьварн", allow_args=True)
async def unwarn_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 2):
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target: return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM warns WHERE id = (SELECT id FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY warned_at DESC LIMIT 1)",
                  (target.id, message.chat.id))
        conn.commit()
    warn_limit, _, _, _ = get_warn_settings(message.chat.id)
    await message.reply(f"{em('check', '✅')} Варн снят. Осталось: {count_warns(target.id, message.chat.id)}/{warn_limit}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@mod_cmd("сбросварнов", allow_args=True)
async def clear_warns_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target: return
    count = count_warns(target.id, message.chat.id)
    clear_warns(target.id, message.chat.id)
    await message.reply(f"♻️ Сброшено варнов: {count}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= НАКАЗАНИЯ / БАНЫ =================
@cmd("наказания", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
async def show_punishments(message: types.Message):
    chat_id = message.chat.id
    actor_id = message.from_user.id
    is_allowed = (
        actor_id == OWNER_ID or is_coowner(actor_id) or has_agent_rank(actor_id, 1)
        or await is_tg_admin(chat_id, actor_id) or has_permission(chat_id, actor_id, 2)
    )
    if not is_allowed:
        return await message.reply(f"{em('cross', '❌')} Нужен <b>Ст. Модератор (2+)</b>, ТГ-админ или агент Mos.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
        if info:
            reason, added_by, added_at = info
            blocks.append(f"{em('shield', '🛡')} <b>В антиспаме MOS</b>\n📝 Причина: <i>{reason}</i>")
    if not blocks:
        return await message.reply(f"{em('check', '✅')} {mention(target)} чист.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"{em('calendar', '🗓')} <b>Наказания {mention(target)}</b>\n\n" + "\n\n".join(blocks)
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("баны", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
async def show_bans(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id) and not has_agent_rank(message.from_user.id, 1):
        return
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply(f"{em('cross', '❌')} Ответьте.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    user_id = target.id
    name = user_link(user_id, target.first_name, target.username)
    bans = get_all_user_bans(user_id)

    was_antispam_ever = False
    for b in bans:
        if len(b) > 5 and b[5] == 1:
            was_antispam_ever = True
            break

    text = f"{em('ban', '🚫')} <b>Баны {name}</b>\n{em('id', '🆔')} <code>{user_id}</code>\n\n"

    if is_in_antispam(user_id):
        info = get_antispam_info(user_id)
        if info:
            reason, added_by, added_at = info
            if added_by and added_by != 0:
                try:
                    u = await bot.get_chat(added_by); who = user_link(added_by, u.first_name, u.username)
                except: who = f"<code>{added_by}</code>"
            else: who = "<i>автоматически</i>"
            text += (f"☢️ <b>В АНТИСПАМЕ</b>\n📝 Причина: <i>{reason}</i>\n"
                     f"👮 Добавил: {who}\n🗓 Когда: <b>{_fmt_added_dt(added_at)}</b>\n\n")
        history = get_antispam_history(user_id, limit=10)
        if history:
            text += f"📜 <b>История антиспама:</b>\n"
            for h_action, h_reason, h_admin, h_at in history:
                icon = "➕" if h_action == "add" else "➖"
                label = "Добавлен" if h_action == "add" else "Снят"
                if h_admin and h_admin != 0:
                    try:
                        u2 = await bot.get_chat(h_admin); h_who = user_link(h_admin, u2.first_name, u2.username)
                    except: h_who = f"<code>{h_admin}</code>"
                else: h_who = "<i>авто</i>"
                text += f"{icon} {label}: {h_who} — <b>{_fmt_added_dt(h_at)}</b>\n"
                if h_reason: text += f"    📝 <i>{h_reason}</i>\n"
            text += "\n"
    elif was_antispam_ever:
        text += f"☢️ <b>Ранее в антиспаме</b> (уже снят)\n"
        history = get_antispam_history(user_id, limit=10)
        if history:
            text += f"\n📜 <b>История антиспама:</b>\n"
            for h_action, h_reason, h_admin, h_at in history:
                icon = "➕" if h_action == "add" else "➖"
                label = "Добавлен" if h_action == "add" else "Снят"
                if h_admin and h_admin != 0:
                    try:
                        u2 = await bot.get_chat(h_admin); h_who = user_link(h_admin, u2.first_name, u2.username)
                    except: h_who = f"<code>{h_admin}</code>"
                else: h_who = "<i>авто</i>"
                text += f"{icon} {label}: {h_who} — <b>{_fmt_added_dt(h_at)}</b>\n"
            text += "\n"
    else:
        text += f"{em('check', '✅')} <b>Не в антиспаме</b>\n\n"

    text += f"{em('stats', '📊')} Всего записей: <b>{len(bans)}</b>\n\n"

    for i, b in enumerate(bans[:10], 1):
        chat_id, reason, banned_by, banned_at, until_date = b[0], b[1], b[2], b[3], b[4]
        was_as = b[5] if len(b) > 5 else 0
        try:
            if banned_by and banned_by != 0:
                u2 = await bot.get_chat(banned_by); bwho = user_link(banned_by, u2.first_name, u2.username)
            else: bwho = "<i>авто</i>"
        except: bwho = f"<code>{banned_by}</code>"
        as_tag = " ☢️" if was_as else ""
        if until_date:
            try:
                until_dt = datetime.fromisoformat(until_date.replace("Z", ""))
                if until_dt > datetime.now():
                    dur = int((until_dt - datetime.now()).total_seconds())
                    if dur >= 86400: dur_str = f"ещё {dur // 86400} дн."
                    elif dur >= 3600: dur_str = f"ещё {dur // 3600} ч."
                    elif dur >= 60: dur_str = f"ещё {dur // 60} мин."
                    else: dur_str = f"ещё {dur} сек."
                    until_str = f" | ⏱ {dur_str}"
                else: until_str = " | <i>истёк</i>"
            except: until_str = ""
        else: until_str = " | <i>навсегда</i>"
        text += (f"<b>{i}.</b> 📝 {reason}{as_tag}\n   👮 {bwho}\n"
                 f"   {em('calendar', '🗓')} {_fmt_added_dt(banned_at)}{until_str}\n\n")
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))# ================= +АС / -АС =================
async def _check_as_perms(message) -> bool:
    user_id = message.from_user.id
    if user_id == OWNER_ID or is_coowner(user_id): return True
    if has_agent_rank(user_id, 1): return True
    return False


async def _parse_as_command(message):
    txt = message.text.strip()
    body = re.sub(r'^[.\/!+-]?\s*\+ас\b', '', txt, flags=re.IGNORECASE).strip()
    mode = "as"
    if re.match(r'^кик\s+игнор\b', body, re.IGNORECASE):
        body = re.sub(r'^кик\s+игнор\b', '', body, count=1, flags=re.IGNORECASE).strip()
        mode = "kick_ignore"
    elif re.match(r'^кик\b', body, re.IGNORECASE):
        body = re.sub(r'^кик\b', '', body, count=1, flags=re.IGNORECASE).strip()
        mode = "kick"
    elif re.match(r'^игнор\b', body, re.IGNORECASE):
        body = re.sub(r'^игнор\b', '', body, count=1, flags=re.IGNORECASE).strip()
        mode = "ignore"
    target = None
    rest_for_reason = body
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        parts = body.split(maxsplit=1)
        if parts:
            first = parts[0]
            if first.startswith('@') or first.lstrip('-').isdigit():
                try:
                    if first.startswith('@'): target = await bot.get_chat(first)
                    else: target = await bot.get_chat(int(first))
                except:
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        c = conn.cursor()
                        if first.startswith('@'):
                            c.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (first[1:],))
                        else:
                            c.execute("SELECT user_id FROM users WHERE user_id = ?", (int(first),))
                        row = c.fetchone()
                    if row:
                        try: target = await bot.get_chat(row[0])
                        except: target = _FakeUser(row[0], f"ID {row[0]}")
                if target:
                    rest_for_reason = parts[1] if len(parts) > 1 else ""
    reason = rest_for_reason.strip()[:200] or "без причины"
    return target, mode, reason


def _as_nick_link(target) -> str:
    name = html_escape_text(target.first_name or "Пользователь")
    username = getattr(target, "username", None)
    if username: return f'<a href="https://t.me/{username}">{name}</a>'
    return f'<a href="tg://user?id={target.id}">{name}</a>'


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*\+ас(?:\s|$)', m.text.strip(), re.IGNORECASE))
async def as_command_handler(message: types.Message):
    try:
        if not await _check_as_perms(message): return
        target, mode, reason = await _parse_as_command(message)
        if not target:
            return await message.reply(
                "📌 <b>Формат:</b>\n"
                "• <code>+ас [@user | ID] причина</code> — только в антиспам\n"
                "• <code>+ас игнор [@user | ID] причина</code> — антиспам + игнор\n"
                "• <code>+ас кик [@user | ID] причина</code> — антиспам + кик\n"
                "• <code>+ас кик игнор [@user | ID] причина</code> — всё вместе\n"
                "💡 Можно ответом на сообщение юзера.",
                parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
            )
        if target.id == OWNER_ID or is_coowner(target.id):
            return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if getattr(target, "is_bot", False):
            return await message.reply(f"{em('cross', '❌')} Нельзя на бота.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        register_user(target.id, target.first_name, getattr(target, "username", "") or "")
        actor_id = message.from_user.id
        add_user_to_antispam(target.id, reason, actor_id)
        kicked_chats = []
        if mode in ("kick", "kick_ignore"):
            if is_antispam_enabled(message.chat.id):
                try:
                    until = datetime.now() + timedelta(seconds=90)
                    await bot.ban_chat_member(message.chat.id, target.id, until_date=until)
                    add_chat_ban(message.chat.id, target.id, f"АС: {reason}", actor_id, until.isoformat(), was_antispam=1)
                    kicked_chats.append(message.chat.id)
                except Exception as e:
                    print(f"⚠️ +ас кик в текущем чате: {e}")
            for cid in get_all_known_chats():
                if cid == message.chat.id: continue
                try:
                    if not is_antispam_enabled(cid): continue
                except: continue
                try:
                    until = datetime.now() + timedelta(seconds=90)
                    await bot.ban_chat_member(cid, target.id, until_date=until)
                    add_chat_ban(cid, target.id, f"АС: {reason}", actor_id, until.isoformat(), was_antispam=1)
                    kicked_chats.append(cid)
                except: pass
        if mode in ("ignore", "kick_ignore"):
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                for cid in get_all_known_chats():
                    try:
                        c.execute("INSERT OR REPLACE INTO ignore_list (user_id, chat_id, reason, added_by) VALUES (?, ?, ?, ?)",
                                  (target.id, cid, "АС+игнор", actor_id))
                    except: pass
                c.execute("INSERT OR REPLACE INTO ignore_list (user_id, chat_id, reason, added_by) VALUES (?, ?, ?, ?)",
                          (target.id, message.chat.id, "АС+игнор", actor_id))
                conn.commit()
            add_bot_ignore(target.id, actor_id)
        nick = _as_nick_link(target)
        if mode == "as":
            lines = [f"{em('check', '✅')} {nick} занесён в базу <b>антиспам-Mos</b>", "", f"💬 Причина: <i>{reason}</i>"]
        elif mode == "ignore":
            lines = [f"{em('check', '✅')} {nick} занесён в базу <b>антиспам-Mos</b> + <b>игнор</b>",
                     "🚷 <b>Бот полностью игнорирует пользователя</b>", "", f"💬 Причина: <i>{reason}</i>"]
        elif mode == "kick":
            lines = [f"{em('check', '✅')} {nick} занесён в базу <b>антиспам-Mos</b> (кик)",
                     f"👢 Кикнут из <b>{len(kicked_chats)}</b> чатов", "", f"💬 Причина: <i>{reason}</i>"]
            if not kicked_chats: lines.append("\n⚠️ Не удалось кикнуть ни из одного чата")
        else:
            lines = [f"{em('check', '✅')} {nick} занесён в базу <b>антиспам-Mos</b> (кик + игнор)",
                     f"👢 Кикнут из <b>{len(kicked_chats)}</b> чатов",
                     "🚷 <b>Бот полностью игнорирует пользователя</b>",
                     "", f"💬 Причина: <i>{reason}</i>"]
            if not kicked_chats: lines.append("\n⚠️ Не удалось кикнуть ни из одного чата")
        await message.reply("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        print(f"❌ +АС ошибка: {traceback.format_exc()}")
        try:
            await message.reply(f"❌ Ошибка +ас: <code>{type(e).__name__}: {e}</code>", parse_mode="HTML", **_reply_kwargs(message))
        except: pass


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*-ас(\s|$)', m.text.strip(), re.IGNORECASE))
async def as_remove_handler(message: types.Message):
    try:
        if not await _check_as_perms(message): return
        body = re.sub(r'^[.\/!+-]?\s*-ас\b', '', message.text.strip(), flags=re.IGNORECASE).strip()
        mode = "as"
        if re.match(r'^игнор\b', body, re.IGNORECASE):
            mode = "as_ignore"
            body = body[5:].strip()
        target = None
        if message.reply_to_message:
            target = message.reply_to_message.from_user
        else:
            parts = body.split(maxsplit=1)
            if parts:
                first = parts[0]
                try:
                    if first.startswith('@'): target = await bot.get_chat(first)
                    elif first.lstrip('-').isdigit(): target = await bot.get_chat(int(first))
                except:
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        c = conn.cursor()
                        if first.startswith('@'):
                            c.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (first[1:],))
                        else:
                            c.execute("SELECT user_id FROM users WHERE user_id = ?", (int(first),))
                        row = c.fetchone()
                    if row:
                        try: target = await bot.get_chat(row[0])
                        except: target = _FakeUser(row[0], f"ID {row[0]}")
        if not target:
            return await message.reply(
                "📌 <b>Формат:</b>\n• <code>-ас</code> ответом\n• <code>-ас игнор</code>\n• <code>-ас @user</code>\n• <code>-ас 123456789</code>",
                parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
            )
        actor_id = message.from_user.id
        was_in_antispam = is_in_antispam(target.id)
        if mode == "as":
            removed = remove_user_from_antispam(target.id, removed_by=actor_id)
            if not was_in_antispam:
                return await message.reply(f"ℹ️ {mention(target)} не был(а) в антиспаме.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
            await message.reply(
                f"✅ <b>Снят с антиспама</b>\n\n👤 Пользователь: {mention(target)}\n👮 Агент: {mention(message.from_user)}",
                parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
            )
        elif mode == "as_ignore":
            remove_bot_ignore(target.id)
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM ignore_list WHERE user_id = ?", (target.id,))
                conn.commit()
            remove_user_from_antispam(target.id, removed_by=actor_id)
            await message.reply(
                f"✅ <b>Снят с антиспама и игнора</b>\n\n👤 Пользователь: {mention(target)}\n👮 Агент: {mention(message.from_user)}",
                parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
            )
    except Exception as e:
        print(f"❌ -АС ошибка: {traceback.format_exc()}")
        try:
            await message.reply(f"❌ Ошибка -ас: <code>{type(e).__name__}: {e}</code>", parse_mode="HTML", **_reply_kwargs(message))
        except: pass


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антиспам", "+ антиспам"])
async def enable_antispam_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    user_id = message.from_user.id; chat_id = message.chat.id
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(chat_id, user_id, 3) and not has_agent_rank(user_id, 1):
        if not await is_tg_admin(chat_id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен <b>Мл. Админ (3+)</b>, ТГ-админ, агент или создатель чата.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if is_antispam_enabled(chat_id):
        return await message.reply("ℹ️ Антиспам уже включён.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_antispam_enabled(chat_id, True)
    await message.reply(f"{em('check', '✅')} <b>Антиспам включён!</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антиспам", "- антиспам"])
async def disable_antispam_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    user_id = message.from_user.id; chat_id = message.chat.id
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if user_id == OWNER_ID or is_coowner(user_id): is_creator = True
    if not is_creator and not has_permission(chat_id, user_id, 3) and not has_agent_rank(user_id, 1):
        if not await is_tg_admin(chat_id, user_id):
            return await message.reply(f"{em('cross', '❌')} Нужен <b>Мл. Админ (3+)</b>, ТГ-админ, агент или создатель чата.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not is_antispam_enabled(chat_id):
        return await message.reply("ℹ️ Антиспам уже выключен.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_antispam_enabled(chat_id, False)
    unban_count = 0
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT user_id FROM chat_bans 
                     WHERE chat_id = ? AND (until_date IS NULL OR until_date > ?)
                     AND LOWER(reason) LIKE '%ас%'""",
                  (chat_id, datetime.now().isoformat()))
        rows = c.fetchall()
    for (uid,) in rows:
        try:
            await bot.unban_chat_member(chat_id, uid)
            clear_chat_ban(chat_id, uid)
            unban_count += 1
        except: pass
    await message.reply(
        f"{em('cross', '❌')} <b>Антиспам выключен!</b>"
        + (f"\n\n♻️ Снято АС-банов: <b>{unban_count}</b>" if unban_count > 0 else ""),
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("антиспам статус")
@cmd("ас статус")
async def antispam_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    enabled = is_antispam_enabled(message.chat.id)
    status = "🟢 включён" if enabled else "🔴 выключен"
    await message.reply(
        f"☢️ <b>Антиспам</b>: {status}\n\n"
        f"📌 Включить: <code>+антиспам</code>\n📌 Выключить: <code>-антиспам</code>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("ас список")
@cmd("антиспам")
async def as_list_cmd(message: types.Message):
    if not await _check_as_perms(message): return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, reason, added_by, added_at FROM antispam ORDER BY added_at DESC LIMIT 50")
        rows = c.fetchall()
    if not rows:
        return await message.reply("📭 Антиспам пуст.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"☢️ <b>Антиспам</b> ({len(rows)}):\n\n"
    for i, (uid, reason, added_by, added_at) in enumerate(rows, 1):
        try:
            u = await bot.get_chat(uid); name = user_link(uid, u.first_name, u.username)
        except: name = f"<code>{uid}</code>"
        if added_by and added_by != 0:
            try:
                u2 = await bot.get_chat(added_by); who = user_link(added_by, u2.first_name, u2.username)
            except: who = f"<code>{added_by}</code>"
        else: who = "<i>авто</i>"
        text += f"{i}. {name}\n    📝 <i>{reason}</i>\n    👮 {who}\n    🗓 {_fmt_added_dt(added_at)}\n\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= АГЕНТЫ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+агент"))
async def add_agent_cmd(message: types.Message):
    actor_id = message.from_user.id
    if actor_id != OWNER_ID and not is_coowner(actor_id) and not has_agent_rank(actor_id, 4): return
    args = message.text.split()
    rank = 1; target_arg = None; target_from_reply = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_from_reply = message.reply_to_message.from_user
        for a in args[1:]:
            if a.isdigit() and 1 <= int(a) <= 4:
                rank = int(a); break
    else:
        for a in args[1:]:
            clean = a.strip().rstrip('.,;:!?')
            if not clean: continue
            if clean.isdigit() and 1 <= int(clean) <= 4 and len(clean) <= 2:
                rank = int(clean); continue
            if target_arg is None: target_arg = clean
    if target_from_reply:
        target = target_from_reply
    elif target_arg:
        try:
            if target_arg.startswith('@'): target = await bot.get_chat(target_arg)
            elif target_arg.lstrip('-').isdigit():
                if len(target_arg.lstrip('-')) < 6:
                    return await message.reply(f"{em('cross', '❌')} <b>Слишком короткий ID.</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
                target = await bot.get_chat(int(target_arg))
        except Exception:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                if target_arg.startswith('@'): c.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (target_arg[1:],))
                else: c.execute("SELECT user_id FROM users WHERE user_id = ?", (int(target_arg),))
                row = c.fetchone()
            if row:
                try: target = await bot.get_chat(row[0])
                except Exception: target = _FakeUser(row[0], f"ID {row[0]}")
            else: target = None
    else: target = None
    if not target:
        return await message.reply("📌 <b>Формат:</b>\n• <code>+агент 2</code> (ответом)\n• <code>+агент @user 2</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if target.id == OWNER_ID: return
    if rank not in [1, 2, 3, 4]:
        return await message.reply(f"{em('cross', '❌')} Ранг 1-4.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    register_user(target.id, target.first_name, getattr(target, "username", "") or "")
    set_agent_rank(target.id, rank, actor_id)
    rank_name = AGENT_RANKS.get(rank, "🛡 Агент")
    try:
        await bot.send_message(target.id,
            f"🛡 <b>Вам выдана должность агента Mos!</b>\n\n👤 Вы: {mention(target)}\n🎖 Ранг: <b>{rank_name}</b>\n👮 Выдал: {mention(message.from_user)}",
            parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"⚠️ Не смог написать в ЛС {target.id}: {e}")
    await message.reply(f"{em('check', '✅')} {mention(target)} теперь <b>{rank_name}</b>!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("-агент"))
async def remove_agent_cmd(message: types.Message):
    actor_id = message.from_user.id
    if actor_id != OWNER_ID and not is_coowner(actor_id) and not has_agent_rank(actor_id, 4): return
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split(); target = None
        if len(args) >= 2:
            clean = args[1].strip().rstrip('.,;:!?')
            try:
                if clean.startswith('@'): target = await bot.get_chat(clean)
                elif clean.lstrip('-').isdigit() and len(clean.lstrip('-')) >= 6: target = await bot.get_chat(int(clean))
            except Exception:
                with sqlite3.connect(DATABASE_PATH) as conn:
                    c = conn.cursor()
                    if clean.startswith('@'): c.execute("SELECT user_id, first_name, username FROM users WHERE LOWER(username) = LOWER(?)", (clean[1:],))
                    else: c.execute("SELECT user_id, first_name, username FROM users WHERE user_id = ?", (int(clean) if clean.lstrip('-').isdigit() else 0,))
                    row = c.fetchone()
                if row: target = _FakeUser(row[0], row[1], row[2])
    if not target: return
    remove_agent(target.id)
    try:
        await bot.send_message(target.id,
            f"{em('cross', '❌')} <b>Вы больше не агент Mos.</b>\n\n👮 Снял: {mention(message.from_user)}",
            parse_mode="HTML", disable_web_page_preview=True)
    except: pass
    await message.reply(f"{em('cross', '❌')} {mention(target)} не агент.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("агенты")
async def list_agents_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID and not is_coowner(user_id) and not has_agent_rank(user_id, 1): return
    hidden_agents = set(get_hidden_agents())
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT a.user_id, COALESCE(r.rank, 1) FROM agents a
                     LEFT JOIN agent_ranks r ON r.user_id = a.user_id
                     ORDER BY COALESCE(r.rank, 1) DESC""")
        rows = c.fetchall()
    visible_rows = rows if (user_id == OWNER_ID or is_coowner(user_id)) else [(uid, rank) for uid, rank in rows if uid not in hidden_agents]
    if not visible_rows:
        return await message.reply("📭 Нет агентов.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"{em('shield', '🛡')} <b>Агенты Mos:</b>\n\n"
    for uid, rank in visible_rows:
        try:
            u = await bot.get_chat(uid); name = user_link(uid, u.first_name, u.username)
        except: name = f"ID {uid}"
        hidden_mark = " 🙈" if ((user_id == OWNER_ID or is_coowner(user_id)) and uid in hidden_agents) else ""
        text += f"{AGENT_RANKS.get(rank, '🛡 Агент')} — {name}{hidden_mark}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-помощь")
async def hide_from_help_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_agent(user_id) and user_id != OWNER_ID and not is_coowner(user_id): return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO hidden_agents (user_id) VALUES (?)", (user_id,))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Вы скрыты.\n↩️ <code>+помощь</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "+помощь")
async def show_in_help_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_agent(user_id) and user_id != OWNER_ID and not is_coowner(user_id): return
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM hidden_agents WHERE user_id = ?", (user_id,))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Вы в списке.\n🙈 <code>-помощь</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))# ================= СОВЛАДЕЛЕЦ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*\+совладелец\b', m.text.strip(), re.IGNORECASE))
async def add_coowner_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    target, arg = await resolve_target(message)
    if not target:
        return await message.reply("📌 <b>Формат:</b>\n• <code>+совладелец</code> (ответом)\n• <code>+совладелец ID</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if target.id == OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Владелец и так владелец.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if getattr(target, "is_bot", False):
        return await message.reply(f"{em('cross', '❌')} Нельзя на бота.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if is_coowner(target.id):
        return await message.reply(f"ℹ️ {mention(target)} уже совладелец.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    register_user(target.id, target.first_name, getattr(target, "username", "") or "")
    add_coowner(target.id, message.from_user.id)
    try:
        await bot.send_message(target.id,
            f"⚜️ <b>Вы теперь совладелец бота Mos!</b>\n\n👤 Вы: {mention(target)}\n👮 Назначил: {mention(message.from_user)}",
            parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e: print(f"⚠️ Не смог написать в ЛС {target.id}: {e}")
    await message.reply(f"{em('check', '✅')} <b>Назначен совладелец!</b>\n\n👤 {mention(target)}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*-совладелец\b', m.text.strip(), re.IGNORECASE))
async def remove_coowner_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    target, arg = await resolve_target(message)
    if not target:
        return await message.reply("📌 <b>Формат:</b>\n• <code>-совладелец</code> (ответом)\n• <code>-совладелец ID</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if target.id == OWNER_ID:
        return await message.reply(f"{em('cross', '❌')} Владельца снять нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not remove_coowner(target.id):
        return await message.reply(f"ℹ️ {mention(target)} не является совладельцем.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        await bot.send_message(target.id, f"{em('cross', '❌')} <b>Вы больше не совладелец бота Mos.</b>", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e: print(f"⚠️ Не смог написать в ЛС {target.id}: {e}")
    await message.reply(f"{em('check', '✅')} {mention(target)} больше не совладелец.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("совладельцы")
async def list_coowners_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id): return
    rows = get_coowners()
    if not rows:
        return await message.reply("📭 Нет совладельцев.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = "⚜️ <b>Совладельцы бота:</b>\n\n"
    for i, (uid, added_at) in enumerate(rows, 1):
        try:
            u = await bot.get_chat(uid); name = user_link(uid, u.first_name, u.username)
        except: name = f"<code>{uid}</code>"
        text += f"{i}. {name} — <i>{_fmt_added_dt(added_at)}</i>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ПОВЫСИТЬ / ПОНИЗИТЬ =================
@cmd("повысить", allow_args=True)
async def promote_cmd(message: types.Message):
    chat_id = message.chat.id; actor_id = message.from_user.id
    is_creator = False
    try:
        m = await bot.get_chat_member(chat_id, actor_id)
        is_creator = (m.status == "creator")
    except: pass
    actor_rank = get_rank(chat_id, actor_id)
    if not is_creator and actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("📌 <code>.повысить @user 3</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if target.id == actor_id:
        return await message.reply(f"{em('cross', '❌')} <b>Нельзя повышать себя.</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    current_rank = get_rank(chat_id, target.id)
    args = message.text.split()
    new_rank = current_rank + 1
    for a in args[1:]:
        if a.isdigit(): new_rank = int(a); break
    if new_rank > 5: new_rank = 5
    if not is_creator and new_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя ≥ твоего.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_rank(chat_id, target.id, new_rank, actor_id)
    await message.reply(f"🏆 {mention(target)}: {rank_display(chat_id, new_rank)}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("понизить", allow_args=True)
async def demote_cmd(message: types.Message):
    chat_id = message.chat.id; actor_id = message.from_user.id
    is_creator = False
    try:
        m = await bot.get_chat_member(chat_id, actor_id)
        is_creator = (m.status == "creator")
    except: pass
    actor_rank = get_rank(chat_id, actor_id)
    if not is_creator and actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("📌 <code>.понизить @user 1</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if target.id == actor_id:
        return await message.reply(f"{em('cross', '❌')} <b>Нельзя понижать себя.</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    current_rank = get_rank(chat_id, target.id)
    args = message.text.split()
    new_rank = current_rank - 1
    for a in args[1:]:
        if a.isdigit(): new_rank = int(a); break
    if new_rank < 0: new_rank = 0
    if not is_creator and new_rank >= actor_rank:
        return await message.reply(f"{em('cross', '❌')} Нельзя ≥ твоего.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if new_rank == 0:
        remove_rank(chat_id, target.id)
        return await message.reply(f"📉 {mention(target)} разжалован.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_rank(chat_id, target.id, new_rank, actor_id)
    await message.reply(f"📉 {mention(target)}: {rank_display(chat_id, new_rank)}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("разжаловать", allow_args=True)
@cmd("снять", allow_args=True)
async def demote_all_cmd(message: types.Message):
    chat_id = message.chat.id; actor_id = message.from_user.id
    is_creator = False
    try:
        m = await bot.get_chat_member(chat_id, actor_id)
        is_creator = (m.status == "creator")
    except: pass
    actor_rank = get_rank(chat_id, actor_id)
    if not is_creator and actor_rank < 3:
        return await message.reply(f"{em('cross', '❌')} Нет прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target: return
    if target.id == actor_id:
        return await message.reply(f"{em('cross', '❌')} Себе нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    remove_rank(chat_id, target.id)
    await message.reply(f"{em('cross', '❌')} {mention(target)} разжалован.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("админы")
@cmd("кто админ")
@cmd("ктоадмин")
async def list_admins_cmd(message: types.Message):
    chat_id = message.chat.id
    admins = get_all_admins(chat_id)
    if not admins:
        return await message.reply("📭 <b>Нет модераторов</b>\n\nНазначить: <code>.повысить @user 1</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    admins_sorted = sorted(admins, key=lambda x: (-x[1], x[0]))
    grouped = {}
    for user_id, rank in admins_sorted:
        grouped.setdefault(rank, []).append(user_id)
    header = get_moderators_header(chat_id)
    text = f"<b>{header}</b>\n"
    counter = 0
    for rank in sorted(grouped.keys(), reverse=True):
        title = get_moderator_title(chat_id, rank, "plu")
        icon = RANK_ICONS.get(rank, "👤")
        text += f"\n<b>[{rank}] {icon} {title}</b>\n"
        for user_id in grouped[rank]:
            counter += 1
            try:
                user = await bot.get_chat(user_id); name = user_link(user_id, user.first_name, user.username)
            except:
                with sqlite3.connect(DATABASE_PATH) as conn:
                    c = conn.cursor()
                    c.execute("SELECT first_name, username FROM users WHERE user_id = ?", (user_id,))
                    r = c.fetchone()
                if r: name = user_link(user_id, r[0] or f"ID {user_id}", r[1])
                else: name = f"<b>ID {user_id}</b>"
            agent_icon = "👨‍💻 " if is_agent(user_id) else ""
            vip_emoji = get_vip_emoji(user_id) or ""
            vip_str = f" {vip_emoji}" if vip_emoji else ""
            text += f"{counter}. {agent_icon}{name}{vip_str}\n"
    await message.reply(text.strip(), parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= МОДЕРАТОРЫ (НАЗВАНИЯ) =================
@cmd("модераторы", allow_args=True)
@cmd("названия", allow_args=True)
@cmd("названия рангов", allow_args=True)
async def moderator_titles_cmd(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    is_creator = False
    try:
        m = await bot.get_chat_member(chat_id, message.from_user.id)
        is_creator = (m.status == "creator")
    except: pass
    if not is_creator and not has_permission(chat_id, message.from_user.id, 4) \
            and message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Нужен <b>Ст. Админ (4+)</b> или создатель.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    args = message.text.split(maxsplit=2)
    sub = args[1].lower().strip() if len(args) >= 2 else ""
    if not sub:
        titles = get_all_moderator_titles(chat_id)
        current_header = get_moderators_header(chat_id)
        text = "🏷 <b>Названия модераторов</b>\n\n"
        text += f"📌 <b>Заголовок</b>: {current_header}\n\n"
        text += "<i>Шаблон ранга: </i><code>и=...;р=...;д=...;т=...;мн=...</code>\n\n"
        for rank in range(6):
            t = titles[rank]
            icon = RANK_ICONS.get(rank, "👤")
            text += f"<b>{rank}</b> {icon} <b>{t['nom']}</b>\n"
            text += f"   и={t['nom']} | р={t['gen']} | д={t['dat']} | т={t['ins']} | мн={t['plu']}\n\n"
        text += (
            "📌 <b>Как менять ранг:</b>\n"
            "<code>.модераторы 3 и=Мл. Админ;р=Мл. Админа;д=Мл. Админу;т=Мл. Админом;мн=Мл. Админы</code>\n\n"
            "📌 <b>Как менять заголовок:</b>\n"
            "<code>.модераторы заголовок ⭐️ Вайберы этой беседы</code>\n\n"
            "📌 <b>Сброс:</b> <code>.модераторы сброс</code>"
        )
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["сброс", "reset"]:
        reset_moderator_titles(chat_id); reset_moderators_header(chat_id)
        return await message.reply(f"{em('check', '✅')} Названия и заголовок сброшены к стандартным.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["заголовок", "header"]:
        full_html = entities_to_html(message)
        m = re.match(r'^\s*[.\/!+-]?\s*модераторы\s+заголовок\s+(.+)$', full_html, re.IGNORECASE | re.DOTALL)
        if not m:
            current = get_moderators_header(chat_id)
            return await message.reply(f"📌 <b>Текущий заголовок:</b>\n{current}\n\n📌 <b>Установить:</b>\n<code>.модераторы заголовок ⭐️ Название</code>\n\n📌 <b>Сбросить:</b>\n<code>.модераторы заголовок сброс</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        new_header = m.group(1).strip()
        if re.sub(r'<[^>]+>', '', new_header).strip().lower() in ["сброс", "reset"]:
            reset_moderators_header(chat_id)
            return await message.reply(f"{em('check', '✅')} Заголовок сброшен: <code>{DEFAULT_MODERATORS_HEADER}</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        set_moderators_header(chat_id, new_header[:128])
        return await message.reply(f"{em('check', '✅')} <b>Заголовок обновлён!</b>\n\n{new_header}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not sub.isdigit() or int(sub) not in range(6):
        return await message.reply("❌ Укажи ранг от 0 до 5.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    rank = int(sub)
    full_html = entities_to_html(message)
    m = re.match(r'^\s*[.\/!+-]?\s*модераторы\s+(\d)\s+(.+)$', full_html, re.IGNORECASE | re.DOTALL)
    if not m:
        return await message.reply(f"📌 <code>.модераторы {rank} и=...;р=...;д=...;т=...;мн=...</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    template = m.group(2).strip()
    parsed = parse_title_template(template)
    if not parsed:
        return await message.reply("❌ Не удалось распарсить шаблон.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    for case, value in parsed.items():
        set_moderator_title(chat_id, rank, case, value[:64])
    titles = get_all_moderator_titles(chat_id)
    t = titles[rank]
    await message.reply(
        f"{em('check', '✅')} <b>Название для ранга {rank} обновлено!</b>\n\n"
        f"{RANK_ICONS.get(rank, '👤')} <b>{t['nom']}</b>\n"
        f"и={t['nom']} | р={t['gen']} | д={t['dat']} | т={t['ins']} | мн={t['plu']}",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


# ================= УХОЖУ В ОТСТАВКУ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*ухожу\s+в\s+отставку\b', m.text.strip(), re.IGNORECASE))
async def resign_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только в группе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    user_id = message.from_user.id; chat_id = message.chat.id
    if user_id == OWNER_ID or is_coowner(user_id):
        return await message.reply(f"{em('cross', '❌')} Владелец/совладелец бота не может уйти в отставку.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status == "creator":
            return await message.reply(f"{em('cross', '❌')} Создатель чата не может уйти в отставку.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except: pass
    current_rank = get_rank(chat_id, user_id)
    if current_rank == 0:
        return await message.reply("ℹ️ Вы и так не имеете ранга в этом чате.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    remove_rank(chat_id, user_id)
    try: unmark_bot_promoted(user_id, chat_id)
    except: pass
    rank_name = rank_display(chat_id, current_rank)
    await message.reply(f"{em('check', '✅')} <b>Вы ушли в отставку</b>\n\n👤 {mention(message.from_user)}\n📉 Было: <b>{rank_name}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("восстановить")
async def restore_creator_cmd(message: types.Message):
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status != "creator":
            return await message.reply(f"{em('cross', '❌')} Только создатель.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except: return
    set_rank(message.chat.id, message.from_user.id, 5, message.from_user.id)
    await message.reply(f"{em('check', '✅')} Вы владелец чата!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+админ"))
async def grant_admin_cmd(message: types.Message):
    actor_rank = get_rank(message.chat.id, message.from_user.id)
    if actor_rank < 3: return
    target, _ = await resolve_target(message)
    if not target or target.id == OWNER_ID: return
    try:
        await bot.promote_chat_member(chat_id=message.chat.id, user_id=target.id, rights=full_admin_rights())
        mark_bot_promoted(target.id, message.chat.id, message.from_user.id)
        await message.reply(f"{em('check', '✅')} {mention(target)} теперь <b>ТГ-админ</b>!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= МРП =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*\+мрп\b', m.text.strip(), re.IGNORECASE))
async def create_rp_cmd(message: types.Message):
    if not get_vip(message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Только VIP.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    full_html = entities_to_html(message)
    body = re.sub(r'^[.\/!+-]?\s*\+мрп\s*', '', full_html, count=1, flags=re.IGNORECASE).strip()
    parts = body.split("/", 2)
    if len(parts) < 3:
        return await message.reply("📌 <b>Формат:</b>\n<code>+мрп ущипнуть / 🤏 / ущипнул</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    name_html = parts[0].strip()
    emoji_html = parts[1].strip()[:120]
    action_html = parts[2].strip()[:400]
    name_clean = re.sub(r'<[^>]+>', '', name_html).strip().lower()[:30]
    if not name_clean or not emoji_html or not action_html:
        return await message.reply("❌ Заполни все 3 поля.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if "{actor}" not in action_html and "{target}" not in action_html:
        full_text = f"{{actor}} {action_html} {{target}}"
    else:
        full_text = action_html
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO rp_commands (chat_id, name, emoji, text, created_by) VALUES (?, ?, ?, ?, ?)",
                      (message.chat.id, name_clean, emoji_html, full_text, message.from_user.id))
            conn.commit()
            await message.reply(f"{em('check', '✅')} РП <b>{emoji_html} {name_clean}</b> создано!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        except sqlite3.IntegrityError:
            return await message.reply(f"{em('cross', '❌')} Уже есть.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


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
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*-мрп\b', m.text.strip(), re.IGNORECASE))
async def delete_rp_cmd(message: types.Message):
    raw = re.sub(r'^[.\/!+-]\s*', '', message.text.strip())
    raw = re.sub(r'^-мрп\s*', '', raw, count=1, flags=re.IGNORECASE).strip()
    if not raw: return
    name = raw.lower()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM rp_commands WHERE chat_id = ? AND name = ? AND created_by = ?",
                  (message.chat.id, name, message.from_user.id))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Удалено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ГМРП =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*\+гмрп\b', m.text.strip(), re.IGNORECASE))
async def create_global_rp_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id) and not has_agent_rank(message.from_user.id, 4):
        return
    full_html = entities_to_html(message)
    body = re.sub(r'^[.\/!+-]?\s*\+гмрп\s*', '', full_html, count=1, flags=re.IGNORECASE).strip()
    parts = body.split("/", 2)
    if len(parts) < 3:
        return await message.reply("📌 <b>Формат:</b>\n<code>+гмрп ущипнуть / 🤏 / ущипнул</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    name_html = parts[0].strip()
    emoji_html = parts[1].strip()[:120]
    action_html = parts[2].strip()[:400]
    name_clean = re.sub(r'<[^>]+>', '', name_html).strip().lower()[:30]
    if not name_clean or not emoji_html or not action_html:
        return await message.reply("❌ Заполни все 3 поля.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if "{actor}" not in action_html and "{target}" not in action_html:
        full_text = f"{{actor}} {action_html} {{target}}"
    else:
        full_text = action_html
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT OR REPLACE INTO global_rp_commands (user_id, name, emoji, text, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                      (message.from_user.id, name_clean, emoji_html, full_text))
            conn.commit()
            await message.reply(f"{em('check', '✅')} Глобальное РП создано!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        except Exception as e:
            return await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*-гмрп\b', m.text.strip(), re.IGNORECASE))
async def delete_global_rp_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id) and not has_agent_rank(message.from_user.id, 4):
        return
    raw = re.sub(r'^[.\/!+-]\s*', '', message.text.strip())
    raw = re.sub(r'^-гмрп\s*', '', raw, count=1, flags=re.IGNORECASE).strip()
    if not raw:
        return await message.reply("📌 <code>-гмрп Название</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM global_rp_commands WHERE user_id = ? AND LOWER(name) = ?", (message.from_user.id, raw.lower()))
        conn.commit()
    await message.reply(f"{em('check', '✅')} Удалено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("гмрп")
async def list_global_rp_cmd(message: types.Message):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, emoji FROM global_rp_commands WHERE user_id = ? ORDER BY id ASC", (message.from_user.id,))
        rows = c.fetchall()
    if not rows:
        return await message.reply("📭 У тебя нет глобальных РП.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = "🌐 <b>Твои глобальные РП:</b>\n\n"
    for i, (rid, name, emoji) in enumerate(rows, 1):
        text += f"{i}. {emoji} <code>{name}</code>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ПРАВИЛА =================
@cmd("правила", allow_args=True)
@cmd("rules", allow_args=True)
async def rules_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        rules = get_chat_rules(message.chat.id)
        if not rules:
            return await message.reply("📭 Правила не установлены.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        return await message.reply(f"📜 <b>Правила:</b>\n\n{rules}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    sub = args[1].strip().lower()
    if sub.startswith("установить"):
        if not has_permission(message.chat.id, message.from_user.id, 3): return
        parts = message.text.split("\n", 1)
        if len(parts) < 2: return
        nl_idx = message.text.find("\n")
        raw_text_html = _extract_html_after(message, nl_idx + 1)[:3500]
        set_chat_rules(message.chat.id, raw_text_html, message.from_user.id)
        return await message.reply(f"{em('check', '✅')} Правила установлены!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["сброс", "удалить"]:
        if not has_permission(message.chat.id, message.from_user.id, 3): return
        reset_chat_rules(message.chat.id)
        return await message.reply(f"{em('check', '✅')} Сброшено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["закрепить", "пин"]:
        if not has_permission(message.chat.id, message.from_user.id, 3): return
        rules = get_chat_rules(message.chat.id)
        if not rules: return
        try:
            msg = await message.reply(f"📜 <b>Правила:</b>\n\n{rules}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
            await bot.pin_chat_message(message.chat.id, msg.message_id, disable_notification=True)
        except: pass


# ================= ПРИВЕТСТВИЕ =================
@cmd("приветствие", allow_args=True)
async def greeting_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    args = message.text.split(maxsplit=1)
    sub = args[1].strip().lower() if len(args) >= 2 else ""
    if not sub:
        current = get_greeting(message.chat.id)
        if not current:
            return await message.reply(
                "📭 <b>Приветствие не установлено</b>\n\n"
                "📌 <b>Установить:</b>\n<code>.приветствие установить</code>\n<code>Твой текст приветствия</code>\n\n"
                "🔹 <b>Плейсхолдеры:</b>\n"
                "• <code>{ник}</code> — кликабельный ник (по умолчанию сверху)\n"
                "• <code>{имя}</code> — имя без ссылки\n"
                "• <code>{юзер}</code> — @username\n"
                "• <code>{чат}</code> — название чата\n"
                "• <code>{айди}</code> — ID юзера\n"
                "• <code>{без_ника}</code> — не добавлять ник сверху",
                parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
            )
        preview = format_greeting(current, message.from_user, message.chat)
        return await message.reply(
            f"📜 <b>Текущее приветствие:</b>\n\n"
            f"<b>Превью (для тебя):</b>\n{preview}\n\n"
            f"<b>Шаблон:</b>\n<code>{html_escape_text(current)}</code>\n\n"
            f"🔹 <b>Плейсхолдеры:</b> <code>{{имя}}</code> · <code>{{ник}}</code> · <code>{{юзер}}</code> · <code>{{чат}}</code> · <code>{{айди}}</code> · <code>{{без_ника}}</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    if sub.startswith("установить"):
        parts = message.text.split("\n", 1)
        if len(parts) < 2: return
        nl_idx = message.text.find("\n")
        raw_text_html = _extract_html_after(message, nl_idx + 1)[:1000]
        if not raw_text_html: return
        set_greeting(message.chat.id, raw_text_html, message.from_user.id)
        preview = format_greeting(raw_text_html, message.from_user, message.chat)
        return await message.reply(f"{em('check', '✅')} Установлено!\n\n<b>Превью:</b>\n{preview}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["сброс", "удалить"]:
        reset_greeting(message.chat.id)
        return await message.reply(f"{em('check', '✅')} Сброшено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ФИЛЬТР ССЫЛОК =================
@cmd("фильтрссылок", allow_args=True)
async def link_filter_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    args = message.text.split(maxsplit=1)
    sub = args[1].strip().lower() if len(args) >= 2 else ""
    if not sub:
        enabled = is_link_filter_enabled(message.chat.id)
        status = "🟢 включён" if enabled else "🔴 выключен"
        return await message.reply(f"🔗 <b>Фильтр ссылок:</b> {status}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["вкл", "on", "+"]:
        set_link_filter(message.chat.id, True)
        return await message.reply(f"{em('check', '✅')} Включён", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if sub in ["выкл", "off", "-"]:
        set_link_filter(message.chat.id, False)
        return await message.reply(f"{em('check', '✅')} Выключен", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))# ================= КАПЧА =================
@dp.message(lambda m: m.text and m.text.lower().strip() in ["+капча", "+ капча"])
async def enable_captcha_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    if is_captcha_enabled(message.chat.id):
        return await message.reply("ℹ️ Уже включена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_captcha_enabled(message.chat.id, True)
    await message.reply(f"{em('check', '✅')} Капча включена!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-капча", "- капча"])
async def disable_captcha_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    if not is_captcha_enabled(message.chat.id):
        return await message.reply("ℹ️ Уже выключена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_captcha_enabled(message.chat.id, False)
    await message.reply(f"{em('check', '✅')} Капча выключена!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("капча")
async def captcha_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    enabled = is_captcha_enabled(message.chat.id)
    timeout = get_captcha_timeout(message.chat.id)
    status = "🟢 включена" if enabled else "🔴 выключена"
    mins = timeout // 60
    secs = timeout % 60
    human = f"{mins} мин. {secs} сек." if mins > 0 else f"{secs} сек."
    await message.reply(
        f"🤖 <b>Капча</b>\n\n📊 Статус: {status}\n⏱ Время на прохождение: <b>{timeout} сек.</b> ({human})\n\n"
        f"📌 <code>+капча</code> / <code>-капча</code> — вкл/выкл\n📌 <code>.капчавремя 180</code> — изменить время",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("капчавремя", allow_args=True, args_pattern=r"^\d+$")
@cmd("капча время", allow_args=True, args_pattern=r"^\d+$")
async def captcha_time_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not await _check_automod_perms(message): return
    args = message.text.split()
    current = get_captcha_timeout(message.chat.id)
    if len(args) < 2:
        return await message.reply(
            f"⏱ <b>Время прохождения капчи</b>\n\n🕐 Сейчас: <b>{current} сек.</b> ({current // 60} мин. {current % 60} сек.)\n\n"
            f"📌 Установить: <code>.капчавремя 180</code>\n📌 Диапазон: от <b>10</b> до <b>3600</b> секунд",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    raw = args[1].strip()
    if not raw.isdigit():
        return await message.reply("❌ Укажи число секунд.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    seconds = int(raw)
    if seconds < 10 or seconds > 3600:
        return await message.reply("❌ Допустимый диапазон: <b>10</b> – <b>3600</b> секунд.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_captcha_timeout(message.chat.id, seconds)
    mins = seconds // 60; secs = seconds % 60
    human = f"{mins} мин. {secs} сек." if mins > 0 else f"{secs} сек."
    await message.reply(f"{em('check', '✅')} <b>Время капчи обновлено!</b>\n\n⏱ Теперь: <b>{seconds} сек.</b> ({human})", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= АВТОМОД =================
def _fmt_time(minutes):
    if minutes >= 1440: return f"{minutes // 1440} дн."
    if minutes >= 60: return f"{minutes // 60} ч."
    return f"{minutes} мин."


async def _check_automod_perms(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if user_id == OWNER_ID or is_coowner(user_id): return True
    if has_agent_rank(user_id, 1): return True
    is_creator = False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_creator = (member.status == "creator")
    except: pass
    if is_creator: return True
    if has_permission(chat_id, user_id, 3): return True
    if await is_tg_admin(chat_id, user_id): return True
    await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    return False


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
        f"🎨 Антистикер: {st(s['antisticker'])} | {act('antisticker')}"
    )
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антимат", "+ антимат"])
async def enable_antimat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antimat", 1)
    await message.reply(f"{em('check', '✅')} Антимат вкл", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антимат", "- антимат"])
async def disable_antimat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antimat", 0)
    await message.reply(f"{em('check', '✅')} Антимат выкл", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антифлуд", "+ антифлуд"])
async def enable_antiflood_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antiflood", 1)
    await message.reply(f"{em('check', '✅')} Антифлуд вкл", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антифлуд", "- антифлуд"])
async def disable_antiflood_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antiflood", 0)
    await message.reply(f"{em('check', '✅')} Антифлуд выкл", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антикапс", "+ антикапс"])
async def enable_anticaps_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "anticaps", 1)
    await message.reply(f"{em('check', '✅')} Антикапс вкл", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антикапс", "- антикапс"])
async def disable_anticaps_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "anticaps", 0)
    await message.reply(f"{em('check', '✅')} Антикапс выкл", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+антисticker", "+ антисticker"])
async def enable_antisticker_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antisticker", 1)
    await message.reply(f"{em('check', '✅')} Антистикер вкл", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-антисticker", "- антисticker"])
async def disable_antisticker_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    set_automod_setting(message.chat.id, "antisticker", 0)
    await message.reply(f"{em('check', '✅')} Антистикер выкл", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


async def _set_automod_action(message, rule):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    args = message.text.split()
    s = get_automod_settings(message.chat.id)
    cur = s[f"{rule}_action"]
    if len(args) < 2:
        return await message.reply(f"🎯 Действие <b>{rule}</b>: {ACTION_NAMES.get(cur, cur)}\n<code>.{rule}действие мут/варн/бан</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    action = args[1].lower()
    mapping = {"удалить": "delete", "delete": "delete", "мут": "mute", "mute": "mute", "варн": "warn", "warn": "warn", "бан": "ban", "ban": "ban"}
    if action not in mapping: return
    set_automod_setting(message.chat.id, f"{rule}_action", mapping[action])
    await message.reply(f"{em('check', '✅')} <b>{rule}</b>: {ACTION_NAMES[mapping[action]]}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("антиматдействие", allow_args=True)
async def am_action_cmd(message): await _set_automod_action(message, "antimat")

@cmd("антифлуддействие", allow_args=True)
async def afl_action_cmd(message): await _set_automod_action(message, "antiflood")

@cmd("антикапсдействие", allow_args=True)
async def ac_action_cmd(message): await _set_automod_action(message, "anticaps")

@cmd("антисtickerдействие", allow_args=True)
async def ast_action_cmd(message): await _set_automod_action(message, "antisticker")


async def _set_automod_time(message, rule, kind):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    args = message.text.split()
    s = get_automod_settings(message.chat.id)
    field = f"{rule}_{kind}"
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply(f"⏱ {_fmt_time(s[field])}\n<code>.{rule}{kind} 60</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    minutes = int(args[1])
    if minutes < 1 or minutes > 525600: return
    set_automod_setting(message.chat.id, field, minutes)
    await message.reply(f"{em('check', '✅')} {rule} {kind}: <b>{_fmt_time(minutes)}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("антиматмут", allow_args=True)
async def am_mute_cmd(message): await _set_automod_time(message, "antimat", "mute")
@cmd("антиматбан", allow_args=True)
async def am_ban_cmd(message): await _set_automod_time(message, "antimat", "ban")
@cmd("антифлудмут", allow_args=True)
async def afl_mute_cmd(message): await _set_automod_time(message, "antiflood", "mute")
@cmd("антифлудбан", allow_args=True)
async def afl_ban_cmd(message): await _set_automod_time(message, "antiflood", "ban")
@cmd("антикапсмут", allow_args=True)
async def ac_mute_cmd(message): await _set_automod_time(message, "anticaps", "mute")
@cmd("антисtickermut", allow_args=True)
async def ast_mute_cmd(message): await _set_automod_time(message, "antisticker", "mute")


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


def get_user_achievements_all_chats(user_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT a.id, a.name, a.emoji, a.description, ua.given_at, ua.chat_id
            FROM user_achievements ua
            JOIN achievements a ON a.id = ua.achievement_id
            WHERE ua.user_id = ?
            ORDER BY ua.given_at DESC""", (user_id,))
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


@cmd("ачивки")
@cmd("все ачивки")
async def list_achievements_cmd(message: types.Message):
    all_ach = get_all_achievements()
    if not all_ach:
        return await message.reply("📭 Нет ачивок.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = "🎖 <b>Все ачивки:</b>\n\n"
    for aid, name, emoji, desc in all_ach:
        text += f"{emoji} <b>{name}</b>"
        if desc: text += f" — <i>{desc}</i>"
        text += "\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("мои ачивки")
async def my_achievements_cmd(message: types.Message):
    ach = get_user_achievements_all_chats(message.from_user.id)
    if not ach:
        return await message.reply("📭 <b>У тебя пока нет ачивок.</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"🎖 <b>Твои ачивки</b> ({len(ach)}):\n\n"
    for aid, name, emoji, desc, given_at, chat_id in ach:
        try:
            chat = await bot.get_chat(chat_id); chat_title = chat.title or f"Чат {chat_id}"
        except: chat_title = f"Чат {chat_id}"
        text += f"{emoji} <b>{name}</b>"
        if desc: text += f" — <i>{desc}</i>"
        text += f"\n   🏠 {chat_title}\n   📅 {_fmt_added_dt(given_at)}\n"
    text += f"\n🔒 Скрыть от других: <code>-ачивки</code>"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("твои ачивки", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
async def your_achievements_cmd(message: types.Message):
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
                return await message.reply(f"{em('cross', '❌')} Не найден.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if not target:
        return await message.reply("📌 <b>Формат:</b> <code>.твои ачивки @user</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    viewer_id = message.from_user.id
    is_self = (viewer_id == target.id)
    is_staff = (viewer_id == OWNER_ID or is_coowner(viewer_id) or has_agent_rank(viewer_id, 1))
    if are_achievements_hidden(target.id) and not is_self and not is_staff:
        return await message.reply(f"🔒 {mention(target)} <b>скрыл(а) свои ачивки</b>.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    ach = get_user_achievements_all_chats(target.id)
    if not ach:
        return await message.reply(f"📭 У {mention(target)} пока нет ачивок.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"🎖 <b>Ачивки {mention(target)}</b> ({len(ach)}):\n\n"
    for aid, name, emoji, desc, given_at, chat_id in ach:
        try:
            chat = await bot.get_chat(chat_id); chat_title = chat.title or f"Чат {chat_id}"
        except: chat_title = f"Чат {chat_id}"
        text += f"{emoji} <b>{name}</b>"
        if desc: text += f" — <i>{desc}</i>"
        text += f"\n   🏠 {chat_title}\n   📅 {_fmt_added_dt(given_at)}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-ачивки")
async def hide_achievements_cmd(message: types.Message):
    user_id = message.from_user.id
    if are_achievements_hidden(user_id):
        return await message.reply("ℹ️ Твои ачивки уже скрыты.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    hide_achievements(user_id)
    await message.reply(f"{em('check', '✅')} <b>Твои ачивки теперь скрыты.</b>\n↩️ Вернуть: <code>+ачивки</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "+ачивки")
async def show_achievements_cmd(message: types.Message):
    user_id = message.from_user.id
    if not are_achievements_hidden(user_id):
        return await message.reply("ℹ️ Твои ачивки и так видны всем.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    show_achievements(user_id)
    await message.reply(f"{em('check', '✅')} <b>Твои ачивки снова видны всем.</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*выдать\s+ачивку\b', m.text.strip(), re.IGNORECASE))
async def give_achievement_cmd(message: types.Message):
    chat_id = message.chat.id; user_id = message.from_user.id
    if user_id != OWNER_ID and not is_coowner(user_id) and not has_agent_rank(user_id, 1):
        return await message.reply(f"{em('cross', '❌')} Только <b>агенты Mos</b>.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        args = message.text.split()
        for a in args[2:]:
            if a.startswith('@'):
                try: target = await bot.get_chat(a); break
                except: pass
            if a.isdigit():
                try: target = await bot.get_chat(int(a)); break
                except: pass
    if not target:
        return await message.reply("📌 <code>.выдать ачивку @user Название</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    raw = re.sub(r'^[.\/!+-]?\s*выдать\s+ачивку\s*', '', message.text.strip(), flags=re.IGNORECASE).strip()
    if message.reply_to_message: ach_name = raw
    else:
        parts = raw.split(maxsplit=1)
        ach_name = parts[1] if len(parts) > 1 else ""
    ach_name = re.sub(r'<[^>]+>', '', ach_name).strip()
    if not ach_name:
        return await message.reply(f"{em('cross', '❌')} Укажи название ачивки.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    ach = get_achievement_by_name(ach_name)
    if not ach:
        return await message.reply(f"{em('cross', '❌')} Ачивка <b>{ach_name}</b> не найдена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    ach_id, name, emoji, desc = ach
    if give_achievement(target.id, chat_id, ach_id, user_id):
        await message.reply(f"{em('check', '✅')} <b>Выдано!</b>\n\n👤 {mention(target)}\n{emoji} <b>{name}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        try:
            await bot.send_message(target.id, f"🎖 <b>Вам выдали ачивку!</b>\n\n{emoji} <b>{name}</b>" + (f"\n<i>{desc}</i>" if desc else ""), parse_mode="HTML", disable_web_page_preview=True)
        except: pass
    else:
        await message.reply(f"{em('cross', '❌')} У {mention(target)} уже есть эта ачивка.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*снять\s+ачивку\b', m.text.strip(), re.IGNORECASE))
async def remove_achievement_cmd(message: types.Message):
    chat_id = message.chat.id; user_id = message.from_user.id
    if user_id != OWNER_ID and not is_coowner(user_id) and not has_agent_rank(user_id, 1):
        return await message.reply(f"{em('cross', '❌')} Только <b>агенты Mos</b>.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target = None
    if message.reply_to_message: target = message.reply_to_message.from_user
    if not target:
        return await message.reply("📌 Ответь на сообщение юзера.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    raw = re.sub(r'^[.\/!+-]?\s*снять\s+ачивку\s*', '', message.text.strip(), flags=re.IGNORECASE).strip()
    if not raw:
        return await message.reply("📌 <code>.снять ачивку Название</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    ach = get_achievement_by_name(re.sub(r'<[^>]+>', '', raw).strip())
    if not ach:
        return await message.reply(f"{em('cross', '❌')} Ачивка не найдена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    remove_achievement(target.id, chat_id, ach[0])
    await message.reply(f"🗑 Снята ачивка <b>{ach[1]}</b> с {mention(target)}.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*создать\s+ачивку\b', m.text.strip(), re.IGNORECASE))
async def create_achievement_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID and not is_coowner(user_id) and not has_agent_rank(user_id, 1):
        return await message.reply(f"{em('cross', '❌')} Только <b>агенты Mos</b>.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    full_html = entities_to_html(message)
    raw = re.sub(r'^[.\/!+-]?\s*создать\s+ачивку\s*', '', full_html, count=1, flags=re.IGNORECASE).strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 1 or not parts[0]:
        return await message.reply("📌 <b>Формат:</b>\n<code>.создать ачивку Название | 🏅 | Описание</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    name_html = parts[0][:120]
    emoji_html = parts[1] if len(parts) > 1 and parts[1] else "🏅"
    desc_html = parts[2] if len(parts) > 2 else ""
    name_clean = re.sub(r'<[^>]+>', '', name_html).strip()[:60]
    if not name_clean:
        return await message.reply("❌ Пустое название.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    new_id = create_achievement(name_clean, emoji_html, desc_html)
    if not new_id:
        return await message.reply(f"{em('cross', '❌')} Ачивка с таким именем уже есть.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(
        f"{em('check', '✅')} Ачивка создана!\n\n{emoji_html} <b>{name_clean}</b>\n"
        + (f"<i>{desc_html}</i>\n" if desc_html else "")
        + f"\n📌 Выдать: <code>.выдать ачивку @user {name_clean}</code>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


# ================= ПОПОЛНИТЬ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*пополнить\b', m.text.strip(), re.IGNORECASE))
async def add_candies_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id) and not has_agent_rank(message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Только владелец, совладелец или агент 3+.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target = None; amount = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        args = message.text.split()
        for a in args[1:]:
            if a.lstrip("-").isdigit():
                amount = int(a); break
    else:
        args = message.text.split()
        if len(args) >= 3:
            try:
                if args[1].startswith("@"): target = await bot.get_chat(args[1])
                elif args[1].lstrip("-").isdigit(): target = await bot.get_chat(int(args[1]))
            except:
                return await message.reply(f"{em('cross', '❌')} Пользователь не найден.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
            if args[2].lstrip("-").isdigit(): amount = int(args[2])
        elif len(args) == 2 and args[1].lstrip("-").isdigit():
            target = message.from_user; amount = int(args[1])
    if not target:
        return await message.reply("📌 <code>.пополнить @user 100</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if amount is None or amount == 0:
        return await message.reply("❌ Укажи сумму.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if abs(amount) > 1000000:
        return await message.reply("❌ Максимум 1 000 000 за раз.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    add_candies(target.id, amount, message.from_user.id)
    new_balance = get_balance(target.id)
    sign = "+" if amount > 0 else ""
    await message.reply(f"{em('check', '✅')} <b>Пополнено!</b>\n\n👤 {mention(target)}\n💰 <b>{sign}{amount}</b> 🍬\n💼 Баланс: <b>{new_balance}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ИРИСКИ =================
@cmd("мешок", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
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
        f"🎒 <b>Мешок {mention(target)}</b>\n\n🍬 mos-конфетки: <b>{get_balance(target.id)}</b>\n☢️ Коины: <b>{get_coins(target.id)}</b> i¢",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("мешки")
async def top_candies_cmd(message: types.Message):
    top = get_top_candies(limit=10)
    if not top:
        return await message.reply("📭 Пусто.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = "🏆 <b>Топ мешков:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, balance) in enumerate(top, 1):
        try:
            user = await bot.get_chat(user_id); name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{balance}</b> 🍬\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*(перевод|перевести)\b', m.text.strip(), re.IGNORECASE))
async def transfer_candies_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("📌 <code>.перевод @user 100</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target = None; amount_arg = None
    if message.reply_to_message and len(args) == 2:
        target = message.reply_to_message.from_user; amount_arg = args[1]
    else:
        target_arg = args[1]; amount_arg = args[2] if len(args) >= 3 else None
        if not amount_arg: return
        if target_arg.startswith('@'):
            try: target = await bot.get_chat(target_arg)
            except: return
        elif target_arg.isdigit():
            try: target = await bot.get_chat(int(target_arg))
            except: return
    if not target or target.id == user_id or target.id == bot.id: return
    if is_transfer_blocked(target.id, user_id):
        return await message.reply(f"{em('cross', '❌')} {mention(target)} <b>запретил(а)</b> тебе переводить.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
    await message.reply(f"{em('check', '✅')} <b>Перевод!</b>\n\n👤 Кому: {mention(target)}\n💰 Сумма: <b>{amount}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        await bot.send_message(target.id, f"🎁 <b>Вам перевели {amount} 🍬 от {message.from_user.first_name}</b>", parse_mode="HTML")
    except: pass


# ================= ЗАПРЕТ ПЕРЕВОДОВ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*запретить\s+переводы\b', m.text.strip(), re.IGNORECASE))
async def block_transfer_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply(f"{em('cross', '❌')} Только в группе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("📌 Ответь на сообщение или <code>.запретить переводы @user</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    blocker_id = message.from_user.id
    if target.id == blocker_id or target.id == bot.id:
        return await message.reply(f"{em('cross', '❌')} Нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    ok = add_transfer_block(blocker_id, target.id, blocker_id)
    if not ok:
        return await message.reply(f"ℹ️ {mention(target)} уже в списке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"{em('check', '✅')} 🚫 {mention(target)} <b>больше не может</b> переводить {mention(message.from_user)}.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*разрешить\s+переводы\b', m.text.strip(), re.IGNORECASE))
async def unblock_transfer_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply(f"{em('cross', '❌')} Только в группе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    target, _ = await resolve_target(message)
    if not target:
        return await message.reply("📌 Ответь на сообщение.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    ok = remove_transfer_block(message.from_user.id, target.id)
    if not ok:
        return await message.reply(f"ℹ️ {mention(target)} не был в списке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"{em('check', '✅')} {mention(target)} снова может переводить.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("мои запреты")
@cmd("запреты")
async def my_transfer_blocks_cmd(message: types.Message):
    blocks = get_transfer_blocks(message.from_user.id)
    if not blocks:
        return await message.reply(f"📭 У вас нет запретов на переводы.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"🚫 <b>Запрет на переводы</b> ({len(blocks)}):\n\n"
    for i, (blocked_id, added_at) in enumerate(blocks, 1):
        try:
            u = await bot.get_chat(blocked_id); name = user_link(blocked_id, u.first_name, u.username)
        except: name = f"<code>{blocked_id}</code>"
        text += f"{i}. {name} — <i>{_fmt_added_dt(added_at)}</i>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


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
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("ферма")
async def farm_cmd(message: types.Message):
    user_id = message.from_user.id
    apply_tax(user_id)
    reward, wait_minutes = get_farm_reward(user_id)
    if reward == 0:
        return await message.reply(f"⏳ Ферма не готова. Ещё <b>{wait_minutes} мин.</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    info = get_coins_info(user_id)
    total_farmed = (info[2] or 0) + reward
    add_coins(user_id, reward, "ферма"); update_farm_time(user_id, total_farmed)
    await message.reply(f"⛏ <b>Урожай!</b>\n💰 +{reward} i¢", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("купить коины", allow_args=True, args_pattern=r"^\d+$")
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
    add_coins(user_id, coins_amount, "обмен")
    await message.reply(f"💱 Обмен!\n💸 -{candies_amount} 🍬\n💰 +{coins_amount} i¢", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("бкоин", allow_args=True, args_pattern=r"^\d+$")
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
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("коинытоп")
async def coins_top_cmd(message: types.Message):
    top = get_coins_top(limit=10)
    if not top: return
    text = "☢️ <b>Топ коинов:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, balance) in enumerate(top, 1):
        try:
            user = await bot.get_chat(user_id); name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{balance}</b> i¢\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= STARS =================
@cmd("купитьириски", allow_args=True, args_pattern=r"^\d+$")
@cmd("купить-ириски", allow_args=True, args_pattern=r"^\d+$")
@cmd("buycandies", allow_args=True, args_pattern=r"^\d+$")
async def buy_candies_stars_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        price = get_stars_per_candy(message.chat.id)
        return await message.reply(f"🍬 <b>Покупка mos-конфеток</b>\n\n💰 Курс: <b>{price} ⭐ = 1 🍬</b>\n\n📌 <code>.купитьириски 10</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    amount = int(args[1])
    if amount < 1 or amount > 10000: return
    price = get_stars_per_candy(message.chat.id); total_stars = amount * price
    payment_id = create_stars_payment(user_id=message.from_user.id, chat_id=message.chat.id, amount_candies=amount, stars=total_stars)
    try:
        await bot.send_invoice(
            chat_id=message.chat.id, title=f"🍬 {amount} mos-конфеток",
            description=f"{amount} mos-конфеток за {total_stars} ⭐",
            payload=f"candies_{payment_id}", provider_token="", currency="XTR",
            prices=[types.LabeledPrice(label=f"{amount} mos-конфеток", amount=total_stars)],
            start_parameter=f"buy_candies_{payment_id}"
        )
    except Exception as e:
        await message.reply(f"{em('cross', '❌')} Ошибка: {e}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


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
    await message.reply(f"{em('check', '✅')} <b>Покупка успешна!</b>\n\n🍬 +{amount_candies} 🍬\n⭐ {stars_paid}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))# ================= РЫБАЛКА — ПОМОЩЬ =================
def _fishing_help_text() -> str:
    return (
        "🎣 <b>Рыбалка — Mos</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📢 <b>Для рыбалки нужна подписка на канал:</b>\n"
        f"👉 <a href='{SUPPORT_CHANNEL_LINK}'>@moskanalp</a>\n\n"
        "🎯 <b>Основные</b>\n"
        "• <code>.рыбалка</code> — забросить удочку\n"
        "• <code>.моя рыбалка</code> — статистика\n"
        "• <code>.рыбтоп</code> — топ-10 рыбаков\n"
        "• <code>.событие</code> — событие в чате\n\n"
        "🌊 <b>Локации</b>\n"
        "• <code>.локация</code> — список\n"
        "• 🌊 Пирс — старт\n"
        "• 🪨 Камни — ур. 5+\n"
        "• 🌅 Закатный мыс — ур. 15+\n"
        "• 🌌 Бездна — ур. 20+\n"
        "• 🏝 Остров сокровищ — ур. 30+ 💎VIP\n"
        "Смена: <code>.локация пирс</code> (ранг 3+)\n\n"
        "🎒 <b>Садок и продажа</b>\n"
        "• <code>.садок</code> — что поймал\n"
        "• <code>.продать все</code>\n"
        "• <code>.продать Щука 5</code>\n\n"
        "🛒 <b>Снасти с прокачкой</b>\n"
        "• <code>.магазин снастей</code>\n"
        "• <code>.купить hook</code> — купить снасть\n"
        "• <code>.улучшить hook</code> — улучшить на ур.\n"
        "• 🪝 Крючок 1-5 ур. (-10 мин КД за ур.)\n"
        "• 🎣 Спиннинг 1-5 ур. (-5 мин КД за ур.)\n"
        "• 🪣 Ведро 1-5 ур.\n"
        "• 🚤 Лодка 1-3 ур.\n"
        "• 🎣 Премиум-удочка 1-3 ур.\n"
        "• 🔮 Магический поплавок 1-5 ур.\n"
        "• <code>+прикормка</code> — +15% на 1 ч (20 🍬)\n\n"
        "🏆 <b>Турнир</b>\n"
        "• <code>.турнир</code> — запустить (админ)\n"
        "• <code>.турнир участвовать</code>\n\n"
        "🎖 <b>Ачивки</b>\n"
        "• <code>.мои рыбные ачивки</code>\n\n"
        "🗺 <b>Регионы</b> (не зависят от локаций)\n"
        "🏞 река · 🌊 озеро · 🌊 море · 🌌 океан\n"
        "Смена: <code>.регион река</code> (ранг 3+)\n\n"
        "📊 <b>Как работает</b>\n"
        "• КД между забросами: <b>2 часа</b> (сокращается снастями до 15 мин)\n"
        "• 🪝 Крючок: −10 мин за уровень\n"
        "• 🎣 Спиннинг: −5 мин за уровень\n"
        "• 🎣 Премиум-удочка: −3 мин за уровень\n"
        "• 🔮 Магический поплавок: −3 мин за уровень\n"
        "• Шанс улова: <b>55% + 5% × уровень</b>\n"
        "• XP за рыбу: <b>5–15</b>, за вещь: <b>3–8</b>\n"
        "• Шанс легендарки: базово <b>3%</b> + бонусы\n"
    )


@cmd("рыбалка помощь")
@cmd("рыбалка хелп")
@cmd("рыбалка help")
async def fishing_help_cmd(message: types.Message):
    await message.reply(_fishing_help_text(), parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= РЫБАЛКА — ОСНОВНОЕ =================
@cmd("рыбалка")
@cmd("рыба")
@cmd("рыбачить")
async def fishing_cmd(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not await is_subscribed_to_fishing_channel(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📢 Подписаться на Mos", url=SUPPORT_CHANNEL_LINK)
        ]])
        return await message.reply(
            f"📢 <b>Требуется подписка на канал Mos</b>\n\n"
            f"Чтобы рыбачить — подпишись на наш канал:\n"
            f"👉 <a href=\"{SUPPORT_CHANNEL_LINK}\">@moskanalp</a>\n\n"
            f"После подписки попробуй снова: <code>.рыбалка</code>",
            parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb, **_reply_kwargs(message)
        )

    info = get_fishing(user_id)
    (uid, level, xp, total_caught, total_empty, has_rod, bait_until, last_fish, inv, legendary) = info

    location_key = get_chat_location(chat_id)
    location = LOCATIONS.get(location_key, LOCATIONS["pier"])

    user_cooldown = get_user_fish_cooldown(user_id)
    cooldown = format_fishing_cooldown(last_fish, user_cooldown)

    if cooldown > 0:
        hours = cooldown // 3600
        mins = (cooldown % 3600) // 60
        secs = cooldown % 60
        parts = []
        if hours > 0: parts.append(f"{hours} ч.")
        if mins > 0: parts.append(f"{mins} мин.")
        if secs > 0 and hours == 0: parts.append(f"{secs} сек.")
        time_str = " ".join(parts) if parts else "1 сек."

        progress = 1.0 - (cooldown / user_cooldown) if user_cooldown else 0
        progress = max(0.0, min(1.0, progress))
        bar_len = 12
        filled = int(progress * bar_len)
        bar = "▰" * filled + "▱" * (bar_len - filled)
        percent = int(progress * 100)

        cd_min = user_cooldown // 60
        cd_hours = cd_min // 60
        cd_min = cd_min % 60
        cd_str = f"{cd_hours} ч. {cd_min} мин." if cd_hours > 0 else f"{cd_min} мин."

        return await message.reply(
            f"⏳ <b>Удочка не готова</b>\n\n<code>{bar}</code> {percent}%\n\n"
            f"⏱ Осталось: <b>{time_str}</b>\n⚙️ Твой кулдаун: <b>{cd_str}</b> <i>(улучшай снасти!)</i>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )

    msg = await message.reply("🎣 Забрасываю удочку...", **_reply_kwargs(message))
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
    gear_bonus, gear_flat, boat_level, legendary_bonus, rare_bonus, gear_info = get_fishing_gear_bonus(user_id)
    chance = int(chance * (1 + gear_bonus))
    chance = min(chance, 98)
    roll = random.randint(1, 100)

    if roll <= chance:
        # СНАЧАЛА ЛЕГЕНДАРКА
        legendary_chance = 3 + legendary_bonus + location["legendary_chance"]
        legendary_chance = int(legendary_chance * rare_boost * event_bonus * (1 + rare_bonus / 100))
        if legendary_chance > 90: legendary_chance = 90
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
            ach_text = "\n\n🎖 <b>Новые ачивки:</b>\n" + "\n".join(f"  • {a}" for a in new_ach) if new_ach else ""
            fish_price = get_fish_price(fish_name) + gear_flat
            xp_needed = xp_needed_for_level(new_level)
            bar_len = 10
            filled = min(bar_len, int((new_xp / xp_needed) * bar_len)) if xp_needed else 0
            xp_bar = "▰" * filled + "▱" * (bar_len - filled)
            hour = datetime.now().hour
            time_icon = "🌙" if (hour >= 22 or hour < 6) else ("🌅" if hour < 11 else ("☀️" if hour < 18 else "🌇"))
            level_up_text = f"\n\n🎉 <b>УРОВЕНЬ ПОВЫШЕН!</b> Теперь <b>{new_level}</b>" if new_level > level else ""
            bait_text = "\n🍯 Прикормка активна" if bait_active else ""
            loc_text = f"\n{location['emoji']} Локация: {location['name']}"
            await msg.edit_text(
                f"🎣 <b>УЛОВ</b> {time_icon}\n\n{fish_emoji} <b>{fish_name}</b>\n"
                f"💎 Редкость: <i>Легендарная</i>\n💵 Цена: <b>{fish_price}</b> 🍬\n"
                f"✨ Опыт: <b>+{xp_gain}</b> XP\n\n"
                f"📊 <b>Уровень {new_level}</b>\n<code>{xp_bar}</code> {new_xp}/{xp_needed}\n\n"
                f"🐟 Всего поймано: <b>{total_caught + 1}</b>\n📦 Продай: <code>.продать</code>"
                f"{level_up_text}{legendary_text}{bait_text}{loc_text}{event_text}{ach_text}",
                parse_mode="HTML"
            )
            return

        # ПОТОМ ВЕЩЬ
        is_thing = random.randint(1, 100) <= (20 + location["treasure_chance"] + boat_level * 5)
        if is_thing:
            total_weight = sum(t[2] for t in THINGS_LIST)
            pick = random.uniform(0, total_weight); cumulative = 0
            chosen = THINGS_LIST[0]
            for thing in THINGS_LIST:
                cumulative += thing[2]
                if pick <= cumulative: chosen = thing; break
            name, emoji, weight, reward_mult, kind = chosen
            reward = reward_mult * random.randint(1, 3)
            add_candies(user_id, reward, 0)
            xp_gain = random.randint(3, 8)
            if kind == "gear_bait": set_fishing_bait(user_id)
            if kind == "gear_lucky": add_to_fishing_inventory(user_id, "hook", 1)
            if kind == "gear_float": add_to_fishing_inventory(user_id, "magic_float", 1)
            new_xp = xp + xp_gain
            new_level = level
            while new_xp >= xp_needed_for_level(new_level):
                new_xp -= xp_needed_for_level(new_level)
                new_level += 1
            update_fishing(user_id, level=new_level, xp=new_xp, total_caught=total_caught + 1)
            set_fishing_last_fish(user_id)
            log_fishing(user_id, chat_id, "caught", name, reward)
            level_up_text = f"\n\n🎉 <b>УРОВЕНЬ ПОВЫШЕН!</b> Теперь <b>{new_level}</b>" if new_level > level else ""
            extra = ""
            if kind == "gear_bait": extra = "\n🍯 Тебе выпала <b>прикормка на 1 час</b>!"
            if kind == "gear_lucky": extra = "\n🪝 Тебе выпал <b>Крючок 1 ур.</b>!"
            if kind == "gear_float": extra = "\n🔮 Тебе выпал <b>Магический поплавок 1 ур.</b>!"
            await msg.edit_text(
                f"🎣 <b>УЛОВ</b>\n\n{emoji} <b>{name}</b>\n💰 Награда: <b>+{reward}</b> 🍬\n"
                f"✨ Опыт: <b>+{xp_gain}</b> XP\n\n"
                f"📊 Уровень: <b>{new_level}</b> | XP: <b>{new_xp}/{xp_needed_for_level(new_level)}</b>\n"
                f"🐟 Всего поймано: <b>{total_caught + 1}</b>{level_up_text}{extra}{event_text}",
                parse_mode="HTML"
            )
            return

        # ОБЫЧНАЯ РЫБА
        region = get_chat_region(chat_id)
        hour = datetime.now().hour
        time_of_day = "night" if (hour >= 22 or hour < 6) else "day"
        available = []
        for fish in FISH_LIST:
            fname, femoji, fmin, fmax, fweight, fregion, ftime = fish
            if fregion not in ("any", region): continue
            if ftime not in ("any", time_of_day): continue
            available.append(fish)
        if not available: available = FISH_LIST
        total_weight = sum(f[4] for f in available)
        pick = random.uniform(0, total_weight); cumulative = 0
        chosen = available[0]
        for fish in available:
            cumulative += fish[4]
            if pick <= cumulative: chosen = fish; break
        fish_name = chosen[0]; fish_emoji = chosen[1]
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
        ach_text = "\n\n🎖 <b>Новые ачивки:</b>\n" + "\n".join(f"  • {a}" for a in new_ach) if new_ach else ""

        fish_price = get_fish_price(fish_name) + gear_flat
        xp_needed = xp_needed_for_level(new_level)
        bar_len = 10
        filled = min(bar_len, int((new_xp / xp_needed) * bar_len)) if xp_needed else 0
        xp_bar = "▰" * filled + "▱" * (bar_len - filled)

        weight = None
        for f in FISH_LIST:
            if f[0] == fish_name:
                weight = f[4]; break
        if weight is None: rarity_icon = "💎"; rarity_name = "Легендарная"
        elif weight >= 50: rarity_icon = "⚪"; rarity_name = "Обычная"
        elif weight >= 15: rarity_icon = "🟢"; rarity_name = "Необычная"
        elif weight >= 3: rarity_icon = "🔵"; rarity_name = "Редкая"
        elif weight >= 0.5: rarity_icon = "🟣"; rarity_name = "Эпическая"
        else: rarity_icon = "🟠"; rarity_name = "Мифическая"

        hour = datetime.now().hour
        time_icon = "🌙" if (hour >= 22 or hour < 6) else ("🌅" if hour < 11 else ("☀️" if hour < 18 else "🌇"))
        level_up_text = f"\n\n🎉 <b>УРОВЕНЬ ПОВЫШЕН!</b> Теперь <b>{new_level}</b>" if new_level > level else ""
        bait_text = "\n🍯 Прикормка активна" if bait_active else ""
        loc_text = f"\n{location['emoji']} Локация: {location['name']}"

        text = (
            f"🎣 <b>УЛОВ</b> {time_icon}\n\n{fish_emoji} <b>{fish_name}</b>\n"
            f"{rarity_icon} Редкость: <i>{rarity_name}</i>\n💵 Цена: <b>{fish_price}</b> 🍬\n"
            f"✨ Опыт: <b>+{xp_gain}</b> XP\n\n"
            f"📊 <b>Уровень {new_level}</b>\n<code>{xp_bar}</code> {new_xp}/{xp_needed}\n\n"
            f"🐟 Всего поймано: <b>{total_caught + 1}</b>\n📦 Продай: <code>.продать</code>"
            f"{level_up_text}{legendary_text}{bait_text}{loc_text}{event_text}{ach_text}"
        )
        await msg.edit_text(text, parse_mode="HTML")
    else:
        update_fishing(user_id, total_empty=total_empty + 1)
        set_fishing_last_fish(user_id)
        log_fishing(user_id, chat_id, "empty")
        phrases = ["🐟 Рыба ушла...","🌊 Ничего не поймал.","🪝 Пустой крючок...","💧 Только водоросли.",
                   "🎣 Попробуй ещё раз!","🦆 Утка утащила наживку!","🌧 Дождь спугнул рыбу...",
                   "🧦 Поймал старый носок...","👻 Тень мелькнула и исчезла...","🌪 Ветер унёс поплавок..."]
        phrase = random.choice(phrases)
        xp_needed = xp_needed_for_level(level)
        bar_len = 10
        filled = min(bar_len, int((xp / xp_needed) * bar_len)) if xp_needed else 0
        xp_bar = "▰" * filled + "▱" * (bar_len - filled)
        hour = datetime.now().hour
        time_icon = "🌙" if (hour >= 22 or hour < 6) else ("🌅" if hour < 11 else ("☀️" if hour < 18 else "🌇"))
        await msg.edit_text(
            f"🎣 <b>ПУСТО</b> {time_icon}\n\n{phrase}\n\n"
            f"📊 <b>Уровень {level}</b>\n<code>{xp_bar}</code> {xp}/{xp_needed}\n\n"
            f"📉 Пустых: <b>{total_empty + 1}</b>",
            parse_mode="HTML"
        )


@cmd("садок")
@cmd("моя рыба")
@cmd("рыбасадок")
async def fish_storage_cmd(message: types.Message):
    user_id = message.from_user.id
    storage = get_fish_storage(user_id)
    if not storage:
        return await message.reply("🎣 <b>Садок пуст</b>\n\nПоймай: <code>.рыбалка</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = "🎒 <b>Твой садок</b>\n\n"
    total_price = 0; total_count = 0
    sorted_fish = sorted(storage.items(), key=lambda x: get_fish_price(x[0]), reverse=True)
    for fish_name, data in sorted_fish:
        qty = data["quantity"]; emoji = data["emoji"]; price = get_fish_price(fish_name)
        total_price += price * qty; total_count += qty
        text += f"{emoji} <b>{fish_name}</b> × <b>{qty}</b> — {price} 🍬/шт\n"
    text += f"\n💰 <b>Всего:</b> {total_count} рыб на <b>{total_price}</b> 🍬 mos-конфеток"
    text += f"\n\n<code>.продать все</code>\n<code>.продать Щука</code>"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("продать", allow_args=True, args_pattern=r"^.+$")
async def sell_fish_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("📌 <code>.продать все</code>\n📌 <code>.продать Щука 5</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    storage = get_fish_storage(user_id)
    if not storage:
        return await message.reply("🎣 Садок пуст", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
        text += f"\n💰 +{total_price} 🍬 mos-конфеток\n📊 Всего: {total_count} рыб\n💼 Баланс: <b>{get_balance(user_id)}</b> 🍬"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    parts = query.split()
    fish_name_query = parts[0]
    matched_fish = None
    for fish_name in storage.keys():
        if fish_name_query.lower() in fish_name.lower() or fish_name.lower() in fish_name_query.lower():
            matched_fish = fish_name; break
    if not matched_fish:
        return await message.reply(f"{em('cross', '❌')} Не найдена.\n<code>.садок</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    available = storage[matched_fish]["quantity"]
    emoji = storage[matched_fish]["emoji"]; price = get_fish_price(matched_fish)
    if len(parts) >= 2 and parts[1].isdigit():
        qty = min(int(parts[1]), available)
        if qty < 1: qty = 1
    else: qty = available
    total_price = price * qty
    remove_fish_from_storage(user_id, matched_fish, qty)
    add_candies(user_id, total_price, 0)
    await message.reply(f"{em('check', '✅')} <b>Продано!</b>\n\n{emoji} <b>{matched_fish}</b> × <b>{qty}</b>\n💰 +{total_price} 🍬 mos-конфеток\n📊 Осталось: <b>{available - qty}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("рыбтоп")
async def fishing_top_cmd(message: types.Message):
    top = get_fishing_top(limit=10)
    if not top:
        return await message.reply("📭 Никто не рыбачил.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = "🏆 <b>Топ рыбаков:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, caught, level) in enumerate(top, 1):
        try:
            user = await bot.get_chat(user_id); name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{caught}</b> 🐟 (ур. {level})\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("моя рыбалка")
@cmd("рыбстата")
async def fishing_stats_cmd(message: types.Message):
    user_id = message.from_user.id
    info = get_fishing(user_id)
    (uid, level, xp, total_caught, total_empty, has_rod, bait_until, last_fish, inv, legendary) = info
    xp_needed = xp_needed_for_level(level)
    bait_active = is_bait_active(bait_until)
    bait_text = "✅ Активна" if bait_active else "❌ Нет"
    total = total_caught + total_empty
    success_rate = int(total_caught / total * 100) if total > 0 else 0
    user_cooldown = get_user_fish_cooldown(user_id)
    cooldown = format_fishing_cooldown(last_fish, user_cooldown)
    if cooldown > 0:
        hours = cooldown // 3600; mins = (cooldown % 3600) // 60
        parts = []
        if hours > 0: parts.append(f"{hours} ч.")
        if mins > 0: parts.append(f"{mins} мин.")
        cooldown_text = "⏳ " + " ".join(parts)
    else: cooldown_text = "✅ Готово"
    cd_min = user_cooldown // 60
    cd_hours = cd_min // 60
    cd_min = cd_min % 60
    cd_full_str = f"{cd_hours} ч. {cd_min} мин." if cd_hours > 0 else f"{cd_min} мин."
    bar_len = 12
    filled = min(bar_len, int((xp / xp_needed) * bar_len)) if xp_needed else 0
    xp_bar = "▰" * filled + "▱" * (bar_len - filled)
    region = get_chat_region(message.chat.id)
    region_names = {"river": "🏞 Река", "lake": "🌊 Озеро", "sea": "🌊 Море", "ocean": "🌌 Океан"}
    region_text = region_names.get(region, region)
    location_key = get_chat_location(message.chat.id)
    location = LOCATIONS.get(location_key, LOCATIONS["pier"])
    if level < 5: lvl_icon = "🟢"
    elif level < 15: lvl_icon = "🔵"
    elif level < 30: lvl_icon = "🟣"
    elif level < 60: lvl_icon = "🟠"
    else: lvl_icon = "🟡"
    await message.reply(
        f"🎣 <b>Твоя рыбалка</b>\n\n{lvl_icon} Уровень: <b>{level}</b>\n<code>{xp_bar}</code> {xp}/{xp_needed} XP\n\n"
        f"📍 Регион: {region_text}\n{location['emoji']} Локация: <b>{location['name']}</b>\n"
        f"🐟 Поймано: <b>{total_caught}</b>\n📉 Пустых: <b>{total_empty}</b>\n"
        f"🎯 Успешность: <b>{success_rate}%</b>\n💎 Легендарных: <b>{legendary or 0}</b>\n\n"
        f"🍯 Прикормка: {bait_text}\n⚙️ Кулдаун: <b>{cd_full_str}</b> (улучшай снасти!)\n⏰ Готовность: {cooldown_text}",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+прикормка"))
async def buy_bait_cmd(message: types.Message):
    user_id = message.from_user.id
    info = get_fishing(user_id)
    if is_bait_active(info[6]):
        return await message.reply("🍯 Уже активна.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    price = 20
    if get_balance(user_id) < price:
        return await message.reply(f"❌ Нужно <b>{price}</b> 🍬 mos-конфеток", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        conn.commit()
    set_fishing_bait(user_id)
    await message.reply(f"✅ <b>Прикормка куплена!</b>\n🍯 {BAIT_DURATION_HOURS} ч.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("магазин снастей")
@cmd("снасти")
async def fishing_shop_cmd(message: types.Message):
    user_id = message.from_user.id
    inv = get_fishing_inventory(user_id)
    text = "🛒 <b>Магазин снастей</b>\n\n"
    for key, gear in FISHING_GEAR.items():
        cur_level = inv.get(key, 0)
        if cur_level > 0:
            next_cost = int(gear["base_price"] * (cur_level + 1) * 0.6) if cur_level < gear["max_level"] else 0
            if cur_level >= gear["max_level"]:
                text += f"<b>{gear['name']}</b> — <b>УР. {cur_level}/{gear['max_level']} ✅ МАКС</b>\n   <i>{gear['desc']}</i>\n\n"
            else:
                text += (f"<b>{gear['name']}</b> — ур. <b>{cur_level}/{gear['max_level']}</b>\n"
                         f"   <i>{gear['desc']}</i>\n   ⬆️ Улучшить: <code>.улучшить {key}</code> ({next_cost} 🍬)\n\n")
        else:
            text += (f"<b>{gear['name']}</b> — <b>{gear['base_price']}</b> 🍬\n"
                     f"   <i>{gear['desc']}</i>\n   Купить: <code>.купить {key}</code>\n\n")
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*купить\s+\S+', m.text.strip(), re.IGNORECASE)
    and not re.match(r'^\s*[.\/!+-]?\s*купить\s+вип\b', m.text.strip(), re.IGNORECASE)
    and not re.match(r'^\s*[.\/!+-]?\s*купить\s+коины\b', m.text.strip(), re.IGNORECASE))
async def fishing_buy_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("📌 <code>.магазин снастей</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    query = args[1].lower()
    gear_key = None
    for k, g in FISHING_GEAR.items():
        if query == k or query in g["name"].lower():
            gear_key = k; break
    if not gear_key:
        return await message.reply("❌ Снасть не найдена. <code>.магазин снастей</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    gear = FISHING_GEAR[gear_key]
    user_id = message.from_user.id
    inv = get_fishing_inventory(user_id)
    if inv.get(gear_key, 0) > 0:
        return await message.reply(f"⚠️ Уже есть <b>{gear['name']}</b>. Улучшить: <code>.улучшить {gear_key}</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    price = gear["base_price"]
    if get_balance(user_id) < price:
        return await message.reply(f"❌ Нужно <b>{price}</b> 🍬 mos-конфеток", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        conn.commit()
    add_to_fishing_inventory(user_id, gear_key, 1)
    await message.reply(f"{em('check', '✅')} <b>Куплено!</b>\n\n{gear['name']} — ур. 1/{gear['max_level']}\n<i>{gear['desc']}</i>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*улучшить\s+\S+', m.text.strip(), re.IGNORECASE))
async def upgrade_gear_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("📌 <code>.улучшить hook</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    query = args[1].lower()
    gear_key = None
    for k, g in FISHING_GEAR.items():
        if query == k or query in g["name"].lower():
            gear_key = k; break
    if not gear_key:
        return await message.reply("❌ Снасть не найдена. <code>.магазин снастей</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    ok, msg_text, new_level = upgrade_fishing_gear(message.from_user.id, gear_key)
    if ok:
        gear = FISHING_GEAR[gear_key]
        await message.reply(f"✅ <b>{gear['name']} улучшено!</b>\n\n⬆️ Теперь уровень: <b>{new_level}/{gear['max_level']}</b>\n{msg_text}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    else:
        await message.reply(f"❌ {msg_text}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("инвентарь")
@cmd("инв")
async def fishing_inventory_cmd(message: types.Message):
    user_id = message.from_user.id
    inv = get_fishing_inventory(user_id)
    text = "🎒 <b>Твой инвентарь</b>\n\n"
    if not inv: text += "<i>Пусто. <code>.магазин снастей</code></i>\n"
    else:
        for key, level in inv.items():
            gear = FISHING_GEAR.get(key)
            if not gear: continue
            if isinstance(level, int) and level > 0:
                text += f"{gear['name']} — ур. <b>{level}/{gear.get('max_level', 1)}</b>\n   <i>{gear['desc']}</i>\n"
    gear_bonus, gear_flat, boat_level, legendary_bonus, rare_bonus, gear_info = get_fishing_gear_bonus(user_id)
    text += f"\n📊 <b>Бонусы:</b>\n"
    text += f"• К улову: <b>+{int(gear_bonus*100)}%</b>\n"
    text += f"• К цене рыбы: <b>+{gear_flat}</b> 🍬\n"
    if legendary_bonus: text += f"• К шансу легендарки: <b>+{legendary_bonus}%</b>\n"
    if rare_bonus: text += f"• К шансу редкой: <b>+{rare_bonus}%</b>\n"
    user_cooldown = get_user_fish_cooldown(user_id)
    cd_min = user_cooldown // 60
    cd_hours = cd_min // 60
    cd_min = cd_min % 60
    cd_str = f"{cd_hours} ч. {cd_min} мин." if cd_hours > 0 else f"{cd_min} мин."
    text += f"\n⚙️ Твой кулдаун: <b>{cd_str}</b>"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


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
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("событие")
@cmd("погода рыбалки")
async def fishing_event_cmd(message: types.Message):
    chat_id = message.chat.id
    event = get_active_event(chat_id)
    if not event:
        return await message.reply("☀️ <b>Сейчас штиль</b>\n\nСледующее событие появится в течение <b>1.5 часа</b>.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    ev_key, bonus, expires = event
    ev_data = FISHING_EVENTS.get(ev_key, {})
    try:
        exp_dt = datetime.strptime(expires[:19], "%Y-%m-%d %H:%M:%S")
        left_seconds = int((exp_dt - datetime.now()).total_seconds())
        if left_seconds < 0: left_seconds = 0
        left_min = left_seconds // 60
        left_hours = left_min // 60
        left_min = left_min % 60
        left_str = f"{left_hours} ч. {left_min} мин." if left_hours > 0 else f"{left_min} мин."
    except: left_str = "?"
    text = f"{ev_data.get('name', ev_key)}\n📈 Бонус: <b>×{bonus}</b>\n⏰ Осталось: <b>{left_str}</b>"
    if ev_data.get("rare_boost"): text += f"\n💎 Шанс редких ×{ev_data['rare_boost']}"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("локация", allow_args=True)
@cmd("локации", allow_args=True)
async def location_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только в группе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    current_key = get_chat_location(message.chat.id)
    current = LOCATIONS.get(current_key, LOCATIONS["pier"])
    args = message.text.split()
    if len(args) < 2:
        text = "🌊 <b>Локации рыбалки</b>\n\n"
        text += f"📍 <b>Сейчас:</b> {current['name']}\n\n"
        for key, loc in LOCATIONS.items():
            mark = "✅" if key == current_key else "•"
            vip = " 💎VIP" if loc["vip_required"] else ""
            text += (f"{mark} {loc['emoji']} <b>{loc['name']}</b>{vip}\n   <i>{loc['desc']}</i>\n"
                     f"   🔓 Мин. ур.: <b>{loc['min_level']}</b> | 🟣 Редкая: <b>+{loc['rare_chance']}%</b> | "
                     f"💎 Легендарка: <b>+{loc['legendary_chance']}%</b> | 💰 Сокровища: <b>+{loc['treasure_chance']}%</b>\n\n")
        text += f"📌 Сменить: <code>.локация пирс</code> (и т.д.)"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    query = args[1].lower()
    mapping = {"пирс":"pier","pier":"pier","камни":"rocks","rocks":"rocks","камень":"rocks",
               "мыс":"sunset_cape","закатный":"sunset_cape","sunset":"sunset_cape","cape":"sunset_cape",
               "бездна":"abyss","abyss":"abyss","остров":"treasure_island","island":"treasure_island","сокровищ":"treasure_island"}
    if query not in mapping:
        return await message.reply("❌ Доступные локации: <code>пирс</code>, <code>камни</code>, <code>закатный</code>, <code>бездна</code>, <code>остров</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    new_key = mapping[query]; new_loc = LOCATIONS[new_key]
    if not has_permission(message.chat.id, message.from_user.id, 3) and message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
        return await message.reply(f"❌ Только <b>Мл. Админ (3+)</b> может менять локацию.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_chat_location(message.chat.id, new_key)
    await message.reply(
        f"✅ <b>Локация изменена!</b>\n\n📍 Теперь: {new_loc['name']}\n   <i>{new_loc['desc']}</i>\n\n"
        f"🔓 Мин. ур.: <b>{new_loc['min_level']}</b>\n🟣 Редкая: <b>+{new_loc['rare_chance']}%</b>\n"
        f"💎 Легендарка: <b>+{new_loc['legendary_chance']}%</b>\n💰 Сокровища: <b>+{new_loc['treasure_chance']}%</b>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("регион", allow_args=True)
@cmd("рыбное место", allow_args=True)
async def region_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только в группе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    current = get_chat_region(message.chat.id)
    region_names = {"river": "🏞 Река", "lake": "🌊 Озеро", "sea": "🌊 Море", "ocean": "🌌 Океан"}
    args = message.text.split()
    if len(args) < 2:
        return await message.reply(
            f"🗺 <b>Регион рыбалки</b>\n\n📍 Сейчас: <b>{region_names.get(current, current)}</b>\n\n"
            f"📌 Сменить (ранг 3+): <code>.регион река|озеро|море|океан</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    if not has_permission(message.chat.id, message.from_user.id, 3):
        return await message.reply(f"{em('cross', '❌')} Нужен Мл. Админ (3+).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    sub = args[1].lower()
    mapping = {"река":"river","river":"river","рек":"river","озеро":"lake","lake":"lake","озер":"lake",
               "море":"sea","sea":"sea","мор":"sea","океан":"ocean","ocean":"ocean","оке":"ocean"}
    if sub not in mapping:
        return await message.reply("❌ Допустимые: <code>река</code>, <code>озеро</code>, <code>море</code>, <code>океан</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    new_region = mapping[sub]
    set_chat_region(message.chat.id, new_region)
    await message.reply(f"{em('check', '✅')} <b>Регион изменён!</b>\n\n📍 Теперь: <b>{region_names[new_region]}</b>\n👮 {mention(message.from_user)}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("турнир", allow_args=True)
async def fishing_tournament_cmd(message: types.Message):
    args = message.text.split(); chat_id = message.chat.id
    if len(args) >= 2 and args[1].lower() in ["участвовать", "join"]:
        tour = get_active_tournament(chat_id)
        if not tour:
            return await message.reply("❌ Нет активного турнира.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        join_tournament(chat_id, message.from_user.id)
        return await message.reply(f"{em('check', '✅')} Ты в турнире!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if len(args) >= 2 and args[1].lower() in ["стоп", "end"]:
        is_admin = (message.from_user.id == OWNER_ID or is_coowner(message.from_user.id)
                    or has_agent_rank(message.from_user.id, 1) or await is_tg_admin(chat_id, message.from_user.id))
        if not is_admin:
            return await message.reply(f"{em('cross', '❌')} Только админ.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        winners = end_tournament(chat_id)
        if not winners:
            return await message.reply("❌ Турнир не найден или нет участников.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        text = "🏆 <b>ТУРНИР ЗАВЕРШЁН!</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, caught, prize) in enumerate(winners):
            try:
                u = await bot.get_chat(uid); name = user_link(uid, u.first_name, u.username)
            except: name = f"ID {uid}"
            text += f"{medals[i]} {name} — <b>{caught}</b> 🐟 (+{prize} 🍬)\n"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    is_admin = (message.from_user.id == OWNER_ID or is_coowner(message.from_user.id)
                or has_agent_rank(message.from_user.id, 1) or await is_tg_admin(chat_id, message.from_user.id))
    if not is_admin:
        return await message.reply(f"{em('cross', '❌')} Только админ может запустить турнир.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    tour = get_active_tournament(chat_id)
    if tour:
        started_by, started_at, expires_at, prize = tour
        try:
            exp_dt = _parse_dt(expires_at)
            left = int((exp_dt - datetime.now()).total_seconds() / 60)
            if left < 0: left = 0
        except: left = 0
        members = get_tournament_members(chat_id, limit=10)
        text = f"🏆 <b>Турнир идёт</b>\n⏰ Осталось: <b>{left} мин.</b>\n💰 Приз: до <b>100</b> 🍬\n\n"
        if members:
            medals = ["🥇", "🥈", "🥉"]
            for i, (uid, caught) in enumerate(members):
                try:
                    u = await bot.get_chat(uid); name = user_link(uid, u.first_name, u.username)
                except: name = f"ID {uid}"
                m = medals[i] if i < 3 else f"{i+1}."
                text += f"{m} {name} — <b>{caught}</b> 🐟\n"
        text += f"\n📌 <code>.турнир участвовать</code>"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    create_tournament(chat_id, message.from_user.id, prize=100, duration_min=TOURNAMENT_DURATION_MIN)
    join_tournament(chat_id, message.from_user.id)
    await message.reply(
        f"🏆 <b>ТУРНИР ЗАПУЩЕН!</b>\n⏰ {TOURNAMENT_DURATION_MIN} мин.\n"
        f"💰 Призы: <b>20–100</b> 🍬 (зависит от числа участников)\n📌 <code>.турнир участвовать</code>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+событие", "+ событие"])
async def enable_events_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    if is_events_enabled(message.chat.id):
        return await message.reply("ℹ️ Уже включены.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_events_enabled(message.chat.id, True)
    await message.reply(f"{em('check', '✅')} Уведомления о событиях включены!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-событие", "- событие"])
async def disable_events_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await _check_automod_perms(message): return
    if not is_events_enabled(message.chat.id):
        return await message.reply("ℹ️ Уже выключены.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_events_enabled(message.chat.id, False)
    await message.reply(f"{em('check', '✅')} Уведомления о событиях выключены!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("события")
@cmd("уведомления")
async def events_status_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    enabled = is_events_enabled(message.chat.id)
    status = "🟢 включены" if enabled else "🔴 выключены"
    await message.reply(f"🌦 Уведомления о событиях: {status}\n\n<code>+событие</code> / <code>-событие</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))# ================= ГРАЖДАНСТВО =================
@dp.message(lambda m: m.text and m.text.lower().strip() == "+гражданство")
async def become_citizen_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    user_id = message.from_user.id; chat_id = message.chat.id
    current = get_citizenship_info(user_id)
    if current:
        if current[0] == chat_id: return
        return await message.reply("⚠️ Уже гражданин другого чата. <code>-гражданство</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_citizenship(user_id, chat_id)
    await message.reply(f"🏠 {mention(message.from_user)} стал гражданином чата!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("гражданство")
async def citizenship_info_cmd(message: types.Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    info = get_citizenship_info(target.id)
    if not info:
        return await message.reply(f"ℹ️ {mention(target)} не гражданин.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    chat_id, became_at = info
    try:
        chat = await bot.get_chat(chat_id); title = chat.title or f"Чат"
    except: title = "Чат"
    duration = format_citizenship_duration(became_at)
    await message.reply(f"🏠 {mention(target)}\n🏠 {title}\n⏳ {duration}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-гражданство")
async def leave_citizenship_cmd(message: types.Message):
    info = get_citizenship_info(message.from_user.id)
    if not info: return
    remove_citizenship(message.from_user.id)
    await message.reply("👋 Вы больше не гражданин.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("кто гражданин")
async def citizens_list_cmd(message: types.Message):
    citizens = get_chat_citizens(message.chat.id)
    if not citizens:
        return await message.reply("📭 Нет граждан.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"🏠 <b>Граждане</b> ({len(citizens)}):\n\n"
    for i, (user_id, became_at) in enumerate(citizens, 1):
        try:
            user = await bot.get_chat(user_id); name = user_link(user_id, user.first_name, user.username)
        except: name = f"ID: {user_id}"
        text += f"{i}. {name} — {format_citizenship_duration(became_at)}\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= НИК / ЗВАНИЕ / ДЕВИЗ / О СЕБЕ =================
@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+ник"))
async def set_nick_cmd(message: types.Message):
    if not message.text: return
    idx = message.text.lower().find("+ник")
    if idx == -1: return
    nick_html = _extract_html_after(message, idx + len("+ник"))[:300]
    if not nick_html: return
    set_user_nick(message.from_user.id, message.chat.id, nick_html)
    await message.reply(f"✅ Ник: <b>{nick_html}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-ник")
async def remove_nick_cmd(message: types.Message):
    remove_user_nick(message.from_user.id, message.chat.id)
    await message.reply("✅ Ник удалён.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("ник")
async def show_my_nick_cmd(message: types.Message):
    nick = get_user_nick(message.from_user.id, message.chat.id)
    if not nick: return await message.reply("📭 Нет ника.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"🔤 {nick}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+звание"))
async def set_rank_text_cmd(message: types.Message):
    if not message.text: return
    idx = message.text.lower().find("+звание")
    if idx == -1: return
    rank_html = _extract_html_after(message, idx + len("+звание"))[:300]
    if not rank_html: return
    set_user_rank_text(message.from_user.id, message.chat.id, rank_html)
    await message.reply(f"✅ Звание: <b>{rank_html}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-звание")
async def remove_rank_text_cmd(message: types.Message):
    remove_user_rank_text(message.from_user.id, message.chat.id)
    await message.reply("✅ Удалено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("звание")
async def show_my_rank_text_cmd(message: types.Message):
    rank_text = get_user_rank_text(message.from_user.id, message.chat.id)
    if not rank_text: return await message.reply("📭 Нет звания.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"📌 {rank_text}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+о себе"))
async def set_about_cmd(message: types.Message):
    if not message.text: return
    nl_idx = message.text.find("\n")
    if nl_idx == -1: return
    raw_html = _extract_html_after(message, nl_idx + 1)[:500]
    set_user_about(message.from_user.id, raw_html)
    await message.reply("✅ Сохранено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-о себе")
async def remove_about_cmd(message: types.Message):
    remove_user_about(message.from_user.id)
    await message.reply("✅ Удалено.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("о себе")
async def show_my_about_cmd(message: types.Message):
    text = get_user_about(message.from_user.id)
    if not text: return await message.reply("📭 Нет описания.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"✏️ {text}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+девиз"))
async def set_motto_cmd(message: types.Message):
    if not message.text: return
    idx = message.text.lower().find("+девиз")
    if idx == -1: return
    motto_html = _extract_html_after(message, idx + len("+девиз"))[:500]
    if not motto_html: return
    update_user_profile(message.from_user.id, "motto", motto_html)
    await message.reply("✅ Девиз установлен.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-девиз")
async def remove_motto_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "motto", None)
    await message.reply("✅ Удалён.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("девиз")
async def show_motto_cmd(message: types.Message):
    profile = get_user_profile(message.from_user.id)
    motto = profile[6] if len(profile) > 6 else None
    if not motto: return await message.reply("📭 Нет девиза.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"💭 {motto}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+анкета", "+ анкета"])
async def show_profile_flag_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "is_hidden", 0)
    await message.reply("✅ Анкета открыта.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-анкета", "- анкета"])
async def hide_profile_flag_cmd(message: types.Message):
    update_user_profile(message.from_user.id, "is_hidden", 1)
    await message.reply("✅ Анкета скрыта.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("моя стата")
async def my_stats_cmd(message: types.Message):
    try: chart_buf = generate_user_activity_chart(message.from_user.id, days=30)
    except: return
    if not chart_buf: return await message.reply("📭 Нет данных.", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply_photo(photo=types.BufferedInputFile(chart_buf.getvalue(), filename="my_stats.png"),
                              caption="📊 Статистика за 30 дней", parse_mode="HTML", **_reply_kwargs(message))


# ================= ЕЖЕДНЕВКА =================
@cmd("ежедневка")
async def daily_reward_cmd(message: types.Message):
    user_id = message.from_user.id
    today = datetime.now().date().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM daily_rewards WHERE user_id = ? AND date = ?", (user_id, today))
        if c.fetchone():
            return await message.reply("⏰ Уже получал(а) сегодня. Заходи завтра!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        c.execute("INSERT INTO daily_rewards (user_id, date) VALUES (?, ?)", (user_id, today))
        conn.commit()
    reward = random.randint(5, 20)
    add_candies(user_id, reward, 0)
    await message.reply(f"🎁 <b>Ежедневная награда!</b>\n💰 +{reward} 🍬 mos-конфеток", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= VIP =================
@cmd("вип цена", allow_args=True, args_pattern=r"^\d+$")
async def vip_set_price_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 4):
        return await message.reply(f"{em('cross', '❌')} Нужен ранг 4+.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    args = message.text.split()
    if len(args) < 3 or not args[2].isdigit():
        return await message.reply("📌 <code>.вип цена 150</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    new_price = int(args[2])
    if new_price < 1 or new_price > 100000:
        return await message.reply("❌ Цена от 1 до 100 000 🍬", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_vip_price(message.chat.id, new_price)
    await message.reply(f"{em('check', '✅')} Новая цена VIP: <b>{new_price} 🍬 mos-конфеток</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("вип")
async def vip_info_cmd(message: types.Message):
    if not await check_command_access(message, "вип"): return
    price = get_vip_price(message.chat.id)
    balance = get_balance(message.from_user.id)
    v = get_vip(message.from_user.id)
    already = ""
    if v:
        days = get_vip_days_left(message.from_user.id)
        already = f"\n\n💎 У тебя уже активен VIP — осталось <b>{days} дн.</b>\n(покупка продлит его на 30 дней)"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"💎 Купить VIP на месяц ({price} 🍬)", callback_data="vip_buy_1m")
    ]])
    await message.reply(
        f"💎 <b>VIP-статус</b>\n\n💰 Цена: <b>{price}</b> 🍬 mos-конфеток / мес\n💼 Баланс: <b>{balance}</b> 🍬"
        f"{already}\n\n📌 <code>.вип цена 150</code> — изменить цену (ранг 4+)\n📌 <code>.купить вип 6</code> — купить\n📌 <code>.мой вип</code> — твой VIP",
        parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb, **_reply_kwargs(message)
    )


@dp.callback_query(lambda c: c.data == "vip_buy_1m")
async def vip_buy_callback(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    price = get_vip_price(chat_id)
    balance = get_balance(user_id)
    if balance < price:
        return await callback.answer(f"❌ Недостаточно mos-конфеток.\nНужно: {price} 🍬\nУ тебя: {balance} 🍬", show_alert=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        conn.commit()
    new_exp = add_vip_months(user_id, 1)
    new_balance = get_balance(user_id)
    new_price = get_vip_price(chat_id)
    days_left = get_vip_days_left(user_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"💎 Продлить VIP ({new_price} 🍬)", callback_data="vip_buy_1m")
    ]])
    try:
        await callback.message.edit_text(
            f"💎 <b>VIP активирован!</b>\n\n👤 {mention(callback.from_user)}\n"
            f"📅 До: <b>{new_exp.strftime('%d.%m.%Y %H:%M')}</b>\n⏳ Осталось: <b>{days_left} дн.</b>\n"
            f"💰 Списано: <b>{price}</b> 🍬 mos-конфеток\n💼 Осталось: <b>{new_balance}</b> 🍬",
            parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb
        )
    except Exception:
        await callback.message.answer(f"💎 <b>VIP активирован!</b>\n\n📅 До: <b>{new_exp.strftime('%d.%m.%Y %H:%M')}</b>\n💰 Списано: <b>{price}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer("💎 VIP активирован!")


@cmd("купить вип", allow_args=True, args_pattern=r"^\d+$")
async def buy_vip_cmd(message: types.Message):
    if not await check_command_access(message, "купить вип"): return
    args = message.text.split()
    months = 1; target = message.from_user
    for a in args[2:]:
        if a.isdigit(): months = int(a)
        else:
            try: target = await bot.get_chat(a)
            except: pass
    if months < 1 or months > 12:
        return await message.reply("📌 <code>.купить вип 6</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    total = get_vip_price(message.chat.id) * months
    if get_balance(message.from_user.id) < total:
        return await message.reply(f"❌ Нужно <b>{total}</b> 🍬 mos-конфеток", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (total, message.from_user.id))
        conn.commit()
    new_exp = add_vip_months(target.id, months)
    await message.reply(f"💎 <b>VIP активирован!</b>\n\n👤 Кому: {mention(target)}\n📅 До: <b>{new_exp.strftime('%d.%m.%Y %H:%M')}</b>\n💰 -{total} 🍬", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("мой вип")
async def my_vip_cmd(message: types.Message):
    v = get_vip(message.from_user.id)
    if not v: return await message.reply("💎 Нет VIP.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    days = get_vip_days_left(message.from_user.id)
    await message.reply(f"💎 <b>Ваш VIP</b>\n📅 Осталось: <b>{days} дн.</b>\n😎 Эмодзи: {v[1] or '—'}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip().startswith("+вип эмодзи"))
async def set_vip_emoji_cmd(message: types.Message):
    if not get_vip(message.from_user.id): return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return
    set_vip_emoji(message.from_user.id, args[2].strip()[:10])
    await message.reply(f"{em('check', '✅')} Эмодзи: {args[2].strip()[:10]}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() == "-вип эмодзи")
async def remove_vip_emoji_cmd(message: types.Message):
    if not get_vip(message.from_user.id): return
    set_vip_emoji(message.from_user.id, None)
    await message.reply("✅ Убран.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= ЗАМЕТКИ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*\+заметка\s+\S+', m.text.strip(), re.IGNORECASE))
async def create_note_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    parts = message.text.split("\n", 1)
    first_line = parts[0]
    name_raw = re.sub(r'^[.\/!+-]?\s*\+заметка\s+', '', first_line, count=1, flags=re.IGNORECASE).strip()
    if not name_raw or len(parts) < 2:
        return await message.reply(
            "📌 <b>Формат:</b>\n"
            "<code>+заметка Название\nТекст заметки</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    name = name_raw[:60]
    nl_idx = message.text.find("\n")
    body_html = _extract_html_after(message, nl_idx + 1)[:3500]
    if not body_html or not body_html.strip():
        return await message.reply("❌ Текст заметки пустой.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    note_id = add_note(message.chat.id, name, body_html, message.from_user.id)
    if not note_id:
        return await message.reply(f"{em('cross', '❌')} Заметка с таким названием уже есть.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"{em('check', '✅')} Заметка <b>{html_escape_text(name)}</b> создана (ID: <code>{note_id}</code>)", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*-заметка\s+\S+', m.text.strip(), re.IGNORECASE))
async def delete_note_cmd(message: types.Message):
    if not has_permission(message.chat.id, message.from_user.id, 3): return
    arg = re.sub(r'^[.\/!+-]?\s*-заметка\s+', '', message.text.strip(), count=1, flags=re.IGNORECASE).strip()
    if not arg: return
    note = get_note_by_number(message.chat.id, int(arg)) if arg.isdigit() else get_note_by_name(message.chat.id, arg)
    if not note:
        return await message.reply(f"{em('cross', '❌')} Не найдена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    delete_note(message.chat.id, note[0])
    await message.reply(f"{em('check', '✅')} Удалена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("заметки")
async def list_notes_cmd(message: types.Message):
    notes = get_all_notes(message.chat.id)
    if not notes:
        return await message.reply("📭 Нет заметок.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = f"📋 <b>Заметки</b> ({len(notes)})\n\n"
    for i, (nid, name) in enumerate(notes, 1):
        text += f"<b>{i}.</b> {html_escape_text(name)}\n"
    text += f"\n📌 Открыть: <code>Заметка название</code> или <code>Заметка 1</code>"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@cmd("заметка", allow_args=True, args_pattern=r"^.+$")
async def get_note_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply(
            "📌 <b>Формат:</b>\n• <code>Заметка Название</code>\n• <code>Заметка 1</code> — по номеру",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    arg = args[1].strip()
    note = get_note_by_number(message.chat.id, int(arg)) if arg.isdigit() else get_note_by_name(message.chat.id, arg)
    if not note:
        return await message.reply(f"{em('cross', '❌')} Заметка не найдена.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    note_id, note_name, note_text = note[0], note[1], note[2]
    out = f"📌 <b>Заметка «{html_escape_text(note_name)}»</b>\n\n{note_text}"
    try:
        await message.reply(out, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        print(f"⚠️ Заметка HTML ошибка: {e}")
        clean = re.sub(r'<[^>]+>', '', note_text)
        await message.reply(f"📌 Заметка «{note_name}»\n\n{clean}", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= СЕТКА =================
@cmd("создать сетку", allow_args=True, args_pattern=r"^.+$")
async def create_grid_cmd(message: types.Message):
    if message.chat.type != "private":
        return await message.reply("⚠️ Только в ЛС с ботом.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Только владелец или совладелец бота.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("📌 <code>.создать сетку Название</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    name = args[2].strip().replace(" ", "_")[:24]
    grid_id = create_grid(name, message.from_user.id)
    if not grid_id:
        return await message.reply("❌ Сетка с таким именем уже есть.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(
        f"{em('check', '✅')} <b>Сетка создана!</b>\n\n🕸 Название: <b>{name}</b>\n🆔 ID: <code>{grid_id}</code>\n\n"
        f"📌 Теперь в каждом чате напишите: <code>сетка {name}</code>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("чаты")
async def list_grid_chats(message: types.Message):
    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не привязан к сетке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    chats = get_grid_chats(grid_id, include_hidden=False)
    if not chats:
        return await message.reply("📭 В сетке нет чатов.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM grids WHERE id = ?", (grid_id,))
        g = c.fetchone()
        grid_name = g[0] if g else f"#{grid_id}"
    text = f"📋 <b>Чаты сетки</b> «{grid_name}»:\n\n"
    for i, (chat_id, hidden, desc) in enumerate(chats, 1):
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title or f"Чат {chat_id}"
            link = None
            if chat.username: link = f"https://t.me/{chat.username}"
            else:
                try:
                    inv = await bot.create_chat_invite_link(chat_id)
                    link = inv.invite_link
                except: link = None
            if link: text += f"{i}. <a href='{link}'>{title}</a>\n"
            else: text += f"{i}. <b>{title}</b> <i>(без ссылки)</i>\n"
        except Exception as e:
            text += f"{i}. <code>{chat_id}</code> <i>(нет доступа)</i>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= +ЧАТ / -ЧАТ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*\+чат\b', m.text.strip(), re.IGNORECASE))
async def open_chat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только в группе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    has_rights = (
        message.from_user.id == OWNER_ID or is_coowner(message.from_user.id)
        or has_agent_rank(message.from_user.id, 1)
        or await is_tg_admin(message.chat.id, message.from_user.id)
        or has_permission(message.chat.id, message.from_user.id, 3)
    )
    if not has_rights:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        bm = await bot.get_chat_member(message.chat.id, bot.id)
        if bm.status not in ["administrator", "creator"]:
            return await message.reply(f"{em('cross', '❌')} Я не админ здесь.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if bm.status == "administrator" and not getattr(bm, "can_change_info", False):
            return await message.reply(f"{em('cross', '❌')} Нет права «Изменение настроек чата».", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} {e}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        await bot.set_chat_permissions(
            chat_id=message.chat.id,
            permissions=types.ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True, can_invite_users=True,
            )
        )
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} {e}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"{em('check', '✅')} <b>Чат открыт</b> для общения!\n👮 {mention(message.from_user)}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*-чат\b', m.text.strip(), re.IGNORECASE))
async def close_chat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только в группе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    has_rights = (
        message.from_user.id == OWNER_ID or is_coowner(message.from_user.id)
        or has_agent_rank(message.from_user.id, 1)
        or await is_tg_admin(message.chat.id, message.from_user.id)
        or has_permission(message.chat.id, message.from_user.id, 3)
    )
    if not has_rights:
        return await message.reply(f"{em('cross', '❌')} Недостаточно прав.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        bm = await bot.get_chat_member(message.chat.id, bot.id)
        if bm.status not in ["administrator", "creator"]:
            return await message.reply(f"{em('cross', '❌')} Я не админ здесь.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if bm.status == "administrator" and not getattr(bm, "can_change_info", False):
            return await message.reply(f"{em('cross', '❌')} Нет права «Изменение настроек чата».", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} {e}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    try:
        await bot.set_chat_permissions(
            chat_id=message.chat.id,
            permissions=types.ChatPermissions(
                can_send_messages=False, can_send_audios=False, can_send_documents=False,
                can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
                can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
                can_add_web_page_previews=False,
            )
        )
    except Exception as e:
        return await message.reply(f"{em('cross', '❌')} {e}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    await message.reply(f"{em('cross', '❌')} <b>Чат закрыт</b> для общения!\n👮 {mention(message.from_user)}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= СЕТКА — РОУТЕР =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*сетка\b', m.text.strip(), re.IGNORECASE))
async def grid_command_router(message: types.Message):
    if message.chat.type == "private":
        return await message.reply("⚠️ Команды сетки работают только в группе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    raw = re.sub(r'^[.\/!+-]\s*', '', message.text.strip())
    parts = raw.split()
    if len(parts) < 2:
        return await message.reply(
            "🕸 <b>Команды сетки:</b>\n\n"
            "• <code>сетка Название</code> — привязать чат\n"
            "• <code>сетка инфо</code>\n"
            "• <code>сетка +админ @user</code>\n"
            "• <code>сетка -админ @user</code>\n"
            "• <code>сетка разжаловать @user</code>\n"
            "• <code>сетка повысить @user 2</code>\n"
            "• <code>сетка понизить @user 1</code>\n"
            "• <code>сетка -чат</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    action = parts[1].lower()
    if action in ["инфо", "info"]:
        grid_id = get_chat_grid(message.chat.id)
        if not grid_id:
            return await message.reply("❌ Чат не привязан к сетке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
                    u = await bot.get_chat(uid); name = user_link(uid, u.first_name, u.username)
                except: name = f"<code>{uid}</code>"
                badge = "👑" if is_admin else "🛡"
                text += f"{badge} {name} — ранг {rank}\n"
        return await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))

    known_actions = ["+админ", "+админка", "+adm", "-админ", "-админка", "-adm",
                     "разжаловать", "снять", "повысить", "понизить", "-чат"]
    if action not in known_actions:
        grid_name = " ".join(parts[1:]).strip()
        existing_grid = get_chat_grid(message.chat.id)
        if existing_grid:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT name FROM grids WHERE id = ?", (existing_grid,))
                g = c.fetchone()
                cur_name = g[0] if g else "?"
            return await message.reply(
                f"ℹ️ Чат уже привязан к сетке <b>{cur_name}</b> (#{existing_grid}).\n📌 Отвязать: <code>сетка -чат</code>",
                parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
            )
        is_creator_of_chat = False
        try:
            m = await bot.get_chat_member(message.chat.id, message.from_user.id)
            is_creator_of_chat = (m.status == "creator")
        except: pass
        grid_lookup = get_grid_by_name(grid_name)
        has_rights = (message.from_user.id == OWNER_ID or is_coowner(message.from_user.id) or is_creator_of_chat)
        if grid_lookup and is_grid_moderator(grid_lookup[0], message.from_user.id, 5):
            has_rights = True
        if not has_rights:
            return await message.reply(f"{em('cross', '❌')} Только создатель чата или владелец сетки.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if not grid_lookup:
            return await message.reply(
                f"{em('cross', '❌')} Сетка <b>{grid_name}</b> не найдена.\n\n📌 Создать: <code>.создать сетку {grid_name}</code>",
                parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
            )
        grid_id, grid_db_name = grid_lookup
        add_chat_to_grid(grid_id, message.chat.id, hidden=0)
        return await message.reply(
            f"{em('check', '✅')} <b>Чат привязан к сетке!</b>\n\n🕸 Название: <b>{grid_db_name}</b>\n🆔 ID: <code>{grid_id}</code>\n👮 Сделал: {mention(message.from_user)}",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )

    grid_id = get_chat_grid(message.chat.id)
    if not grid_id:
        return await message.reply("❌ Чат не привязан к сетке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    actor_id = message.from_user.id
    chats = get_grid_chats(grid_id, include_hidden=True)

    async def notify_all_chats(text_to_send):
        sent = 0
        for cid, hidden, desc in chats:
            try:
                await bot.send_message(cid, text_to_send, parse_mode="HTML", disable_web_page_preview=True)
                sent += 1
            except Exception as e: pass
        return sent

    if action in ["+админ", "+админка", "+adm"]:
        if actor_id != OWNER_ID and not is_coowner(actor_id) and not is_grid_moderator(grid_id, actor_id, 5):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 5 в сетке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка +админ @user</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if target.id == OWNER_ID: return
        added_to = 0; failed = 0
        for chat_id, hidden, desc in chats:
            try:
                await bot.promote_chat_member(chat_id=chat_id, user_id=target.id, rights=full_admin_rights())
                added_to += 1
                mark_bot_promoted(target.id, chat_id, actor_id)
            except Exception as e:
                failed += 1
        add_grid_moderator(grid_id, target.id, rank=4, is_admin=1)
        for chat_id, hidden, desc in chats:
            try: set_rank(chat_id, target.id, 4, actor_id)
            except Exception as e: pass
        notify_text = (f"🛡 <b>Назначение администратора в сетке</b>\n\n"
                       f"👤 {mention(target)} назначен <b>ТГ-админом</b> во всех чатах сетки.\n"
                       f"👮 Сделал: {mention(message.from_user)}")
        sent = await notify_all_chats(notify_text)
        return await message.reply(
            f"{em('check', '✅')} {mention(target)} — <b>ТГ-админ</b> в <b>{added_to}/{len(chats)}</b> чатах.\n"
            f"⚠️ Ошибок: {failed}\n📢 Уведомлений: {sent}/{len(chats)}",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )

    if action in ["-админ", "-админка", "-adm"]:
        if actor_id != OWNER_ID and not is_coowner(actor_id) and not is_grid_moderator(grid_id, actor_id, 5):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 5 в сетке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка -админ @user</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if target.id == OWNER_ID: return
        removed_from = 0; failed = 0; errors_log = []
        for chat_id, hidden, desc in chats:
            success_this_chat = False
            try:
                await bot.promote_chat_member(chat_id=chat_id, user_id=target.id, rights=empty_admin_rights())
                success_this_chat = True
            except Exception as e:
                errors_log.append(f"{chat_id}: {e}")
            if success_this_chat: removed_from += 1
            else: failed += 1
            try: remove_rank(chat_id, target.id)
            except: pass
            try: unmark_bot_promoted(target.id, chat_id)
            except: pass
        remove_grid_moderator(grid_id, target.id)
        try: remove_grid_user_rank(grid_id, target.id)
        except: pass
        notify_text = (f"❌ <b>Снятие администратора в сетке</b>\n\n"
                       f"👤 {mention(target)} снят со всех постов в чатах сетки.\n"
                       f"👮 Сделал: {mention(message.from_user)}")
        sent = await notify_all_chats(notify_text)
        result_text = (
            f"{em('check', '✅')} <b>Снято с {mention(target)}:</b>\n\n"
            f"🛡 ТГ-права: <b>{removed_from}/{len(chats)}</b>\n"
            f"🎖 Ранг в боте: <b>сброшен</b>\n🕸 Ранг в сетке: <b>сброшен</b>\n"
            f"📢 Уведомлений: <b>{sent}/{len(chats)}</b>\n⚠️ Ошибок: <b>{failed}</b>"
        )
        if errors_log: result_text += f"\n\n<b>Первая ошибка:</b>\n<code>{errors_log[0][:200]}</code>"
        return await message.reply(result_text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))

    if action in ["разжаловать", "снять"]:
        if actor_id != OWNER_ID and not is_coowner(actor_id) and not is_grid_moderator(grid_id, actor_id, 3):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 3.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка разжаловать @user</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if target.id == OWNER_ID: return
        removed_from = 0
        for chat_id, hidden, desc in chats:
            try:
                await bot.promote_chat_member(chat_id=chat_id, user_id=target.id, rights=empty_admin_rights())
                removed_from += 1
            except Exception as e: pass
            try: remove_rank(chat_id, target.id)
            except: pass
            try: unmark_bot_promoted(target.id, chat_id)
            except: pass
        remove_grid_moderator(grid_id, target.id)
        try: remove_grid_user_rank(grid_id, target.id)
        except: pass
        notify_text = (f"📉 <b>Разжалование в сетке</b>\n\n"
                       f"👤 {mention(target)} полностью <b>разжалован</b> в сетке.\n"
                       f"👮 Сделал: {mention(message.from_user)}")
        sent = await notify_all_chats(notify_text)
        return await message.reply(
            f"{em('cross', '❌')} {mention(target)} <b>разжалован</b> в {removed_from}/{len(chats)} чатах.\n📢 Уведомлений: {sent}/{len(chats)}",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )

    if action in ["повысить"]:
        if actor_id != OWNER_ID and not is_coowner(actor_id) and not is_grid_moderator(grid_id, actor_id, 4):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 4.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка повысить @user 2</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if target.id == OWNER_ID: return
        new_rank = 1
        for p in parts:
            if p.isdigit(): new_rank = int(p); break
        new_rank = max(1, min(4, new_rank))
        try: set_grid_user_rank(grid_id, target.id, new_rank, actor_id)
        except: pass
        add_grid_moderator(grid_id, target.id, rank=new_rank, is_admin=0)
        set_rank_in_grid_chats(grid_id, target.id, new_rank, actor_id)
        notify_text = (f"🏆 <b>Повышение в сетке</b>\n\n"
                       f"👤 {mention(target)} повышен до ранга <b>{new_rank}</b>.\n"
                       f"👮 Сделал: {mention(message.from_user)}")
        sent = await notify_all_chats(notify_text)
        return await message.reply(f"🏆 {mention(target)} повышен до ранга <b>{new_rank}</b>\n📢 Уведомлений: {sent}/{len(chats)}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))

    if action in ["понизить"]:
        if actor_id != OWNER_ID and not is_coowner(actor_id) and not is_grid_moderator(grid_id, actor_id, 4):
            return await message.reply(f"{em('cross', '❌')} Нужен ранг 4.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        target, _ = await resolve_target(message)
        if not target:
            return await message.reply("📌 <code>сетка понизить @user 1</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        if target.id == OWNER_ID: return
        new_rank = 1
        for p in parts:
            if p.isdigit(): new_rank = int(p); break
        new_rank = max(1, min(4, new_rank))
        try: set_grid_user_rank(grid_id, target.id, new_rank, actor_id)
        except: pass
        add_grid_moderator(grid_id, target.id, rank=new_rank, is_admin=0)
        set_rank_in_grid_chats(grid_id, target.id, new_rank, actor_id)
        notify_text = (f"📉 <b>Понижение в сетке</b>\n\n"
                       f"👤 {mention(target)} понижен до ранга <b>{new_rank}</b>.\n"
                       f"👮 Сделал: {mention(message.from_user)}")
        sent = await notify_all_chats(notify_text)
        return await message.reply(f"📉 {mention(target)} понижен до ранга <b>{new_rank}</b>\n📢 Уведомлений: {sent}/{len(chats)}", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))

    if action in ["-чат"]:
        is_creator_of_chat = False
        try:
            m = await bot.get_chat_member(message.chat.id, actor_id)
            is_creator_of_chat = (m.status == "creator")
        except: pass
        if not (actor_id == OWNER_ID or is_coowner(actor_id) or is_creator_of_chat or is_grid_moderator(grid_id, actor_id, 5)):
            return await message.reply(f"{em('cross', '❌')} Только создатель чата или владелец сетки.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM grids WHERE id = ?", (grid_id,))
            g = c.fetchone()
            grid_name = g[0] if g else f"#{grid_id}"
            c.execute("DELETE FROM grid_chats WHERE grid_id = ? AND chat_id = ?", (grid_id, message.chat.id))
            conn.commit()
        return await message.reply(f"{em('check', '✅')} <b>Чат отвязан от сетки</b>\n\n🕸 Было: <b>{grid_name}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= РЕПОРТЫ =================
REPORT_COMMAND_RE = re.compile(r'^[.!\/+-]\s*репорт\b', re.IGNORECASE)


@dp.message(lambda m: m.text and REPORT_COMMAND_RE.match(m.text.strip()))
async def report_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not message.reply_to_message:
        return await message.reply(f"{em('cross', '❌')} Ответьте на сообщение.\n📌 <code>.репорт [причина]</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
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
        f"🏠 Чат: {chat_title}\n📝 {reason}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Проверен", callback_data=f"report_done:{report_id}")]])
    if report_chat_id:
        try:
            fwd = await bot.forward_message(chat_id=report_chat_id, from_chat_id=message.chat.id, message_id=target_msg.message_id)
            sent = await bot.send_message(report_chat_id, header, parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb, reply_to_message_id=fwd.message_id)
            set_report_forward_message(report_id, sent.message_id)
        except: pass
    await message.reply(f"✅ Жалоба отправлена. Спасибо!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.callback_query(lambda c: c.data and c.data.startswith("report_done:"))
async def report_done_handler(callback: types.CallbackQuery):
    report_id = int(callback.data.split(":")[1])
    report = get_report(report_id)
    if not report or report[13] == "reviewed": return await callback.answer("⚠️ Уже", show_alert=True)
    mark_report_reviewed(report_id, callback.from_user.id)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.answer("✅ Проверен")


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*\+репорты\b', m.text.strip(), re.IGNORECASE))
async def set_report_chat_cmd(message: types.Message):
    chat_id = message.chat.id; user_id = message.from_user.id
    if user_id != OWNER_ID and not is_coowner(user_id) and not has_permission(chat_id, user_id, 3):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("📌 <b>Формат:</b>\n<code>+репорты КОДЧАТА</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    report_chat_id = get_chat_by_code(args[1].strip().upper())
    if not report_chat_id:
        return await message.reply(f"{em('cross', '❌')} Чат с таким кодом не найден.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_report_chat(chat_id, report_chat_id, user_id)
    await message.reply(f"{em('check', '✅')} <b>Репорты привязаны!</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


# ================= БЭКАП / ИМПОРТ =================
@cmd("бэкап")
async def backup_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id): return
    try:
        with open(DATABASE_PATH, "rb") as f:
            data = f.read()
        await message.reply_document(types.BufferedInputFile(data, filename=f"bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"), caption="💾 Бэкап", **_reply_kwargs(message))
    except Exception as e:
        await message.reply(f"❌ {e}", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.sub(r'^[.\/!+-]\s*', '', m.text.strip().lower()) == "импорт")
async def import_db_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id): return
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply(f"{em('cross', '❌')} <b>Ответьте на .db файл командой .импорт</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    doc = message.reply_to_message.document
    if not doc.file_name.lower().endswith(".db"):
        return await message.reply(f"{em('cross', '❌')} Только <code>.db</code>.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        return await message.reply(f"{em('cross', '❌')} Файл больше 20 МБ.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    status_msg = await message.reply("📥 Скачиваю...", **_reply_kwargs(message))
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
            return await status_msg.edit_text(f"{em('cross', '❌')} Не база Mos-бота.", parse_mode="HTML")
        os.makedirs("backups", exist_ok=True)
        old_backup = f"backups/old_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil
        if os.path.exists(DATABASE_PATH): shutil.copy2(DATABASE_PATH, old_backup)
        shutil.move(temp_path, DATABASE_PATH)
        try: init_db()
        except: pass
        size_mb = doc.file_size / (1024 * 1024) if doc.file_size else 0
        await status_msg.edit_text(f"{em('check', '✅')} <b>База импортирована!</b>\n\n💾 Размер: <b>{size_mb:.2f} МБ</b>\n\n⚠️ <b>ПЕРЕЗАПУСТИТЕ БОТА</b>", parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        await status_msg.edit_text(f"{em('cross', '❌')} Ошибка: <code>{e}</code>", parse_mode="HTML")# ================= БРАКИ =================
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*брак(\s|$)', m.text.strip(), re.IGNORECASE))
async def marriage_router(message: types.Message):
    txt = message.text.strip()
    txt = re.sub(r'^[.\/!+-]\s*', '', txt)
    rest = re.sub(r'^брак\s*', '', txt, count=1, flags=re.IGNORECASE).strip()
    if rest.lower().startswith("цена продления"):
        return await set_marriage_price_cmd(message)
    if rest.lower().startswith("продлить"):
        return await prolong_marriage_cmd(message)
    if rest.lower().startswith("режим развода"):
        return await set_divorce_mode_cmd(message)
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif rest:
        for w in rest.split():
            if w.startswith("@"):
                try:
                    target = await bot.get_chat(w); break
                except:
                    return await message.reply(f"{em('cross', '❌')} Пользователь <code>{w}</code> не найден.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
            if w.isdigit():
                try:
                    target = await bot.get_chat(int(w)); break
                except: pass
    if not target:
        return await message.reply(
            "💍 <b>Как жениться:</b>\n\n• Ответь на сообщение юзера: <code>брак</code>\n• Или: <code>брак @username</code>",
            parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
        )
    if target.id == message.from_user.id:
        return await message.reply(f"{em('cross', '❌')} На себя нельзя.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if target.is_bot:
        return await message.reply(f"{em('cross', '❌')} Нельзя на бота.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if get_marriage(message.chat.id, message.from_user.id):
        return await message.reply(f"{em('cross', '❌')} Ты уже в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if get_marriage(message.chat.id, target.id):
        return await message.reply(f"{em('cross', '❌')} {mention(target)} уже в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    div = get_divorced_marriage(message.chat.id, message.from_user.id)
    if div:
        restore_marriage(div[0])
        return await message.reply("💞 <b>Брак восстановлен!</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    add_proposal(message.chat.id, message.from_user.id, target.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept:{message.from_user.id}:{target.id}:{message.chat.id}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"marry_reject:{message.from_user.id}:{target.id}:{message.chat.id}")
    ]])
    await message.reply(
        f"💍 <b>Предложение!</b>\n\n{mention(message.from_user)} → {mention(target)}\n\n{mention(target)}, ты согласен(на)?",
        parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb, **_reply_kwargs(message)
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
        fu = await bot.get_chat(from_id); tu = await bot.get_chat(to_id)
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
        return await message.reply("💔 Ты не в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra = mar
    partner_id = u2_id if u1_id == message.from_user.id else u1_id
    partner_name = u2_name if u1_id == message.from_user.id else u1_name
    duration = format_marriage_duration(married_at, extra or 0)
    divorce_marriage(message.chat.id, message.from_user.id)
    await message.reply(
        f"💔 {mention(message.from_user)} и {mention_by_id(partner_id, partner_name)} развелись.\n📅 Длился: <b>{duration}</b>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("мой брак")
@cmd("моя пара")
async def my_marriage_cmd(message: types.Message):
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar:
        return await message.reply("💔 Ты не в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra = mar
    partner_id = u2_id if u1_id == message.from_user.id else u1_id
    partner_name = u2_name if u1_id == message.from_user.id else u1_name
    duration = format_marriage_duration(married_at, extra or 0)
    await message.reply(
        f"💍 <b>Ваш брак</b>\n\n👫 {mention(message.from_user)} 💞 {mention_by_id(partner_id, partner_name)}\n📅 {married_at[:10]}\n⏳ Вместе: <b>{duration}</b>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("твой брак", allow_args=True, args_pattern=r"^(@\S+|\d+)$")
async def user_marriage_cmd(message: types.Message):
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
    if not target:
        return await message.reply("📌 <b>Формат:</b>\n• <code>твой брак @user</code>\n• Ответом на сообщение", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    mar = get_marriage(message.chat.id, target.id)
    if not mar:
        return await message.reply(f"💔 {mention(target)} не в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    _, u1_id, u2_id, u1_name, u2_name, married_at, _, _, _, extra = mar
    partner_id = u2_id if u1_id == target.id else u1_id
    partner_name = u2_name if u1_id == target.id else u1_name
    duration = format_marriage_duration(married_at, extra or 0)
    await message.reply(
        f"💍 <b>Брак {mention(target)}</b>\n\n👫 {mention_by_id(u1_id, u1_name)} 💞 {mention_by_id(u2_id, u2_name)}\n📅 {married_at[:10]}\n⏳ Вместе: <b>{duration}</b>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@cmd("браки")
async def marriages_list_cmd(message: types.Message):
    pairs = get_all_marriages(message.chat.id)
    if not pairs:
        return await message.reply("📭 В этом чате пока нет браков.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = "💍 <b>Браки в этом чате:</b>\n\n"
    for i, (u1_id, u1_name, u2_id, u2_name, married_at, extra) in enumerate(pairs, 1):
        duration = format_marriage_duration(married_at, extra or 0)
        text += f"{i}. {mention_by_id(u1_id, u1_name)} 💞 {mention_by_id(u2_id, u2_name)} — <i>{duration}</i>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*брак\s+цена\s+продления\s+\d+', m.text.strip(), re.IGNORECASE))
async def set_marriage_price_cmd(message: types.Message):
    if not await check_command_access(message, "брак"): return
    args = message.text.split()
    price = int(args[-1])
    if price < 1 or price > 10000:
        return await message.reply("❌ Цена от 1 до 10000 🍬", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_marriage_price(message.chat.id, price)
    await message.reply(f"{em('check', '✅')} Цена продления брака: <b>{price} 🍬</b> за 1 день.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*брак\s+продлить\s+\d+', m.text.strip(), re.IGNORECASE))
async def prolong_marriage_cmd(message: types.Message):
    if not await check_command_access(message, "брак"): return
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar:
        return await message.reply("💔 Ты не в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    args = message.text.split()
    days = int(args[-1])
    if days < 1 or days > 365:
        return await message.reply("❌ Дней от 1 до 365", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    settings = get_marriage_settings(message.chat.id)
    price_per_day = settings[0]
    total_cost = price_per_day * days
    if get_balance(message.from_user.id) < total_cost:
        return await message.reply(f"❌ Нужно <b>{total_cost}</b> 🍬 (по {price_per_day} за день).", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE candies SET balance = balance - ? WHERE user_id = ?", (total_cost, message.from_user.id))
        conn.commit()
    add_marriage_days(message.chat.id, message.from_user.id, days)
    await message.reply(f"{em('check', '✅')} Брак продлён на <b>{days} дн.</b>\n💰 Списано: <b>{total_cost}</b> 🍬", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*брак\s+режим\s+развода', m.text.strip(), re.IGNORECASE))
async def set_divorce_mode_cmd(message: types.Message):
    if not await check_command_access(message, "брак"): return
    args = message.text.split(maxsplit=3)
    mode = args[3].lower() if len(args) > 3 else "показать"
    settings = get_marriage_settings(message.chat.id)
    current_mode = settings[1]
    if mode in ["выключить", "off"]:
        set_divorce_mode(message.chat.id, "выключить")
        return await message.reply(f"{em('check', '✅')} Автоматическое расторжение браков <b>отключено</b>.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if mode == "один":
        set_divorce_mode(message.chat.id, "один")
        return await message.reply(f"{em('check', '✅')} Режим: брак расторгается, если <b>один</b> из супругов выйдет.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if mode == "оба":
        set_divorce_mode(message.chat.id, "оба")
        return await message.reply(f"{em('check', '✅')} Режим: брак расторгается, если <b>оба</b> супруга выйдут.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    mode_names = {"выключить": "❌ Выключено", "один": "👤 Один", "оба": "👥 Оба"}
    await message.reply(
        f"💔 <b>Режим развода</b>\n\nТекущий: <b>{mode_names.get(current_mode, current_mode)}</b>\n\n"
        f"<code>брак режим развода выключить</code>\n<code>брак режим развода один</code>\n<code>брак режим развода оба</code>",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*поженить\s+пару\b', m.text.strip(), re.IGNORECASE))
async def force_marry_cmd(message: types.Message):
    if not await check_command_access(message, "поженить пару"): return
    args = message.text.split()
    target1 = None; target2 = None
    for a in args[2:]:
        if a.startswith("@"):
            try:
                user = await bot.get_chat(a)
                if not target1: target1 = user
                elif not target2: target2 = user
            except: pass
        elif a.isdigit():
            try:
                user = await bot.get_chat(int(a))
                if not target1: target1 = user
                elif not target2: target2 = user
            except: pass
    if not target1 or not target2:
        return await message.reply("📌 <code>.поженить пару @user1 @user2</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if target1.id == target2.id:
        return await message.reply("❌ Нельзя поженить одного и того же.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if get_marriage(message.chat.id, target1.id) or get_marriage(message.chat.id, target2.id):
        return await message.reply("❌ Кто-то уже в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    create_marriage(message.chat.id, target1.id, target1.first_name, target2.id, target2.first_name)
    await message.reply(
        f"💍💐 <b>Свадьба!</b>\n\n{mention(target1)} и {mention(target2)} теперь в браке!\n👮 Сделал: {mention(message.from_user)}",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*развести\s+пару\b', m.text.strip(), re.IGNORECASE))
async def force_divorce_cmd(message: types.Message):
    if not await check_command_access(message, "развести пару"): return
    args = message.text.split()
    target1 = None; target2 = None
    for a in args[2:]:
        if a.startswith("@"):
            try:
                user = await bot.get_chat(a)
                if not target1: target1 = user
                elif not target2: target2 = user
            except: pass
        elif a.isdigit():
            try:
                user = await bot.get_chat(int(a))
                if not target1: target1 = user
                elif not target2: target2 = user
            except: pass
    if not target1 or not target2:
        return await message.reply("📌 <code>.развести пару @user1 @user2</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    mar = get_marriage_by_users(message.chat.id, target1.id, target2.id)
    if not mar:
        return await message.reply("❌ Эти пользователи не в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    divorce_marriage(message.chat.id, target1.id)
    await message.reply(
        f"💔 {mention(target1)} и {mention(target2)} разведены.\n👮 Сделал: {mention(message.from_user)}",
        parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message)
    )


@dp.message(lambda m: m.text and re.sub(r'^[.\/!+-]\s*', '', m.text.strip().lower()) in ["сброс браков"])
async def reset_marriages_cmd(message: types.Message):
    if not await check_command_access(message, "сброс браков"): return
    count = reset_all_marriages(message.chat.id)
    await message.reply(f"{em('check', '✅')} Сброшено браков: <b>{count}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.sub(r'^[.\/!+-]\s*', '', m.text.strip().lower()) in ["развести вышедших"])
async def divorce_left_cmd(message: types.Message):
    if not await check_command_access(message, "развести вышедших"): return
    settings = get_marriage_settings(message.chat.id)
    mode = settings[1]
    if mode == "выключить":
        return await message.reply("❌ Режим развода выключен.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    pairs = get_all_marriages(message.chat.id)
    divorced_count = 0
    for u1_id, u1_name, u2_id, u2_name, married_at, extra in pairs:
        try:
            m1 = await bot.get_chat_member(message.chat.id, u1_id)
            m2 = await bot.get_chat_member(message.chat.id, u2_id)
            u1_left = m1.status in ["left", "kicked"]
            u2_left = m2.status in ["left", "kicked"]
            should_divorce = False
            if mode == "один" and (u1_left or u2_left): should_divorce = True
            elif mode == "оба" and u1_left and u2_left: should_divorce = True
            if should_divorce:
                divorce_marriage(message.chat.id, u1_id)
                divorced_count += 1
        except: pass
    await message.reply(f"{em('check', '✅')} Разведено пар: <b>{divorced_count}</b>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+-]?\s*топ\s+браков\b', m.text.strip(), re.IGNORECASE))
async def marriage_top_cmd(message: types.Message):
    if not await check_command_access(message, "топ браков"): return
    pairs = get_top_marriages(message.chat.id)
    if not pairs:
        return await message.reply("📭 Топ браков пуст. Добавьте свой брак в топ: <code>+брак рейтинг</code>", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    text = "🏆 <b>Топ браков:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (u1_id, u1_name, u2_id, u2_name, married_at, extra) in enumerate(pairs, 1):
        duration = format_marriage_duration(married_at, extra or 0)
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {mention_by_id(u1_id, u1_name)} 💞 {mention_by_id(u2_id, u2_name)} — <i>{duration}</i>\n"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["+брак рейтинг"])
async def add_marriage_to_top_cmd(message: types.Message):
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar:
        return await message.reply("💔 Ты не в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if mar[8] == 1:
        return await message.reply("ℹ️ Твой брак уже в топе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_marriage_top_status(message.chat.id, message.from_user.id, True)
    await message.reply(f"{em('check', '✅')} Твой брак добавлен в топ!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))


@dp.message(lambda m: m.text and m.text.lower().strip() in ["-брак рейтинг"])
async def remove_marriage_from_top_cmd(message: types.Message):
    mar = get_marriage(message.chat.id, message.from_user.id)
    if not mar:
        return await message.reply("💔 Ты не в браке.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    if mar[8] == 0:
        return await message.reply("ℹ️ Твоего брака нет в топе.", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))
    set_marriage_top_status(message.chat.id, message.from_user.id, False)
    await message.reply(f"{em('check', '✅')} Твой брак удалён из топа!", parse_mode="HTML", disable_web_page_preview=True, **_reply_kwargs(message))# ================= РП ХЕНДЛЕР (ФИКС: идёт на цель, не на автора) =================
@dp.message(lambda m: m.text and not m.text.startswith(('.', '+', '-', '!', '/'))
    and not m.text.lower().strip().startswith("брак")
    and not m.text.lower().strip().startswith("сетка")
    and not m.text.lower().strip().startswith("заметка")
    and not m.text.lower().strip().startswith("заметки")
    and not m.text.lower().strip().startswith("мой ")
    and not m.text.lower().strip().startswith("моя ")
    and not m.text.lower().strip().startswith("твоя ")
    and not m.text.lower().strip().startswith("твой ")
    and not m.text.lower().strip().startswith("мойдр")
    and not m.text.lower().strip().startswith("мойпол")
    and not m.text.lower().strip().startswith("мойгород"))
async def standard_rp_handler(message: types.Message):
    if not message.text:
        return
    txt = message.text.strip()
    if not txt:
        return

    txt_lines = txt.split("\n", 1)
    first_line = txt_lines[0].strip()
    first_line_lower = first_line.lower()
    comment = txt_lines[1].strip() if len(txt_lines) > 1 else ""

    actor = message.from_user

    # ========== ЕДИНАЯ ЛОГИКА ОПРЕДЕЛЕНИЯ ЦЕЛИ ==========
    target = None
    reply_to_id = None

    if message.reply_to_message and message.reply_to_message.from_user:
        reply_user = message.reply_to_message.from_user
        # Reply на бота или на себя — игнорируем
        if not reply_user.is_bot and reply_user.id != actor.id:
            target = reply_user
            reply_to_id = message.reply_to_message.message_id

    # ========== 1. ПОЛЬЗОВАТЕЛЬСКИЕ РП ==========
    rp_emoji = None
    rp_template = None
    matched_name = None
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT emoji, text FROM rp_commands WHERE chat_id = ? AND LOWER(name) = ?",
                  (message.chat.id, first_line_lower))
        row = c.fetchone()
        if row:
            rp_emoji, rp_template = row
            matched_name = first_line_lower
        else:
            first_word = first_line_lower.split()[0] if first_line_lower.split() else ""
            if first_word and first_word != first_line_lower:
                c.execute("SELECT emoji, text FROM rp_commands WHERE chat_id = ? AND LOWER(name) = ?",
                          (message.chat.id, first_word))
                row = c.fetchone()
                if row:
                    rp_emoji, rp_template = row
                    matched_name = first_word
        if not rp_template:
            c.execute("SELECT emoji, text FROM global_rp_commands WHERE LOWER(name) = ? LIMIT 1",
                      (first_line_lower,))
            row = c.fetchone()
            if row:
                rp_emoji, rp_template = row
                matched_name = first_line_lower
            else:
                first_word = first_line_lower.split()[0] if first_line_lower.split() else ""
                if first_word and first_word != first_line_lower:
                    c.execute("SELECT emoji, text FROM global_rp_commands WHERE LOWER(name) = ? LIMIT 1",
                              (first_word,))
                    row = c.fetchone()
                    if row:
                        rp_emoji, rp_template = row
                        matched_name = first_word

    if rp_template:
        # Если цели из reply нет — ищем @user / ID в тексте
        if target is None and matched_name:
            rest_first = first_line_lower[len(matched_name):].strip()
            for w in rest_first.split():
                clean = w.strip().rstrip('.,;:!?')
                if clean.startswith('@'):
                    try:
                        candidate = await bot.get_chat(clean)
                        if not candidate.is_bot and candidate.id != actor.id:
                            target = candidate
                            break
                    except Exception:
                        pass
                elif clean.isdigit() and len(clean) >= 6:
                    try:
                        candidate = await bot.get_chat(int(clean))
                        if not candidate.is_bot and candidate.id != actor.id:
                            target = candidate
                            break
                    except Exception:
                        pass

        if target is not None:
            out = rp_template.replace("{actor}", mention(actor)).replace("{target}", mention(target))
        else:
            out = rp_template.replace("{actor}", mention(actor)).replace("{target}", mention(actor))
            reply_to_id = None

        final_text = f"{rp_emoji} {out}"
        if comment:
            final_text += f"\n\n{comment}"
        send_kwargs = {"parse_mode": "HTML", "disable_web_page_preview": True}
        if reply_to_id:
            send_kwargs["reply_to_message_id"] = reply_to_id
        await message.reply(final_text, **send_kwargs)
        return

    # ========== 2. СТАНДАРТНЫЕ РП ==========
    rp_data = None
    rp_name = None
    if first_line_lower in STANDARD_RP:
        rp_name = first_line_lower
        rp_data = STANDARD_RP[first_line_lower]
    else:
        for name in sorted(STANDARD_RP.keys(), key=len, reverse=True):
            if first_line_lower.startswith(name):
                rest = first_line_lower[len(name):]
                if not rest or rest[0] == ' ':
                    rp_name = name
                    rp_data = STANDARD_RP[name]
                    break
    if not rp_data:
        return

    # Если цели из reply нет — ищем @user / ID
    if target is None:
        rest_first = first_line_lower[len(rp_name):].strip()
        if rest_first:
            for w in rest_first.split():
                clean = w.strip().rstrip('.,;:!?')
                if clean.startswith('@'):
                    try:
                        candidate = await bot.get_chat(clean)
                        if not candidate.is_bot and candidate.id != actor.id:
                            target = candidate
                            break
                    except Exception:
                        pass
                elif clean.isdigit() and len(clean) >= 6:
                    try:
                        candidate = await bot.get_chat(int(clean))
                        if not candidate.is_bot and candidate.id != actor.id:
                            target = candidate
                            break
                    except Exception:
                        pass

    if target is None:
        text_out = f"{rp_data['emoji']} {rp_data['self_text'].format(actor=mention(actor), target=mention(actor))}"
        if comment:
            text_out += f"\n\n{comment}"
        await message.reply(text_out, parse_mode="HTML", disable_web_page_preview=True)
        return

    text_out = f"{rp_data['emoji']} {rp_data['text'].format(actor=mention(actor), target=mention(target))}"
    if comment:
        text_out += f"\n\n{comment}"
    send_kwargs = {"parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_to_id:
        send_kwargs["reply_to_message_id"] = reply_to_id
    await message.reply(text_out, **send_kwargs)# ================= АВТО-РЕАКЦИИ =================
AUTO_REACTIONS_ENABLED = True
AUTO_REACTION_CHANCE = 7
AUTO_REACTION_COOLDOWN = 15
AUTO_REACTION_PER_USER_COOLDOWN = 120
AUTO_REACTION_MIN_LEN = 3

REACTION_POOL = ["👍", "❤️", "🔥", "😂", "🎉", "👏", "🤔", "💯", "⚡️", "😍", "🥰", "😎", "🤝", "✨"]

_last_auto_reaction_time = 0.0
_user_last_reaction = {}
_user_reaction_count = {}


def _should_auto_react(message: types.Message) -> bool:
    global _last_auto_reaction_time
    if not AUTO_REACTIONS_ENABLED:
        return False
    if not message.from_user or message.from_user.is_bot:
        return False
    if message.chat.type not in ["group", "supergroup"]:
        return False

    txt = (message.text or message.caption or "").strip()
    if not txt:
        return False
    if txt[0] in ".!/+-":
        return False
    if len(txt) < AUTO_REACTION_MIN_LEN:
        return False

    now = datetime.now().timestamp()
    if now - _last_auto_reaction_time < AUTO_REACTION_COOLDOWN:
        return False

    uid = message.from_user.id
    last = _user_last_reaction.get(uid, 0)
    if now - last < AUTO_REACTION_PER_USER_COOLDOWN:
        return False

    if random.randint(1, 100) > AUTO_REACTION_CHANCE:
        return False

    return True


async def _auto_react(message: types.Message):
    global _last_auto_reaction_time
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if bot_member.status not in ("administrator", "creator"):
            return
    except Exception:
        return

    uid = message.from_user.id
    cnt = _user_reaction_count.get(uid, 0)
    if cnt < 3:
        emoji = "👍"
    else:
        pool = [e for e in REACTION_POOL if e != "👍"]
        emoji = random.choice(pool) if pool else "👍"

    try:
        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[types.ReactionTypeEmoji(emoji=emoji)]
        )
        _last_auto_reaction_time = datetime.now().timestamp()
        _user_last_reaction[uid] = _last_auto_reaction_time
        _user_reaction_count[uid] = cnt + 1
    except Exception as e:
        print(f"⚠️ Авто-реакция: {e}")


# ================= ОБРАБОТКА ВСЕХ СООБЩЕНИЙ =================
@dp.message()
async def all_messages(message: types.Message):
    if not message.from_user or message.from_user.is_bot: return

    # Сбор премиум-эмодзи
    try:
        ents = message.entities or message.caption_entities or []
        text_src = message.text or message.caption or ""
        for e in ents:
            if e.type == "custom_emoji":
                eid = getattr(e, "custom_emoji_id", None)
                if eid and text_src:
                    raw = text_src[e.offset:e.offset + e.length]
                    register_premium_emoji(eid, raw)
    except Exception:
        pass

    if message.from_user.id != OWNER_ID and not is_coowner(message.from_user.id):
        if is_bot_ignored(message.from_user.id): return
        if is_in_antispam(message.from_user.id):
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT 1 FROM ignore_list WHERE user_id = ? LIMIT 1", (message.from_user.id,))
                if c.fetchone(): return

    if message.chat.type in ["group", "supergroup"]:
        if is_link_filter_enabled(message.chat.id):
            is_staff = (message.from_user.id == OWNER_ID or is_coowner(message.from_user.id)
                        or has_agent_rank(message.from_user.id, 1)
                        or await is_tg_admin(message.chat.id, message.from_user.id))
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

    if message.chat.type in ["group", "supergroup"]:
        user_id = message.from_user.id
        chat_id = message.chat.id
        is_staff = (user_id == OWNER_ID or is_coowner(user_id)
                    or has_agent_rank(user_id, 1) or get_rank(chat_id, user_id) >= 3)
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

    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status == "creator":
            if get_rank(message.chat.id, message.from_user.id) < 5:
                set_rank(message.chat.id, message.from_user.id, 5, message.from_user.id)
    except: pass

    if message.reply_to_message and message.reply_to_message.from_user:
        ru = message.reply_to_message.from_user
        if not ru.is_bot:
            register_user(ru.id, ru.first_name, ru.username or "")

    register_user(message.from_user.id, message.from_user.first_name, message.from_user.username or "")

    try:
        entities = message.entities or message.caption_entities or []
        for e in entities:
            if e.type == "text_mention" and getattr(e, "user", None) and not e.user.is_bot:
                ru = e.user
                register_user(ru.id, ru.first_name, ru.username or "")
    except: pass

    if is_agent(message.from_user.id) or message.from_user.id == OWNER_ID or is_coowner(message.from_user.id):
        update_agent_activity(message.from_user.id)

    today = datetime.now().date().isoformat()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO messages_stats (user_id, chat_id, date, count, last_message_at)
               VALUES (?, ?, ?, 1, ?)
               ON CONFLICT(user_id, chat_id, date) DO UPDATE SET
                   count = count + 1,
                   last_message_at = excluded.last_message_at""",
            (message.from_user.id, message.chat.id, today, now_str)
        )
        conn.commit()

    # ================= АВТО-РЕАКЦИИ =================
    try:
        if _should_auto_react(message):
            asyncio.create_task(_auto_react(message))
    except Exception as e:
        print(f"⚠️ auto_react: {e}")


def _should_ai_reply(message: types.Message) -> bool:
    global _last_ai_reply_time
    
    # Для теста: если написать "тест ии", бот ответит 100%
    if message.text and "тест ии" in message.text.lower():
        logging.info("🚀 AI: Принудительный тест!")
        return True

    logging.info(f"🔍 AI check: chat={message.chat.id} type={message.chat.type}")
    
    if not ai_client:
        logging.info("🔍 AI: ai_client=None (ключ не загружен)")
        return False
    if not message.from_user or message.from_user.is_bot:
        return False
    if message.chat.type not in ["group", "supergroup"]:
        return False
    if message.chat.id in _ai_disabled_chats:
        logging.info("🔍 AI: выключен в этом чате")
        return False

    txt = (message.text or message.caption or "").strip()
    if not txt or len(txt) < AI_REPLY_MIN_LEN:
        return False
    if txt[0] in ".!/+-":
        return False
    if has_link(txt):
        return False

    first_line_lower = txt.split("\n", 1)[0].strip().lower()
    if first_line_lower in STANDARD_RP:
        return False
    for rp_name in STANDARD_RP.keys():
        if first_line_lower.startswith(rp_name + " ") or first_line_lower == rp_name:
            return False

    now = datetime.now().timestamp()
    uid = message.from_user.id
    if now - _last_ai_reply_time < AI_REPLY_COOLDOWN:
        logging.info(f"🔍 AI: глобальный кулдаун")
        return False
    if now - _user_last_ai_reply.get(uid, 0) < AI_REPLY_PER_USER:
        logging.info(f"🔍 AI: кулдаун юзера")
        return False

    chance = AI_REPLY_CHANCE_QUESTION if "?" in txt else AI_REPLY_CHANCE
    r = random.randint(1, 100)
    logging.info(f"🔍 AI: шанс {chance}%, выпало {r} -> {'ОТВЕЧАЮ' if r <= chance else 'МОЛЧУ'}")
    return r <= chance


async def _ai_reply(message: types.Message):
    global _last_ai_reply_time
    chat_id = message.chat.id
    uid = message.from_user.id
    txt = (message.text or message.caption or "").strip()

    history = _chat_history.get(chat_id, [])
    history.append({"role": "user", "content": txt})
    history = history[-AI_MAX_HISTORY * 2:]
    _chat_history[chat_id] = history

    try:
        logging.info(f"🚀 AI: Отправляю запрос в ZvenoAI ({ZVENOAI_MODEL})...")
        response = await ai_client.chat.completions.create(
            model=ZVENOAI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            max_tokens=150,
            temperature=1.3,
        )
        reply_text = response.choices[0].message.content.strip()
        logging.info(f"✅ AI: Получен ответ: {reply_text[:50]}")
        
        if not reply_text: 
            logging.info("❌ AI: Пустой ответ от модели")
            return

        history.append({"role": "assistant", "content": reply_text})
        _chat_history[chat_id] = history[-AI_MAX_HISTORY * 2:]

        await message.reply(reply_text)
        _last_ai_reply_time = datetime.now().timestamp()
        _user_last_ai_reply[uid] = _last_ai_reply_time
    except APIError as e:
        logging.error(f"❌ AI APIError: {e}")
    except Exception as e:
        logging.error(f"❌ AI Exception: {type(e).__name__}: {e}")


# ================= ВХОД В ЧАТ =================
@dp.chat_member()
async def on_join(event: types.ChatMemberUpdated):
    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status
    if new_status != "member": return
    if old_status in ["member", "administrator", "creator"]: return
    user = event.new_chat_member.user
    chat_id = event.chat.id

    if not user.is_bot:
        register_user(user.id, user.first_name, user.username or "")

    if is_antispam_enabled(chat_id) and is_in_antispam(user.id):
        try:
            until = datetime.now() + timedelta(seconds=90)
            await bot.ban_chat_member(chat_id, user.id, until_date=until)
            add_chat_ban(chat_id, user.id, "АС: вход в чат", 0, until.isoformat(), was_antispam=1)
            name = html_escape_text(user.first_name or "Пользователь")
            if getattr(user, "username", None): nick = f'<a href="https://t.me/{user.username}">{name}</a>'
            else: nick = f'<a href="tg://user?id={user.id}">{name}</a>'
            reason = "спам"
            info = get_antispam_info(user.id)
            if info and info[0]: reason = info[0]
            await bot.send_message(
                chat_id,
                f"🚫 {nick} — <b>в антиспаме Mos</b>\n📝 Причина: <i>{reason}</i>",
                parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception as e:
            print(f"⚠️ on_join АС кик: {e}")
        return

    bot_can_restrict = False
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status == "creator": bot_can_restrict = True
        elif bot_member.status == "administrator":
            bot_can_restrict = getattr(bot_member, "can_restrict_members", False)
    except: bot_can_restrict = False

    captcha_on = is_captcha_enabled(chat_id) and bot_can_restrict
    if not captcha_on:
        greeting = get_greeting(chat_id)
        if greeting:
            try:
                sent = await bot.send_message(chat_id, format_greeting(greeting, user, event.chat), parse_mode="HTML")
                _schedule_greeting_delete(chat_id, sent)
            except Exception as e: pass
        await _send_short_about_if_enabled(chat_id, user)
        return

    try:
        await bot.restrict_chat_member(chat_id=chat_id, user_id=user.id, permissions=types.ChatPermissions(can_send_messages=False))
    except Exception as e:
        greeting = get_greeting(chat_id)
        if greeting:
            try:
                sent = await bot.send_message(chat_id, format_greeting(greeting, user, event.chat), parse_mode="HTML")
                _schedule_greeting_delete(chat_id, sent)
            except: pass
        await _send_short_about_if_enabled(chat_id, user)
        return

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
    except Exception as e:
        greeting = get_greeting(chat_id)
        if greeting:
            try:
                sent = await bot.send_message(chat_id, format_greeting(greeting, user, event.chat), parse_mode="HTML")
                _schedule_greeting_delete(chat_id, sent)
            except: pass
        await _send_short_about_if_enabled(chat_id, user)


async def captcha_timeout(user_id, chat_id):
    try:
        timeout_sec = get_captcha_timeout(chat_id)
    except Exception:
        timeout_sec = 120
    if timeout_sec < 10: timeout_sec = 10
    if timeout_sec > 3600: timeout_sec = 3600
    await asyncio.sleep(timeout_sec)
    cap = get_captcha(user_id, chat_id)
    if not cap: return
    user = None
    try:
        user = await bot.get_chat(user_id)
    except Exception:
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT first_name, username FROM users WHERE user_id = ?", (user_id,))
                r = c.fetchone()
            if r: user = _FakeUser(user_id, r[0] or f"ID {user_id}", r[1])
        except Exception: user = None
    try:
        await bot.ban_chat_member(chat_id, user_id)
        await bot.unban_chat_member(chat_id, user_id)
    except: pass
    if cap[0]:
        try: await bot.delete_message(chat_id, cap[0])
        except: pass
    if user is not None:
        try:
            name = html_escape_text(user.first_name or "Пользователь")
            if getattr(user, "username", None): nick = f'<a href="https://t.me/{user.username}">{name}</a>'
            else: nick = f'<a href="tg://user?id={user.id}">{name}</a>'
            await bot.send_message(
                chat_id,
                f"🔴 {nick} исключен(а) из беседы\n💬 Причина: ❗️Не пройдена капча\n👤 Модератор: <b>mos</b>",
                parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception as e:
            print(f"⚠️ captcha_timeout сообщение: {e}")
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
        user = callback.from_user
        name = html_escape_text(user.first_name or "Пользователь")
        if getattr(user, "username", None): nick = f'<a href="https://t.me/{user.username}">{name}</a>'
        else: nick = f'<a href="tg://user?id={user.id}">{name}</a>'
        remove_captcha(target_user_id, chat_id)
        try: await callback.message.delete()
        except: pass
        try:
            await bot.send_message(
                chat_id,
                f"🔴 {nick} исключен(а) из беседы\n💬 Причина: ❗️Не пройдена капча\n👤 Модератор: <b>mos</b>",
                parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception as e:
            print(f"⚠️ captcha неверный ответ: {e}")
        return await callback.answer("❌ Неверно!", show_alert=True)

    started_at = get_captcha_created_at(target_user_id, chat_id)
    elapsed_str = None
    if started_at:
        elapsed = (datetime.now() - started_at).total_seconds()
        if elapsed < 0: elapsed = 0
        elapsed_str = f"{elapsed:.2f}"

    try:
        await bot.restrict_chat_member(chat_id=chat_id, user_id=target_user_id,
            permissions=types.ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_send_polls=True, can_invite_users=True))
    except: pass
    remove_captcha(target_user_id, chat_id)
    try: await callback.message.delete()
    except: pass

    user = callback.from_user
    name = html_escape_text(user.first_name or "Пользователь")
    if getattr(user, "username", None): nick = f'<a href="https://t.me/{user.username}">{name}</a>'
    else: nick = f'<a href="tg://user?id={user.id}">{name}</a>'

    if elapsed_str is not None:
        try:
            await bot.send_message(
                chat_id,
                f"✅ {nick} завершил(-а) прохождение капчи за <b>{elapsed_str} секунд</b>",
                parse_mode="HTML", disable_web_page_preview=True
            )
        except: pass

    greeting = get_greeting(chat_id)
    if greeting:
        try:
            chat = await bot.get_chat(chat_id)
            sent = await bot.send_message(chat_id, format_greeting(greeting, user, chat), parse_mode="HTML")
            _schedule_greeting_delete(chat_id, sent)
        except: pass
    else:
        sent = await bot.send_message(chat_id, f"👋 Привет, {mention(user)}!", parse_mode="HTML")
        _schedule_greeting_delete(chat_id, sent)

    await _send_short_about_if_enabled(chat_id, user)
    await callback.answer("✅ Пройдена!")


@dp.chat_join_request()
async def on_join_request(request: types.ChatJoinRequest):
    chat_id = request.chat.id; user = request.from_user
    if not user.is_bot:
        register_user(user.id, user.first_name, user.username or "")
    if is_antispam_enabled(chat_id) and is_in_antispam(user.id):
        try: await request.decline()
        except: pass
        return
    try: await request.approve()
    except: pass


@dp.message(Command("my_bans"))
async def my_bans_cmd(message: types.Message):
    if message.chat.type != "private":
        return await message.reply(
            "🔒 Команда доступна <b>только в личных сообщениях</b> с ботом.\n📌 Напиши мне в ЛС: <code>/my_bans</code>",
            parse_mode="HTML", disable_web_page_preview=True
        )
    user_id = message.from_user.id
    bans = []
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT chat_id, reason, banned_at, until_date 
                     FROM chat_bans WHERE user_id = ? 
                     ORDER BY banned_at DESC LIMIT 50""", (user_id,))
        rows = c.fetchall()
    for chat_id, reason, banned_at, until_date in rows:
        status = ""
        if until_date:
            try:
                until_dt = datetime.fromisoformat(until_date.replace("Z", ""))
                if until_dt > datetime.now():
                    dur = int((until_dt - datetime.now()).total_seconds())
                    if dur >= 86400: status = f"ещё {dur // 86400} дн."
                    elif dur >= 3600: status = f"ещё {dur // 3600} ч."
                    elif dur >= 60: status = f"ещё {dur // 60} мин."
                    else: status = f"ещё {dur} сек."
                else: status = "истёк"
            except: status = ""
        else: status = "навсегда"
        try:
            chat = await bot.get_chat(chat_id); chat_title = chat.title or f"Чат {chat_id}"
        except: chat_title = f"Чат {chat_id}"
        bans.append(f"🚫 <b>{html_escape_text(chat_title)}</b>\n   📝 <i>{html_escape_text(reason or 'без причины')}</i>\n   🗓 {_fmt_added_dt(banned_at)} · ⏱ {status}")
    if is_in_antispam(user_id):
        info = get_antispam_info(user_id)
        reason = info[0] if info else "?"
        bans.append(f"\n☢️ <b>Антиспам:</b> <i>{html_escape_text(reason)}</i>")
    if not bans:
        return await message.reply("✅ <b>У вас нет банов.</b>\n\n🎉 Всё чисто!", parse_mode="HTML", disable_web_page_preview=True)
    text = f"📋 <b>Ваши наказания</b>\n\n" + "\n\n".join(bans)
    text += f"\n\n💬 <i>Если считаешь наказание несправедливым — напиши в поддержку:</i> {SUPPORT_CHAT_LINK}"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    if event.new_chat_member.status not in ["member", "administrator"]: return
    chat_id = event.chat.id
    chat_type = event.chat.type
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            u = admin.user
            register_user(u.id, u.first_name, u.username or "")
            if admin.status == "creator": set_rank(chat_id, u.id, 5, u.id)
            elif admin.status == "administrator":
                if get_rank(chat_id, u.id) < 4:
                    set_rank(chat_id, u.id, 4, u.id)
                    mark_bot_promoted(u.id, chat_id, u.id)
    except Exception as e:
        print(f"⚠️ on_bot_added admins: {e}")
    try:
        creator = await bot.get_chat_member(chat_id, event.from_user.id)
        if creator.status == "creator":
            register_user(event.from_user.id, event.from_user.first_name, event.from_user.username or "")
            set_rank(chat_id, event.from_user.id, 5, event.from_user.id)
    except: pass
    if event.from_user:
        u = event.from_user
        register_user(u.id, u.first_name, u.username or "")
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT DISTINCT user_id FROM messages_stats WHERE chat_id = ?", (chat_id,))
            known = c.fetchall()
        for (uid,) in known:
            with sqlite3.connect(DATABASE_PATH) as conn2:
                c2 = conn2.cursor()
                c2.execute("SELECT first_name, username FROM users WHERE user_id = ?", (uid,))
                r = c2.fetchone()
            if r: register_user(uid, r[0], r[1] or "")
    except: pass
    if chat_type in ["group", "supergroup"]:
        try:
            await bot.send_message(
                chat_id,
                f"👋 Я <b>{BOT_NAME}</b>!\n⚙️ Дайте права администратора для полной работы.\n🆘 {SUPPORT_CHAT_LINK}",
                parse_mode="HTML"
            )
        except: pass


@dp.business_connection()
async def on_business_connection(connection: types.BusinessConnection):
    if connection.is_enabled:
        save_business_connection(connection.user.id, connection.id)# ================= ПЕРЕЕЗД / ИМПОРТ =================
MOVE_CMD_RE = re.compile(
    r'^\s*[.\/!+\-]?\s*(переезд|импорт\s+заметок|импорт\s+команд|импорт\s+настроек)\b',
    re.IGNORECASE
)


async def _move_check_access(message: types.Message, source_chat_id: int | None = None) -> tuple[bool, str]:
    actor_id = message.from_user.id
    target_chat_id = message.chat.id

    if actor_id == OWNER_ID or is_coowner(actor_id):
        return True, ""

    is_target_creator = False
    try:
        m = await bot.get_chat_member(target_chat_id, actor_id)
        is_target_creator = (m.status == "creator")
    except Exception:
        pass

    target_rank = get_rank(target_chat_id, actor_id)
    if not (is_target_creator or target_rank >= 5):
        return False, ("❌ <b>Недостаточно прав в целевом чате.</b>\n"
                       "Нужно быть <b>создателем чата</b> или иметь <b>5 ранг</b> в боте.")

    if source_chat_id:
        is_source_creator = False
        try:
            m = await bot.get_chat_member(source_chat_id, actor_id)
            is_source_creator = (m.status == "creator")
        except Exception:
            return False, "❌ Бот не состоит в исходном чате или нет доступа."
        source_rank = get_rank(source_chat_id, actor_id)
        if not (is_source_creator or source_rank >= 5):
            return False, ("❌ <b>Недостаточно прав в исходном чате.</b>\n"
                           "Нужно быть <b>создателем чата</b> или иметь <b>5 ранг</b> в боте.")

    return True, ""


def _resolve_source_chat(code: str) -> int | None:
    code = code.strip().upper()
    return get_chat_by_code(code)


def _import_notes_replace(source_chat_id: int, target_chat_id: int) -> int:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM notes WHERE chat_id = ?", (target_chat_id,))
        c.execute("SELECT name, text, created_by FROM notes WHERE chat_id = ?", (source_chat_id,))
        rows = c.fetchall()
        for name, text, created_by in rows:
            try:
                c.execute("INSERT INTO notes (chat_id, name, text, created_by) VALUES (?, ?, ?, ?)",
                          (target_chat_id, name, text, created_by or 0))
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        return len(rows)


def _import_notes_add(source_chat_id: int, target_chat_id: int) -> tuple[int, list]:
    added = 0
    conflicts = []
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM notes WHERE chat_id = ?", (target_chat_id,))
        existing = {r[0].lower() for r in c.fetchall()}
        c.execute("SELECT name, text, created_by FROM notes WHERE chat_id = ?", (source_chat_id,))
        rows = c.fetchall()
        for name, text, created_by in rows:
            if name.lower() in existing:
                conflicts.append(name)
                continue
            try:
                c.execute("INSERT INTO notes (chat_id, name, text, created_by) VALUES (?, ?, ?, ?)",
                          (target_chat_id, name, text, created_by or 0))
                added += 1
            except sqlite3.IntegrityError:
                conflicts.append(name)
        conn.commit()
    return added, conflicts


def _import_commands(source_chat_id: int, target_chat_id: int) -> int:
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM command_access WHERE chat_id = ?", (target_chat_id,))
        c.execute("SELECT command, min_rank FROM command_access WHERE chat_id = ?", (source_chat_id,))
        rows = c.fetchall()
        for cmd_name, min_rank in rows:
            c.execute("INSERT OR REPLACE INTO command_access (chat_id, command, min_rank) VALUES (?, ?, ?)",
                      (target_chat_id, cmd_name, min_rank))
        conn.commit()
        return len(rows)


def _import_settings(source_chat_id: int, target_chat_id: int) -> dict:
    report = {}
    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()

        c.execute("SELECT text, updated_by FROM chat_rules WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO chat_rules (chat_id, text, updated_by, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                      (target_chat_id, r[0], r[1]))
            report["Правила"] = "✅"

        c.execute("SELECT text FROM greetings WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO greetings (chat_id, text, updated_by) VALUES (?, ?, ?)",
                      (target_chat_id, r[0], 0))
            report["Приветствие"] = "✅"

        c.execute("SELECT seconds FROM greeting_autodelete WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO greeting_autodelete (chat_id, seconds) VALUES (?, ?)",
                      (target_chat_id, r[0]))
            report["Автоудаление приветствий"] = f"✅ ({r[0]}с)"

        c.execute("SELECT enabled FROM short_about_settings WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO short_about_settings (chat_id, enabled) VALUES (?, ?)",
                      (target_chat_id, r[0]))
            report["Коротко про"] = "✅" if r[0] else "❌"

        c.execute("""SELECT antimat, antiflood, anticaps, antisticker,
                            antimat_action, antimat_mute, antimat_ban,
                            antiflood_action, antiflood_mute, antiflood_ban,
                            anticaps_action, anticaps_mute, anticaps_ban,
                            antisticker_action, antisticker_mute, antisticker_ban
                     FROM automod_settings WHERE chat_id = ?""", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("""INSERT OR REPLACE INTO automod_settings
                (chat_id, antimat, antiflood, anticaps, antisticker,
                 antimat_action, antimat_mute, antimat_ban,
                 antiflood_action, antiflood_mute, antiflood_ban,
                 anticaps_action, anticaps_mute, anticaps_ban,
                 antisticker_action, antisticker_mute, antisticker_ban)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (target_chat_id, *r))
            report["Автомод"] = "✅"

        c.execute("SELECT enabled, timeout FROM captcha_settings WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO captcha_settings (chat_id, enabled, timeout) VALUES (?, ?, ?)",
                      (target_chat_id, r[0], r[1] or 120))
            report["Капча"] = f"✅ ({'вкл' if r[0] else 'выкл'})"

        c.execute("SELECT antispam_enabled FROM chat_antispam_settings WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO chat_antispam_settings (chat_id, antispam_enabled) VALUES (?, ?)",
                      (target_chat_id, r[0]))
            report["Антиспам"] = "✅" if r[0] else "❌"

        c.execute("SELECT enabled FROM link_filter WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO link_filter (chat_id, enabled) VALUES (?, ?)",
                      (target_chat_id, r[0]))
            report["Фильтр ссылок"] = "✅" if r[0] else "❌"

        c.execute("SELECT warn_limit, action, duration_text, duration_seconds FROM warn_settings WHERE chat_id = ?",
                  (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("""INSERT OR REPLACE INTO warn_settings
                (chat_id, warn_limit, action, duration_text, duration_seconds)
                VALUES (?, ?, ?, ?, ?)""", (target_chat_id, *r))
            report["Настройки варнов"] = "✅"

        c.execute("SELECT notify_enabled FROM command_notify_settings WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO command_notify_settings (chat_id, notify_enabled) VALUES (?, ?)",
                      (target_chat_id, r[0]))
            report["Оповещения команд"] = "✅" if r[0] else "❌"

        c.execute("SELECT value FROM global_settings WHERE key = ?", (f"location:{source_chat_id}",))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)",
                      (f"location:{target_chat_id}", r[0]))
            report["Локация рыбалки"] = f"✅ ({r[0]})"

        c.execute("SELECT value FROM global_settings WHERE key = ?", (f"region:{source_chat_id}",))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)",
                      (f"region:{target_chat_id}", r[0]))
            report["Регион рыбалки"] = f"✅ ({r[0]})"

        c.execute("SELECT events_enabled FROM fishing_events_settings WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO fishing_events_settings (chat_id, events_enabled) VALUES (?, ?)",
                      (target_chat_id, r[0]))
            report["События рыбалки"] = "✅" if r[0] else "❌"

        c.execute("SELECT header FROM chat_moderators_header WHERE chat_id = ?", (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO chat_moderators_header (chat_id, header) VALUES (?, ?)",
                      (target_chat_id, r[0]))
            report["Заголовок модераторов"] = "✅"

        c.execute("""SELECT rank, title_nom, title_gen, title_dat, title_ins, title_plu
                     FROM moderator_titles WHERE chat_id = ?""", (source_chat_id,))
        rows = c.fetchall()
        if rows:
            c.execute("DELETE FROM moderator_titles WHERE chat_id = ?", (target_chat_id,))
            for row in rows:
                c.execute("""INSERT OR REPLACE INTO moderator_titles
                    (chat_id, rank, title_nom, title_gen, title_dat, title_ins, title_plu)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""", (target_chat_id, *row))
            report["Названия рангов"] = f"✅ ({len(rows)})"

        c.execute("SELECT prolong_price, divorce_mode FROM marriage_settings WHERE chat_id = ?",
                  (source_chat_id,))
        r = c.fetchone()
        if r:
            c.execute("INSERT OR REPLACE INTO marriage_settings (chat_id, prolong_price, divorce_mode) VALUES (?, ?, ?)",
                      (target_chat_id, r[0], r[1]))
            report["Настройки браков"] = "✅"

        conn.commit()
    return report


@dp.message(lambda m: m.text and MOVE_CMD_RE.match(m.text.strip()))
async def move_import_router(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML",
                                    disable_web_page_preview=True)

    txt = message.text.strip()
    txt_clean = re.sub(r'^[.\/!+\-]\s*', '', txt)

    action = None
    source_code = None

    m = re.match(r'^переезд\s+([A-Za-z0-9]+)\s*$', txt_clean, re.IGNORECASE)
    if m:
        action = "full"
        source_code = m.group(1)

    if not action:
        m = re.match(r'^импорт\s+заметок\s+(с\s+заменой\s+)?(добавить\s+)?из\s+([A-Za-z0-9]+)\s*$',
                     txt_clean, re.IGNORECASE)
        if m:
            if m.group(1):
                action = "notes_replace"
            elif m.group(2):
                action = "notes_add"
            else:
                action = "notes_replace"
            source_code = m.group(3)

    if not action:
        m = re.match(r'^импорт\s+команд\s+из\s+([A-Za-z0-9]+)\s*$', txt_clean, re.IGNORECASE)
        if m:
            action = "commands"
            source_code = m.group(1)

    if not action:
        m = re.match(r'^импорт\s+настроек\s+из\s+([A-Za-z0-9]+)\s*$', txt_clean, re.IGNORECASE)
        if m:
            action = "settings"
            source_code = m.group(1)

    if not action:
        return

    source_chat_id = _resolve_source_chat(source_code)
    if not source_chat_id:
        return await message.reply(
            f"❌ Чат с кодом <code>{source_code}</code> не найден.\n\n"
            f"📌 В исходном чате пропишите <code>Код чата</code> и возьмите код оттуда.",
            parse_mode="HTML", disable_web_page_preview=True
        )

    if source_chat_id == message.chat.id:
        return await message.reply("❌ Нельзя импортировать из того же чата.",
                                    parse_mode="HTML", disable_web_page_preview=True)

    ok, err = await _move_check_access(message, source_chat_id)
    if not ok:
        return await message.reply(err, parse_mode="HTML", disable_web_page_preview=True)

    try:
        await bot.get_chat(source_chat_id)
    except Exception:
        return await message.reply("❌ Бот не имеет доступа к исходному чату.",
                                    parse_mode="HTML", disable_web_page_preview=True)

    try:
        src_chat = await bot.get_chat(source_chat_id)
        src_title = src_chat.title or f"чат {source_chat_id}"
    except Exception:
        src_title = f"чат {source_chat_id}"

    status = await message.reply(
        f"⏳ <b>Начинаю импорт...</b>\n\n"
        f"📥 Источник: <b>{html_escape_text(src_title)}</b>\n"
        f"🎯 Куда: <b>{html_escape_text(message.chat.title or 'этот чат')}</b>",
        parse_mode="HTML", disable_web_page_preview=True
    )

    lines = []

    try:
        if action == "full":
            notes_count = _import_notes_replace(source_chat_id, message.chat.id)
            lines.append(f"📝 Заметки (с заменой): <b>{notes_count}</b>")
            cmds_count = _import_commands(source_chat_id, message.chat.id)
            lines.append(f"⚙️ Команды (ДК): <b>{cmds_count}</b>")
            report = _import_settings(source_chat_id, message.chat.id)
            lines.append(f"🔧 Настройки:")
            for k, v in report.items():
                lines.append(f"   • {k}: {v}")

        elif action in ("notes_replace", "notes_add"):
            if action == "notes_replace":
                notes_count = _import_notes_replace(source_chat_id, message.chat.id)
                lines.append(f"📝 Заметки (с заменой): <b>{notes_count}</b>")
            else:
                added, conflicts = _import_notes_add(source_chat_id, message.chat.id)
                lines.append(f"📝 Заметки (добавлено): <b>{added}</b>")
                if conflicts:
                    lines.append(f"\n⚠️ <b>Конфликты ({len(conflicts)}):</b>")
                    for name in conflicts[:20]:
                        lines.append(f"   • <b>{html_escape_text(name)}</b>")
                    if len(conflicts) > 20:
                        lines.append(f"   ... +{len(conflicts)-20} ещё")
                    lines.append(
                        "\n💡 Разрешить конфликт — переименуйте существующую заметку:\n"
                        "<code>~Название заметки 1</code>"
                    )

        elif action == "commands":
            cmds_count = _import_commands(source_chat_id, message.chat.id)
            lines.append(f"⚙️ Команды (ДК): <b>{cmds_count}</b>")
            lines.append("<i>Доступ к командам полностью заменён.</i>")

        elif action == "settings":
            report = _import_settings(source_chat_id, message.chat.id)
            lines.append(f"🔧 <b>Импортированные настройки:</b>")
            for k, v in report.items():
                lines.append(f"   • {k}: {v}")

    except Exception as e:
        traceback.print_exc()
        return await status.edit_text(
            f"❌ <b>Ошибка импорта</b>\n\n<code>{type(e).__name__}: {e}</code>",
            parse_mode="HTML"
        )

    header = f"✅ <b>Импорт завершён!</b>\n\n📥 Из: <b>{html_escape_text(src_title)}</b>\n\n"
    await status.edit_text(header + "\n".join(lines), parse_mode="HTML",
                            disable_web_page_preview=True)


# ---------- КОМАНДА "Код чата" ----------
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+\-]?\s*код\s+чата\s*$', m.text.strip(), re.IGNORECASE))
async def code_chat_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("⚠️ Только для групп.", parse_mode="HTML",
                                    disable_web_page_preview=True)
    actor_id = message.from_user.id
    chat_id = message.chat.id

    is_creator = False
    try:
        m = await bot.get_chat_member(chat_id, actor_id)
        is_creator = (m.status == "creator")
    except Exception:
        pass

    actor_rank = get_rank(chat_id, actor_id)
    if not (is_creator or actor_rank >= 5 or actor_id == OWNER_ID or is_coowner(actor_id)):
        return await message.reply(
            "❌ <b>Недостаточно прав.</b>\nНужно быть создателем или иметь 5 ранг.",
            parse_mode="HTML", disable_web_page_preview=True
        )

    code = get_chat_code(chat_id)
    await message.reply(
        f"🔑 <b>Код этого чата:</b>\n\n<code>{code}</code>\n\n"
        f"<i>Используйте его для переезда/импорта в другом чате.</i>",
        parse_mode="HTML", disable_web_page_preview=True
    )


# ---------- РАЗРЕШЕНИЕ КОНФЛИКТА ЗАМЕТОК ----------
@dp.message(lambda m: m.text and re.match(r'^\s*[.\/!+\-]?\s*~\s*.+?\s+\d+\s*$', m.text.strip()))
async def resolve_note_conflict_cmd(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    actor_id = message.from_user.id
    chat_id = message.chat.id
    if not has_permission(chat_id, actor_id, 3):
        return await message.reply("❌ Нужен Мл. Админ (3+).", parse_mode="HTML",
                                    disable_web_page_preview=True)

    txt = message.text.strip()
    txt = re.sub(r'^[.\/!+\-]\s*', '', txt)
    m = re.match(r'^~\s*(.+?)\s+(\d+)\s*$', txt)
    if not m:
        return
    note_name = m.group(1).strip()
    number = int(m.group(2))

    existing = get_note_by_name(chat_id, note_name)
    if not existing:
        return await message.reply(
            f"❌ Заметка <b>{html_escape_text(note_name)}</b> не найдена.",
            parse_mode="HTML", disable_web_page_preview=True
        )

    new_name = f"{note_name} ({number})"

    if get_note_by_name(chat_id, new_name):
        return await message.reply(
            f"❌ Имя <b>{html_escape_text(new_name)}</b> уже занято. Выберите другой номер.",
            parse_mode="HTML", disable_web_page_preview=True
        )

    with sqlite3.connect(DATABASE_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE notes SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                  (new_name, existing[0]))
        conn.commit()

    await message.reply(
        f"✅ <b>Заметка переименована</b>\n\n"
        f"📝 «{html_escape_text(note_name)}» → «{html_escape_text(new_name)}»\n\n"
        f"💡 Теперь можете повторить импорт.",
        parse_mode="HTML", disable_web_page_preview=True
    )# ================= ФОНОВЫЕ ЗАДАЧИ =================
async def auto_unban_loop():
    while True:
        try:
            expired = get_expired_bans()
            for chat_id, user_id, reason, banned_by in expired:
                try:
                    await bot.unban_chat_member(chat_id, user_id)
                    clear_chat_ban(chat_id, user_id)
                    try:
                        await bot.restrict_chat_member(
                            chat_id, user_id,
                            permissions=types.ChatPermissions(
                                can_send_messages=True,
                                can_send_media_messages=True,
                                can_send_other_messages=True,
                                can_add_web_page_previews=True,
                                can_send_polls=True,
                                can_invite_users=True,
                            )
                        )
                    except: pass
                except Exception as e: pass
            expired_mutes = get_expired_mutes()
            for chat_id, user_id, reason in expired_mutes:
                try: clear_chat_mute(chat_id, user_id)
                except Exception as e: pass
        except Exception as e: pass
        await asyncio.sleep(30)


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
            await asyncio.sleep(5400)
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
                current_event = get_active_event(chat_id)
                if current_event: continue
                if random.randint(1, 100) <= 40:
                    ev_key = random.choice(list(FISHING_EVENTS.keys()))
                    ev = FISHING_EVENTS[ev_key]
                    set_event(chat_id, ev_key, ev["bonus"], 90)
                    try:
                        await bot.send_message(
                            chat_id,
                            f"🌦 <b>Новое событие на рыбалке!</b>\n\n"
                            f"{ev['name']}\n📈 Бонус: ×{ev['bonus']}\n⏰ Длительность: <b>1 ч 30 мин</b>",
                            parse_mode="HTML", disable_web_page_preview=True
                        )
                    except: pass
        except Exception as e:
            print(f"❌ auto_fishing_events_loop: {e}")


async def auto_holidays_loop():
    last_sent_date = None
    while True:
        try:
            now_msk = datetime.now(timezone.utc) + timedelta(hours=3)
            today_str = now_msk.strftime("%Y-%m-%d")
            if now_msk.hour == 0 and now_msk.minute < 5 and last_sent_date != today_str:
                with sqlite3.connect(DATABASE_PATH) as conn:
                    c = conn.cursor()
                    c.execute("SELECT key FROM global_settings WHERE key LIKE 'holidays:%' AND value = '1'")
                    rows = c.fetchall()
                text = get_all_holidays_text(now_msk)
                sent = 0
                for (key,) in rows:
                    try: chat_id = int(key.split(":")[1])
                    except: continue
                    try:
                        chat = await bot.get_chat(chat_id)
                        if chat.type not in ["group", "supergroup"]: continue
                        await bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
                        sent += 1
                    except: pass
                last_sent_date = today_str
                print(f"✅ Праздники {now_msk.strftime('%d.%m.%Y')} → {sent} чатов")
        except Exception as e:
            print(f"❌ auto_holidays_loop: {e}")
        await asyncio.sleep(60)


async def auto_tournament_end_loop():
    while True:
        try:
            await asyncio.sleep(60)
            now_str = _fmt_dt(datetime.now())
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT chat_id FROM fishing_tournaments WHERE expires_at <= ?", (now_str,))
                expired = [r[0] for r in c.fetchall()]
            for chat_id in expired:
                winners = end_tournament(chat_id)
                if winners:
                    text = "🏆 <b>ТУРНИР ЗАВЕРШЁН!</b>\n\n"
                    medals = ["🥇", "🥈", "🥉"]
                    for i, (uid, caught, prize) in enumerate(winners):
                        try:
                            u = await bot.get_chat(uid); name = user_link(uid, u.first_name, u.username)
                        except: name = f"ID {uid}"
                        text += f"{medals[i]} {name} — <b>{caught}</b> 🐟 (+{prize} 🍬)\n"
                    try: await bot.send_message(chat_id, text, parse_mode="HTML")
                    except: pass
        except Exception as e: pass
        await asyncio.sleep(30)


async def auto_marriage_divorce_loop():
    while True:
        try:
            await asyncio.sleep(3600)
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT DISTINCT chat_id FROM marriages WHERE status = 'active'")
                chats = [r[0] for r in c.fetchall()]
            for chat_id in chats:
                settings = get_marriage_settings(chat_id)
                mode = settings[1]
                if mode == "выключить": continue
                pairs = get_all_marriages(chat_id)
                for u1_id, u1_name, u2_id, u2_name, married_at, extra in pairs:
                    try:
                        m1 = await bot.get_chat_member(chat_id, u1_id)
                        m2 = await bot.get_chat_member(chat_id, u2_id)
                        u1_left = m1.status in ["left", "kicked"]
                        u2_left = m2.status in ["left", "kicked"]
                        should_divorce = False
                        if mode == "один" and (u1_left or u2_left): should_divorce = True
                        elif mode == "оба" and u1_left and u2_left: should_divorce = True
                        if should_divorce:
                            divorce_marriage(chat_id, u1_id)
                            try:
                                await bot.send_message(chat_id,
                                    f"💔 <b>Автоматический развод</b>\n\n"
                                    f"{mention_by_id(u1_id, u1_name)} и {mention_by_id(u2_id, u2_name)} разведены, "
                                    f"так как {'один из супругов' if mode == 'один' else 'оба супруга'} покинул(и) чат.",
                                    parse_mode="HTML")
                            except: pass
                    except: pass
        except Exception as e: pass
        await asyncio.sleep(3600)


async def auto_fill_users_loop():
    while True:
        try:
            await asyncio.sleep(43200)
            with sqlite3.connect(DATABASE_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT DISTINCT chat_id FROM messages_stats WHERE chat_id < 0")
                chats = [r[0] for r in c.fetchall()]
            total = 0
            for chat_id in chats:
                try:
                    admins = await bot.get_chat_administrators(chat_id)
                    for admin in admins:
                        u = admin.user
                        if u.is_bot: continue
                        register_user(u.id, u.first_name, u.username or "")
                        total += 1
                except: continue
            print(f"✅ auto_fill_users: обработано {total} админов")
        except Exception as e:
            print(f"❌ auto_fill_users_loop: {e}")


# ================= ЗАПУСК =================
async def main():
    init_db()
    cleanup_zero_ranks()

    # Восстанавливаем verified премиум-эмодзи из БД
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS premium_emojis (
                emoji_id TEXT PRIMARY KEY, fallback TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            c.execute("SELECT emoji_id FROM premium_emojis")
            for (eid,) in c.fetchall():
                _VERIFIED_EMOJI_IDS.add(str(eid))
            conn.commit()
        print(f"✅ Verified emoji: {len(_VERIFIED_EMOJI_IDS)}")
    except Exception as e:
        print(f"⚠️ premium_emojis init: {e}")

    print("✅ Бот запущен!")
    print(f"👑 Владелец: {OWNER_ID}")

    if get_all_holidays_count() < 300:
        STARTER_HOLIDAYS = [
            ("01-01", "Новый год", "global"),("01-01", "Новый год", "local"),("01-01", "День былинного богатыря Ильи Муромца", "folk"),
            ("01-02", "День научной фантастики", "fun"),("01-03", "День стереоскопического кино", "fun"),("01-04", "Всемирный день азбуки Брайля", "global"),
            ("01-05", "День физики", "fun"),("01-06", "Сочельник", "church"),("01-07", "Рождество Христово", "church"),
            ("01-08", "День поворачивания на правый бок", "fun"),("01-09", "День путешествия на воздушном шаре", "fun"),
            ("01-10", "День благодарности комнатным растениям", "fun"),("01-11", "Всемирный день спасибо", "fun"),
            ("01-12", "День работника прокуратуры РФ", "prof"),("01-13", "Старый Новый год (Васильев вечер)", "folk"),
            ("01-13", "День российской печати", "prof"),("01-14", "Всемирный день логики", "global"),("01-14", "День защитников неба", "fun"),
            ("01-15", "День рождения Википедии", "global"),("01-15", "Национальный день шляпы", "fun"),("01-16", "День ледовара", "fun"),
            ("01-17", "День детских изобретений", "fun"),("01-18", "День Винни-Пуха", "fun"),("01-19", "Крещение Господне", "church"),
            ("01-20", "День пингвина", "fun"),("01-21", "День объятий", "global"),("01-22", "День дедушки", "fun"),
            ("01-23", "День ручного письма", "global"),("01-24", "Международный день образования", "global"),
            ("01-24", "Международный день эскимо", "fun"),("01-25", "День российского студенчества (Татьянин день)", "prof"),
            ("01-25", "Татьянин день", "folk"),("01-26", "Международный день таможенника", "prof"),
            ("01-27", "Международный день памяти жертв Холокоста", "global"),("01-28", "День открытия Антарктиды", "global"),
            ("01-28", "Международный день ЛЕГО", "fun"),("01-29", "День необъятной любви к себе", "fun"),
            ("01-30", "День деда Мороза и Снегурочки", "folk"),("01-31", "Международный день ювелира", "prof"),
            ("02-01", "День лифтовика", "prof"),("02-02", "День сурка", "fun"),("02-02", "День ежа", "fun"),
            ("02-03", "Всемирный день борьбы с ненормативной лексикой", "global"),("02-04", "Всемирный день борьбы против рака", "global"),
            ("02-04", "Праздник хорошего настроения", "fun"),("02-05", "День эрудита", "fun"),("02-06", "День бармена", "prof"),
            ("02-07", "День балета", "global"),("02-08", "День российской науки", "prof"),("02-09", "День стоматолога", "prof"),
            ("02-10", "День домового", "folk"),("02-11", "Всемирный день больного", "global"),
            ("02-11", "Международный день женщин и девочек в науке", "global"),("02-12", "День Дарвина", "global"),
            ("02-13", "Всемирный день радио", "global"),("02-14", "День всех влюблённых", "global"),("02-15", "Сретение Господне", "church"),
            ("02-16", "День свежего ананаса", "fun"),("02-17", "День спонтанного проявления доброты", "global"),
            ("02-18", "День пельменей", "fun"),("02-19", "Всемирный день китов", "global"),
            ("02-20", "Всемирный день социальной справедливости", "global"),("02-21", "Международный день родного языка", "global"),
            ("02-22", "День кошки в Японии", "fun"),("02-23", "День защитника Отечества", "global"),
            ("02-23", "День защитника Отечества", "prof"),("02-24", "День рождения лотереи", "fun"),
            ("02-25", "День открытия спирта", "fun"),("02-26", "День неторопливости", "fun"),
            ("02-27", "Международный день полярного медведя", "global"),("02-28", "День общественного сна", "fun"),
            ("02-29", "День Кащея Бессмертного", "folk"),("03-01", "Всемирный день кошек", "global"),("03-02", "День спичек", "fun"),
            ("03-03", "Всемирный день дикой природы", "global"),("03-04", "День грамматики", "fun"),
            ("03-05", "День выключенных гаджетов", "fun"),("03-06", "Международный день зубного врача", "prof"),
            ("03-07", "День тюльпанов", "fun"),("03-08", "Международный женский день", "global"),
            ("03-08", "Международный женский день", "prof"),("03-09", "День диджея", "prof"),("03-10", "День архивов", "prof"),
            ("03-11", "День работника органов наркоконтроля", "prof"),("03-12", "День посадки деревьев", "global"),
            ("03-13", "День рождения микрофона", "fun"),("03-14", "Международный день числа Пи", "global"),
            ("03-15", "Всемирный день защиты прав потребителей", "global"),("03-16", "День цветных карандашей", "fun"),
            ("03-17", "День Святого Патрика", "global"),("03-18", "День воссоединения Крыма с Россией", "global"),
            ("03-19", "День моряка-подводника", "prof"),("03-20", "Международный день счастья", "global"),
            ("03-21", "Всемирный день поэзии", "global"),("03-21", "Международный день Навруз", "global"),
            ("03-22", "Всемирный день водных ресурсов", "global"),("03-23", "Всемирный метеорологический день", "global"),
            ("03-24", "Всемирный день борьбы с туберкулёзом", "global"),("03-25", "День работника культуры РФ", "prof"),
            ("03-26", "День фиолетового дня", "fun"),("03-27", "Всемирный день театра", "global"),
            ("03-28", "День уважения кошек", "fun"),("03-29", "День самопознания", "fun"),("03-30", "День защиты Земли", "global"),
            ("03-31", "Международный день бэкапа", "global"),("04-01", "День смеха", "fun"),
            ("04-02", "Международный день детской книги", "global"),("04-03", "Всемирный день вечеринки", "fun"),
            ("04-04", "Международный день интернета", "global"),("04-05", "Международный день супа", "fun"),
            ("04-06", "Международный день спорта", "global"),("04-07", "Всемирный день здоровья", "global"),
            ("04-08", "День российской анимации", "prof"),("04-09", "День финского языка", "global"),
            ("04-10", "День братьев и сестёр", "global"),("04-11", "Международный день освобождения узников фашистских лагерей", "global"),
            ("04-12", "День космонавтики", "global"),("04-12", "День космонавтики", "prof"),("04-13", "Всемирный день рок-н-ролла", "global"),
            ("04-14", "День медицинской службы", "prof"),("04-15", "Всемирный день искусства", "global"),
            ("04-16", "Всемирный день голоса", "global"),("04-17", "Всемирный день гемофилии", "global"),
            ("04-18", "Международный день памятников и исторических мест", "global"),("04-19", "День российской полиграфии", "prof"),
            ("04-20", "Международный день цирка", "global"),("04-21", "Всемирный день творчества", "global"),
            ("04-22", "Международный день Матери-Земли", "global"),("04-23", "Всемирный день книги", "global"),
            ("04-24", "Международный день солидарности молодёжи", "global"),("04-25", "Всемирный день пингвинов", "fun"),
            ("04-26", "Международный день интеллектуальной собственности", "global"),("04-27", "Всемирный день графического дизайна", "prof"),
            ("04-28", "Всемирный день охраны труда", "global"),("04-29", "Международный день танца", "global"),
            ("04-30", "День пожарной охраны", "prof"),("05-01", "Праздник Весны и Труда", "global"),
            ("05-02", "Всемирный день тунца", "fun"),("05-03", "Всемирный день свободы печати", "global"),
            ("05-04", "День пожарных", "prof"),("05-05", "День водолаза", "prof"),("05-07", "День радио", "prof"),
            ("05-08", "Всемирный день Красного Креста", "global"),("05-09", "День Победы", "global"),
            ("05-10", "Всемирный день движения", "global"),("05-11", "Всемирный день борьбы с гипертонией", "global"),
            ("05-12", "Международный день медсестры", "prof"),("05-13", "День Черноморского флота", "prof"),
            ("05-14", "День фрилансера", "prof"),("05-15", "Международный день семьи", "global"),
            ("05-16", "Международный день биографов", "fun"),("05-17", "Всемирный день электросвязи", "global"),
            ("05-18", "Международный день музеев", "global"),("05-19", "День пионерии", "global"),
            ("05-20", "Всемирный день метрологии", "global"),("05-21", "Всемирный день культурного разнообразия", "global"),
            ("05-22", "Международный день биологического разнообразия", "global"),("05-23", "Всемирный день черепахи", "global"),
            ("05-24", "День славянской письменности и культуры", "prof"),("05-25", "День филолога", "prof"),
            ("05-26", "День российского предпринимательства", "prof"),("05-27", "Общероссийский день библиотек", "prof"),
            ("05-28", "День пограничника", "prof"),("05-29", "День военного автомобилиста", "prof"),
            ("05-30", "Всемирный день без табака", "global"),("05-31", "Всемирный день блондинок", "fun"),
            ("06-01", "Международный день защиты детей", "global"),("06-02", "День здорового питания", "global"),
            ("06-03", "Всемирный день велосипеда", "global"),("06-04", "Международный день невинных детей", "global"),
            ("06-05", "Всемирный день окружающей среды", "global"),("06-06", "День русского языка (Пушкинский день)", "prof"),
            ("06-07", "Всемирный день безопасности пищевых продуктов", "global"),("06-08", "Всемирный день океанов", "global"),
            ("06-09", "Международный день друзей", "global"),("06-10", "Всемирный день мороженого", "fun"),
            ("06-11", "Всемирный день куклы", "fun"),("06-12", "День России", "global"),("06-12", "День России", "prof"),
            ("06-13", "Международный день распространения информации об альбинизме", "global"),
            ("06-14", "Всемирный день донора крови", "global"),("06-15", "Всемирный день ветра", "global"),
            ("06-16", "Международный день отца", "global"),("06-17", "Всемирный день борьбы с опустыниванием", "global"),
            ("06-18", "Международный день пикника", "fun"),("06-19", "Всемирный день неспешной прогулки", "fun"),
            ("06-20", "Всемирный день беженцев", "global"),("06-21", "Международный день йоги", "global"),
            ("06-22", "День памяти и скорби", "global"),("06-23", "Международный Олимпийский день", "global"),
            ("06-24", "День парада Победы", "global"),("06-25", "День дружбы и единения славян", "global"),
            ("06-26", "Международный день борьбы с наркоманией", "global"),("06-27", "День молодёжи России", "prof"),
            ("06-28", "День украинской Конституции", "global"),("06-29", "Международный день тропиков", "global"),
            ("06-30", "Всемирный день астероида", "global"),("07-01", "Всемирный день архитектуры", "prof"),
            ("07-02", "Всемирный день НЛО", "fun"),("07-03", "День ГИБДД", "prof"),("07-04", "День независимости США", "global"),
            ("07-05", "Всемирный день поцелуя", "fun"),("07-06", "Всемирный день кардиолога", "prof"),("07-07", "Иван Купала", "folk"),
            ("07-08", "День семьи, любви и верности", "global"),("07-08", "День семьи, любви и верности", "prof"),
            ("07-09", "Всемирный день веры в единорогов", "fun"),("07-10", "День рыбака", "prof"),
            ("07-11", "Всемирный день шоколада", "fun"),("07-12", "Всемирный день бортпроводника", "prof"),
            ("07-13", "Международный день головоломки", "fun"),("07-14", "День взятия Бастилии", "global"),
            ("07-15", "Всемирный день навыков молодёжи", "global"),("07-16", "Международный день змеи", "global"),
            ("07-17", "Всемирный день эмодзи", "fun"),("07-18", "Международный день Нельсона Манделы", "global"),
            ("07-19", "Всемирный день фотографии", "fun"),("07-20", "Международный день шахмат", "global"),
            ("07-21", "День металлурга", "prof"),("07-22", "Всемирный день мозга", "global"),
            ("07-23", "Всемирный день китов и дельфинов", "global"),("07-24", "День флориста", "prof"),
            ("07-25", "День системного администратора", "prof"),("07-26", "День парашютиста", "prof"),
            ("07-27", "День работников торговли", "prof"),("07-28", "Всемирный день борьбы с гепатитом", "global"),
            ("07-29", "Международный день тигра", "global"),("07-30", "Международный день дружбы", "global"),
            ("07-31", "День военно-морского флота", "prof"),("08-01", "Всемирный день матери-кормилицы", "global"),
            ("08-02", "День Воздушно-десантных войск", "prof"),("08-03", "День арбуза", "fun"),
            ("08-04", "День одиноких работающих женщин", "fun"),("08-05", "Международный день светофора", "fun"),
            ("08-06", "День железнодорожника", "prof"),("08-07", "День холостяка", "fun"),
            ("08-08", "Всемирный день кошек", "global"),("08-09", "День физкультурника", "prof"),
            ("08-10", "День строителя", "prof"),("08-12", "Международный день молодёжи", "global"),
            ("08-13", "День левшей", "fun"),("08-15", "День археолога", "prof"),("08-16", "День малинового варенья", "fun"),
            ("08-17", "День рождения русской тельняшки", "fun"),("08-18", "День географа", "prof"),
            ("08-19", "Всемирный день фотографии", "global"),("08-20", "Всемирный день лени", "fun"),
            ("08-21", "День офицера России", "prof"),("08-22", "День Государственного флага РФ", "global"),
            ("08-22", "День Государственного флага РФ", "prof"),("08-23", "День разгрома немецко-фашистских войск в Курской битве", "global"),
            ("08-24", "День рождения картофельных чипсов", "fun"),("08-25", "День шахтёра", "prof"),
            ("08-26", "День благодарности собаке", "fun"),("08-27", "День российского кино", "prof"),
            ("08-28", "День мечты", "fun"),("08-29", "День спецназа", "prof"),("08-30", "День кино", "prof"),
            ("08-31", "День блога", "fun"),("09-01", "День знаний", "global"),("09-01", "День знаний", "prof"),
            ("09-02", "День окончания Второй мировой войны", "global"),("09-03", "День солидарности в борьбе с терроризмом", "global"),
            ("09-04", "День специалиста по ядерному обеспечению", "prof"),("09-05", "День благотворительности", "global"),
            ("09-06", "День чтения книг", "fun"),("09-07", "День барабанщика", "fun"),
            ("09-08", "Международный день грамотности", "global"),("09-09", "Всемирный день красоты", "global"),
            ("09-10", "Всемирный день предотвращения самоубийств", "global"),("09-11", "Всемирный день трезвости", "global"),
            ("09-12", "День программиста", "prof"),("09-13", "День парикмахера", "prof"),
            ("09-14", "День слушания шорохов", "fun"),("09-15", "Международный день демократии", "global"),
            ("09-16", "День рождения Джульетты", "fun"),("09-17", "Всемирный день безопасности пациентов", "global"),
            ("09-18", "Всемирный день мониторинга качества воды", "global"),("09-19", "День смайлика", "fun"),
            ("09-20", "Всемирный день благодарности", "fun"),("09-21", "Международный день мира", "global"),
            ("09-22", "Всемирный день без автомобиля", "global"),("09-23", "День осеннего равноденствия", "global"),
            ("09-24", "Международный день караванщика", "prof"),("09-25", "Всемирный день фармацевта", "prof"),
            ("09-26", "Всемирный день контрацепции", "global"),("09-27", "Всемирный день туризма", "global"),
            ("09-27", "День воспитателя и всех дошкольных работников", "prof"),("09-28", "Всемирный день борьбы против бешенства", "global"),
            ("09-29", "Всемирный день сердца", "global"),("09-30", "Международный день переводчика", "prof"),
            ("10-01", "Международный день пожилых людей", "global"),("10-01", "Международный день музыки", "global"),
            ("10-01", "Международный день кофе", "global"),("10-02", "Международный день ненасилия", "global"),
            ("10-03", "Всемирный день трезвости и борьбы с алкоголизмом", "global"),("10-04", "День защиты животных", "global"),
            ("10-05", "День учителя", "global"),("10-05", "День учителя", "prof"),("10-06", "Всемирный день охраны мест обитания", "global"),
            ("10-07", "Всемирный день улыбки", "fun"),("10-08", "Всемирный день осьминога", "fun"),("10-09", "Всемирный день почты", "global"),
            ("10-10", "Всемирный день психического здоровья", "global"),("10-11", "Международный день девочек", "global"),
            ("10-12", "Всемирный день борьбы с артритом", "global"),("10-13", "Международный день по снижению риска бедствий", "global"),
            ("10-13", "Всемирный день борьбы с тромбозом", "global"),("10-13", "День гидрографической службы ВМФ РФ", "prof"),
            ("10-13", "День инфобизнесмена", "prof"),("10-13", "Международный день костюма", "fun"),
            ("10-13", "День «Побалуйте себя»", "fun"),("10-13", "Международный день неудач", "fun"),
            ("10-13", "Михаил Соломенный (народный)", "folk"),("10-14", "Всемирный день зрения", "global"),
            ("10-15", "Всемирный день мытья рук", "global"),("10-16", "Всемирный день продовольствия", "global"),
            ("10-17", "Международный день борьбы за ликвидацию нищеты", "global"),("10-18", "Всемирный день конфет", "fun"),
            ("10-19", "Всемирный день детского церебрального паралича", "global"),("10-20", "Всемирный день статистики", "global"),
            ("10-21", "День яблока", "fun"),("10-22", "День белых журавлей", "global"),("10-23", "День работников рекламы", "prof"),
            ("10-24", "День Организации Объединённых Наций", "global"),("10-25", "День маркетолога", "prof"),
            ("10-26", "День приятных неожиданностей", "fun"),("10-27", "Всемирный день аудиовизуального наследия", "global"),
            ("10-28", "День бабушек и дедушек", "fun"),("10-29", "Всемирный день борьбы с инсультом", "global"),
            ("10-30", "День памяти жертв политических репрессий", "global"),("10-31", "Хэллоуин", "fun"),
            ("11-01", "День менеджера", "prof"),("11-02", "День международного признания Санкт-Петербурга", "local"),
            ("11-03", "День рождения паровоза", "fun"),("11-04", "День народного единства", "global"),
            ("11-04", "День народного единства", "prof"),("11-05", "День военного разведчика", "prof"),
            ("11-06", "День саамского народа", "folk"),("11-07", "День Октябрьской революции", "global"),
            ("11-08", "День пианиста", "prof"),("11-09", "День качества", "global"),
            ("11-10", "День сотрудника органов внутренних дел РФ", "prof"),("11-11", "День холостяка (11.11)", "fun"),
            ("11-12", "День специалиста по безопасности", "prof"),("11-13", "Всемирный день доброты", "global"),
            ("11-14", "День социолога", "prof"),("11-15", "Всемирный день вторичной переработки", "global"),
            ("11-16", "Международный день толерантности", "global"),("11-17", "Международный день студентов", "global"),
            ("11-18", "День рождения Деда Мороза", "fun"),("11-19", "Международный день мужчин", "global"),
            ("11-20", "Всемирный день ребёнка", "global"),("11-21", "Всемирный день приветствий", "global"),
            ("11-22", "День психолога", "prof"),("11-23", "День благодарения", "global"),("11-24", "День моржа", "fun"),
            ("11-25", "Международный день борьбы за ликвидацию насилия в отношении женщин", "global"),
            ("11-26", "Всемирный день информации", "global"),("11-27", "День матери", "prof"),
            ("11-28", "День бухгалтера", "prof"),("11-29", "День буквы Ё", "fun"),("11-30", "День домашних животных", "fun"),
            ("12-01", "Всемирный день борьбы со СПИДом", "global"),("12-02", "День банковского работника", "prof"),
            ("12-03", "Международный день инвалидов", "global"),("12-03", "День юриста", "prof"),
            ("12-04", "День информатики", "prof"),("12-05", "День добровольца", "global"),
            ("12-06", "День рождения микроволновой печи", "fun"),("12-07", "День гражданской авиации", "prof"),
            ("12-08", "День художника", "prof"),("12-09", "День героев Отечества", "global"),("12-10", "День прав человека", "global"),
            ("12-11", "Международный день гор", "global"),("12-12", "День Конституции РФ", "global"),
            ("12-12", "День Конституции РФ", "prof"),("12-13", "День медведя", "fun"),("12-14", "День обезьян", "fun"),
            ("12-15", "День чая", "fun"),("12-16", "День покорения вершин", "fun"),("12-17", "День ракетных войск", "prof"),
            ("12-18", "День работников ЗАГС", "prof"),("12-19", "День вечнозелёных растений", "fun"),
            ("12-20", "День рождения ёлочной гирлянды", "fun"),("12-21", "День зимнего солнцестояния", "global"),
            ("12-22", "День энергетика", "prof"),("12-23", "День дальней авиации", "prof"),
            ("12-24", "Католический сочельник", "church"),("12-25", "Католическое Рождество", "church"),
            ("12-26", "День подарков", "fun"),("12-27", "День спасателя", "prof"),("12-28", "День кино", "prof"),
            ("12-29", "День конституции Ирландии", "global"),("12-30", "День заворачивания подарков", "fun"),
            ("12-31", "Новогодний вечер", "fun"),
        ]
        with sqlite3.connect(DATABASE_PATH) as conn:
            c = conn.cursor()
            for date_mm_dd, name, cat in STARTER_HOLIDAYS:
                try:
                    c.execute("INSERT OR IGNORE INTO holidays (date, name, category) VALUES (?, ?, ?)",
                              (date_mm_dd, name, cat))
                except: pass
            conn.commit()
        print(f"✅ Залито праздников: {get_all_holidays_count()}")

    asyncio.create_task(auto_unban_loop())
    asyncio.create_task(auto_backup_loop())
    asyncio.create_task(auto_fishing_events_loop())
    asyncio.create_task(auto_holidays_loop())
    asyncio.create_task(auto_tournament_end_loop())
    asyncio.create_task(auto_marriage_divorce_loop())
    asyncio.create_task(auto_fill_users_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
