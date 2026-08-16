"""年度汇总聚合逻辑测试"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gui.summary_tab import _aggregate_year
from data import storage


@pytest.fixture
def db(tmp_path, monkeypatch):
    """在临时 DB 中插入测试数据，并 monkeypatch summary_tab 的 DB 访问"""
    db = str(tmp_path / "test.db")
    storage.init_db(db)
    # summary_tab.list_records_asc 是直接 import 的函数，
    # 默认参数 db_path=DB_PATH 在定义时绑定，monkeypatch storage.DB_PATH 无效。
    # 改为 patch summary_tab 模块内的引用，强制使用测试 DB。
    import gui.summary_tab as st
    monkeypatch.setattr(st, "list_records_asc", lambda: storage.list_records_asc(db))
    return db


def _save(db, ym, gross=15000, net=10000, extra=0, tax=1000, insurance=3000,
          nec=3000, flex=2000, sav=1000, closing=None):
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
        'closing_balance': closing if closing is not None else net + extra - nec - flex - sav,
        'total_available': net + extra,
        'total_expense': nec + flex + sav,
        'save_rate': 0,
    }
    storage.save_monthly_record(rec, db)


class TestAggregateYear:
    def test_single_year(self, db):
        _save(db, '2026-01', gross=15000, net=11000, extra=500, tax=800, insurance=3200,
              nec=3000, flex=2000, sav=1500, closing=6500)
        _save(db, '2026-02', gross=15000, net=11200, extra=0, tax=850, insurance=3200,
              nec=3000, flex=2000, sav=2000, closing=8700)

        agg = _aggregate_year('2026')
        assert agg['months'] == 2
        assert agg['gross'] == 30000
        assert agg['insurance'] == 6400
        assert agg['tax'] == 1650
        assert agg['net'] == 22200
        assert agg['extra'] == 500
        assert agg['expense'] == 13500  # 6500(1月) + 7000(2月)
        assert agg['savings'] == 3500
        assert agg['closing'] == 8700  # 最后一条
        # 储蓄率 = 3500 / (22200+500)
        assert agg['save_rate'] == pytest.approx(3500 / 22700 * 100, rel=1e-2)

    def test_excludes_other_years(self, db):
        _save(db, '2025-12', gross=15000, net=10000, nec=3000, flex=2000, sav=1000)
        _save(db, '2026-01', gross=15000, net=10000, nec=3000, flex=2000, sav=1000)
        _save(db, '2027-01', gross=99999, net=88888, nec=3000, flex=2000, sav=1000)

        agg = _aggregate_year('2026')
        assert agg['months'] == 1
        assert agg['gross'] == 15000
        assert agg['net'] == 10000

    def test_empty_year(self, db):
        agg = _aggregate_year('2030')
        assert agg['months'] == 0
        assert agg['gross'] == 0
        assert agg['save_rate'] == 0
        assert agg['monthly'] == []

    def test_zero_income_save_rate(self, db):
        _save(db, '2026-05', gross=0, net=0, extra=0, nec=0, flex=0, sav=0)
        agg = _aggregate_year('2026')
        assert agg['save_rate'] == 0  # 不除零崩溃

    def test_extra_income_included(self, db):
        _save(db, '2026-06', gross=15000, net=10000, extra=3000,
              nec=3000, flex=2000, sav=2000, closing=6000)
        agg = _aggregate_year('2026')
        assert agg['extra'] == 3000
        # 储蓄率分母含额外收入
        assert agg['save_rate'] == pytest.approx(2000 / 13000 * 100, rel=1e-2)
