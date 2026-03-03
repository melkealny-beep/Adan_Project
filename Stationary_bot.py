#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت مكتبة الأدوات المدرسية وخدمات الطباعة
Stationary & Printing Services Telegram Bot
"""

import logging
import sqlite3
import json
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── إعدادات ───────────────────────────────────────────────────────────────────
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_IDS = [123456789]  # ضع هنا الـ Telegram ID بتاعك

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── حالات المحادثة ─────────────────────────────────────────────────────────────
(
    REGISTER_TYPE, REGISTER_NAME, REGISTER_PHONE,
    MAIN_MENU, CATEGORY_MENU, PRODUCT_DETAIL,
    CART_VIEW, CHECKOUT, PAYMENT_METHOD,
    ORDER_NOTES, PRINT_SERVICE, PRINT_DETAILS,
    RESEARCH_SERVICE, RESEARCH_DETAILS, BOOK_ORDER,
    ADMIN_MENU, ADMIN_PRODUCTS, ADMIN_ORDERS
) = range(18)


# ═══════════════════════════════════════════════════════════════════════════════
#  قاعدة البيانات
# ═══════════════════════════════════════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect("stationary_shop.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            full_name  TEXT,
            phone      TEXT,
            user_type  TEXT DEFAULT 'student',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT NOT NULL,
            name        TEXT NOT NULL,
            description TEXT,
            price       REAL NOT NULL,
            unit        TEXT DEFAULT 'قطعة',
            stock       INTEGER DEFAULT 100,
            active      INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            product_id INTEGER,
            qty        INTEGER DEFAULT 1,
            notes      TEXT,
            added_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER,
            order_type     TEXT,
            items_json     TEXT,
            total_price    REAL,
            payment_method TEXT,
            status         TEXT DEFAULT 'pending',
            notes          TEXT,
            created_at     TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS print_orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            service_type TEXT,
            pages        INTEGER,
            copies       INTEGER DEFAULT 1,
            color        INTEGER DEFAULT 0,
            binding      TEXT,
            total_price  REAL,
            status       TEXT DEFAULT 'pending',
            notes        TEXT,
            created_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS research_orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            service_type TEXT,
            topic        TEXT,
            pages        INTEGER,
            deadline     TEXT,
            total_price  REAL,
            status       TEXT DEFAULT 'pending',
            notes        TEXT,
            created_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # ─── بيانات المنتجات الأولية ───────────────────────────────────────────────
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        sample_products = [
            # دفاتر وكشاكيل
            ("notebooks", "دفتر سلك 100 ورقة", "دفتر مبطن جودة عالية", 12.0, "دفتر"),
            ("notebooks", "دفتر سلك 60 ورقة", "دفتر مبطن عادي", 7.0, "دفتر"),
            ("notebooks", "كراسة رسم A4", "كراسة رسم 40 ورقة", 15.0, "كراسة"),
            ("notebooks", "بلوك ملاحظات صغير", "بلوك لاصق ملون", 10.0, "بلوك"),
            ("notebooks", "دفتر حلقات A5", "دفتر حلقات مقسم", 18.0, "دفتر"),
            # أقلام
            ("pens", "قلم جاف أزرق", "قلم بايلوت 0.7", 3.0, "قلم"),
            ("pens", "قلم رصاص HB", "قلم رصاص ستاندر", 2.0, "قلم"),
            ("pens", "أقلام ملونة 12 لون", "أقلام تلوين خشبية", 25.0, "علبة"),
            ("pens", "ماركر ملون", "ماركر فلوماستر", 5.0, "قلم"),
            ("pens", "قلم هايلايتر", "تحديد فلوري", 6.0, "قلم"),
            # أدوات هندسية
            ("geometry", "فرجار معدني", "فرجار 15 سم معدني", 8.0, "قطعة"),
            ("geometry", "منقلة شفافة", "منقلة 180 درجة", 4.0, "قطعة"),
            ("geometry", "طقم هندسة كامل", "فرجار+منقلة+مسطرة+مثلث", 35.0, "طقم"),
            ("geometry", "مسطرة 30 سم", "مسطرة بلاستيك شفاف", 3.0, "قطعة"),
            # أدوات فنية
            ("art", "ألوان مائية 12 لون", "ألوان مائية بالفرشاة", 30.0, "علبة"),
            ("art", "ألوان أكريليك", "ألوان أكريليك 6 أنابيب", 45.0, "طقم"),
            ("art", "فرش رسم طقم", "فرش رسم 7 قطع", 20.0, "طقم"),
            ("art", "لوح رسم A3", "لوح رسم خشبي", 55.0, "قطعة"),
            # أدوات جامعية
            ("university", "فلاش ميموري 16GB", "فلاش USB 3.0", 70.0, "قطعة"),
            ("university", "آلة حاسبة علمية", "كاسيو 991", 185.0, "قطعة"),
            ("university", "ملفات بلاستيك A4", "ملف شفاف 50 ورقة", 5.0, "قطعة"),
            ("university", "ستابلر مع دباسات", "دباسة مكتبية+علبة دبابيس", 22.0, "قطعة"),
            # شنط مدرسية
            ("bags", "شنطة مدرسية صغيرة", "شنطة ابتدائي جودة متوسطة", 120.0, "شنطة"),
            ("bags", "شنطة مدرسية كبيرة", "شنطة إعدادي/ثانوي", 175.0, "شنطة"),
            ("bags", "شنطة جامعية ظهر", "شنطة لابتوب 15 بوصة", 220.0, "شنطة"),
        ]
        c.executemany(
            "INSERT INTO products (category, name, description, price, unit) VALUES (?,?,?,?,?)",
            sample_products
        )

    conn.commit()
    conn.close()


def get_db():
    return sqlite3.connect("stationary_shop.db")


# ═══════════════════════════════════════════════════════════════════════════════
#  مساعدات عامة
# ═══════════════════════════════════════════════════════════════════════════════
CATEGORIES = {
    "notebooks":  {"icon": "📓", "label": "دفاتر وكشاكيل"},
    "pens":       {"icon": "✏️",  "label": "أقلام وأدوات كتابة"},
    "geometry":   {"icon": "📐",  "label": "أدوات هندسية"},
    "art":        {"icon": "🎨",  "label": "أدوات فنية"},
    "university": {"icon": "🎓",  "label": "أدوات جامعية"},
    "bags":       {"icon": "🎒",  "label": "شنط مدرسية"},
}

PRINT_PRICES = {
    "bw_copy":      {"label": "تصوير أبيض وأسود",  "price": 0.50},
    "color_copy":   {"label": "تصوير ملون",         "price": 2.00},
    "bw_print":     {"label": "طباعة ليزر عادية",   "price": 1.00},
    "color_print":  {"label": "طباعة ليزر ملون",    "price": 3.00},
    "memo_print":   {"label": "طباعة مذكرات",       "price": 2.00},
    "book_print":   {"label": "طباعة كتب",          "price": 3.50},
}

BINDING_PRICES = {
    "thermal": {"label": "تجليد حراري",  "price": 15.0},
    "wire":    {"label": "تجليد سلك",    "price":  8.0},
    "none":    {"label": "بدون تجليد",   "price":  0.0},
}

RESEARCH_PRICES = {
    "university": {"label": "بحث جامعي",           "price": 200.0},
    "masters":    {"label": "رسالة ماجستير",        "price": 1500.0},
    "phd":        {"label": "أطروحة دكتوراه",       "price": 3000.0},
    "diploma":    {"label": "بحث دبلوم",            "price": 800.0},
    "format":     {"label": "تنسيق بحث فقط",        "price": 100.0},
    "translate":  {"label": "ترجمة بحث",            "price": 150.0},
    "review":     {"label": "مراجعة لغوية وعلمية",  "price": 120.0},
}

PAYMENT_METHODS = {
    "cash":   "💵 كاش عند الاستلام",
    "card":   "💳 بطاقة بنكية",
    "wallet": "📱 محفظة إلكترونية",
}

STATUS_LABELS = {
    "pending":    "⏳ قيد المراجعة",
    "confirmed":  "✅ مؤكد",
    "processing": "🔄 جاري التنفيذ",
    "ready":      "📦 جاهز للاستلام",
    "delivered":  "🎉 تم التسليم",
    "cancelled":  "❌ ملغي",
}


def get_user(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def register_user(user_id, username, full_name, phone, user_type):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO users (user_id,username,full_name,phone,user_type) VALUES (?,?,?,?,?)",
        (user_id, username, full_name, phone, user_type)
    )
    conn.commit()
    conn.close()


def get_cart(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.id, p.name, p.price, c.qty, p.unit, c.notes
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    """, (user_id,))
    items = c.fetchall()
    conn.close()
    return items


