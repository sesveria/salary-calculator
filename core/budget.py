"""Budget allocation schemes, sub-items, and distribution.

支持三大类 + 细项分配：
  - necessary: 必要支出
  - flexible:  弹性支出
  - savings:   储蓄投资
"""

# 分配方案
SCHEMES = {
    '50/30/20': {'necessary': 0.50, 'flexible': 0.30, 'savings': 0.20},
    '631':      {'necessary': 0.60, 'flexible': 0.10, 'savings': 0.30},
    '333':      {'necessary': 0.34, 'flexible': 0.33, 'savings': 0.33},
}

# 默认子项模板（每条记录包含 name, category, weight）
# 权重用于自动摊分同类金额，比如"房租"权重 50 表示占必要支出的 50%
# sort_order 控制同类内的显示顺序
DEFAULT_SUB_ITEMS = [
    # 必要支出
    {'category': 'necessary', 'name': '房租/房贷',      'weight': 40, 'sort_order': 0},
    {'category': 'necessary', 'name': '水电煤/物业',    'weight': 8,  'sort_order': 1},
    {'category': 'necessary', 'name': '交通通勤',       'weight': 10, 'sort_order': 2},
    {'category': 'necessary', 'name': '基础餐饮',       'weight': 25, 'sort_order': 3},
    {'category': 'necessary', 'name': '通讯网络',       'weight': 7,  'sort_order': 4},
    {'category': 'necessary', 'name': '保险',           'weight': 10, 'sort_order': 5},
    # 弹性支出
    {'category': 'flexible',  'name': '外食/社交',      'weight': 30, 'sort_order': 0},
    {'category': 'flexible',  'name': '购物娱乐',       'weight': 25, 'sort_order': 1},
    {'category': 'flexible',  'name': '学习提升',       'weight': 25, 'sort_order': 2},
    {'category': 'flexible',  'name': '旅行度假',       'weight': 20, 'sort_order': 3},
    # 储蓄投资
    {'category': 'savings',   'name': '紧急储备金',     'weight': 30, 'sort_order': 0},
    {'category': 'savings',   'name': '基金/定投',      'weight': 40, 'sort_order': 1},
    {'category': 'savings',   'name': '额外还贷',       'weight': 30, 'sort_order': 2},
]

CATEGORY_LABELS = {
    'necessary': '🏠 必要支出',
    'flexible': '🛒 弹性支出',
    'savings': '💰 储蓄投资',
}

CATEGORY_ICONS = {
    'necessary': 'HOME',
    'flexible': 'SHOPPING_CART',
    'savings': 'TRENDING_UP',
}


def get_scheme(name: str) -> dict:
    """获取分配方案的比例"""
    if name in SCHEMES:
        return dict(SCHEMES[name])
    raise ValueError(f"未知方案: {name}，可选: {list(SCHEMES.keys())}")


def allocate(net_income: float, scheme: str = '50/30/20') -> dict:
    """按方案分配税后收入到三大类"""
    ratios = get_scheme(scheme)
    result = {}
    for key, ratio in ratios.items():
        result[key] = round(net_income * ratio, 2)
    total = sum(result.values())
    diff = round(net_income - total, 2)
    if diff != 0:
        max_key = max(result, key=lambda k: result[k])
        result[max_key] = round(result[max_key] + diff, 2)
    return result


def distribute_to_items(category_amount: float, items: list) -> list[dict]:
    """将大类金额按权重摊分到子项
    
    Args:
        category_amount: 大类分配的金额
        items: 子项列表，每项含 {'name': str, 'weight': float}
    
    Returns:
        更新后的子项列表，每项含追加的 'amount' 字段
    """
    if not items:
        return []

    total_weight = sum(item.get('weight', 1) for item in items)
    if total_weight <= 0:
        total_weight = len(items)

    result = []
    for i, item in enumerate(items):
        amount = round(category_amount * item['weight'] / total_weight, 2)
        result.append({
            **item,
            'amount': amount,
        })

    # 修正舍入误差（加到最大权重的子项）
    allocated = sum(r['amount'] for r in result)
    diff = round(category_amount - allocated, 2)
    if diff != 0 and result:
        max_idx = max(range(len(result)), key=lambda i: result[i]['weight'])
        result[max_idx]['amount'] = round(result[max_idx]['amount'] + diff, 2)

    return result


def validate(items: dict, total: float) -> dict:
    """校验预算分配总和是否等于总收入"""
    allocated = sum(items.values())
    diff = round(total - allocated, 2)
    return {
        'total_allocated': allocated,
        'diff': diff,
        'ok': abs(diff) < 0.02,
    }


def calc_remaining(net_income: float, category_budgets: dict,
                   sub_items: list) -> dict:
    """计算各大类的已分配金额和剩余金额
    
    Args:
        net_income: 税后总收入
        category_budgets: 三大类预算，如 {'necessary': 7000, 'flexible': 4200, 'savings': 2800}
        sub_items: 子项列表，每项含 'category' 和 'amount'
    
    Returns:
        {
            'per_category': {
                'necessary': {'budget': 7000, 'allocated': 6500, 'remaining': 500},
                ...
            },
            'total_allocated': 13600,
            'total_remaining': 400,
            'net_income': 14000,
            'all_ok': True,  # 所有类别都不超支
        }
    """
    per_cat = {}
    for cat in ['necessary', 'flexible', 'savings']:
        budget = round(category_budgets.get(cat, 0), 2)
        allocated = round(sum(
            i.get('amount', 0) for i in sub_items if i.get('category') == cat
        ), 2)
        remaining = round(budget - allocated, 2)
        per_cat[cat] = {
            'budget': budget,
            'allocated': allocated,
            'remaining': remaining,
        }

    total_allocated = round(sum(p['allocated'] for p in per_cat.values()), 2)
    total_remaining = round(net_income - total_allocated, 2)
    all_ok = all(p['remaining'] >= -0.01 for p in per_cat.values())

    return {
        'per_category': per_cat,
        'total_allocated': total_allocated,
        'total_remaining': total_remaining,
        'net_income': net_income,
        'all_ok': all_ok,
    }


def get_default_items_for_month() -> list[dict]:
    """获取某月的默认子项列表（深拷贝）"""
    return [dict(item) for item in DEFAULT_SUB_ITEMS]
