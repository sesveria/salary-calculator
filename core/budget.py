"""Budget allocation schemes and validation.

Supported schemes:
  - 50/30/20: 必要50% / 弹性30% / 储蓄20%
  - 631:      必要60% / 弹性10% / 储蓄30%
  - 333:      必要34% / 弹性33% / 储蓄33%
  - custom:   自定义比例
"""

SCHEMES = {
    '50/30/20': {'necessary': 0.50, 'flexible': 0.30, 'savings': 0.20},
    '631':      {'necessary': 0.60, 'flexible': 0.10, 'savings': 0.30},
    '333':      {'necessary': 0.34, 'flexible': 0.33, 'savings': 0.33},
}


def get_scheme(name: str) -> dict:
    """获取分配方案的比例"""
    if name in SCHEMES:
        return dict(SCHEMES[name])
    raise ValueError(f"未知方案: {name}，可选: {list(SCHEMES.keys())}")


def allocate(net_income: float, scheme: str = '50/30/20') -> dict:
    """按方案分配税后收入"""
    ratios = get_scheme(scheme)
    result = {}
    for key, ratio in ratios.items():
        result[key] = round(net_income * ratio, 2)
    # Fix rounding by adjusting the largest bucket
    total = sum(result.values())
    diff = round(net_income - total, 2)
    if diff != 0:
        # Add rounding diff to the largest bucket
        max_key = max(result, key=lambda k: result[k])
        result[max_key] = round(result[max_key] + diff, 2)
    return result


def validate(items: dict, total: float) -> dict:
    """校验预算分配总和是否等于总收入
    
    items = {'necessary': x, 'flexible': y, 'savings': z, ...}
    total = 税后收入
    
    Returns dict with:
      - total_allocated: sum of all items
      - diff: total - total_allocated (should be 0)
      - ok: boolean
    """
    allocated = sum(items.values())
    diff = round(total - allocated, 2)
    return {
        'total_allocated': allocated,
        'diff': diff,
        'ok': abs(diff) < 0.02,
    }
