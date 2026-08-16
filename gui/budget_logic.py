"""预算 Tab 纯逻辑层 — 无 UI 依赖，可独立测试

从 budget_tab.py 提取的与 flet 控件无关的逻辑。
"""
from core.budget import CATEGORY_LABELS, SCHEMES

# 类别显示顺序（与 budget_tab 原 CATEGORY_ORDER 一致）
CATEGORY_ORDER = {'necessary': 0, 'flexible': 1, 'savings': 2}


def sort_items(items: list) -> list:
    """按类别优先级 + sort_order 稳定排序（不修改原列表）"""
    return sorted(items, key=lambda i: (
        CATEGORY_ORDER.get(i.get('category', ''), 99),
        i.get('sort_order', 0),
    ))


def get_last_month_items(current_ym: str) -> list:
    """获取上个月的预算细项（用于复制方案）"""
    from data.storage import list_records, get_budget_items
    records = list_records()
    for r in records:
        if r['year_month'] < current_ym:
            return get_budget_items(r['year_month'])
    return []


def match_scheme(record: dict) -> str:
    """从月度记录的预算金额反推使用的方案"""
    nec = record.get('budget_necessary', 0) or 0
    flex = record.get('budget_flexible', 0) or 0
    sav = record.get('budget_savings', 0) or 0
    total = nec + flex + sav
    if total <= 0:
        return ''
    ratios = {
        'necessary': nec / total,
        'flexible': flex / total,
        'savings': sav / total,
    }
    for name, scheme in SCHEMES.items():
        if all(abs(ratios[k] - v) < 0.05 for k, v in scheme.items()):
            return name
    return '自定义'


def extract_items_from_rows(rows, item_weights: list) -> list:
    """从 DataTable 行提取子项数据（含实际支出）

    这是 _get_current_items 的纯函数版本：
      rows: 表格行，每行 cells 结构为
            [类别cell, 名称cell, 预算输入, 实际输入, 差额text, 操作]
      item_weights: 与行对应的权重列表（来自 _item_weights）

    Returns:
        list of {'category', 'name', 'weight', 'amount', 'actual_amount'}
    """
    items = []
    for i, row in enumerate(rows):
        cells = row.cells
        cat_text = cells[0].content.controls[1].value
        name = cells[1].content.value
        try:
            budget_amt = float(cells[2].content.value or 0)
        except (ValueError, AttributeError):
            budget_amt = 0
        try:
            actual_amt = float(cells[3].content.value or 0)
        except (ValueError, AttributeError):
            actual_amt = 0
        # 反向映射类别标签
        cat = 'flexible'
        for k, v in CATEGORY_LABELS.items():
            if v == cat_text:
                cat = k
                break
        weight = item_weights[i] if i < len(item_weights) else 10
        items.append({
            'category': cat,
            'name': name,
            'weight': weight,
            'amount': budget_amt,
            'actual_amount': actual_amt,
        })
    return items
