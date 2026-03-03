#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
لوحة تحكم إدارية - مكتبة عدن
تشغيل: python admin_panel.py
"""

import sqlite3
from datetime import datetime


def get_db():
    return sqlite3.connect("stationary_shop.db")


def print_header(title):
    print("\n" + "═" * 50)
    print(f"  {title}")
    print("═" * 50)


def show_dashboard():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    pending_orders = c.fetchone()[0]

    c.execute("SELECT SUM(total_price) FROM orders WHERE status='delivered'")
    revenue = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM print_orders")
    print_orders = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM research_orders")
    research_orders = c.fetchone()[0]

    conn.close()

    print_header("📊 لوحة التحكم الرئيسية")
    print(f"  👥 المستخدمون المسجلون : {users}")
    print(f"  📦 إجمالي الطلبات      : {total_orders}")
    print(f"  ⏳ طلبات معلقة         : {pending_orders}")
    print(f"  🖨️  طلبات طباعة         : {print_orders}")
    print(f"  📝 طلبات أبحاث          : {research_orders}")
    print(f"  💰 إيرادات مكتسبة       : {revenue:.2f} ج")


def list_pending_orders():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT o.id, u.full_name, u.phone, o.order_type, o.total_price, o.payment_method, o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        WHERE o.status = 'pending'
        ORDER BY o.id DESC
    """)
    orders = c.fetchall()
    conn.close()

    print_header("⏳ الطلبات المعلقة")
    if not orders:
        print("  ✅ لا توجد طلبات معلقة!")
        return

    for o in orders:
        print(f"\n  🆔 #{o[0]}  |  👤 {o[1]}  |  📱 {o[2]}")
        print(f"     نوع: {o[3]}  |  💰 {o[4]:.2f} ج  |  💳 {o[5]}")
        print(f"     📅 {o[6][:16]}")


def update_order_status(order_id: int, new_status: str):
    valid = ["pending", "confirmed", "processing", "ready", "delivered", "cancelled"]
    if new_status not in valid:
        print(f"❌ حالة غير صالحة. الحالات المتاحة: {', '.join(valid)}")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    if c.rowcount:
        print(f"✅ تم تحديث الطلب #{order_id} إلى: {new_status}")
    else:
        print(f"❌ لم يُعثر على الطلب #{order_id}")
    conn.commit()
    conn.close()


def list_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, phone, user_type, created_at FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()

    print_header("👥 المستخدمون المسجلون")
    type_labels = {
        "student": "🎒 مدرسي", "college": "🎓 جامعي",
        "teacher": "👨‍🏫 مدرس",  "researcher": "🔬 باحث",
    }
    for u in users:
        label = type_labels.get(u[3], u[3])
        print(f"  🆔 {u[0]}  |  {u[1]}  |  📱 {u[2]}  |  {label}  |  📅 {u[4][:10]}")


def add_product():
    print_header("➕ إضافة منتج جديد")
    categories = {
        "1": "notebooks", "2": "pens", "3": "geometry",
        "4": "art",       "5": "university", "6": "bags",
    }
    print("  الفئات:\n  1=دفاتر  2=أقلام  3=هندسة  4=فنية  5=جامعية  6=شنط")
    cat_choice = input("  اختار الفئة (1-6): ").strip()
    category = categories.get(cat_choice)
    if not category:
        print("❌ اختيار غير صالح")
        return

    name = input("  اسم المنتج: ").strip()
    desc = input("  وصف المنتج: ").strip()
    price = float(input("  السعر (ج): ").strip())
    unit = input("  الوحدة (قطعة/دفتر/...): ").strip() or "قطعة"
    stock = int(input("  الكمية المتاحة: ").strip() or "100")

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO products (category,name,description,price,unit,stock) VALUES (?,?,?,?,?,?)",
        (category, name, desc, price, unit, stock)
    )
    conn.commit()
    conn.close()
    print(f"✅ تمت إضافة: {name} بسعر {price} ج")


def list_products():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, category, name, price, unit, stock, active FROM products ORDER BY category, id")
    products = c.fetchall()
    conn.close()

    print_header("📦 قائمة المنتجات")
    current_cat = None
    for p in products:
        if p[1] != current_cat:
            current_cat = p[1]
            print(f"\n  ── {p[1].upper()} ──")
        status = "✅" if p[6] else "❌"
        print(f"  {status} #{p[0]}  {p[2]}  |  {p[3]} ج/{p[4]}  |  مخزون: {p[5]}")


def toggle_product(product_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT active, name FROM products WHERE id=?", (product_id,))
    row = c.fetchone()
    if not row:
        print(f"❌ المنتج #{product_id} غير موجود")
        conn.close()
        return
    new_state = 0 if row[0] else 1
    c.execute("UPDATE products SET active=? WHERE id=?", (new_state, product_id))
    conn.commit()
    conn.close()
    state_label = "مفعّل ✅" if new_state else "معطّل ❌"
    print(f"✅ المنتج '{row[1]}' الآن: {state_label}")


def export_orders_csv():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT o.id, u.full_name, u.phone, o.order_type, o.total_price,
               o.payment_method, o.status, o.created_at
        FROM orders o JOIN users u ON o.user_id = u.user_id
        ORDER BY o.id DESC
    """)
    orders = c.fetchall()
    conn.close()

    filename = f"orders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, "w", encoding="utf-8-sig") as f:
        f.write("ID,الاسم,الهاتف,النوع,الإجمالي,الدفع,الحالة,التاريخ\n")
        for o in orders:
            f.write(",".join(str(x) for x in o) + "\n")
    print(f"✅ تم التصدير إلى: {filename}")


def main_menu():
    while True:
        print_header("🔧 لوحة تحكم مكتبة عدن")
        print("  1. 📊 لوحة الإحصائيات")
        print("  2. ⏳ الطلبات المعلقة")
        print("  3. 🔄 تحديث حالة طلب")
        print("  4. 👥 قائمة المستخدمين")
        print("  5. 📦 قائمة المنتجات")
        print("  6. ➕ إضافة منتج")
        print("  7. 🔁 تفعيل/تعطيل منتج")
        print("  8. 📤 تصدير الطلبات CSV")
        print("  0. 🚪 خروج")
        print()

        choice = input("  اختار: ").strip()

        if choice == "1":
            show_dashboard()
        elif choice == "2":
            list_pending_orders()
        elif choice == "3":
            order_id = int(input("  رقم الطلب: ").strip())
            print("  الحالات: pending / confirmed / processing / ready / delivered / cancelled")
            status = input("  الحالة الجديدة: ").strip()
            update_order_status(order_id, status)
        elif choice == "4":
            list_users()
        elif choice == "5":
            list_products()
        elif choice == "6":
            add_product()
        elif choice == "7":
            product_id = int(input("  رقم المنتج: ").strip())
            toggle_product(product_id)
        elif choice == "8":
            export_orders_csv()
        elif choice == "0":
            print("\n👋 إلى اللقاء!")
            break
        else:
            print("⚠️ اختيار غير صالح")

        input("\n  ↩️ اضغط Enter للمتابعة...")


if __name__ == "__main__":
    main_menu()
