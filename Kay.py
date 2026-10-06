import sqlite3
import secrets
import string
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================================================
# إعدادات البوت
# =========================================================

BOT_TOKEN = "8932533833:AAFdTtLA_lFN2b1n6z9CW1nInvkrW833FFs"

# ضع Telegram ID الخاص بك هنا
ADMIN_ID = 8821125770

DB = "ali_vip.db"


# =========================================================
# قاعدة البيانات
# =========================================================

def db():
    return sqlite3.connect(DB)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            banned INTEGER DEFAULT 0,
            devices INTEGER DEFAULT 0,
            last_seen TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            key TEXT,
            created_at TEXT
        )
    """)

    con.commit()
    con.close()


# =========================================================
# أدوات
# =========================================================

def now():
    return datetime.now()


def log_action(user_id, action, key=""):
    con = db()
    con.execute(
        """
        INSERT INTO logs(user_id, action, key, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, action, key, now().isoformat())
    )
    con.commit()
    con.close()


def generate_key():
    alphabet = string.ascii_uppercase + string.digits

    parts = []

    for _ in range(4):
        parts.append(
            "".join(secrets.choice(alphabet) for _ in range(4))
        )

    return "-".join(parts)


def create_key(days):
    while True:
        key = generate_key()

        try:
            con = db()

            created = now()
            expires = created + timedelta(days=days)

            con.execute(
                """
                INSERT INTO keys
                (key, created_at, expires_at)
                VALUES (?, ?, ?)
                """,
                (
                    key,
                    created.isoformat(),
                    expires.isoformat()
                )
            )

            con.commit()
            con.close()

            return key, expires

        except sqlite3.IntegrityError:
            con.close()


def is_admin(update):
    return (
        update.effective_user
        and update.effective_user.id == ADMIN_ID
    )


def format_status(banned, expires_at):
    if banned:
        return "🚫 محظور"

    expiry = datetime.fromisoformat(expires_at)

    if now() >= expiry:
        return "⚫ منتهي"

    return "🟢 فعال"


# =========================================================
# القائمة الرئيسية
# =========================================================

def main_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "🔑 توليد مفاتيح جديدة",
                callback_data="generate"
            )
        ],
        [
            InlineKeyboardButton(
                "🔑 إدارة المفاتيح",
                callback_data="manage"
            ),
            InlineKeyboardButton(
                "📊 الإحصائيات",
                callback_data="stats"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 المتصلين الآن",
                callback_data="online"
            ),
            InlineKeyboardButton(
                "📝 النشاط اليومي",
                callback_data="activity"
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 الأجهزة المحظورة",
                callback_data="banned"
            ),
            InlineKeyboardButton(
                "📋 سجل الدخول",
                callback_data="logs"
            )
        ],
        [
            InlineKeyboardButton(
                "⚠️ المحاولات الفاشلة",
                callback_data="failed"
            ),
            InlineKeyboardButton(
                "ℹ️ معلومات النظام",
                callback_data="system"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# /start
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        await update.message.reply_text(
            "❌ ليس لديك صلاحية استخدام لوحة الإدارة."
        )
        return

    text = """
🚀 ALI VIP

👋 مرحباً بك

⚙️ التحكم الكامل في نظام المفاتيح

⚡ الأوامر السريعة:

/menu — القائمة
/find KEY — تفاصيل مفتاح
/gen 30d 5 — توليد 5 مفاتيح
/restart KEY — تصفير أجهزة المفتاح
/ban KEY — حظر مفتاح
/unban KEY — فك حظر المفتاح
"""

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard()
    )


# =========================================================
# /menu
# =========================================================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        return

    await update.message.reply_text(
        "🚀 ALI VIP\n\nاختر العملية:",
        reply_markup=main_keyboard()
    )


# =========================================================
# /gen 30d 5
# =========================================================

async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "الاستخدام الصحيح:\n\n"
            "/gen 30d 5\n\n"
            "30d = 30 يوم\n"
            "5 = عدد المفاتيح"
        )
        return

    duration = context.args[0].lower()
    quantity_text = context.args[1]

    if not duration.endswith("d"):
        await update.message.reply_text(
            "❌ استخدم المدة بهذا الشكل: 30d"
        )
        return

    try:
        days = int(duration[:-1])
        quantity = int(quantity_text)
    except ValueError:
        await update.message.reply_text(
            "❌ المدة أو العدد غير صحيح."
        )
        return

    if days <= 0 or days > 3650:
        await update.message.reply_text(
            "❌ المدة يجب أن تكون من 1 إلى 3650 يوم."
        )
        return

    if quantity <= 0 or quantity > 100:
        await update.message.reply_text(
            "❌ يمكنك إنشاء من 1 إلى 100 مفتاح في المرة."
        )
        return

    result = []

    for _ in range(quantity):

        key, expires = create_key(days)

        result.append(
            f"🔑 `{key}`\n"
            f"📅 {expires.strftime('%Y-%m-%d %H:%M')}"
        )

        log_action(
            update.effective_user.id,
            f"إنشاء مفتاح لمدة {days} يوم",
            key
        )

    text = (
        f"✅ تم إنشاء {quantity} مفتاح\n"
        f"⏳ المدة: {days} يوم\n\n"
        + "\n\n".join(result)
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )


# =========================================================
# /find KEY
# =========================================================

async def find_key(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "الاستخدام:\n/find KEY"
        )
        return

    key = context.args[0].upper()

    con = db()

    row = con.execute(
        """
        SELECT key, created_at, expires_at,
               banned, devices, last_seen
        FROM keys
        WHERE key = ?
        """,
        (key,)
    ).fetchone()

    con.close()

    if not row:
        await update.message.reply_text(
            "❌ المفتاح غير موجود."
        )
        return

    (
        key,
        created_at,
        expires_at,
        banned,
        devices,
        last_seen
    ) = row

    status = format_status(banned, expires_at)

    await update.message.reply_text(
        f"""
🔎 تفاصيل المفتاح

🔑 المفتاح:
{key}

📅 الإنشاء:
{datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M')}

⏳ الانتهاء:
{datetime.fromisoformat(expires_at).strftime('%Y-%m-%d %H:%M')}

📱 الأجهزة:
{devices}

📡 آخر اتصال:
{last_seen or "لا يوجد"}

📌 الحالة:
{status}
"""
    )


# =========================================================
# /ban KEY
# =========================================================

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "الاستخدام:\n/ban KEY"
        )
        return

    key = context.args[0].upper()

    con = db()

    cur = con.execute(
        "UPDATE keys SET banned = 1 WHERE key = ?",
        (key,)
    )

    con.commit()
    con.close()

    if cur.rowcount == 0:
        await update.message.reply_text(
            "❌ المفتاح غير موجود."
        )
        return

    log_action(
        update.effective_user.id,
        "حظر مفتاح",
        key
    )

    await update.message.reply_text(
        f"🚫 تم حظر المفتاح:\n{key}"
    )


# =========================================================
# /unban KEY
# =========================================================

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "الاستخدام:\n/unban KEY"
        )
        return

    key = context.args[0].upper()

    con = db()

    cur = con.execute(
        "UPDATE keys SET banned = 0 WHERE key = ?",
        (key,)
    )

    con.commit()
    con.close()

    if cur.rowcount == 0:
        await update.message.reply_text(
            "❌ المفتاح غير موجود."
        )
        return

    log_action(
        update.effective_user.id,
        "فك حظر مفتاح",
        key
    )

    await update.message.reply_text(
        f"✅ تم فك حظر المفتاح:\n{key}"
    )


# =========================================================
# /restart KEY
# تصفير عدد الأجهزة
# =========================================================

async def restart_key(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "الاستخدام:\n/restart KEY"
        )
        return

    key = context.args[0].upper()

    con = db()

    cur = con.execute(
        """
        UPDATE keys
        SET devices = 0,
            last_seen = NULL
        WHERE key = ?
        """,
        (key,)
    )

    con.commit()
    con.close()

    if cur.rowcount == 0:
        await update.message.reply_text(
            "❌ المفتاح غير موجود."
        )
        return

    log_action(
        update.effective_user.id,
        "تصفير أجهزة المفتاح",
        key
    )

    await update.message.reply_text(
        f"🔄 تم تصفير أجهزة المفتاح:\n{key}"
    )


# =========================================================
# زر التوليد
# =========================================================

async def generate_button(query):

    text = """
🔑 توليد مفاتيح

استخدم الأمر:

/gen 1d 5

أو:

/gen 7d 5

أو:

/gen 30d 5

أو:

/gen 365d 5
"""

    await query.edit_message_text(
        text,
        reply_markup=main_keyboard()
    )


# =========================================================
# الإحصائيات
# =========================================================

async def stats_button(query):

    con = db()

    total = con.execute(
        "SELECT COUNT(*) FROM keys"
    ).fetchone()[0]

    banned = con.execute(
        "SELECT COUNT(*) FROM keys WHERE banned = 1"
    ).fetchone()[0]

    active = con.execute(
        """
        SELECT COUNT(*)
        FROM keys
        WHERE banned = 0
        AND expires_at > ?
        """,
        (now().isoformat(),)
    ).fetchone()[0]

    expired = total - active - banned

    con.close()

    text = f"""
📊 إحصائيات ALI VIP

🔑 إجمالي المفاتيح:
{total}

🟢 المفاتيح الفعالة:
{active}

⚫ المفاتيح المنتهية:
{max(expired, 0)}

🚫 المفاتيح المحظورة:
{banned}
"""

    await query.edit_message_text(
        text,
        reply_markup=main_keyboard()
    )


# =========================================================
# المتصلين
# =========================================================

