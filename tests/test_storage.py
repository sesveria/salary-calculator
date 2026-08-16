"""storage 层测试 — 结余链、删除重建、累计税、迁移幂等

使用 tmp_path 临时数据库，不触碰真实 salary.db。
"""
import os
import sys
import sqlite3

import pytest

# 确保项目根在 sys.path（pytest 从项目根运行时通常已就绪）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data import storage


def _make_db(tmp_path) -> str:
    """在临时目录创建并初始化数据库，返回路径"""
    db = str(tmp_path / "test.db")
    storage.init_db(db)
    return db


def _save(db, ym, net=10000, extra=0, nec=3000, flex=2000, sav=1000,
          gross=15000, tax=1000, insurance=3000, **kw):
    """便捷保存一条月度记录"""
    rec = {
        'year_month': ym,
        'basic_salary': gross,
        'gross_salary': gross,
        'tax_amount': tax,
        'insurance_total': insurance,
        'net_salary': net,
        'extra_income': extra,
        'actual_necessary': nec,
        'actual_flexible': flex,
        'actual_savings': sav,
        'opening_balance': 0,
        'closing_balance': 0,
        'total_available': 0,
        'total_expense': 0,
        'save_rate': 0,
    }
    rec.update(kw)
    return storage.save_monthly_record(rec, db)


class TestBalanceChain:
    """结余链：期初/期末余额自动串联"""

    def test_chain_basic(self, tmp_path):
        db = _make_db(tmp_path)
        storage.set_initial_balance(5000, db)

        _save(db, '2026-01', net=10000, nec=3000, flex=2000, sav=1000)
        _save(db, '2026-02', net=12000, nec=4000, flex=2000, sav=2000)

        storage.reconcile_balances(db)

        r1 = storage.get_monthly_record('2026-01', db)
        r2 = storage.get_monthly_record('2026-02', db)

        # 1月: 期初5000 + 10000 - 6000 = 9000
        assert r1['opening_balance'] == 5000
        assert r1['closing_balance'] == 9000
        # 2月: 期初9000 + 12000 - 8000 = 13000
        assert r2['opening_balance'] == 9000
        assert r2['closing_balance'] == 13000

    def test_chain_with_extra_income(self, tmp_path):
        db = _make_db(tmp_path)
        storage.set_initial_balance(0, db)

        # 额外收入税后直接计入可用资金
        _save(db, '2026-03', net=10000, extra=2000, nec=3000, flex=1000, sav=2000)

        storage.reconcile_balances(db)
        r = storage.get_monthly_record('2026-03', db)
        # total_available = 期初 + net + extra
        assert r['total_available'] == 12000
        # closing = 0 + 10000 + 2000 - 6000 = 6000
        assert r['closing_balance'] == 6000

    def test_delete_middle_month_reconcile(self, tmp_path):
        """删除中间月份后，后续月份余额必须重算（回归 Bug）"""
        db = _make_db(tmp_path)
        storage.set_initial_balance(1000, db)

        _save(db, '2026-01', net=10000, nec=3000, flex=2000, sav=1000)
        _save(db, '2026-02', net=12000, nec=4000, flex=2000, sav=2000)
        _save(db, '2026-03', net=11000, nec=3000, flex=1000, sav=2000)

        storage.reconcile_balances(db)
        before = storage.get_monthly_record('2026-03', db)['closing_balance']

        # 删除 2 月 → 必须重建结余链（GUI do_delete 里调用 reconcile_balances）
        storage.delete_record('2026-02', db)
        storage.reconcile_balances(db)

        r1 = storage.get_monthly_record('2026-01', db)
        r3 = storage.get_monthly_record('2026-03', db)

        # 1月不受影响: 1000+10000-6000=5000
        assert r1['closing_balance'] == 5000
        # 3月期初应为 1 月的期末 5000（而不是 2 月的旧值）
        assert r3['opening_balance'] == 5000
        # 3月期末 = 5000 + 11000 - 6000 = 10000
        assert r3['closing_balance'] == 10000
        assert r3['closing_balance'] != before  # 确实发生了变化

    def test_delete_record_removes_budget_items(self, tmp_path):
        db = _make_db(tmp_path)
        _save(db, '2026-05')
        storage.save_budget_items('2026-05', [
            {'category': 'necessary', 'name': '房租', 'budget_amount': 3000,
             'actual_amount': 3000, 'weight': 40, 'sort_order': 0},
        ], db)
        assert len(storage.get_budget_items('2026-05', db)) == 1

        storage.delete_record('2026-05', db)
        assert storage.get_monthly_record('2026-05', db) is None
        assert storage.get_budget_items('2026-05', db) == []


