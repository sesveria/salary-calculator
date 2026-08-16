"""核心计算单元测试"""
import datetime
import pytest
from core.salary_calc import (
    calc_daily_wage, calc_overtime, calc_gross,
    calc_overtime_from_base, calc_daily_mode_gross,
)
from core.tax import calc_insurance, calc_net, calc_all, calc_cumulative_tax
from core.budget import allocate, validate, get_scheme, distribute_to_items, DEFAULT_SUB_ITEMS, calc_remaining


class TestSalaryCalc:
    def test_daily_wage(self):
        assert calc_daily_wage(15000) == pytest.approx(689.655, rel=1e-3)
    
    def test_daily_wage_zero(self):
        assert calc_daily_wage(0) == 0
    
    def test_overtime_weekend(self):
        dw = calc_daily_wage(15000)
        ot = calc_overtime(dw, weekend_days=1)
        assert ot['weekend_amount'] == pytest.approx(dw * 2, rel=1e-2)
        assert ot['holiday_amount'] == 0
    
    def test_overtime_holiday(self):
        dw = calc_daily_wage(15000)
        ot = calc_overtime(dw, holiday_days=1)
        assert ot['holiday_amount'] == pytest.approx(dw * 3, rel=1e-2)
        assert ot['weekend_amount'] == 0
    
    def test_overtime_both(self):
        dw = calc_daily_wage(15000)
        ot = calc_overtime(dw, weekend_days=1, holiday_days=1)
        expected = dw * 2 + dw * 3
        assert ot['total'] == pytest.approx(expected, rel=1e-2)
    
    def test_gross(self):
        assert calc_gross(15000, 2000) == 17000.0
    
    def test_negative_error(self):
        import pytest
        with pytest.raises(ValueError):
            calc_daily_wage(-100)
        with pytest.raises(ValueError):
            calc_overtime(100, weekend_days=-1)


class TestTax:
    def test_insurance_default(self):
        ins = calc_insurance(15000, 15000)
        assert ins['pension'] == 1200.0
        assert ins['medical'] == 300.0
        assert ins['unemployment'] == 75.0
        assert ins['housing_fund'] == 1200.0
        assert ins['critical_illness'] == 10.0
        assert ins['total'] == 2785.0  # 2775 + 10（大病医保）
    
    def test_insurance_custom_rate(self):
        ins = calc_insurance(15000, 15000, housing_rate=0.12)
        assert ins['housing_fund'] == 1800.0
        assert ins['critical_illness'] == 10.0
        assert ins['total'] == 3385.0  # 3375 + 10（大病医保）
    
    def test_tax_below_threshold(self):
        # 累计应发 5000 - 5000×1 = 0 应纳税所得 → 税为 0
        assert calc_cumulative_tax(5000, 0, 1, 0, 0) == 0.0

    def test_cumulative_tax_bracket_1(self):
        # 第1月累计应发 8000，应税 = 8000-5000 = 3000 → 3% 档
        t = calc_cumulative_tax(8000, 0, 1, 0, 0)
        assert t == pytest.approx(3000 * 0.03, rel=1e-2)

    def test_cumulative_tax_bracket_2(self):
        # 第1月累计应发 155000，应税 = 150000 → 20% 档，速算扣除 16920
        t = calc_cumulative_tax(155000, 0, 1, 0, 0)
        assert t == pytest.approx(150000 * 0.20 - 16920, rel=1e-2)

    def test_cumulative_tax_subtracts_paid(self):
        # 第2月累计应发 11000，应税 = 11000-5000×1 = 6000 → 3% 档
        # 已缴 90 → 本月补扣 180-90 = 90
        t = calc_cumulative_tax(11000, 0, 1, 0, 90)
        assert t == pytest.approx(6000 * 0.03 - 90, rel=1e-2)

    def test_cumulative_tax_never_negative(self):
        # 已缴 > 累计应缴（年终汇算多缴）→ 返回 0，不退
        t = calc_cumulative_tax(3000, 0, 1, 0, 500)
        assert t == 0.0

    def test_net(self):
        net = calc_net(17000, 2775, 651)
        assert net == pytest.approx(13574, rel=1e-2)
    
    def test_calc_all_integration(self):
        result = calc_all(15000, 15000, 15000)
        assert result['basic_salary'] == 15000
        assert result['daily_wage'] > 0
        assert result['overtime']['total'] > 0
        assert result['gross_salary'] > 15000
        assert result['insurance']['total'] > 0
        assert result['net_salary'] > 0
        assert result['net_salary'] < result['gross_salary']


class TestBudget:
    def test_get_scheme(self):
        s = get_scheme('50/30/20')
        assert abs(s['necessary'] - 0.50) < 0.01
        assert abs(s['flexible'] - 0.30) < 0.01
        assert abs(s['savings'] - 0.20) < 0.01
    
    def test_allocate_502020(self):
        alloc = allocate(14000, '50/30/20')
        total = alloc['necessary'] + alloc['flexible'] + alloc['savings']
        assert abs(total - 14000) < 0.05
    
    def test_allocate_631(self):
        alloc = allocate(14000, '631')
        total = sum(alloc.values())
        assert abs(total - 14000) < 0.05
    
    def test_validate_ok(self):
        result = validate({'necessary': 7000, 'flexible': 4200, 'savings': 2800}, 14000)
        assert result['ok'] is True
    
    def test_validate_mismatch(self):
        result = validate({'necessary': 8000, 'flexible': 5000, 'savings': 2000}, 14000)
        assert result['ok'] is False


