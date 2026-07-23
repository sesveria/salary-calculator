"""五险一金 + 大病医疗 + 个税（累计预扣法）+ 一站式工资计算.

社保默认比例: 养老8%, 医疗2%, 失业0.5%, 工伤0%, 生育0%
公积金比例: 5%~12% 可配置
大病医疗保险: 固定金额（默认10元/月）
个税: 累计预扣法 (2019年起) — 年度累计应纳税所得额 × 税率 - 速算扣除数 - 已缴税款
"""

# ── 全年综合所得税率表（累计预扣法用）──
ANNUAL_TAX_BRACKETS = [
    (0, 36000, 0.03, 0),
    (36000, 144000, 0.10, 2520),
    (144000, 300000, 0.20, 16920),
    (300000, 420000, 0.25, 31920),
    (420000, 660000, 0.30, 52920),
    (660000, 960000, 0.35, 85920),
    (960000, float('inf'), 0.45, 181920),
]

DEFAULT_PENSION_RATE = 0.08
DEFAULT_MEDICAL_RATE = 0.02
DEFAULT_UNEMPLOYMENT_RATE = 0.005
DEFAULT_WORK_INJURY_RATE = 0.0
DEFAULT_MATERNITY_RATE = 0.0
DEFAULT_HOUSING_RATE = 0.08
DEFAULT_CRITICAL_ILLNESS = 10.0  # 大病医疗保险，每月固定金额
TAX_FREE_THRESHOLD = 5000


def calc_insurance(social_base: float, housing_base: float,
                   housing_rate: float = DEFAULT_HOUSING_RATE,
                   pension_rate: float = DEFAULT_PENSION_RATE,
                   medical_rate: float = DEFAULT_MEDICAL_RATE,
                   unemployment_rate: float = DEFAULT_UNEMPLOYMENT_RATE,
                   injury_rate: float = DEFAULT_WORK_INJURY_RATE,
                   maternity_rate: float = DEFAULT_MATERNITY_RATE,
                   critical_illness_amount: float = DEFAULT_CRITICAL_ILLNESS) -> dict:
    """计算五险一金 + 大病医疗保险 个人缴纳部分"""
    if any(x < 0 for x in [social_base, housing_base]):
        raise ValueError("基数为负数")

    pension = round(social_base * pension_rate, 2)
    medical = round(social_base * medical_rate, 2)
    unemployment = round(social_base * unemployment_rate, 2)
    injury = round(social_base * injury_rate, 2)
    maternity = round(social_base * maternity_rate, 2)
    housing = round(housing_base * housing_rate, 2)
    critical_illness = round(critical_illness_amount, 2)

    total = round(pension + medical + unemployment + injury + maternity + housing + critical_illness, 2)

    return {
        'pension': pension,
        'medical': medical,
        'unemployment': unemployment,
        'work_injury': injury,
        'maternity': maternity,
        'housing_fund': housing,
        'critical_illness': critical_illness,
        'total': total,
        'rates': {
            'pension': pension_rate,
            'medical': medical_rate,
            'unemployment': unemployment_rate,
            'housing': housing_rate,
        }
    }


def calc_tax_quick(taxable_income: float) -> float:
    """按月度预扣法计算个税（单月，旧算法，用于无累计数据时的退路）"""
    if taxable_income <= 0:
        return 0.0
    # 用月度级距（旧版保留作为 fallback）
    brackets = [
        (0, 3000, 0.03, 0),
        (3000, 12000, 0.10, 210),
        (12000, 25000, 0.20, 1410),
        (25000, 35000, 0.25, 2660),
        (35000, 55000, 0.30, 4410),
        (55000, 80000, 0.35, 7160),
        (80000, float('inf'), 0.45, 15160),
    ]
    for lower, upper, rate, deduction in brackets:
        if lower < taxable_income <= upper:
            return round(taxable_income * rate - deduction, 2)
    return 0.0


def calc_tax(gross_salary: float, insurance_total: float,
             tax_deductions: float = 0) -> float:
    """计算个税（单月，旧算法，无累计数据时的退路）
    应纳税所得额 = 应发工资 - 五险一金 - 大病医疗 - 5000 - 专项附加扣除
    """
    taxable = gross_salary - insurance_total - TAX_FREE_THRESHOLD - tax_deductions
    return calc_tax_quick(taxable)