class TestCumulativeTaxInfo:
    """累计计税信息聚合"""

    def test_same_year_accumulates(self, tmp_path):
        db = _make_db(tmp_path)
        _save(db, '2026-01', gross=15000, tax=100, insurance=3000)
        _save(db, '2026-02', gross=15000, tax=200, insurance=3000)
        _save(db, '2026-03', gross=15000, tax=300, insurance=3000)

        cum = storage.get_cumulative_tax_info('2026-04', db)
        assert cum['months_count'] == 3
        assert cum['ytd_gross'] == 45000
        assert cum['ytd_insurance'] == 9000
        assert cum['ytd_tax'] == 600

    def test_excludes_future_and_other_year(self, tmp_path):
        db = _make_db(tmp_path)
        _save(db, '2025-12', gross=15000, tax=500, insurance=3000)
        _save(db, '2026-01', gross=15000, tax=100, insurance=3000)
        _save(db, '2026-02', gross=15000, tax=200, insurance=3000)
        # 04 月的记录不应算进查询 03 月的累计
        _save(db, '2026-04', gross=99999, tax=999, insurance=3000)

        cum = storage.get_cumulative_tax_info('2026-03', db)
        assert cum['months_count'] == 2  # 01, 02（2025-12 和 2026-04 都不算）
        assert cum['ytd_gross'] == 30000
        assert cum['ytd_tax'] == 300

    def test_empty_year(self, tmp_path):
        db = _make_db(tmp_path)
        cum = storage.get_cumulative_tax_info('2026-06', db)
        assert cum['months_count'] == 0
        assert cum['ytd_gross'] == 0
        assert cum['ytd_tax'] == 0


class TestMigration:
    """init_db 自动迁移幂等性"""

    def test_init_db_idempotent(self, tmp_path):
        db = _make_db(tmp_path)
        # 再次初始化不应报错，也不应重复添加列
        storage.init_db(db)
        storage.init_db(db)

        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(monthly_records)")
        cols = {r[1] for r in cur.fetchall()}
        conn.close()
        # 关键列存在
        for c in ['year_month', 'gross_salary', 'extra_income', 'pension_rate',
                  'medical_rate', 'unemployment_rate', 'insurance_critical_illness']:
            assert c in cols, f"缺列 {c}"

    def test_init_db_preserves_data(self, tmp_path):
        db = _make_db(tmp_path)
        _save(db, '2026-06', gross=20000, net=15000)
        # 重新 init 不丢数据
        storage.init_db(db)
        rec = storage.get_monthly_record('2026-06', db)
        assert rec is not None
        assert rec['gross_salary'] == 20000

    def test_save_load_roundtrip(self, tmp_path):
        db = _make_db(tmp_path)
        _save(db, '2026-07', gross=18000, net=13500, extra=500,
              nec=3000, flex=2000, sav=1500)
        rec = storage.get_monthly_record('2026-07', db)
        assert rec['gross_salary'] == 18000
        assert rec['net_salary'] == 13500
        assert rec['extra_income'] == 500
        assert rec['actual_necessary'] == 3000

    def test_settings_roundtrip(self, tmp_path):
        db = _make_db(tmp_path)
        storage.set_initial_balance(8888, db)
        assert storage.get_initial_balance(db) == 8888
        storage.set_setting('pay_day', '20', db)
        assert storage.get_setting('pay_day', '', db) == '20'
