"""SQLite 本地存储层 — 全量快照模式

每月记录存储所有输入参数 + 基准值 + 计算结果，
读取时直接查询，不做重复计算。
"""

import sqlite3
import os
from typing import Optional

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(DB_DIR), 'salary.db')

# ── 新增字段清单（用于自动迁移） ──────────────────────────

NEW_COLUMNS = {
    # 基准值（不再硬编码）
    'pension_rate': 'REAL DEFAULT 0.08',
    'medical_rate': 'REAL DEFAULT 0.02',
    'unemployment_rate': 'REAL DEFAULT 0.005',
    'tax_free_threshold': 'REAL DEFAULT 5000',
    # 计算结果（保存时算好，读取不重算）
    'gross_salary': 'REAL DEFAULT 0',
    'daily_wage': 'REAL DEFAULT 0',
    'overtime_weekend': 'REAL DEFAULT 0',
    'overtime_holiday': 'REAL DEFAULT 0',
    'overtime_total': 'REAL DEFAULT 0',
    'insurance_pension': 'REAL DEFAULT 0',
    'insurance_medical': 'REAL DEFAULT 0',
    'insurance_unemployment': 'REAL DEFAULT 0',
    'insurance_housing_fund': 'REAL DEFAULT 0',
    'insurance_critical_illness': 'REAL DEFAULT 10',
    'extra_income': 'REAL DEFAULT 0',
    'insurance_total': 'REAL DEFAULT 0',
    'tax_amount': 'REAL DEFAULT 0',
    'total_available': 'REAL DEFAULT 0',
    'total_expense': 'REAL DEFAULT 0',
    'save_rate': 'REAL DEFAULT 0',
    'scheme_name': "TEXT DEFAULT ''",
}