# ========== 新增功能测试 ==========


class TestOvertimeBase:
    def test_overtime_from_base(self):
        ot = calc_overtime_from_base(15000, weekend_days=1)
        daily = 15000 / 21.75
        assert ot['weekend_amount'] == pytest.approx(daily * 2, rel=0.02)

    def test_overtime_base_different(self):
        """加班基数不同于基本工资"""
        ot = calc_overtime_from_base(20000, weekend_days=1)
        daily = 20000 / 21.75
        assert ot['total'] == pytest.approx(daily * 2, rel=0.02)


class TestDailyMode:
    def test_daily_mode_gross(self):
        """首月按天计算"""
        result = calc_daily_mode_gross(15000, 10, 19)
        assert result['daily_wage'] == pytest.approx(15000 / 19, rel=0.01)
        assert result['work_salary'] == pytest.approx(result['daily_wage'] * 10, rel=0.01)

    def test_daily_mode_with_overtime(self):
        result = calc_daily_mode_gross(15000, 10, 19, overtime_total=2000)
        expected_work = (15000 / 19) * 10
        assert result['gross_salary'] == pytest.approx(expected_work + 2000, rel=0.01)

    def test_daily_mode_full_month(self):
        """全勤情况"""
        result = calc_daily_mode_gross(15000, 21, 21)
        assert result['gross_salary'] == pytest.approx(15000, rel=0.1)

    def test_daily_mode_invalid(self):
        import pytest
        with pytest.raises(ValueError):
            calc_daily_mode_gross(15000, 0, 0)


class TestCalcAllEnhanced:
    def test_calc_all_with_overtime_base(self):
        """calc_all 使用加班基数"""
        result = calc_all(
            15000, 15000, 15000,
            overtime_base=20000, weekend_days=1,
        )
        # 加班费应该基于 20000/21.75 而不是 15000/21.75
        expected_ot = (20000 / 21.75) * 2
        assert result['overtime']['total'] == pytest.approx(expected_ot, rel=0.02)

    def test_calc_all_daily_mode(self):
        """calc_all 按天模式"""
        result = calc_all(
            15000, 15000, 15000,
            weekend_days=0, holiday_days=0,
            daily_mode=True, actual_work_days=10, month_work_days=19,
            overtime_base=0,
        )
        daily = 15000 / 19
        expected_gross = daily * 10
        assert result['gross_salary'] == pytest.approx(expected_gross, rel=0.1)

    def test_calc_all_zero_overtime(self):
        """无加班"""
        result = calc_all(15000, 15000, 15000, weekend_days=0, holiday_days=0)
        assert result['overtime']['total'] == 0
        assert result['gross_salary'] == 15000


class TestBudgetItems:
    def test_distribute_equal_weights(self):
        items = [
            {'name': '房租', 'category': 'necessary', 'weight': 1},
            {'name': '餐饮', 'category': 'necessary', 'weight': 1},
        ]
        result = distribute_to_items(6000, items)
        assert len(result) == 2
        assert result[0]['amount'] == 3000.0
        assert result[1]['amount'] == 3000.0

    def test_distribute_weighted(self):
        items = [
            {'name': '房租', 'category': 'necessary', 'weight': 40},
            {'name': '餐饮', 'category': 'necessary', 'weight': 20},
        ]
        result = distribute_to_items(6000, items)
        assert result[0]['amount'] == pytest.approx(4000, rel=0.1)
        assert result[1]['amount'] == pytest.approx(2000, rel=0.1)

    def test_default_items_structure(self):
        assert len(DEFAULT_SUB_ITEMS) > 0
        for item in DEFAULT_SUB_ITEMS:
            assert 'name' in item
            assert 'category' in item
            assert 'weight' in item


class TestCalcRemaining:
    def test_exact_allocation(self):
        items = [
            {'category': 'necessary', 'name': '房租', 'amount': 7000},
            {'category': 'flexible', 'name': '社交', 'amount': 4200},
            {'category': 'savings', 'name': '定投', 'amount': 2800},
        ]
        result = calc_remaining(14000, {'necessary': 7000, 'flexible': 4200, 'savings': 2800}, items)
        assert result['total_remaining'] == 0.0
        assert result['all_ok'] is True

    def test_under_budget(self):
        items = [
            {'category': 'necessary', 'name': '房租', 'amount': 6500},
            {'category': 'flexible', 'name': '社交', 'amount': 4200},
            {'category': 'savings', 'name': '定投', 'amount': 2800},
        ]
        result = calc_remaining(14000, {'necessary': 7000, 'flexible': 4200, 'savings': 2800}, items)
        assert result['per_category']['necessary']['remaining'] == 500.0
        assert result['total_remaining'] == 500.0
        assert result['all_ok'] is True

    def test_over_budget(self):
        items = [
            {'category': 'necessary', 'name': '房租', 'amount': 7500},
            {'category': 'flexible', 'name': '社交', 'amount': 4200},
            {'category': 'savings', 'name': '定投', 'amount': 2800},
        ]
        result = calc_remaining(14000, {'necessary': 7000, 'flexible': 4200, 'savings': 2800}, items)
        assert result['per_category']['necessary']['remaining'] == -500.0
        assert result['total_remaining'] == -500.0
        assert result['all_ok'] is False

    def test_empty_items(self):
        result = calc_remaining(14000, {'necessary': 7000, 'flexible': 4200, 'savings': 2800}, [])
        assert result['total_allocated'] == 0
        assert result['total_remaining'] == 14000.0
        assert result['all_ok'] is True
