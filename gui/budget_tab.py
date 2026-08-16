"""预算分配 Tab — 支持子项分配、剩余计算、实际支出对比"""
import datetime
import flet as ft
from core.budget import (
    SCHEMES, CATEGORY_LABELS, CATEGORY_ICONS,
    allocate, distribute_to_items, get_default_items_for_month,
    calc_remaining,
)
from data.storage import (
    list_records, save_monthly_record, get_monthly_record,
    save_budget_items, get_budget_items,
    get_opening_balance, reconcile_balances, get_initial_balance, set_initial_balance,
)
from gui.budget_logic import (
    sort_items, get_last_month_items, match_scheme,
    extract_items_from_rows,
)
from gui.logger import get_logger

log = get_logger()

# 兼容旧引用（外部若 import 这两个模块级函数）
_get_last_month_items = get_last_month_items
_match_scheme = match_scheme


class BudgetTab:
    SCHEME_NAMES = list(SCHEMES.keys()) + ['自定义']

    def __init__(self, page: ft.Page):
        self.page = page

        now = datetime.datetime.now()
        default_ym = now.strftime("%Y-%m")

        # 月份选择
        self.month_selector = ft.Dropdown(
            label="选择月份", value=default_ym, width=220,
            options=[],
            on_select=self._on_month_changed,
        )

        self.scheme_dropdown = ft.Dropdown(
            label="分配方案", value='50/30/20', width=200,
            options=[ft.dropdown.Option(n) for n in self.SCHEME_NAMES],
        )

        # 概览
        self.opening_balance_input = ft.TextField(
            label="上月结余（¥）", value="0", width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.ACCOUNT_BALANCE,
            hint_text="首月填初始资金",
            on_change=self._on_opening_changed,
        )
        self.net_income_display = ft.Text("¥0.00", size=16, color=ft.Colors.GREY_700)
        self.extra_income_input = ft.TextField(
            label="月额外收入（元）", value="0", width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.ATTACH_MONEY,
            hint_text="税后，不计入工资",
            on_change=self._on_extra_changed,
        )
        self.total_available_display = ft.Text(
            "¥0.00", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700,
        )
        self.result_necessary = ft.Text("¥0.00", size=18)
        self.result_flexible = ft.Text("¥0.00", size=18)
        self.result_savings = ft.Text("¥0.00", size=18)
        self.validation_text = ft.Text("", color=ft.Colors.GREEN_700)

        # 剩余金额显示
        self.remaining_necessary = ft.Text("", size=13, color=ft.Colors.GREEN_700)
        self.remaining_flexible = ft.Text("", size=13, color=ft.Colors.GREEN_700)
        self.remaining_savings = ft.Text("", size=13, color=ft.Colors.GREEN_700)
        self.total_remaining_display = ft.Text(
            "", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700,
        )

        self.current_net = 0
        self.current_base_net = 0
        self.current_ym = ""
        self.current_allocation = {}
        self.current_total_available = 0

        # 实时更新差额和剩余
        self._diff_texts: list[ft.Text] = []      # 差额列 Text 引用，用于原地更新
        self._item_weights: list[float] = []       # 子项权重，用于保存时持久化

        # 子项表格（新增实际支出列、差额列）
        self.items_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("类别", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("项目", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("预算金额", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("实际支出", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("差额", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("操作", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.Border(
                ft.BorderSide(1, ft.Colors.GREY_300),
                ft.BorderSide(1, ft.Colors.GREY_300),
                ft.BorderSide(1, ft.Colors.GREY_300),
                ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            expand=True,
        )

        self._custom_name_input = ft.TextField(
            label="新增项目", width=150, hint_text="项目名称",
        )
        self._custom_cat_input = ft.Dropdown(
            label="类别", value='flexible', width=130,
            options=[
                ft.dropdown.Option('necessary', "必要支出"),
                ft.dropdown.Option('flexible', "弹性支出"),
                ft.dropdown.Option('savings', "储蓄投资"),
            ],
        )

        now = datetime.datetime.now()
        self.current_ym = now.strftime("%Y-%m")

    # ──── 图标 ────

    def _get_category_icon(self, category: str):
        return getattr(ft.Icons, CATEGORY_ICONS.get(category, 'HELP'), ft.Icons.HELP)

    # ──── 构建 UI ────

    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📊 预算分配", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self.month_selector,
                    self.scheme_dropdown,
                    ft.Button(content=ft.Text("🔄 刷新"),
                              icon=ft.Icons.REFRESH, on_click=self.on_refresh),
                    ft.Button(content=ft.Text("📋 生成细项"),
                              icon=ft.Icons.ADD_TASK, on_click=self.on_calculate),
                    ft.Button(content=ft.Text("💾 保存"),
                              icon=ft.Icons.SAVE, on_click=self.on_save),
                ]),
                ft.Divider(),
                ft.Row([
                    # ── 左侧：概览 + 剩余分布 ──
                    ft.Container(
                        content=ft.Column([
                            # 资金概况
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        self.opening_balance_input,
                                        ft.Column([
                                            ft.Text("本月税后收入", size=11, color=ft.Colors.GREY_500),
                                            self.net_income_display,
                                        ], spacing=2),
                                    ]),
                                    ft.Row([
                                        self.extra_income_input,
                                        ft.Container(expand=True),
                                    ]),
                                    ft.Row([
                                        ft.Text("💰 总可用资金", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                                        ft.Container(expand=True),
                                        self.total_available_display,
                                    ]),
                                ]),
                                bgcolor=ft.Colors.BLUE_50,
                                padding=ft.Padding(left=10, top=8, right=10, bottom=8),
                                border_radius=8,
                            ),
                            ft.Divider(),

                            self._mk_row("🏠 必要支出", self.result_necessary, ft.Colors.RED_700),
                            ft.Row([ft.Container(width=20), self.remaining_necessary]),

                            self._mk_row("🛒 弹性支出", self.result_flexible, ft.Colors.ORANGE_700),
                            ft.Row([ft.Container(width=20), self.remaining_flexible]),

                            self._mk_row("💰 储蓄投资", self.result_savings, ft.Colors.GREEN_700),
                            ft.Row([ft.Container(width=20), self.remaining_savings]),

                            ft.Divider(height=2, color=ft.Colors.BLUE_200),

                            # 总剩余
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("总剩余资金", size=13, color=ft.Colors.BLUE_700),
                                    self.total_remaining_display,
                                ], spacing=2),
                                bgcolor=ft.Colors.BLUE_50,
                                padding=ft.Padding(left=10, top=8, right=10, bottom=8),
                                border_radius=8,
                            ),

                            ft.Divider(),
                            self.validation_text,
                        ]),
                        padding=ft.Padding(left=15, top=15, right=15, bottom=15),
                        expand=1,
                        border=ft.Border(
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                        ),
                        border_radius=10,
                    ),
                    # ── 右侧：子项表格 ──
                    ft.Container(
                        content=ft.Column([
                            ft.Text("预算细项", size=14, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                [self.items_table],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            ft.Divider(),
                            ft.Row([
                                self._custom_name_input,
                                self._custom_cat_input,
                                ft.Button(content=ft.Text("➕ 添加"),
                                          icon=ft.Icons.ADD,
                                          on_click=self._add_custom_item),
                            ]),
                        ]),
                        padding=ft.Padding(left=10, top=10, right=10, bottom=10),
                        expand=2,
                        border=ft.Border(
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                        ),
                        border_radius=10,
                    ),
                ]),
            ], scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding(left=15, top=15, right=15, bottom=15),
            expand=True,
        )

    def _mk_row(self, label, value_field, color):
        return ft.Row([
            ft.Text(label, size=15, weight=ft.FontWeight.BOLD, color=color),
            ft.Container(expand=True),
            value_field,
        ])

    # ──── 排序规则 ────

    def _sort_items(self, items: list) -> list:
        """按类别 + sort_order 稳定排序（委托逻辑层）"""
        return sort_items(items)

    # ──── 表格构建 ────

    def _build_items_table(self, items: list):
        """根据子项列表重建 DataTable（按类别+序号排序）"""
        items = self._sort_items(items)
        self._diff_texts.clear()
        self._item_weights.clear()
        rows = []
        for i, item in enumerate(items):
            cat = item.get('category', 'flexible')
            name = item.get('name', '')
            budget_amt = item.get('amount', 0) or 0
            actual_amt = item.get('actual_amount', 0) or 0
            weight = item.get('weight', 10)
            diff = round(budget_amt - actual_amt, 2)
            self._item_weights.append(weight)

            budget_input = ft.TextField(
                value=str(budget_amt),
                width=110,
                keyboard_type=ft.KeyboardType.NUMBER,
                data={'index': i, 'field': 'budget'},
                on_change=self._on_amount_changed,
            )
            actual_input = ft.TextField(
                value=str(actual_amt),
                width=110,
                keyboard_type=ft.KeyboardType.NUMBER,
                data={'index': i, 'field': 'actual'},
                on_change=self._on_actual_changed,
            )
            diff_text = ft.Text(
                f"{diff:+,.0f}",
                size=13,
                color=ft.Colors.GREEN_700 if diff >= 0 else ft.Colors.RED_700,
            )
            self._diff_texts.append(diff_text)

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Row([
                    ft.Icon(self._get_category_icon(cat), size=16),
                    ft.Text(CATEGORY_LABELS.get(cat, cat), size=12),
                ])),
                ft.DataCell(ft.Text(name, size=13)),
                ft.DataCell(budget_input),
                ft.DataCell(actual_input),
                ft.DataCell(diff_text),
                ft.DataCell(
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_size=18,
                        tooltip="删除该项目",
                        on_click=lambda e, idx=i: self._delete_item(idx),
                    )
                ),
            ]))
        self.items_table.rows = rows

    # ──── 实时剩余刷新 ────

    def _on_amount_changed(self, e=None):
        """预算金额变化时实时更新差额和剩余"""
        self._update_diff_in_place()
        self._refresh_remaining()

    def _on_actual_changed(self, e=None):
        """实际支出变化时实时更新差额和剩余"""
        self._update_diff_in_place()
        self._refresh_remaining()

    def _update_diff_in_place(self):
        """从当前表格读取预算/实际，原地更新差额列 Text"""
        for i, row in enumerate(self.items_table.rows):
            if i >= len(self._diff_texts):
                break
            cells = row.cells
            try:
                budget_amt = float(cells[2].content.value or 0)
            except ValueError:
                budget_amt = 0
            try:
                actual_amt = float(cells[3].content.value or 0)
            except ValueError:
                actual_amt = 0
            diff = round(budget_amt - actual_amt, 2)
            self._diff_texts[i].value = f"{diff:+,.0f}"
            self._diff_texts[i].color = (
                ft.Colors.GREEN_700 if diff >= 0 else ft.Colors.RED_700
            )

    def _refresh_remaining(self):
        """实时刷新各大类剩余和总剩余显示"""
        items = self._get_current_items()
        if not self.current_allocation or not items:
            return

        try:
            opening = float(self.opening_balance_input.value or 0)
        except ValueError:
            opening = 0
        total_available = round(opening + self.current_net, 2)
        self.current_total_available = total_available

        remaining_data = calc_remaining(
            total_available, self.current_allocation, items,
        )
        per_cat = remaining_data['per_category']

        for cat, field in [
            ('necessary', self.remaining_necessary),
            ('flexible', self.remaining_flexible),
            ('savings', self.remaining_savings),
        ]:
            info = per_cat[cat]
            r = info['remaining']
            if r > 0.5:
                field.value = (
                    f"     已分配 ¥{info['allocated']:,.0f}  |  剩余 ¥{r:,.0f}"
                )
                field.color = ft.Colors.GREEN_700
            elif r >= -0.5:
                field.value = (
                    f"     已分配 ¥{info['allocated']:,.0f}  |  ✅ 已分完"
                )
                field.color = ft.Colors.GREY_500
            else:
                field.value = (
                    f"     已分配 ¥{info['allocated']:,.0f}  |  ⚠️ 超支 ¥{abs(r):,.0f}"
                )
                field.color = ft.Colors.RED_700

        # 总剩余
        tr = remaining_data['total_remaining']
        if tr > 0.5:
            self.total_remaining_display.value = f"¥{tr:,.2f}（还可分配）"
            self.total_remaining_display.color = ft.Colors.BLUE_700
        elif tr >= -0.5:
            self.total_remaining_display.value = "✅ 已全部用完"
            self.total_remaining_display.color = ft.Colors.GREEN_700
        else:
            self.total_remaining_display.value = f"⚠️ 超支 ¥{abs(tr):,.2f}"
            self.total_remaining_display.color = ft.Colors.RED_700

        # 验证提示
        if remaining_data['all_ok']:
            self.validation_text.value = (
                f"✅ 总预算 ¥{remaining_data['total_allocated']:,.0f}"
                f" / 可用 ¥{remaining_data['net_income']:,.0f}"
            )
            self.validation_text.color = ft.Colors.GREEN_700
        else:
            self.validation_text.value = "⚠️ 部分类别超支，请调整预算金额"
            self.validation_text.color = ft.Colors.AMBER_700

        self.page.update()

    def _on_opening_changed(self, e=None):
        """上月结余变化时实时更新总可用资金显示"""
        try:
            opening = float(self.opening_balance_input.value or 0)
        except ValueError:
            opening = 0
        total = round(opening + self.current_net, 2)
        self.total_available_display.value = f"¥{total:,.2f}"
        self.page.update()

    def _on_extra_changed(self, e=None):
        """额外收入变化时实时更新总可用资金显示"""
        try:
            extra = float(self.extra_income_input.value or 0)
        except ValueError:
            extra = 0
        try:
            opening = float(self.opening_balance_input.value or 0)
        except ValueError:
            opening = 0
        total = round(opening + self.current_base_net + extra, 2)
        self.current_net = self.current_base_net + extra
        self.total_available_display.value = f"¥{total:,.2f}"
        self.page.update()

    # ──── 添加/删除子项 ────

    def _add_custom_item(self, e=None):
        name = self._custom_name_input.value.strip()
        cat = self._custom_cat_input.value
        if not name:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("请输入项目名称"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        items = self._get_current_items()
        # 找到同类别的最大 sort_order
        max_order = max(
            (i.get('sort_order', 0) for i in items if i.get('category') == cat),
            default=-1,
        )
        items.append({
            'category': cat, 'name': name,
            'weight': 10, 'amount': 0, 'actual_amount': 0,
            'sort_order': max_order + 1,
        })
        self._custom_name_input.value = ""
        self._build_items_table(items)
        self._refresh_remaining()
        self.page.update()

    def _delete_item(self, index: int):
        items = self._get_current_items()
        if 0 <= index < len(items):
            items.pop(index)
        self._build_items_table(items)
        self._refresh_remaining()
        self.page.update()

    def _get_current_items(self) -> list:
        """从当前表格中提取子项数据（含实际支出）"""
        return extract_items_from_rows(self.items_table.rows, self._item_weights)

    # ──── 月份切换 ────

    def _refresh_month_options(self, preserve_selection=True):
        """从数据库刷新月份选择器的选项"""
        records = list_records()
        options = []
        for r in records:
            ym = r['year_month']
            options.append(ft.dropdown.Option(ym, f"{ym} (¥{r.get('net_salary', 0):,.0f})"))
        if not options:
            options.append(ft.dropdown.Option(self.current_ym or datetime.datetime.now().strftime("%Y-%m")))
        self.month_selector.options = options
        # 如果 preserve_selection=True，不要覆盖用户当前选择
        if not preserve_selection:
            # 仅在初始化时设置默认值
            if self.current_ym and self.current_ym in {r['year_month'] for r in records}:
                self.month_selector.value = self.current_ym
        log.info(f"月份选项已刷新: {len(options)} 个, 当前选中={self.month_selector.value}")

    def _on_month_changed(self, e=None):
        """月份切换时：加载数据 + 自动分配 + 继承上月方案"""
        ym = self.month_selector.value
        if not ym:
            return
        log.info(f"月份切换: {ym}")
        self.current_ym = ym

        rec = get_monthly_record(ym)
        if not rec:
            self.current_net = 0
            self.current_base_net = 0
            self.current_allocation = {}
            self.net_income_display.value = "¥0.00"
            self.extra_income_input.value = "0"
            self.total_available_display.value = "¥0.00"
            self.result_necessary.value = "¥0.00"
            self.result_flexible.value = "¥0.00"
            self.result_savings.value = "¥0.00"
            self.opening_balance_input.value = str(get_opening_balance(ym))
            self.items_table.rows = []
            self.validation_text.value = ""
            log.info(f"  该月无工资记录")
            self.page.update()
            return

        # 直接读取净收入
        net = rec.get('net_salary', 0) or 0
        extra = rec.get('extra_income', 0) or 0
        self.current_base_net = net
        self.current_net = net + extra
        self.net_income_display.value = f"¥{net:,.2f} + ¥{extra:,.2f}（额外）"
        self.extra_income_input.value = str(extra)
        opening = get_opening_balance(ym)
        self.opening_balance_input.value = str(opening)
        total_available = round(opening + net + extra, 2)
        self.total_available_display.value = f"¥{total_available:,.2f}"

        # 继承上月方案
        scheme = self._get_inherited_scheme(ym, rec)
        self.scheme_dropdown.value = scheme

        # 总是计算分配并显示（不管有没有已保存细项）
        if scheme != '自定义':
            from core.budget import allocate
            alloc = allocate(total_available, scheme)
            self.current_allocation = alloc
            self.result_necessary.value = f"¥{alloc['necessary']:,.2f}"
            self.result_flexible.value = f"¥{alloc['flexible']:,.2f}"
            self.result_savings.value = f"¥{alloc['savings']:,.2f}"
        else:
            # 自定义 → 使用已有预算金额
            alloc = {
                'necessary': rec.get('budget_necessary', 0) or 0,
                'flexible': rec.get('budget_flexible', 0) or 0,
                'savings': rec.get('budget_savings', 0) or 0,
            }
            self.current_allocation = alloc
            self.result_necessary.value = f"¥{alloc['necessary']:,.2f}"
            self.result_flexible.value = f"¥{alloc['flexible']:,.2f}"
            self.result_savings.value = f"¥{alloc['savings']:,.2f}"

        # 加载已有预算细项
        saved = get_budget_items(ym)
        if saved:
            items = []
            for si in saved:
                items.append({
                    'category': si['category'],
                    'name': si['name'],
                    'weight': si.get('weight', 10),
                    'amount': si.get('budget_amount', 0),
                    'actual_amount': si.get('actual_amount', 0),
                })
            self._build_items_table(items)
            self._refresh_remaining()
            log.info(f"  加载已有细项: {len(items)} 个")
        else:
            # 没有已有细项 → 清空表格，用户可点计算分配生成
            self.items_table.rows = []
            self.validation_text.value = f"💡 请点击「计算分配」生成预算细项"
            log.info(f"  无细项，等待用户点计算分配")

        self.page.update()

    def _get_inherited_scheme(self, ym: str, rec: dict) -> str:
        """继承方案：优先用该月已保存的方案，其次继承上月的，最后用默认"""
        saved = rec.get('scheme_name', '') or ''
        if saved and saved in self.SCHEME_NAMES:
            return saved
        # 查上月记录继承方案
        from data.storage import list_records
        for r in list_records():
            if r['year_month'] < ym:
                prev_scheme = r.get('scheme_name', '') or _match_scheme(r)
                if prev_scheme:
                    return prev_scheme
                break
        return self.SCHEME_NAMES[0]

    # ──── 刷新 ────

    def on_refresh(self, e=None):
        """刷新：更新月份下拉框 + 重新加载当前月份数据"""
        self._refresh_month_options(preserve_selection=True)
        self._on_month_changed()
        log.info("预算Tab: 刷新完成")

    # ──── 计算分配 ────

    def on_calculate(self, e=None):
        """「计算分配」：只对当前选中月份生效，不切换月份"""
        ym = self.month_selector.value
        if not ym:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("请先在「选择月份」下拉框中选一个月份"),
                bgcolor=ft.Colors.AMBER_100,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        self.current_ym = ym
        log.info(f"计算分配: month={self.current_ym}")
        rec = get_monthly_record(self.current_ym)
        if not rec:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"未找到 {self.current_ym} 的记录"),
                bgcolor=ft.Colors.AMBER_100,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        net = rec.get('net_salary', 0) or 0
        extra = rec.get('extra_income', 0) or 0
        self.current_base_net = net
        self.current_net = net + extra
        self.net_income_display.value = f"¥{net:,.2f} + ¥{extra:,.2f}（额外）"
        self.extra_income_input.value = str(extra)

        # 加载上月结余
        opening = get_opening_balance(self.current_ym)
        self.opening_balance_input.value = str(opening)

        total_available = round(opening + net + extra, 2)
        self.total_available_display.value = f"¥{total_available:,.2f}"

        # 生成细项（方案A：使用精确金额，不做方案重算）
        saved_items = get_budget_items(self.current_ym)
        items = []
        alloc = {}

        if saved_items:
            # ① 有已保存 → 使用精确金额
            for si in saved_items:
                items.append({
                    'category': si['category'],
                    'name': si['name'],
                    'weight': si.get('weight', 10),
                    'amount': si.get('budget_amount', 0),
                    'actual_amount': si.get('actual_amount', 0),
                })
            # 从子项汇总大类金额
            alloc = {
                'necessary': sum(i['amount'] for i in items if i['category'] == 'necessary'),
                'flexible': sum(i['amount'] for i in items if i['category'] == 'flexible'),
                'savings': sum(i['amount'] for i in items if i['category'] == 'savings'),
            }
            log.info(f"  使用已有细项: {len(items)} 个 (精确金额)")
        else:
            # ② 没有已保存 → 尝试复制上月
            prev = _get_last_month_items(self.current_ym)
            if prev:
                for pi in prev:
                    items.append({
                        'category': pi['category'],
                        'name': pi['name'],
                        'weight': pi.get('weight', 10),
                        'amount': pi.get('budget_amount', 0),
                        'actual_amount': 0,
                        'sort_order': pi.get('sort_order', 0),
                    })
                alloc = {
                    'necessary': sum(i['amount'] for i in items if i['category'] == 'necessary'),
                    'flexible': sum(i['amount'] for i in items if i['category'] == 'flexible'),
                    'savings': sum(i['amount'] for i in items if i['category'] == 'savings'),
                }
                log.info(f"  复制上月细项: {len(items)} 个 (精确金额)")
            else:
                # ③ 没有上月数据 → 按方案生成默认（仅第一次）
                scheme = self.scheme_dropdown.value
                if scheme == '自定义' or not scheme:
                    scheme = '50/30/20'
                alloc = allocate(total_available, scheme)
                default_items = get_default_items_for_month()
                for cat, cat_amt in [
                    ('necessary', alloc['necessary']),
                    ('flexible', alloc['flexible']),
                    ('savings', alloc['savings']),
                ]:
                    cat_items = [i for i in default_items if i['category'] == cat]
                    distributed = distribute_to_items(cat_amt, cat_items)
                    items.extend(distributed)
                for item in items:
                    item.setdefault('actual_amount', 0)
                self.scheme_dropdown.value = scheme
                log.info(f"  生成默认细项: {len(items)} 个 (按方案 {scheme})")

        # 更新大类金额显示（从子项汇总）
        self.current_allocation = alloc
        self.result_necessary.value = f"¥{alloc.get('necessary', 0):,.2f}"
        self.result_flexible.value = f"¥{alloc.get('flexible', 0):,.2f}"
        self.result_savings.value = f"¥{alloc.get('savings', 0):,.2f}"

        self._build_items_table(items)
        self._refresh_remaining()
        self.page.update()

    # ──── 保存 ────

    def on_save(self, e=None):
        if self.current_net <= 0:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("请先点击「计算分配」"),
                bgcolor=ft.Colors.AMBER_100,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        items = self._get_current_items()
        remaining_data = calc_remaining(
            self.current_net, self.current_allocation, items,
        )

        # 校验提示
        warnings = []
        for cat, label in [
            ('necessary', '必要支出'),
            ('flexible', '弹性支出'),
            ('savings', '储蓄投资'),
        ]:
            info = remaining_data['per_category'][cat]
            if info['remaining'] < -0.5:
                warnings.append(f"{label} 超支 ¥{abs(info['remaining']):,.0f}")

        tr = remaining_data['total_remaining']
        if tr < -0.5:
            warnings.append(f"总预算超支 ¥{abs(tr):,.0f}")
        elif tr > 0.5:
            warnings.append(f"还有 ¥{tr:,.0f} 未分配")

        # 1. 保存大类金额到月度记录 + 更新结余
        rec = get_monthly_record(self.current_ym)
        if rec:
            rec['budget_necessary'] = self.current_allocation.get('necessary', 0)
            rec['budget_flexible'] = self.current_allocation.get('flexible', 0)
            rec['budget_savings'] = self.current_allocation.get('savings', 0)
            rec['scheme_name'] = self.scheme_dropdown.value or ''

            # 如果用户修改了上月结余，同步到 opening_balance
            try:
                opening_val = float(self.opening_balance_input.value or 0)
            except ValueError:
                opening_val = 0
            rec['opening_balance'] = opening_val

            # 从子项的实际支出汇总到大类，并同步到月度记录
            act_nec = sum(i.get('actual_amount', 0) for i in items if i.get('category') == 'necessary')
            act_flex = sum(i.get('actual_amount', 0) for i in items if i.get('category') == 'flexible')
            act_sav = sum(i.get('actual_amount', 0) for i in items if i.get('category') == 'savings')
            rec['actual_necessary'] = act_nec
            rec['actual_flexible'] = act_flex
            rec['actual_savings'] = act_sav

            # 重新计算 closing_balance
            net = rec.get('net_salary', 0) or 0
            try:
                extra = float(self.extra_income_input.value or 0)
            except ValueError:
                extra = 0
            rec['extra_income'] = extra
            nec = rec.get('actual_necessary', 0) or 0
            flex = rec.get('actual_flexible', 0) or 0
            sav = rec.get('actual_savings', 0) or 0
            actual_total = nec + flex + sav
            rec['closing_balance'] = round(opening_val + net + extra - actual_total, 2)
            rec['total_available'] = round(opening_val + net + extra, 2)
            rec['total_expense'] = actual_total
            rec['save_rate'] = round(sav / (net + extra) * 100, 2) if (net + extra) > 0 else 0

            save_monthly_record(dict(rec))

            # 如果是第一个月且用户修改了结余，同时更新初始资金设置
            if opening_val != get_initial_balance():
                # 检查是否没有更早的月份
                all_recs = list_records()
                earlier = [r for r in all_recs if r['year_month'] < self.current_ym]
                if not earlier:
                    set_initial_balance(opening_val)

            # 重新串联所有后续月份
            reconcile_balances()

        # 2. 保存细项到 budget_items（含实际支出）
        save_items = []
        for i, item in enumerate(items):
            save_items.append({
                'category': item['category'],
                'name': item['name'],
                'budget_amount': item.get('amount', 0),
                'actual_amount': item.get('actual_amount', 0),
                'weight': item.get('weight', 10),
                'sort_order': item.get('sort_order', i),
            })
        save_budget_items(self.current_ym, save_items)

        msg = f"✅ {self.current_ym} 已保存（{len(save_items)}个细项）"
        if warnings:
            msg += " | ⚠️ " + "；".join(warnings)

        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(msg),
            bgcolor=ft.Colors.GREEN_100 if not warnings else ft.Colors.AMBER_100,
        )
        self.page.snack_bar.open = True
        self.page.update()