def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = DB_PATH):
    """初始化/迁移数据库"""
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

            -- 基础输入
            basic_salary REAL DEFAULT 0,
            overtime_base REAL DEFAULT 0,
            weekend_overtime_days REAL DEFAULT 1,
            holiday_overtime_days REAL DEFAULT 0,
            social_insurance_base REAL DEFAULT 0,
            housing_fund_base REAL DEFAULT 0,
            housing_fund_rate REAL DEFAULT 0.08,
            tax_deductions REAL DEFAULT 0,
            pay_day INTEGER DEFAULT 15,

            -- 模式信息
            daily_mode INTEGER DEFAULT 0,
            entry_date TEXT DEFAULT '',
            actual_work_days REAL DEFAULT 0,
            month_work_days REAL DEFAULT 0,
            work_year_month TEXT DEFAULT '',

            -- 预算/实际
            actual_necessary REAL DEFAULT 0,
            actual_flexible REAL DEFAULT 0,
            actual_savings REAL DEFAULT 0,
            budget_necessary REAL DEFAULT 0,
            budget_flexible REAL DEFAULT 0,
            budget_savings REAL DEFAULT 0,
            notes TEXT DEFAULT '',

            -- 结余
            net_salary REAL DEFAULT 0,
            opening_balance REAL DEFAULT 0,
            closing_balance REAL DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS budget_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year_month TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            budget_amount REAL DEFAULT 0,
            actual_amount REAL DEFAULT 0,
            weight REAL DEFAULT 10,
            sort_order INTEGER DEFAULT 0
        );
    """)

    # 自动添加新字段
    _add_new_columns(cursor)
    # 补全旧记录的计算字段
    _backfill_computed_fields(cursor, conn)

    conn.commit()
    conn.close()


def _add_new_columns(cursor: sqlite3.Cursor):
    """增量添加新字段（幂等）"""
    cursor.execute("PRAGMA table_info(monthly_records)")
    existing = {row['name'] for row in cursor.fetchall()}

    for col, dtype in NEW_COLUMNS.items():
        if col not in existing:
            cursor.execute(f"ALTER TABLE monthly_records ADD COLUMN {col} {dtype}")


def _backfill_computed_fields(cursor: sqlite3.Cursor, conn: sqlite3.Connection):
    """为旧记录补全计算字段和基准值"""
    cursor.execute("SELECT * FROM monthly_records WHERE gross_salary IS NULL OR gross_salary = 0")
    old_records = [dict(r) for r in cursor.fetchall()]
    if not old_records:
        return

    from core.tax import calc_all

    for rec in old_records:
        ym = rec['year_month']
        try:
            result = calc_all(
                basic_salary=rec.get('basic_salary', 0),
                social_base=rec.get('social_insurance_base', 0),
                housing_base=rec.get('housing_fund_base', 0),
                housing_rate=float(rec.get('housing_fund_rate', 0.08) or 0.08),
                weekend_days=rec.get('weekend_overtime_days', 0),
                holiday_days=rec.get('holiday_overtime_days', 0),
                tax_deductions=rec.get('tax_deductions', 0),
                overtime_base=rec.get('overtime_base', 0),
                daily_mode=bool(rec.get('daily_mode', 0)),
                actual_work_days=rec.get('actual_work_days', 0),
                month_work_days=rec.get('month_work_days', 0),
            )
        except Exception:
            continue

        ot = result['overtime']
        ins = result['insurance']
        net = result['net_salary']
        nec = rec.get('actual_necessary', 0) or 0
        flex = rec.get('actual_flexible', 0) or 0
        sav = rec.get('actual_savings', 0) or 0
        opening = rec.get('opening_balance', 0) or 0
        total_expense = nec + flex + sav
        total_available = round(opening + net, 2)
        save_rate = round(sav / net * 100, 2) if net > 0 else 0

        cursor.execute("""
            UPDATE monthly_records SET
                pension_rate=0.08, medical_rate=0.02, unemployment_rate=0.005,
                tax_free_threshold=5000,
                gross_salary=?, daily_wage=?,
                overtime_weekend=?, overtime_holiday=?, overtime_total=?,
                insurance_pension=?, insurance_medical=?, insurance_unemployment=?,
                insurance_housing_fund=?, insurance_total=?,
                tax_amount=?, net_salary=?,
                total_available=?, total_expense=?, save_rate=?
            WHERE year_month=?
        """, (
            result['gross_salary'], result['daily_wage'],
            ot['weekend_amount'], ot['holiday_amount'], ot['total'],
            ins['pension'], ins['medical'], ins['unemployment'],
            ins['housing_fund'], ins['total'],
            result['tax'], net,
            total_available, total_expense, save_rate,
            ym,
        ))


# ── CRUD 月度记录 ──────────────────────────────────────


ALL_FIELDS = [
    'year_month', 'basic_salary', 'overtime_base',
    'weekend_overtime_days', 'holiday_overtime_days',
    'social_insurance_base', 'housing_fund_base', 'housing_fund_rate',
    'tax_deductions', 'daily_mode', 'entry_date',
    'actual_work_days', 'month_work_days', 'pay_day', 'work_year_month',
    'actual_necessary', 'actual_flexible', 'actual_savings',
    'budget_necessary', 'budget_flexible', 'budget_savings',
    'notes', 'net_salary', 'opening_balance', 'closing_balance',
    # 新增
    'pension_rate', 'medical_rate', 'unemployment_rate', 'tax_free_threshold',
    'gross_salary', 'daily_wage',
    'overtime_weekend', 'overtime_holiday', 'overtime_total',
    'insurance_pension', 'insurance_medical', 'insurance_unemployment',
    'insurance_housing_fund', 'insurance_critical_illness', 'extra_income', 'insurance_total', 'tax_amount',
    'total_available', 'total_expense', 'save_rate',
    'scheme_name',
]

INSERT_SQL = f"""
    INSERT INTO monthly_records ({', '.join(ALL_FIELDS)})
    VALUES ({', '.join(':' + f for f in ALL_FIELDS)})
    ON CONFLICT(year_month) DO UPDATE SET
        {', '.join(f'{f}=excluded.{f}' for f in ALL_FIELDS if f != 'year_month')}
