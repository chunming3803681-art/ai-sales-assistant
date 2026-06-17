"""
SQLite 数据库模块 - 管理客户分析记录
"""
import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "customers.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_text TEXT NOT NULL,
            customer_name TEXT,
            need_summary TEXT,
            budget TEXT,
            region TEXT,
            buy_type TEXT,
            purpose TEXT,
            interest_level TEXT,
            follow_up TEXT,
            note TEXT,
            dealt INTEGER DEFAULT 0,
            dealt_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 兼容旧列
    for col, col_type in [("customer_name", "TEXT"), ("note", "TEXT"), ("dealt", "INTEGER DEFAULT 0"), ("dealt_at", "TIMESTAMP")]:
        try:
            cursor.execute(f"SELECT {col} FROM customers LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute(f"ALTER TABLE customers ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def save_analysis(chat_text, customer_name, need_summary, budget, region, buy_type, purpose, interest_level, follow_up):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO customers (chat_text, customer_name, need_summary, budget, region, buy_type, purpose, interest_level, follow_up) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (chat_text, customer_name, need_summary, budget, region, buy_type, purpose, interest_level, follow_up),
    )
    conn.commit()
    conn.close()


def save_name(customer_id, name):
    """更新客户名字"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE customers SET customer_name=? WHERE id=?", (name, customer_id))
    conn.commit()
    conn.close()


def save_note(customer_id, note):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE customers SET note=? WHERE id=?", (note, customer_id))
    conn.commit()
    conn.close()


def mark_dealt(customer_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE customers SET dealt=1, dealt_at=? WHERE id=?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), customer_id),
    )
    conn.commit()
    conn.close()


def get_all_records(limit=50):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, customer_name, need_summary, budget, region, buy_type, interest_level, follow_up, note, dealt, created_at FROM customers ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_record_count():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM customers")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_clients(interest_filter=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if interest_filter and interest_filter in ("高", "中", "低"):
        cursor.execute(
            "SELECT id, customer_name, need_summary, budget, region, buy_type, purpose, interest_level, follow_up, note, dealt, created_at FROM customers WHERE interest_level=? ORDER BY id DESC",
            (interest_filter,),
        )
    else:
        cursor.execute(
            "SELECT id, customer_name, need_summary, budget, region, buy_type, purpose, interest_level, follow_up, note, dealt, created_at FROM customers ORDER BY id DESC"
        )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_today_stats():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM customers WHERE date(created_at)=?", (today,))
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM customers WHERE date(dealt_at)=?", (today,))
    dealt = cursor.fetchone()[0]
    conn.close()
    return total, dealt


def get_week_stats():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday_str = monday.strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COUNT(*) FROM customers WHERE date(created_at) BETWEEN ? AND ?",
        (monday_str, today_str),
    )
    total = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM customers WHERE date(dealt_at) BETWEEN ? AND ?",
        (monday_str, today_str),
    )
    dealt = cursor.fetchone()[0]
    conn.close()
    return total, dealt


def get_month_stats():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now()
    first_day = today.replace(day=1).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COUNT(*) FROM customers WHERE date(created_at) BETWEEN ? AND ?",
        (first_day, today_str),
    )
    total = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM customers WHERE date(dealt_at) BETWEEN ? AND ?",
        (first_day, today_str),
    )
    dealt = cursor.fetchone()[0]
    conn.close()
    return total, dealt


def get_need_followup():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, customer_name, need_summary, budget, region, interest_level, follow_up, created_at FROM customers WHERE dealt=0 AND interest_level IN ('高','中') ORDER BY CASE WHEN interest_level='高' THEN 0 ELSE 1 END, id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_client(customer_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    conn.commit()
    conn.close()


def batch_delete(ids):
    if not ids:
        return
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    cursor.execute(f"DELETE FROM customers WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()


def get_dealt_records(limit=50):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, customer_name, need_summary, budget, region, dealt_at FROM customers WHERE dealt=1 ORDER BY dealt_at DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows