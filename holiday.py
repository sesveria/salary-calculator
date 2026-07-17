"""
工作日/节假日计算 —— 基于 chinese-calendar。

自动处理中国法定节假日、调休补班。
如果未安装 chinese-calendar，回退到简单的周末判断。
"""

import datetime

try:
    from chinese_calendar import is_workday as _lib_is_workday

    _HAS_LIB = True
    _LIB_VERSION = __import__("importlib.metadata").metadata.version(
        "chinese-calendar"
    )
except (ImportError, Exception):
    _HAS_LIB = False
    _LIB_VERSION = None


def _get_supported_years():
    """获取库支持的年份范围"""
    if _HAS_LIB:
        from chinese_calendar.utils import get_supported_years as _gsy

        return _gsy()
    return []


def is_workday(dt: datetime.date) -> bool:
    """判断某天是否上班"""
    if _HAS_LIB:
        return _lib_is_workday(dt)
    # 回退：简单周末判断（不包含法定假和补班）
    return dt.weekday() < 5


def is_holiday(dt: datetime.date) -> bool:
    """判断某天是否休息"""
    return not is_workday(dt)


def get_workdays_in_month(year: int, month: int) -> int:
    """获取某月的工作日数"""
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    first_day = datetime.date(year, month, 1)
    days_in_month = (next_month - first_day).days

    count = 0
    for day in range(1, days_in_month + 1):
        if is_workday(datetime.date(year, month, day)):
            count += 1
    return count


def get_workdays_between(start: datetime.date, end: datetime.date) -> int:
    """获取日期区间内的工作日数（含起止）"""
    if start > end:
        return 0
    count = 0
    d = start
    while d <= end:
        if is_workday(d):
            count += 1
        d += datetime.timedelta(days=1)
    return count


def get_workday_ratio(year: int, month: int, start_day: int) -> float:
    """
    计算入职当月的工作比例：从 start_day 到月底的工作日 / 当月总工作日

    用于首月工资计算：首月工资 = 基本工资 × 比例
    """
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    first_day = datetime.date(year, month, 1)
    days_in_month = (next_month - first_day).days

    start = datetime.date(year, month, start_day)
    end = datetime.date(year, month, days_in_month)

    actual = get_workdays_between(start, end)
    total = get_workdays_in_month(year, month)
    return actual / total if total > 0 else 0.0


def get_library_version() -> str | None:
    """获取 chinese-calendar 库版本"""
    return _LIB_VERSION


def is_library_available() -> bool:
    """检查 chinese-calendar 是否已安装"""
    return _HAS_LIB


def get_supported_years() -> list[int]:
    """获取库支持的年份列表"""
    return _get_supported_years()
