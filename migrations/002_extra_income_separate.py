"""
Migration 002: 月额外收入改为税后，不参与工资计算
=================================================

改动说明:
  新版 extra_income 不再计入应发工资/个税，直接作为税后收入供预算分配。
  旧记录中 extra_income>0 的条目，其 gross_salary/tax/net_salary 含了
  这部分收入，需要重新计算。

操作:
  1. 按时间顺序遍历记录
  2. 对 extra_income > 0 的记录重新计税（累计预扣法）
  3. 更新 gross_salary / tax_amount / net_salary
  4. 全部处理完调用 reconcile_balances() 重算余额链

幂等: 可重复运行，已处理的记录不再变动。
"""

import sqlite3
import os
import sys

# ── 项目根路径 ────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'salary.db')
sys.path.insert(0, PROJECT_ROOT)


def log(msg: str):
    print(f"[migrate-002] {msg}")


def migrate():
    if not os.path.exists(DB_PATH):
        log(f"数据库不存在 ({DB_PATH})，跳过")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 确保列存在
    cursor.execute("PRAGMA table_info(monthly_records)")
    existing = {r['name'] for r in cursor.fetchall()}
    if 'extra_income' not in existing:
        cursor.execute("ALTER TABLE monthly_records ADD COLUMN extra_income REAL DEFAULT 0")
        log("extra_income 列已添加")
    else:
        log("extra_income 列已存在")

    # 2. 查出所有有额外收入的记录
    cursor.execute("""
        SELECT * FROM monthly_records
        WHERE extra_income IS NOT NULL AND extra_income > 0
        ORDER BY year_month ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        log("没有需要迁移的记录（extra_income > 0 的记录数为 0）")
        conn.close()
        return

    log(f"找到 {len(rows)} 条需要迁移的记录")

    # 3. 逐条重算
    from core.tax import calc_all

    for rec in rows:
        ym = rec['year_month']
        extra = rec.get('extra_income', 0) or 0

        # 累计计税：查询本年已有记录（不含当前月）
        from data.storage import get_cumulative_tax_info
        cum = get_cumulative_tax_info(ym, DB_PATH)

        result = calc_all(
            basic_salary=rec.get('basic_salary', 0),
            social_base=rec.get('social_insurance_base', 0),
            housing_base=rec.get('housing_fund_base', 0),
            housing_rate=float(rec.get('housing_fund_rate', 0.08) or 0.08),
            weekend_days=rec.get('weekend_overtime_days', 0),
            holiday_days=rec.get('holiday_overtime_days', 0),
            tax_deductions=rec.get('tax_deductions', 0),
            overtime_base=rec.get('overtime_base', 0) or rec.get('basic_salary', 0),
            daily_mode=bool(rec.get('daily_mode', 0)),
            actual_work_days=rec.get('actual_work_days', 0),
            month_work_days=rec.get('month_work_days', 0),
            critical_illness_amount=rec.get('insurance_critical_illness', 10),
            cum_ytd_gross=cum['ytd_gross'],
            cum_ytd_insurance=cum['ytd_insurance'],
            cum_months=cum['months_count'],
            cum_ytd_deductions=cum['ytd_deductions'],
            cum_tax_paid=cum['ytd_tax'],
        )

        old_gross = rec.get('gross_salary', 0)
        old_tax = rec.get('tax_amount', 0)
        old_net = rec.get('net_salary', 0)
        new_gross = result['gross_salary']
        new_tax = result['tax']
        new_net = result['net_salary']
        new_ins_total = result['insurance']['total']

        # 更新记录
        ot = result['overtime']
        ins = result['insurance']
        cursor.execute("""
            UPDATE monthly_records SET
                gross_salary = ?,
                daily_wage = ?,
                overtime_weekend = ?,
                overtime_holiday = ?,
                overtime_total = ?,
                insurance_pension = ?,
                insurance_medical = ?,
                insurance_unemployment = ?,
                insurance_housing_fund = ?,
                insurance_total = ?,
                tax_amount = ?,
                net_salary = ?
            WHERE year_month = ?
        """, (
            new_gross, result['daily_wage'],
            ot['weekend_amount'], ot['holiday_amount'], ot['total'],
            ins['pension'], ins['medical'], ins['unemployment'],
            ins['housing_fund'], new_ins_total,
            new_tax, new_net,
            ym,
        ))

        log(
            f"  {ym}: extra={extra:.0f} | "
            f"gross {old_gross:>8.0f}→{new_gross:>8.0f} | "
            f"tax {old_tax:>6.0f}→{new_tax:>6.0f} | "
            f"net {old_net:>8.0f}→{new_net:>8.0f}"
        )

    conn.commit()
    conn.close()

    # 4. 重算余额链
    from data.storage import reconcile_balances
    reconcile_balances(DB_PATH)
    log("余额链已重算")
    log("迁移完成 ✅")


if __name__ == '__main__':
    migrate()