def calc_cumulative_tax(ytd_gross: float, ytd_insurance: float,
                        months_worked: int, ytd_deductions: float = 0,
                        tax_paid_ytd: float = 0) -> float:
    """累计预扣法计算当月个税

    公式:
      累计应纳税所得额 = 累计收入 - 累计五险一金 - 5000×月份数 - 累计专项扣除
      累计应纳税额     = 累计应纳税所得额 × 税率 - 速算扣除数
      当月应预扣税款   = 累计应纳税额 - 本年已预扣税款

    Args:
        ytd_gross: 本年累计至当月的应发工资
        ytd_insurance: 本年累计至当月的五险一金+大病医疗
        months_worked: 本年工作月数（含当月）
        ytd_deductions: 本年累计专项附加扣除
        tax_paid_ytd: 本年已预扣税款（前N-1个月）

    Returns:
        当月应预扣税款
    """
    cumulative_taxable = ytd_gross - ytd_insurance - TAX_FREE_THRESHOLD * months_worked - ytd_deductions
    if cumulative_taxable <= 0:
        return 0.0

    cumulative_tax = 0.0
    for lower, upper, rate, quick_deduction in ANNUAL_TAX_BRACKETS:
        if lower < cumulative_taxable <= upper:
            cumulative_tax = round(cumulative_taxable * rate - quick_deduction, 2)
            break

    current_month_tax = round(cumulative_tax - tax_paid_ytd, 2)
    return max(current_month_tax, 0.0)


def calc_net(gross_salary: float, insurance_total: float,
             tax: float) -> float:
    """实发工资 = 应发工资 - 五险一金 - 大病医疗 - 个税"""
    return round(gross_salary - insurance_total - tax, 2)


def calc_all(basic_salary: float, social_base: float,
             housing_base: float, housing_rate: float = DEFAULT_HOUSING_RATE,
             weekend_days: float = 1, holiday_days: float = 0,
             tax_deductions: float = 0,
             overtime_base: float = 0,
             daily_mode: bool = False,
             actual_work_days: float = 0,
             month_work_days: float = 0,
             critical_illness_amount: float = DEFAULT_CRITICAL_ILLNESS,
             cum_ytd_gross: float = 0,
             cum_ytd_insurance: float = 0,
             cum_months: int = 0,
             cum_ytd_deductions: float = 0,
             cum_tax_paid: float = 0) -> dict:
    """一站式工资计算（支持累计预扣法 + 大病医疗 + 额外收入）

    累计计税逻辑:
      - 始终使用累计预扣法，cum_months=0 即为新年首月

    参数:
        cum_ytd_gross: 本年累计至前月的应发工资
        cum_ytd_insurance: 本年累计至前月的五险一金+大病医疗
        cum_months: 本年已有记录月数（前N-1个月计数）
        cum_ytd_deductions: 本年累计至前月的专项附加扣除
        cum_tax_paid: 本年已预扣税款（前N-1个月总和）
    """
    from .salary_calc import calc_overtime_from_base, calc_overtime_from_salary, calc_daily_mode_gross, calc_gross as _calc_gross

    # 1. 加班费（独立基数）
    if overtime_base and overtime_base > 0:
        overtime = calc_overtime_from_base(overtime_base, weekend_days, holiday_days)
    else:
        overtime = calc_overtime_from_salary(basic_salary, weekend_days, holiday_days)

    # 2. 应发工资（含额外收入）
    if daily_mode and month_work_days > 0:
        dm = calc_daily_mode_gross(basic_salary, actual_work_days, month_work_days, overtime['total'])
        gross = dm['gross_salary']
        daily_wage = dm['daily_wage']
    else:
        gross = _calc_gross(basic_salary, overtime['total'])
        daily_wage = round(basic_salary / 21.75, 2)
    # gross = round(gross + extra_income, 2)

    # 3. 五险一金 + 大病医疗
    insurance = calc_insurance(social_base, housing_base, housing_rate,
                               critical_illness_amount=critical_illness_amount)

    # 4. 个税（累计预扣法）
    # 始终使用累计预扣法，即使 cum_months=0（新年首月）
    ytd_gross = cum_ytd_gross + gross
    ytd_insurance = cum_ytd_insurance + insurance['total']
    ytd_deductions = cum_ytd_deductions + tax_deductions
    months = cum_months + 1
    tax = calc_cumulative_tax(ytd_gross, ytd_insurance, months, ytd_deductions, cum_tax_paid)

    # 5. 实发
    net = calc_net(gross, insurance['total'], tax)

    return {
        'basic_salary': basic_salary,
        'daily_wage': daily_wage,
        'overtime': overtime,
        'gross_salary': gross,
        'insurance': insurance,
        'tax': tax,
        'net_salary': net,
        'daily_mode': daily_mode,
    }
