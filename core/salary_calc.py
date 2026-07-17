"""Salary calculation with overtime and daily-mode support.

加班规则:
  - 周末加班: 日工资 × 2 × 天数
  - 节假日加班: 日工资 × 3 × 天数

按天工资（首月/离职）:
  - 日工资 = 基本工资 / 当月实际工作日数
  - 应发 = 日工资 × 实际出勤天数 + 加班费

加班费:
  - 加班日工资 = 加班基数 / 21.75（固定）
  - 不受按天模式影响
"""

DAYS_PER_MONTH = 21.75


def calc_daily_wage(basic_salary: float) -> float:
    """日工资 = 基本工资 / 21.75（标准算法）"""
    if basic_salary < 0:
        raise ValueError("基本工资不能为负数")
    return round(basic_salary / DAYS_PER_MONTH, 2)


def calc_overtime(daily_wage: float, weekend_days: float = 0,
                  holiday_days: float = 0) -> dict:
    """计算加班费（使用给定的日工资基数）
    
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


def calc_overtime_from_base(overtime_base: float, weekend_days: float = 0,
                            holiday_days: float = 0) -> dict:
    """计算加班费（使用加班基数）
    
    加班日工资 = 加班基数 / 21.75（固定使用21.75）
    """
    daily = overtime_base / DAYS_PER_MONTH
    return calc_overtime(daily, weekend_days, holiday_days)


def calc_overtime_from_salary(basic_salary: float, weekend_days: float = 0,
                              holiday_days: float = 0) -> dict:
    """计算加班费（使用基本工资为基数，旧接口兼容）"""
    daily = calc_daily_wage(basic_salary)
    return calc_overtime(daily, weekend_days, holiday_days)


def calc_gross(basic_salary: float, overtime_total: float) -> float:
    """应发工资 = 基本工资 + 加班费"""
    return round(basic_salary + overtime_total, 2)


def calc_daily_mode_gross(basic_salary: float, actual_work_days: float,
                          month_work_days: float, overtime_total: float = 0) -> dict:
    """按天计算：首月/离职等场景
    
    Args:
        basic_salary: 基本工资
        actual_work_days: 实际出勤天数（从入职到月底）
        month_work_days: 当月总工作日
        overtime_total: 加班费合计（可选）
    
    Returns:
        dict with daily_wage, gross_salary, details
    """
    if basic_salary < 0:
        raise ValueError("基本工资不能为负数")
    if actual_work_days < 0 or month_work_days <= 0:
        raise ValueError("工作天数必须大于0")
    if actual_work_days > month_work_days:
        raise ValueError("出勤天数不能超过当月总工作日")

    daily_wage = round(basic_salary / month_work_days, 2)
    work_salary = round(daily_wage * actual_work_days, 2)
    gross = round(work_salary + overtime_total, 2)

    return {
        'daily_wage': daily_wage,
        'month_work_days': month_work_days,
        'actual_work_days': actual_work_days,
        'work_salary': work_salary,
        'overtime_total': overtime_total,
        'gross_salary': gross,
        'attendance_rate': round(actual_work_days / month_work_days, 4),
    }
