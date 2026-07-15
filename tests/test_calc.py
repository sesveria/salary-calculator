"""核心计算单元测试"""
import pytest
from core.salary_calc import calc_daily_wage, calc_overtime, calc_gross
from core.tax import calc_insurance, calc_tax, calc_tax_quick, calc_net, calc_all
from core.budget import allocate, validate, get_scheme


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
        assert ins['total'] == 2775.0
    
    def test_insurance_custom_rate(self):
        ins = calc_insurance(15000, 15000, housing_rate=0.12)
        assert ins['housing_fund'] == 1800.0
        assert ins['total'] == 3375.0
    
    def test_tax_below_threshold(self):
        assert calc_tax(5000, 0, 0) == 0.0
    
    def test_tax_bracket_1(self):
        # 应纳税所得额 = 8000 - 0 - 5000 - 0 = 3000
        t = calc_tax(8000, 0, 0)
        assert t == pytest.approx(3000 * 0.03, rel=1e-2)
    
    def test_tax_bracket_2(self):
        # 应纳税所得额 = 15000
        t = calc_tax_quick(15000)
        assert t == pytest.approx(15000 * 0.2 - 1410, rel=1e-2)  # = 1590
    
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