def cart_total(user_id: int) -> float:
    items = get_cart(user_id)
    return sum(item[2] * item[3] for item in items)


def clear_cart(user_id: int):
    conn = get_db()
    get_db().execute("DELETE FROM cart WHERE user_id=?", (user_id,)).connection.commit()
    conn.close()


def add_to_cart(user_id, product_id, qty=1, notes=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, qty FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE cart SET qty=? WHERE id=?", (existing[1] + qty, existing[0]))
    else:
        c.execute("INSERT INTO cart (user_id,product_id,qty,notes) VALUES (?,?,?,?)",
                  (user_id, product_id, qty, notes))
    conn.commit()
    conn.close()


def create_order(user_id, order_type, items_json, total, payment, notes=""):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (user_id,order_type,items_json,total_price,payment_method,notes) VALUES (?,?,?,?,?,?)",
        (user_id, order_type, items_json, total, payment, notes)
    )
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id


# ═══════════════════════════════════════════════════════════════════════════════
#  لوحات المفاتيح
# ═══════════════════════════════════════════════════════════════════════════════
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 أدوات مدرسية",      callback_data="menu_stationery"),
         InlineKeyboardButton("📚 حجز كتب ومذكرات",   callback_data="menu_books")],
        [InlineKeyboardButton("🖨️ خدمات الطباعة",     callback_data="menu_print"),
         InlineKeyboardButton("📝 أبحاث علمية",        callback_data="menu_research")],
        [InlineKeyboardButton("🛍️ سلة التسوق",         callback_data="menu_cart"),
         InlineKeyboardButton("📦 طلباتي",             callback_data="menu_orders")],
        [InlineKeyboardButton("👤 حسابي",              callback_data="menu_profile"),
         InlineKeyboardButton("📞 تواصل معنا",          callback_data="menu_contact")],
    ])


