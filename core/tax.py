"""五险一金 + 个税计算.

社保默认比例: 养老8%, 医疗2%, 失业0.5%, 工伤0%, 生育0%
公积金比例: 5%~12% 可配置
个税: 月度预扣法 (5000起征点 + 专项附加扣除)
"""

TAX_BRACKETS = [
    (0, 3000, 0.03, 0),
    (3000, 12000, 0.10, 210),
    (12000, 25000, 0.20, 1410),
    (25000, 35000, 0.25, 2660),
    (35000, 55000, 0.30, 4410),
    (55000, 80000, 0.35, 7160),
    (80000, float('inf'), 0.45, 15160),
]

DEFAULT_PENSION_RATE = 0.08
DEFAULT_MEDICAL_RATE = 0.02
DEFAULT_UNEMPLOYMENT_RATE = 0.005
DEFAULT_WORK_INJURY_RATE = 0.0
DEFAULT_MATERNITY_RATE = 0.0
DEFAULT_HOUSING_RATE = 0.08
TAX_FREE_THRESHOLD = 5000


def calc_insurance(social_base: float, housing_base: float,
                   housing_rate: float = DEFAULT_HOUSING_RATE,
                   pension_rate: float = DEFAULT_PENSION_RATE,
                   medical_rate: float = DEFAULT_MEDICAL_RATE,
                   unemployment_rate: float = DEFAULT_UNEMPLOYMENT_RATE,
                   injury_rate: float = DEFAULT_WORK_INJURY_RATE,
                   maternity_rate: float = DEFAULT_MATERNITY_RATE) -> dict:
    """计算五险一金个人缴纳部分"""
    if any(x < 0 for x in [social_base, housing_base]):
        raise ValueError("基数为负数")
    
    pension = round(social_base * pension_rate, 2)
    medical = round(social_base * medical_rate, 2)
    unemployment = round(social_base * unemployment_rate, 2)
    injury = round(social_base * injury_rate, 2)
    maternity = round(social_base * maternity_rate, 2)
    housing = round(housing_base * housing_rate, 2)
    
    total = round(pension + medical + unemployment + injury + maternity + housing, 2)
    
    return {
        'pension': pension,
        'medical': medical,
        'unemployment': unemployment,
        'work_injury': injury,
        'maternity': maternity,
        'housing_fund': housing,
        'total': total,
        'rates': {
            'pension': pension_rate,
            'medical': medical_rate,
            'unemployment': unemployment_rate,
            'housing': housing_rate,
        }
    }


def calc_tax_quick(taxable_income: float) -> float:
    """按月度预扣法计算个税"""
    if taxable_income <= 0:
        return 0.0
    for lower, upper, rate, deduction in TAX_BRACKETS:
        if lower < taxable_income <= upper:
            return round(taxable_income * rate - deduction, 2)
    return 0.0


def calc_tax(gross_salary: float, insurance_total: float,
             tax_deductions: float = 0) -> float:
    """计算个税
    
    应纳税所得额 = 应发工资 - 五险一金 - 5000 - 专项附加扣除
    """
    taxable = gross_salary - insurance_total - TAX_FREE_THRESHOLD - tax_deductions
    return calc_tax_quick(taxable)


def calc_net(gross_salary: float, insurance_total: float,
             tax: float) -> float:
    """实发工资 = 应发工资 - 五险一金 - 个税"""
    return round(gross_salary - insurance_total - tax, 2)


def calc_all(basic_salary: float, social_base: float,
             housing_base: float, housing_rate: float = DEFAULT_HOUSING_RATE,
             weekend_days: float = 1, holiday_days: float = 0,
             tax_deductions: float = 0) -> dict:
    """一站式工资计算"""
    from .salary_calc import calc_daily_wage, calc_overtime, calc_gross
    
    daily = calc_daily_wage(basic_salary)
    overtime = calc_overtime(daily, weekend_days, holiday_days)
    gross = calc_gross(basic_salary, overtime['total'])
    insurance = calc_insurance(social_base, housing_base, housing_rate)
    tax = calc_tax(gross, insurance['total'], tax_deductions)
    net = calc_net(gross, insurance['total'], tax)
    
    return {
        'basic_salary': basic_salary,
        'daily_wage': round(daily, 2),
        'overtime': overtime,
        'gross_salary': gross,
        'insurance': insurance,
        'tax': tax,
        'net_salary': net,
    }
