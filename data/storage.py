"""SQLite 本地存储层"""
import sqlite3
import os
from typing import Optional

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(DB_DIR), 'salary.db')


def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = DB_PATH):
    """初始化数据库表"""
    conn = get_conn(db_path)
    cursor = conn.cursor()
    
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        
        CREATE TABLE IF NOT EXISTS monthly_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year_month TEXT NOT NULL UNIQUE,
            basic_salary REAL DEFAULT 0,
            weekend_overtime_days REAL DEFAULT 1,
            holiday_overtime_days REAL DEFAULT 0,
            social_insurance_base REAL DEFAULT 0,
            housing_fund_base REAL DEFAULT 0,
            housing_fund_rate REAL DEFAULT 0.08,
            tax_deductions REAL DEFAULT 0,
            actual_necessary REAL DEFAULT 0,
            actual_flexible REAL DEFAULT 0,
            actual_savings REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS budget_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year_month TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            budget_amount REAL DEFAULT 0,
            actual_amount REAL DEFAULT 0,
            sort_order INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


# ---- 月度记录 CRUD ----

def save_monthly_record(record: dict, db_path: str = DB_PATH) -> int:
    """保存或更新月度记录（year_month 为唯一键）"""
    conn = get_conn(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO monthly_records (
            year_month, basic_salary, weekend_overtime_days, holiday_overtime_days,
            social_insurance_base, housing_fund_base, housing_fund_rate,
            tax_deductions, actual_necessary, actual_flexible, actual_savings, notes
        ) VALUES (
            :year_month, :basic_salary, :weekend_overtime_days, :holiday_overtime_days,
            :social_insurance_base, :housing_fund_base, :housing_fund_rate,
            :tax_deductions, :actual_necessary, :actual_flexible, :actual_savings, :notes
        )
        ON CONFLICT(year_month) DO UPDATE SET
            basic_salary=excluded.basic_salary,
            weekend_overtime_days=excluded.weekend_overtime_days,
            holiday_overtime_days=excluded.holiday_overtime_days,
            social_insurance_base=excluded.social_insurance_base,
            housing_fund_base=excluded.housing_fund_base,
            housing_fund_rate=excluded.housing_fund_rate,
            tax_deductions=excluded.tax_deductions,
            actual_necessary=excluded.actual_necessary,
            actual_flexible=excluded.actual_flexible,
            actual_savings=excluded.actual_savings,
            notes=excluded.notes
    """, record)
    conn.commit()
    rid: int = cursor.lastrowid or 0
    conn.close()
    return rid


def get_monthly_record(year_month: str, db_path: str = DB_PATH) -> Optional[dict]:
    """查询指定月份的记录"""
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monthly_records WHERE year_month=?", (year_month,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def list_records(db_path: str = DB_PATH) -> list:
    """列出所有记录（按年月降序）"""
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monthly_records ORDER BY year_month DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ---- 预算细项 CRUD ----

def save_budget_items(year_month: str, items: list, db_path: str = DB_PATH):
    """保存预算细项（先删后插）"""
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budget_items WHERE year_month=?", (year_month,))
    for item in items:
        cursor.execute("""
            INSERT INTO budget_items (year_month, category, name, budget_amount, actual_amount, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (year_month, item['category'], item['name'],
              item.get('budget_amount', 0), item.get('actual_amount', 0),
              item.get('sort_order', 0)))
    conn.commit()
    conn.close()


def get_budget_items(year_month: str, db_path: str = DB_PATH) -> list:
    """查询某月的预算细项"""
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM budget_items
        WHERE year_month=?
        ORDER BY category, sort_order
    """, (year_month,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ---- 全局设置 ----

def get_setting(key: str, default: str = '', db_path: str = DB_PATH) -> str:
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key: str, value: str, db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    conn.commit()
    conn.close()