def categories_keyboard():
    buttons = []
    row = []
    for key, val in CATEGORIES.items():
        row.append(InlineKeyboardButton(
            f"{val['icon']} {val['label']}", callback_data=f"cat_{key}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(category: str, page: int = 0):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, price, unit FROM products WHERE category=? AND active=1", (category,))
    products = c.fetchall()
    conn.close()

    per_page = 6
    start = page * per_page
    end = start + per_page
    page_products = products[start:end]

    buttons = []
    for prod in page_products:
        buttons.append([InlineKeyboardButton(
            f"🔹 {prod[1]}  —  {prod[2]} ج/{prod[3]}",
            callback_data=f"prod_{prod[0]}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"catpage_{category}_{page-1}"))
    if end < len(products):
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"catpage_{category}_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("🔙 الفئات", callback_data="menu_stationery")])
    return InlineKeyboardMarkup(buttons)


def product_action_keyboard(product_id: int, category: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ أضف للسلة (1 قطعة)", callback_data=f"addcart_{product_id}_1"),
         InlineKeyboardButton("➕ أضف (3 قطع)",        callback_data=f"addcart_{product_id}_3")],
        [InlineKeyboardButton("➕ أضف (5 قطع)",        callback_data=f"addcart_{product_id}_5"),
         InlineKeyboardButton("➕ كمية مخصصة",         callback_data=f"addcart_{product_id}_custom")],
        [InlineKeyboardButton("🔙 رجوع للمنتجات",      callback_data=f"cat_{category}")],
    ])


def print_services_keyboard():
    buttons = []
    for key, val in PRINT_PRICES.items():
        buttons.append([InlineKeyboardButton(
            f"🖨️ {val['label']}  —  {val['price']} ج/صفحة",
            callback_data=f"print_{key}"
        )])
    buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def binding_keyboard():
    buttons = []
    for key, val in BINDING_PRICES.items():
        label = f"📎 {val['label']}  —  {val['price']} ج" if val["price"] > 0 else f"🚫 {val['label']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"bind_{key}")])
    return InlineKeyboardMarkup(buttons)


def research_keyboard():
    buttons = []
    for key, val in RESEARCH_PRICES.items():
        buttons.append([InlineKeyboardButton(
            f"📝 {val['label']}  —  من {val['price']} ج",
            callback_data=f"research_{key}"
        )])
    buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def payment_keyboard():
    buttons = [[InlineKeyboardButton(label, callback_data=f"pay_{key}")]
               for key, label in PAYMENT_METHODS.items()]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def cart_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ إتمام الطلب",       callback_data="checkout_start"),
         InlineKeyboardButton("🗑️ تفريغ السلة",       callback_data="cart_clear")],
        [InlineKeyboardButton("🛒 إضافة منتجات",      callback_data="menu_stationery"),
         InlineKeyboardButton("🔙 القائمة الرئيسية",  callback_data="back_main")],
    ])


# ═══════════════════════════════════════════════════════════════════════════════
#  المعالجات
# ═══════════════════════════════════════════════════════════════════════════════

