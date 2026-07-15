"""预算分配 Tab - 方案选择 + 三类预算明细编辑"""
import flet as ft
from core.budget import allocate, get_scheme, SCHEMES
from data.storage import save_budget_items, get_budget_items, list_records


class BudgetTab:
    SCHEME_NAMES = list(SCHEMES.keys()) + ['自定义']

    def __init__(self, page: ft.Page):
        self.page = page
        self.scheme_dropdown = ft.Dropdown(
            label="分配方案", value='50/30/20', width=200,
            options=[ft.dropdown.Option(n) for n in self.SCHEME_NAMES],
            on_change=self.on_scheme_change,
        )
        
        self.income_display = ft.Text("¥0.00", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
        self.result_necessary = ft.Text("¥0.00", size=18)
        self.result_flexible = ft.Text("¥0.00", size=18)
        self.result_savings = ft.Text("¥0.00", size=18)
        self.validation_text = ft.Text("", color=ft.Colors.GREEN_700)
        
        # 细项编辑
        self.nec_items = ft.Column()
        self.flex_items = ft.Column()
        self.save_items = ft.Column()
        
        self.current_net = 0

    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📊 预算分配", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self.scheme_dropdown,
                    ft.ElevatedButton("🔄 计算分配", icon=ft.icons.REFRESH, on_click=self.on_calculate),
                    ft.ElevatedButton("💾 保存模板", icon=ft.icons.SAVE, on_click=self.on_save),
                ]),
                ft.Divider(),
                ft.Row([
                    # 自动分配结果
                    ft.Container(
                        content=ft.Column([
                            ft.Text("税后收入", size=14),
                            self.income_display,
                            ft.Divider(),
                            self._make_alloc_row("必要支出", self.result_necessary, ft.Colors.RED_700),
                            self._make_alloc_row("弹性支出", self.result_flexible, ft.Colors.ORANGE_700),
                            self._make_alloc_row("储蓄投资", self.result_savings, ft.Colors.GREEN_700),
                            ft.Divider(),
                            self.validation_text,
                        ]),
                        padding=15, expand=1,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=10,
                    ),
                    # 细项编辑
                    ft.Container(
                        content=ft.Column([
                            ft.Tabs(
                                selected_index=0,
                                tabs=[
                                    ft.Tab(text="必要支出", icon=ft.icons.HOME,
                                           content=ft.Container(content=self.nec_items, padding=10)),
                                    ft.Tab(text="弹性支出", icon=ft.icons.SHOPPING_CART,
                                           content=ft.Container(content=self.flex_items, padding=10)),
                                    ft.Tab(text="储蓄投资", icon=ft.icons.TRENDING_UP,
                                           content=ft.Container(content=self.save_items, padding=10)),
                                ],
                                expand=True,
                            ),
                        ]),
                        padding=5, expand=2,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=10,
                    ),
                ]),
            ]),
            padding=15, expand=True,
        )
    
    def _make_alloc_row(self, label, value_field, color):
        return ft.Row([
            ft.Text(label, size=15, weight=ft.FontWeight.BOLD, color=color),
            ft.Container(expand=True),
            value_field,
        ])
    
    def on_scheme_change(self, e):
        self.on_calculate()
    
    def on_calculate(self, e=None):
        """根据税后收入自动计算分配"""
        records = list_records()
        if not records:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("请先在「工资计算」Tab 保存一条记录"),
                bgcolor=ft.Colors.AMBER_100,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        # 用最新月份的税后收入
        latest = records[0]
        from core.tax import calc_all
        rate_str = str(latest.get('housing_fund_rate', 0.08))
        rate = float(rate_str) if rate_str else 0.08
        result = calc_all(
            basic_salary=latest['basic_salary'],
            social_base=latest['social_insurance_base'],
            housing_base=latest['housing_fund_base'],
            housing_rate=rate,
            weekend_days=latest['weekend_overtime_days'],
            holiday_days=latest['holiday_overtime_days'],
            tax_deductions=latest['tax_deductions'],
        )
        net = result['net_salary']
        self.current_net = net
        self.income_display.value = f"¥{net:,.2f}"
        
        scheme = self.scheme_dropdown.value
        if scheme == '自定义':
            return
        
        alloc = allocate(net, scheme)
        self.result_necessary.value = f"¥{alloc['necessary']:,.2f}"
        self.result_flexible.value = f"¥{alloc['flexible']:,.2f}"
        self.result_savings.value = f"¥{alloc['savings']:,.2f}"
        
        total_alloc = alloc['necessary'] + alloc['flexible'] + alloc['savings']
        diff = round(net - total_alloc, 2)
        if abs(diff) < 0.02:
            self.validation_text.value = "✅ 预算校验通过（支出+储蓄=税后收入）"
            self.validation_text.color = ft.Colors.GREEN_700
        else:
            self.validation_text.value = f"⚠️ 差额: ¥{diff:+,.2f}"
            self.validation_text.color = ft.Colors.AMBER_700
        
        self.page.update()
    
    def on_save(self, e=None):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("✅ 预算模板已保存（此功能待完善）"),
            bgcolor=ft.Colors.GREEN_100,
        )
        self.page.snack_bar.open = True
        self.page.update()