"""


def save_monthly_record(record: dict, db_path: str = DB_PATH) -> int:
    """保存或更新月度记录（全量写入）"""
    conn = get_conn(db_path)
    cursor = conn.cursor()

    # 确保所有字段都存在
    clean = {}
    for f in ALL_FIELDS:
        clean[f] = record.get(f, 0)

    cursor.execute(INSERT_SQL, clean)
    conn.commit()
    rid: int = cursor.lastrowid or 0
    conn.close()
    return rid


def get_monthly_record(year_month: str, db_path: str = DB_PATH) -> Optional[dict]:
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monthly_records WHERE year_month=?", (year_month,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def list_records(db_path: str = DB_PATH) -> list:
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monthly_records ORDER BY year_month DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def list_records_asc(db_path: str = DB_PATH) -> list:
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monthly_records ORDER BY year_month ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ── 结余计算 ──────────────────────────────────────────


def get_initial_balance(db_path: str = DB_PATH) -> float:
    return float(get_setting('initial_balance', '0', db_path))


def set_initial_balance(value: float, db_path: str = DB_PATH):
    set_setting('initial_balance', str(value), db_path)


def reconcile_balances(db_path: str = DB_PATH):
    """从头梳理结余链"""
    records = list_records_asc(db_path)
    if not records:
        return
    prev_closing = get_initial_balance(db_path)
    for rec in records:
        ym = rec['year_month']
        net = rec.get('net_salary', 0) or 0
        extra = rec.get('extra_income', 0) or 0
        nec = rec.get('actual_necessary', 0) or 0
        flex = rec.get('actual_flexible', 0) or 0
        sav = rec.get('actual_savings', 0) or 0
        actual_total = nec + flex + sav
        rec['opening_balance'] = prev_closing
        rec['closing_balance'] = round(prev_closing + net + extra - actual_total, 2)
        rec['total_available'] = round(prev_closing + net + extra, 2)
        rec['total_expense'] = actual_total
        rec['save_rate'] = round(sav / net * 100, 2) if net > 0 else 0
        save_monthly_record(dict(rec), db_path)
        prev_closing = rec['closing_balance']


def get_opening_balance(year_month: str, db_path: str = DB_PATH) -> float:
    rec = get_monthly_record(year_month, db_path)
    if rec:
        return rec.get('opening_balance', 0) or 0
    records = list_records(db_path)
    for r in records:
        if r['year_month'] < year_month:
            return r.get('closing_balance', 0) or 0
    return get_initial_balance(db_path)


def get_cumulative_tax_info(year_month: str, db_path: str = DB_PATH) -> dict:
    """获取截至前一个月的年度累计计税信息

    用于累计预扣法:
      - cum_ytd_gross: 本年累计至前月的应发工资
      - cum_ytd_insurance: 本年累计至前月的五险一金+大病医疗
      - cum_months: 本年已有记录月数（不含当月）
      - cum_ytd_deductions: 本年累计至前月的专项附加扣除
      - cum_tax_paid: 本年已预扣税款

    Returns:
        dict with keys: ytd_gross, ytd_insurance, months_count,
                        ytd_deductions, ytd_tax
    """
    year = year_month[:4]
    all_recs = list_records_asc(db_path)
    ytd_gross = 0.0
    ytd_insurance = 0.0
    ytd_deductions = 0.0
    ytd_tax = 0.0
    months_count = 0

    for rec in all_recs:
        ym = rec['year_month']
        if ym.startswith(year) and ym < year_month:
            ytd_gross += rec.get('gross_salary', 0) or 0
            ytd_insurance += rec.get('insurance_total', 0) or 0
            ytd_deductions += rec.get('tax_deductions', 0) or 0
            ytd_tax += rec.get('tax_amount', 0) or 0
            months_count += 1

    return {
        'ytd_gross': round(ytd_gross, 2),
        'ytd_insurance': round(ytd_insurance, 2),
        'months_count': months_count,
        'ytd_deductions': round(ytd_deductions, 2),
        'ytd_tax': round(ytd_tax, 2),
    }


# ── 预算细项 ──────────────────────────────────────────


def delete_record(year_month: str, db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budget_items WHERE year_month=?", (year_month,))
    cursor.execute("DELETE FROM monthly_records WHERE year_month=?", (year_month,))
    conn.commit()
    conn.close()


def save_budget_items(year_month: str, items: list, db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budget_items WHERE year_month=?", (year_month,))
    for item in items:
        cursor.execute("""
            INSERT INTO budget_items (year_month, category, name, budget_amount, actual_amount, weight, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            year_month,
            item['category'], item['name'],
            item.get('budget_amount', 0), item.get('actual_amount', 0),
            item.get('weight', 10), item.get('sort_order', 0),
        ))
    conn.commit()
    conn.close()


def get_budget_items(year_month: str, db_path: str = DB_PATH) -> list:
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


# ── 全局设置 ──────────────────────────────────────────


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