# ── /start ────────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if user:
        await update.message.reply_text(
            f"👋 أهلاً بك مجدداً *{user[2]}*!\n\n"
            "🏪 *مكتبة عدن للأدوات المدرسية وخدمات الطباعة*\n"
            "اختار من القائمة ما تحتاجه:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎒 طالب مدرسي",    callback_data="reg_student")],
        [InlineKeyboardButton("🎓 طالب جامعي",    callback_data="reg_college")],
        [InlineKeyboardButton("👨‍🏫 مدرس / مركز",  callback_data="reg_teacher")],
        [InlineKeyboardButton("🔬 باحث أكاديمي",  callback_data="reg_researcher")],
    ])
    await update.message.reply_text(
        "🏪 *مرحباً بك في مكتبة عدن!*\n\n"
        "للأدوات المدرسية • الطباعة • الأبحاث العلمية\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "أولاً، ما هو وصفك؟",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return REGISTER_TYPE


# ── التسجيل ───────────────────────────────────────────────────────────────────
async def register_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    type_map = {
        "reg_student":    "student",
        "reg_college":    "college",
        "reg_teacher":    "teacher",
        "reg_researcher": "researcher",
    }
    ctx.user_data["user_type"] = type_map.get(query.data, "student")
    await query.edit_message_text(
        "✏️ اكتب *اسمك الكامل* من فضلك:",
        parse_mode="Markdown"
    )
    return REGISTER_NAME


async def register_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["full_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📱 اكتب *رقم هاتفك* (مثال: 01012345678):",
        parse_mode="Markdown"
    )
    return REGISTER_PHONE


async def register_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.startswith("0") or len(phone) < 10:
        await update.message.reply_text("⚠️ رقم غير صحيح، حاول تاني:")
        return REGISTER_PHONE

    u = update.effective_user
    register_user(u.id, u.username or "", ctx.user_data["full_name"], phone, ctx.user_data["user_type"])

    type_labels = {
        "student":    "طالب مدرسي", "college": "طالب جامعي",
        "teacher":    "مدرس",       "researcher": "باحث أكاديمي",
    }
    await update.message.reply_text(
        f"🎉 *تم التسجيل بنجاح!*\n\n"
        f"👤 الاسم: {ctx.user_data['full_name']}\n"
        f"📱 الهاتف: {phone}\n"
        f"🏷️ النوع: {type_labels[ctx.user_data['user_type']]}\n\n"
        "اختار من القائمة ما تحتاجه:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU


# ── القائمة الرئيسية ──────────────────────────────────────────────────────────
async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data in ("back_main", "menu_home"):
        await query.edit_message_text(
            "🏪 *مكتبة عدن*\nاختار الخدمة التي تحتاجها:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if data == "menu_stationery":
        await query.edit_message_text(
            "🛒 *الأدوات المدرسية والجامعية*\nاختار الفئة:",
            parse_mode="Markdown",
            reply_markup=categories_keyboard()
        )
        return CATEGORY_MENU

    if data == "menu_books":
        await query.edit_message_text(
            "📚 *حجز كتب ومذكرات*\n\n"
            "نوفر:\n"
            "• 📗 كتب مدرسية لجميع الصفوف\n"
            "• 📘 مذكرات السناتر لكل المواد\n"
            "• 📙 كتب جامعية\n\n"
            "📞 اتصل بنا لطلب الكتب:\n*01000000000*\n\n"
            "أو اكتب اسم الكتاب/المذكرة التي تريدها وسنرد عليك فوراً:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")]
            ])
        )
        return MAIN_MENU

    if data == "menu_print":
        await query.edit_message_text(
            "🖨️ *خدمات الطباعة والتصوير*\n\nاختار الخدمة:",
            parse_mode="Markdown",
            reply_markup=print_services_keyboard()
        )
        return PRINT_SERVICE

    if data == "menu_research":
        await query.edit_message_text(
            "📝 *الأبحاث العلمية والأكاديمية*\n\nاختار نوع الخدمة:",
            parse_mode="Markdown",
            reply_markup=research_keyboard()
        )
        return RESEARCH_SERVICE

    if data == "menu_cart":
        return await show_cart(update, ctx)

    if data == "menu_orders":
        return await show_orders(update, ctx)

    if data == "menu_profile":
        return await show_profile(update, ctx)

    if data == "menu_contact":
        await query.edit_message_text(
            "📞 *تواصل معنا*\n\n"
            "🏪 مكتبة عدن\n"
            "📍 العنوان: شارع المدارس، أمام المدرسة الابتدائية\n"
            "📱 هاتف: 01000000000\n"
            "📱 واتساب: 01000000000\n"
            "🕐 مواعيد العمل: السبت - الخميس، 8 ص - 10 م",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )
        return MAIN_MENU

    return MAIN_MENU


