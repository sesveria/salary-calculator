"""budget_logic 纯逻辑层测试（无 UI 依赖）"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gui.budget_logic import sort_items, match_scheme


class TestSortItems:
    def test_category_priority(self):
        items = [
            {'category': 'savings', 'name': '基金', 'sort_order': 0},
            {'category': 'necessary', 'name': '房租', 'sort_order': 0},
            {'category': 'flexible', 'name': '外食', 'sort_order': 0},
        ]
        result = sort_items(items)
        assert [i['category'] for i in result] == ['necessary', 'flexible', 'savings']

    def test_sort_order_within_category(self):
        items = [
            {'category': 'necessary', 'name': 'B', 'sort_order': 1},
            {'category': 'necessary', 'name': 'A', 'sort_order': 0},
        ]
        result = sort_items(items)
        assert [i['name'] for i in result] == ['A', 'B']

    def test_unknown_category_last(self):
        items = [
            {'category': 'weird', 'name': 'X', 'sort_order': 0},
            {'category': 'necessary', 'name': 'A', 'sort_order': 0},
        ]
        result = sort_items(items)
        assert result[-1]['category'] == 'weird'

    def test_does_not_mutate_input(self):
        items = [
            {'category': 'savings', 'name': '基金', 'sort_order': 0},
            {'category': 'necessary', 'name': '房租', 'sort_order': 0},
        ]
        original = [dict(i) for i in items]
        sort_items(items)
        assert items == original


class TestMatchScheme:
    def test_502020(self):
        rec = {'budget_necessary': 7000, 'budget_flexible': 4200, 'budget_savings': 2800}
        assert match_scheme(rec) == '50/30/20'

    def test_631(self):
        rec = {'budget_necessary': 8400, 'budget_flexible': 1400, 'budget_savings': 4200}
        assert match_scheme(rec) == '631'

    def test_custom(self):
        rec = {'budget_necessary': 9000, 'budget_flexible': 1000, 'budget_savings': 1000}
        assert match_scheme(rec) == '自定义'

    def test_zero_total(self):
        assert match_scheme({'budget_necessary': 0, 'budget_flexible': 0, 'budget_savings': 0}) == ''

    def test_ratio_tolerance(self):
        # 轻微舍入误差（0.05 容差内）仍能识别
        rec = {'budget_necessary': 7001, 'budget_flexible': 4199, 'budget_savings': 2800}
        assert match_scheme(rec) == '50/30/20'
