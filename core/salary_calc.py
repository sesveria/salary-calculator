"""Salary calculation with overtime (weekend 2x, holiday 3x).

Spec: 日工资 = 基本工资 / 21.75
"""

DAYS_PER_MONTH = 21.75


def calc_daily_wage(basic_salary: float) -> float:
    """日工资 = 基本工资 / 21.75"""
    if basic_salary < 0:
        raise ValueError("基本工资不能为负数")
    return basic_salary / DAYS_PER_MONTH


def calc_overtime(daily_wage: float, weekend_days: float = 0,
                  holiday_days: float = 0) -> dict:
    """计算加班费
    
    周末加班: 日工资 × 2 × 天数
    节假日加班: 日工资 × 3 × 天数
    
    Returns:
        dict with weekend_amount, holiday_amount, total
    """
    if daily_wage < 0:
        raise ValueError("日工资不能为负数")
    if weekend_days < 0 or holiday_days < 0:
        raise ValueError("加班天数不能为负数")
    
    weekend_amount = round(daily_wage * 2 * weekend_days, 2)
    holiday_amount = round(daily_wage * 3 * holiday_days, 2)
    
    return {
        'weekend_amount': weekend_amount,
        'holiday_amount': holiday_amount,
        'total': round(weekend_amount + holiday_amount, 2),
    }


def calc_gross(basic_salary: float, overtime_total: float) -> float:
    """应发工资 = 基本工资 + 加班费"""
    return round(basic_salary + overtime_total, 2)