# ── الفئات والمنتجات ──────────────────────────────────────────────────────────
async def category_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("cat_"):
        cat = data[4:]
        ctx.user_data["current_category"] = cat
        cat_info = CATEGORIES.get(cat, {"icon": "📦", "label": cat})
        await query.edit_message_text(
            f"{cat_info['icon']} *{cat_info['label']}*\nاختار المنتج:",
            parse_mode="Markdown",
            reply_markup=products_keyboard(cat)
        )
        return PRODUCT_DETAIL

    if data.startswith("catpage_"):
        _, cat, page = data.split("_")
        await query.edit_message_text(
            f"📦 المنتجات — الصفحة {int(page)+1}:",
            parse_mode="Markdown",
            reply_markup=products_keyboard(cat, int(page))
        )
        return PRODUCT_DETAIL

    if data.startswith("prod_"):
        product_id = int(data[5:])
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE id=?", (product_id,))
        prod = c.fetchone()
        conn.close()

        if prod:
            ctx.user_data["current_product"] = product_id
            cat = prod[1]
            text = (
                f"🔹 *{prod[2]}*\n\n"
                f"📝 {prod[3]}\n"
                f"💰 السعر: *{prod[4]} ج / {prod[5]}*\n"
                f"📦 المتاح: {prod[6]} قطعة\n"
            )
            await query.edit_message_text(
                text, parse_mode="Markdown",
                reply_markup=product_action_keyboard(product_id, cat)
            )
        return PRODUCT_DETAIL

    if data.startswith("addcart_"):
        parts = data.split("_")
        product_id = int(parts[1])
        qty_str = parts[2]

        if qty_str == "custom":
            ctx.user_data["pending_product"] = product_id
            await query.edit_message_text("📦 اكتب الكمية التي تريدها:")
            return PRODUCT_DETAIL

        qty = int(qty_str)
        add_to_cart(query.from_user.id, product_id, qty)
        total = cart_total(query.from_user.id)
        await query.answer(f"✅ تمت الإضافة! إجمالي السلة: {total:.2f} ج", show_alert=True)
        return PRODUCT_DETAIL

    return PRODUCT_DETAIL


async def handle_custom_qty(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if "pending_product" in ctx.user_data:
        try:
            qty = int(update.message.text.strip())
            if qty <= 0:
                raise ValueError
            add_to_cart(update.effective_user.id, ctx.user_data["pending_product"], qty)
            total = cart_total(update.effective_user.id)
            del ctx.user_data["pending_product"]
            await update.message.reply_text(
                f"✅ تمت إضافة {qty} قطعة!\n💰 إجمالي السلة: *{total:.2f} ج*",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        except ValueError:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً أكبر من صفر:")
        return PRODUCT_DETAIL
    return MAIN_MENU


# ── السلة ─────────────────────────────────────────────────────────────────────
async def show_cart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    items = get_cart(user_id)

    if not items:
        await query.edit_message_text(
            "🛍️ *سلة التسوق فارغة!*\n\nأضف منتجات من قسم الأدوات المدرسية.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 تصفح المنتجات", callback_data="menu_stationery")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")],
            ])
        )
        return CART_VIEW

    text = "🛍️ *سلة التسوق*\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, item in enumerate(items, 1):
        subtotal = item[2] * item[3]
        text += f"{i}. {item[1]}\n   {item[3]} × {item[2]} ج = *{subtotal:.2f} ج*\n"
    text += f"\n━━━━━━━━━━━━━━━━━━━━\n💰 *الإجمالي: {cart_total(user_id):.2f} ج*"

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=cart_keyboard())
    return CART_VIEW


async def cart_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cart_clear":
        conn = get_db()
        conn.execute("DELETE FROM cart WHERE user_id=?", (query.from_user.id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(
            "🗑️ تم تفريغ السلة.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 تصفح المنتجات", callback_data="menu_stationery")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")],
            ])
        )
        return CART_VIEW

    if query.data == "checkout_start":
        await query.edit_message_text(
            "💳 *اختار طريقة الدفع:*",
            parse_mode="Markdown",
            reply_markup=payment_keyboard()
        )
        return PAYMENT_METHOD

    return CART_VIEW


# ── الدفع وإتمام الطلب ────────────────────────────────────────────────────────
async def payment_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("pay_"):
        method = query.data[4:]
        ctx.user_data["payment_method"] = method
        items = get_cart(query.from_user.id)
        total = cart_total(query.from_user.id)

        items_data = [{"name": i[1], "price": i[2], "qty": i[3]} for i in items]
        order_id = create_order(
            query.from_user.id, "stationery",
            json.dumps(items_data, ensure_ascii=False),
            total, method
        )

        conn = get_db()
        conn.execute("DELETE FROM cart WHERE user_id=?", (query.from_user.id,))
        conn.commit()
        conn.close()

        payment_label = PAYMENT_METHODS.get(method, method)
        await query.edit_message_text(
            f"🎉 *تم استلام طلبك بنجاح!*\n\n"
            f"🆔 رقم الطلب: *#{order_id}*\n"
            f"💰 الإجمالي: *{total:.2f} ج*\n"
            f"💳 الدفع: {payment_label}\n"
            f"⏳ الحالة: قيد المراجعة\n\n"
            "📞 سنتواصل معك قريباً للتأكيد!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
            ])
        )
        return MAIN_MENU

    return PAYMENT_METHOD


# ── خدمات الطباعة ─────────────────────────────────────────────────────────────
async def print_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("print_"):
        service = query.data[6:]
        ctx.user_data["print_service"] = service
        svc = PRINT_PRICES[service]
        ctx.user_data["print_price_per_page"] = svc["price"]

        await query.edit_message_text(
            f"🖨️ *{svc['label']}*\n"
            f"💰 السعر: {svc['price']} ج / صفحة\n\n"
            "📄 كم عدد الصفحات؟\n(اكتب الرقم فقط)",
            parse_mode="Markdown"
        )
        ctx.user_data["print_step"] = "pages"
        return PRINT_DETAILS

    return PRINT_SERVICE


async def print_details_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = ctx.user_data.get("print_step", "")

    if step == "pages":
        try:
            pages = int(text)
            if pages <= 0:
                raise ValueError
            ctx.user_data["print_pages"] = pages
            ctx.user_data["print_step"] = "copies"
            await update.message.reply_text("🔢 كم نسخة تريد؟ (اكتب الرقم فقط)")
        except ValueError:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً:")
        return PRINT_DETAILS

    if step == "copies":
        try:
            copies = int(text)
            if copies <= 0:
                raise ValueError
            ctx.user_data["print_copies"] = copies
            ctx.user_data["print_step"] = "binding"
            await update.message.reply_text(
                "📎 هل تريد تجليد؟",
                reply_markup=binding_keyboard()
            )
        except ValueError:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً:")
        return PRINT_DETAILS

    return PRINT_DETAILS


async def binding_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("bind_"):
        binding = query.data[5:]
        ctx.user_data["print_binding"] = binding
        ctx.user_data["print_step"] = "confirm"

        pages = ctx.user_data.get("print_pages", 0)
        copies = ctx.user_data.get("print_copies", 1)
        price_per_page = ctx.user_data.get("print_price_per_page", 0)
        bind_price = BINDING_PRICES[binding]["price"]

        subtotal = pages * copies * price_per_page
        total = subtotal + (bind_price * copies)
        ctx.user_data["print_total"] = total

        service_name = PRINT_PRICES[ctx.user_data["print_service"]]["label"]
        bind_name = BINDING_PRICES[binding]["label"]

        await query.edit_message_text(
            f"📋 *ملخص طلب الطباعة*\n\n"
            f"🖨️ الخدمة: {service_name}\n"
            f"📄 عدد الصفحات: {pages}\n"
            f"🔢 عدد النسخ: {copies}\n"
            f"📎 التجليد: {bind_name}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *الإجمالي: {total:.2f} ج*\n\n"
            "اختار طريقة الدفع:",
            parse_mode="Markdown",
            reply_markup=payment_keyboard()
        )
        return PAYMENT_METHOD

    return PRINT_DETAILS


async def print_payment_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("pay_") and ctx.user_data.get("print_service"):
        method = query.data[4:]
        total = ctx.user_data.get("print_total", 0)

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO print_orders (user_id,service_type,pages,copies,binding,total_price,payment_method) VALUES (?,?,?,?,?,?,?)",
            (
                query.from_user.id,
                ctx.user_data.get("print_service"),
                ctx.user_data.get("print_pages", 0),
                ctx.user_data.get("print_copies", 1),
                ctx.user_data.get("print_binding", "none"),
                total, method
            )
        )
        order_id = c.lastrowid
        conn.commit()
        conn.close()

        for key in ["print_service", "print_pages", "print_copies", "print_binding",
                    "print_total", "print_price_per_page", "print_step"]:
            ctx.user_data.pop(key, None)

        await query.edit_message_text(
            f"✅ *تم استلام طلب الطباعة!*\n\n"
            f"🆔 رقم الطلب: *#{order_id}*\n"
            f"💰 الإجمالي: *{total:.2f} ج*\n\n"
            "📦 سيكون جاهزاً خلال 24 ساعة.\nسنبلغك عند الجاهزية!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
            ])
        )
        return MAIN_MENU

    return PAYMENT_METHOD


