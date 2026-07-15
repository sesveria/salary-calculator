"""月度记录 Tab — 实际收支跟踪 + 结余"""
import flet as ft
from data.storage import list_records, get_monthly_record, save_monthly_record


class RecordTab:
    def __init__(self, page: ft.Page):
        self.page = page
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("月份", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("税前", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("税后", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("必要支出", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("弹性支出", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("储蓄", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("月结余", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("储蓄率", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.GREY_300),
            vertical_lines=ft.border.BorderSide(1, ft.Colors.GREY_200),
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_200),
            heading_row_color=ft.Colors.BLUE_50,
            expand=True,
        )
        
        self.summary_net = ft.Text("¥0", size=18, weight=ft.FontWeight.BOLD)
        self.summary_save = ft.Text("¥0", size=18, weight=ft.FontWeight.BOLD)
        self.summary_rate = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        
        # 编辑表单
        self.edit_ym = ft.Text("")
        self.edit_necessary = ft.TextField(label="实际必要支出", value="0", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        self.edit_flexible = ft.TextField(label="实际弹性支出", value="0", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        self.edit_savings = ft.TextField(label="实际储蓄", value="0", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        self.edit_notes = ft.TextField(label="备注", value="", width=300)

    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📅 月度记录", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.ElevatedButton("🔄 刷新", icon=ft.icons.REFRESH, on_click=self.refresh),
                ]),
                ft.Divider(),
                # 编辑区
                ft.Container(
                    content=ft.Column([
                        ft.Text("编辑本月实际支出", size=14, weight=ft.FontWeight.BOLD),
                        ft.ResponsiveRow([
                            self.edit_necessary, self.edit_flexible,
                            self.edit_savings, self.edit_notes,
                            ft.ElevatedButton("💾 保存支出", icon=ft.icons.SAVE, on_click=self.save_actuals),
                        ]),
                    ]),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.BLUE_200),
                    border_radius=8,
                    bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Divider(),
                # 年度汇总
                ft.Container(
                    content=ft.Row([
                        ft.Column([ft.Text("年税后收入", size=12), self.summary_net]),
                        ft.VerticalDivider(),
                        ft.Column([ft.Text("年储蓄", size=12), self.summary_save]),
                        ft.VerticalDivider(),
                        ft.Column([ft.Text("储蓄率", size=12), self.summary_rate]),
                    ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREEN_200),
                    border_radius=8,
                    bgcolor=ft.Colors.GREEN_50,
                ),
                ft.Divider(),
                # 历史记录表格
                ft.Container(
                    content=ft.Column([
                        ft.Text("历史记录", size=14, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=self.table,
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ]),
                    expand=True,
                ),
            ]),
            padding=15, expand=True,
        )
    
    def refresh(self, e=None):
        """加载并刷新数据"""
        # 先自动填入当月
        import datetime
        now = datetime.datetime.now()
        ym = now.strftime("%Y-%m")
        self.edit_ym.value = ym
        
        records = list_records()
        rows_data = []
        total_net = 0
        total_save = 0
        
        from core.tax import calc_all
        
        for rec in records:
            ym = rec['year_month']
            rate = float(rec.get('housing_fund_rate', 0.08) or 0.08)
            
            # 重新计算
            result = calc_all(
                basic_salary=rec['basic_salary'],
                social_base=rec['social_insurance_base'],
                housing_base=rec['housing_fund_base'],
                housing_rate=rate,
                weekend_days=rec['weekend_overtime_days'],
                holiday_days=rec['holiday_overtime_days'],
                tax_deductions=rec['tax_deductions'],
            )
            net = result['net_salary']
            total_net += net
            
            nec = rec.get('actual_necessary', 0) or 0
            flex = rec.get('actual_flexible', 0) or 0
            savings = rec.get('actual_savings', 0) or 0
            total_save += savings
            
            monthly_balance = net - nec - flex - savings
            save_rate = savings / net * 100 if net > 0 else 0
            
            rows_data.append((ym, net, nec, flex, savings, monthly_balance, save_rate))
        
        self.table.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(ym)),
                ft.DataCell(ft.Text(f"¥{g:,.0f}")),
                ft.DataCell(ft.Text(f"¥{n:,.0f}")),
                ft.DataCell(ft.Text(f"¥{ne:,.0f}")),
                ft.DataCell(ft.Text(f"¥{fl:,.0f}")),
                ft.DataCell(ft.Text(f"¥{sa:,.0f}")),
                ft.DataCell(ft.Text(f"¥{mb:+,.0f}", color=ft.Colors.GREEN_700 if mb >= 0 else ft.Colors.RED_700)),
                ft.DataCell(ft.Text(f"{sr:.1f}%")),
            ])
            for ym, n, ne, fl, sa, mb, sr in rows_data
        ]
        
        # 汇总
        self.summary_net.value = f"¥{total_net:,.0f}"
        self.summary_save.value = f"¥{total_save:,.0f}"
        rate_str = f"{total_save / total_net * 100:.1f}%" if total_net > 0 else "0%"
        self.summary_rate.value = rate_str
        
        self.page.update()
    
    def save_actuals(self, e=None):
        from data.storage import get_monthly_record, save_monthly_record
        
        rec = get_monthly_record(self.edit_ym.value)
        if not rec:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("请先在「工资计算」Tab 保存该月记录"),
                bgcolor=ft.Colors.AMBER_100,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        rec['actual_necessary'] = float(self.edit_necessary.value or 0)
        rec['actual_flexible'] = float(self.edit_flexible.value or 0)
        rec['actual_savings'] = float(self.edit_savings.value or 0)
        rec['notes'] = self.edit_notes.value or ''
        
        save_monthly_record(rec)
        self.refresh()
        
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("✅ 实际支出已保存"),
            bgcolor=ft.Colors.GREEN_100,
        )
        self.page.snack_bar.open = True
        self.page.update()