async def online_button(query):

    con = db()

    limit = now() - timedelta(minutes=5)

    count = con.execute(
        """
        SELECT COUNT(*)
        FROM keys
        WHERE last_seen IS NOT NULL
        AND last_seen > ?
        """,
        (limit.isoformat(),)
    ).fetchone()[0]

    con.close()

    await query.edit_message_text(
        f"""
👥 المتصلين الآن

🟢 عدد المفاتيح التي أرسلت اتصالًا
خلال آخر 5 دقائق:

{count}

ℹ️️ يحتاج هذا القسم إلى ربط API
بالتطبيق حتى تظهر الاتصالات الحقيقية.
""",
        reply_markup=main_keyboard()
    )


# =========================================================
# النشاط اليومي
# =========================================================

async def activity_button(query):

    start_day = now().replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    con = db()

    count = con.execute(
        """
        SELECT COUNT(*)
        FROM logs
        WHERE created_at >= ?
        """,
        (start_day.isoformat(),)
    ).fetchone()[0]

    con.close()

    await query.edit_message_text(
        f"""
📝 النشاط اليومي

📅 اليوم:
{now().strftime('%Y-%m-%d')}

⚡ عدد العمليات:
{count}
""",
        reply_markup=main_keyboard()
    )


# =========================================================
# الأجهزة المحظورة
# =========================================================

async def banned_button(query):

    con = db()

    rows = con.execute(
        """
        SELECT key
        FROM keys
        WHERE banned = 1
        ORDER BY id DESC
        LIMIT 30
        """
    ).fetchall()

    con.close()

    if not rows:
        text = "🚫 لا توجد مفاتيح محظورة."
    else:
        text = "🚫 المفاتيح المحظورة:\n\n"

        for row in rows:
            text += f"🔑 {row[0]}\n"

    await query.edit_message_text(
        text,
        reply_markup=main_keyboard()
    )


# =========================================================
# سجل الدخول
# =========================================================

async def logs_button(query):

    con = db()

    rows = con.execute(
        """
        SELECT action, key, created_at
        FROM logs
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()

    con.close()

    if not rows:
        text = "📋 لا يوجد سجل حتى الآن."
    else:
        text = "📋 آخر العمليات:\n\n"

        for action, key, created_at in rows:

            dt = datetime.fromisoformat(created_at)

            text += (
                f"⚡ {action}\n"
                f"🔑 {key or '-'}\n"
                f"🕐 {dt.strftime('%Y-%m-%d %H:%M')}\n\n"
            )

    await query.edit_message_text(
        text,
        reply_markup=main_keyboard()
    )


# =========================================================
# المحاولات الفاشلة
# =========================================================

async def failed_button(query):

    await query.edit_message_text(
        """
⚠️ المحاولات الفاشلة

لا توجد محاولات فاشلة مسجلة حاليًا.

سيتم استخدام هذا القسم لاحقًا
مع API التحقق من التطبيق.
""",
        reply_markup=main_keyboard()
    )


# =========================================================
# معلومات النظام
# =========================================================

async def system_button(query):

    con = db()

    total_logs = con.execute(
        "SELECT COUNT(*) FROM logs"
    ).fetchone()[0]

    con.close()

    await query.edit_message_text(
        f"""
ℹ️ معلومات النظام

🚀 النظام: ALI VIP
💾 قاعدة البيانات: SQLite
🔐 نظام المفاتيح: فعال
📋 السجلات: {total_logs}

🤖 البوت يعمل بنظام Telegram API.
""",
        reply_markup=main_keyboard()
    )


# =========================================================
# إدارة المفاتيح
# =========================================================

async def manage_button(query):

    await query.edit_message_text(
        """
🔑 إدارة المفاتيح

الأوامر المتاحة:

/find KEY
عرض تفاصيل مفتاح

/ban KEY
حظر مفتاح

/unban KEY
فك حظر مفتاح

/restart KEY
تصفير أجهزة المفتاح

/gen 30d 5
توليد مفاتيح
""",
        reply_markup=main_keyboard()
    )


# =========================================================
# الأزرار
# =========================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ غير مسموح",
            show_alert=True
        )
        return

    action = query.data

    if action == "generate":
        await generate_button(query)

    elif action == "manage":
        await manage_button(query)

    elif action == "stats":
        await stats_button(query)

    elif action == "online":
        await online_button(query)

    elif action == "activity":
        await activity_button(query)

    elif action == "banned":
        await banned_button(query)

    elif action == "logs":
        await logs_button(query)

    elif action == "failed":
        await failed_button(query)

    elif action == "system":
        await system_button(query)


# =========================================================
# تشغيل البوت
# =========================================================

def main():

    init_db()

    print("================================")
    print("       ALI VIP BOT")
    print("================================")
    print("Bot is running...")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("menu", menu)
    )

    app.add_handler(
        CommandHandler("gen", gen)
    )

    app.add_handler(
        CommandHandler("find", find_key)
    )

    app.add_handler(
        CommandHandler("ban", ban)
    )

    app.add_handler(
        CommandHandler("unban", unban)
    )

    app.add_handler(
        CommandHandler("restart", restart_key)
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.run_polling()


if __name__ == "__main__":
    main()
    