# ── الأبحاث العلمية ───────────────────────────────────────────────────────────
async def research_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("research_"):
        service = query.data[9:]
        ctx.user_data["research_service"] = service
        svc = RESEARCH_PRICES[service]

        await query.edit_message_text(
            f"📝 *{svc['label']}*\n"
            f"💰 السعر يبدأ من: {svc['price']} ج\n\n"
            "✍️ اكتب *موضوع البحث* أو التفاصيل التي تريدها:",
            parse_mode="Markdown"
        )
        ctx.user_data["research_step"] = "topic"
        return RESEARCH_DETAILS

    return RESEARCH_SERVICE


async def research_details_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = ctx.user_data.get("research_step", "")

    if step == "topic":
        ctx.user_data["research_topic"] = text
        ctx.user_data["research_step"] = "pages"
        await update.message.reply_text(
            "📄 كم عدد الصفحات المطلوبة؟\n(اكتب رقماً أو اكتب 'غير محدد')"
        )
        return RESEARCH_DETAILS

    if step == "pages":
        ctx.user_data["research_pages"] = text
        ctx.user_data["research_step"] = "deadline"
        await update.message.reply_text(
            "📅 ما هو الموعد النهائي للتسليم؟\n(مثال: بعد أسبوع، أو تاريخ محدد)"
        )
        return RESEARCH_DETAILS

    if step == "deadline":
        ctx.user_data["research_deadline"] = text
        service = ctx.user_data.get("research_service", "")
        svc = RESEARCH_PRICES.get(service, {})
        base_price = svc.get("price", 0)

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO research_orders (user_id,service_type,topic,pages,deadline,total_price) VALUES (?,?,?,?,?,?)",
            (
                update.effective_user.id,
                service,
                ctx.user_data.get("research_topic", ""),
                ctx.user_data.get("research_pages", "غير محدد"),
                text,
                base_price
            )
        )
        order_id = c.lastrowid
        conn.commit()
        conn.close()

        for key in ["research_service", "research_topic", "research_pages",
                    "research_deadline", "research_step"]:
            ctx.user_data.pop(key, None)

        await update.message.reply_text(
            f"📨 *تم استلام طلبك!*\n\n"
            f"🆔 رقم الطلب: *#{order_id}*\n"
            f"📝 الموضوع: {ctx.user_data.get('research_topic', text)}\n"
            f"💰 السعر يبدأ من: *{base_price} ج* (سيُحدد بعد المراجعة)\n\n"
            "📞 سيتواصل معك متخصصنا خلال ساعات لمناقشة التفاصيل.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    return RESEARCH_DETAILS


# ── الطلبات والحساب الشخصي ────────────────────────────────────────────────────
async def show_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, order_type, total_price, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (user_id,)
    )
    orders = c.fetchall()
    conn.close()

    if not orders:
        await query.edit_message_text(
            "📦 *لا توجد طلبات بعد.*\n\nابدأ التسوق الآن!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 تسوق الآن", callback_data="menu_stationery")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
            ])
        )
        return MAIN_MENU

    text = "📦 *آخر طلباتك:*\n━━━━━━━━━━━━━━━━━━━━\n"
    type_labels = {
        "stationery": "🛒 أدوات",
        "print":      "🖨️ طباعة",
        "research":   "📝 بحث",
    }
    for o in orders:
        status_label = STATUS_LABELS.get(o[3], o[3])
        type_label = type_labels.get(o[1], o[1])
        text += (
            f"#{o[0]} {type_label}\n"
            f"   💰 {o[2]:.2f} ج | {status_label}\n"
            f"   📅 {o[4][:10]}\n\n"
        )

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")]
        ])
    )
    return MAIN_MENU


async def show_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user(query.from_user.id)

    if not user:
        await query.edit_message_text("⚠️ لم يتم العثور على بياناتك. اكتب /start للتسجيل.")
        return MAIN_MENU

    type_labels = {
        "student":    "🎒 طالب مدرسي",
        "college":    "🎓 طالب جامعي",
        "teacher":    "👨‍🏫 مدرس",
        "researcher": "🔬 باحث",
    }

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (user[0],))
    orders_count = c.fetchone()[0]
    c.execute("SELECT SUM(total_price) FROM orders WHERE user_id=? AND status='delivered'", (user[0],))
    total_spent = c.fetchone()[0] or 0
    conn.close()

    await query.edit_message_text(
        f"👤 *حسابي*\n\n"
        f"📛 الاسم: {user[2]}\n"
        f"📱 الهاتف: {user[3]}\n"
        f"🏷️ النوع: {type_labels.get(user[4], user[4])}\n"
        f"📦 عدد الطلبات: {orders_count}\n"
        f"💰 إجمالي المشتريات: {total_spent:.2f} ج\n"
        f"📅 عضو منذ: {user[5][:10]}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")]
        ])
    )
    return MAIN_MENU


# ── لوحة الإدارة ──────────────────────────────────────────────────────────────
async def admin_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح.")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT SUM(total_price) FROM orders WHERE status='delivered'")
    revenue = c.fetchone()[0] or 0
    conn.close()

    await update.message.reply_text(
        f"🔧 *لوحة التحكم*\n\n"
        f"👥 المستخدمون: {users}\n"
        f"⏳ طلبات معلقة: {pending}\n"
        f"💰 إيرادات: {revenue:.2f} ج\n",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 الطلبات المعلقة",  callback_data="adm_pending"),
             InlineKeyboardButton("👥 المستخدمون",        callback_data="adm_users")],
            [InlineKeyboardButton("📊 إحصائيات",         callback_data="adm_stats"),
             InlineKeyboardButton("🔙 إغلاق",            callback_data="back_main")],
        ])
    )


async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "adm_pending":
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT o.id, u.full_name, o.order_type, o.total_price, o.created_at
            FROM orders o JOIN users u ON o.user_id = u.user_id
            WHERE o.status='pending' ORDER BY o.id DESC LIMIT 10
        """)
        orders = c.fetchall()
        conn.close()

        if not orders:
            await query.edit_message_text("✅ لا توجد طلبات معلقة.",
                                          reply_markup=InlineKeyboardMarkup([[
                                              InlineKeyboardButton("🔙", callback_data="back_main")
                                          ]]))
            return

        text = "⏳ *الطلبات المعلقة:*\n\n"
        for o in orders:
            text += f"#{o[0]} | {o[1]} | {o[2]} | {o[3]:.2f} ج | {o[4][:10]}\n"

        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton("🔙", callback_data="back_main")
                                      ]]))

    if data == "adm_stats":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM orders")
        total_orders = c.fetchone()[0]
        c.execute("SELECT SUM(total_price) FROM orders")
        total_rev = c.fetchone()[0] or 0
        c.execute("SELECT category, COUNT(*) FROM products GROUP BY category")
        cats = c.fetchall()
        conn.close()

        text = (
            f"📊 *الإحصائيات*\n\n"
            f"📦 إجمالي الطلبات: {total_orders}\n"
            f"💰 إجمالي الإيرادات: {total_rev:.2f} ج\n\n"
            "📁 المنتجات:\n"
        )
        for cat in cats:
            cat_info = CATEGORIES.get(cat[0], {"icon": "📦", "label": cat[0]})
            text += f"  {cat_info['icon']} {cat_info['label']}: {cat[1]} منتج\n"

        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton("🔙", callback_data="back_main")
                                      ]]))


# ═══════════════════════════════════════════════════════════════════════════════
#  نقطة الدخول الرئيسية
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    init_db()
    logger.info("✅ قاعدة البيانات جاهزة")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER_TYPE:   [CallbackQueryHandler(register_type,        pattern="^reg_")],
            REGISTER_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_PHONE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone)],
            MAIN_MENU: [
                CallbackQueryHandler(menu_callback),
                CallbackQueryHandler(cart_action,      pattern="^(cart_|checkout_)"),
                CallbackQueryHandler(admin_callback,   pattern="^adm_"),
            ],
            CATEGORY_MENU:  [CallbackQueryHandler(menu_callback, pattern="^(back_main|menu_)"),
                             CallbackQueryHandler(category_callback)],
            PRODUCT_DETAIL: [
                CallbackQueryHandler(category_callback),
                CallbackQueryHandler(menu_callback,    pattern="^(back_main|menu_)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_qty),
            ],
            CART_VIEW: [
                CallbackQueryHandler(cart_action,      pattern="^(cart_|checkout_)"),
                CallbackQueryHandler(menu_callback,    pattern="^(back_main|menu_)"),
            ],
            PAYMENT_METHOD: [
                CallbackQueryHandler(print_payment_callback, pattern="^pay_"),
                CallbackQueryHandler(payment_callback,       pattern="^pay_"),
                CallbackQueryHandler(menu_callback,          pattern="^(back_main|menu_)"),
            ],
            PRINT_SERVICE:  [
                CallbackQueryHandler(print_callback,   pattern="^print_"),
                CallbackQueryHandler(menu_callback,    pattern="^(back_main|menu_)"),
            ],
            PRINT_DETAILS:  [
                CallbackQueryHandler(binding_callback, pattern="^bind_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, print_details_input),
            ],
            RESEARCH_SERVICE: [
                CallbackQueryHandler(research_callback, pattern="^research_"),
                CallbackQueryHandler(menu_callback,     pattern="^(back_main|menu_)"),
            ],
            RESEARCH_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, research_details_input),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("admin", admin_command))

    logger.info("🚀 البوت يعمل...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
