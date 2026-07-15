"""工资计算 Tab - 输入参数 + 自动计算结果"""
import flet as ft
from core.tax import calc_all
from data.storage import get_setting, set_setting


class SalaryTab:
    def __init__(self, page: ft.Page):
        self.page = page
        
        # 输入控件
        self.basic_salary = ft.TextField(
            label="基本工资（元）", value="15000", width=180,
            prefix_icon=ft.icons.MONETIZATION_ON, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.social_base = ft.TextField(
            label="社保基数", value="15000", width=180,
            prefix_icon=ft.icons.SECURITY, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.housing_base = ft.TextField(
            label="公积金基数", value="15000", width=180,
            prefix_icon=ft.icons.HOME, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.housing_rate = ft.Dropdown(
            label="公积金比例", value="8%", width=140,
            options=[ft.dropdown.Option(f"{i}%") for i in range(5, 13)],
        )
        self.weekend_days = ft.TextField(
            label="周末加班（天）", value="1", width=140,
            prefix_icon=ft.icons.WEEKEND, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.holiday_days = ft.TextField(
            label="节假日加班（天）", value="0", width=140,
            prefix_icon=ft.icons.CELEBRATION, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.tax_deductions = ft.TextField(
            label="专项附加扣除（元）", value="0", width=180,
            prefix_icon=ft.icons.REMOVE, keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        # 结果展示
        self.result_income = ft.Text("—", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.result_daily = ft.Text("—")
        self.result_overtime = ft.Text("—")
        self.result_gross = ft.Text("—")
        self.result_pension = ft.Text("—")
        self.result_medical = ft.Text("—")
        self.result_unemployment = ft.Text("—")
        self.result_housing = ft.Text("—")
        self.result_insurance_total = ft.Text("—")
        self.result_tax = ft.Text("—")
        self.result_net = ft.Text("—", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        
        # 状态
        self.current_result = None

    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    # 左侧：输入区
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📥 输入参数", size=16, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            ft.ResponsiveRow([
                                self.basic_salary, self.social_base, self.housing_base,
                            ]),
                            ft.ResponsiveRow([
                                self.housing_rate, self.weekend_days, self.holiday_days,
                            ]),
                            ft.ResponsiveRow([
                                self.tax_deductions,
                            ]),
                            ft.Row([
                                ft.ElevatedButton("🧮 计算", icon=ft.icons.CALCULATE,
                                                  on_click=self.on_calculate,
                                                  style=ft.ButtonStyle(padding=20)),
                                ft.ElevatedButton("💾 保存", icon=ft.icons.SAVE,
                                                  on_click=self.on_save),
                            ]),
                        ]),
                        padding=20, expand=1,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=10,
                    ),
                    # 右侧：结果区
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📊 计算结果", size=16, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self._make_result_row("基本工资", self.result_income),
                            self._make_result_row("日工资（21.75天）", self.result_daily),
                            self._make_result_row("加班费合计", self.result_overtime),
                            ft.Divider(),
                            self._make_result_row("应发工资", self.result_gross, True),
                            ft.Divider(),
                            ft.Text("— 五险一金 —", size=12, color=ft.Colors.GREY_500),
                            self._make_result_row("  养老保险", self.result_pension),
                            self._make_result_row("  医疗保险", self.result_medical),
                            self._make_result_row("  失业保险", self.result_unemployment),
                            self._make_result_row("  住房公积金", self.result_housing),
                            self._make_result_row("  五险一金合计", self.result_insurance_total, True),
                            ft.Divider(),
                            self._make_result_row("应缴个税", self.result_tax),
                            ft.Divider(height=2, color=ft.Colors.GREEN_700),
                            self._make_result_row("★ 实发工资", self.result_net, True),
                        ]),
                        padding=20, expand=1,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=10,
                    ),
                ]),
            ]),
            padding=15, expand=True,
        )
    
    def _make_result_row(self, label, value_field, bold=False):
        return ft.Row([
            ft.Text(label, size=14 if not bold else 16,
                    weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL),
            ft.Container(expand=True),
            value_field,
        ])
    
    def on_calculate(self, e=None):
        try:
            rate_str = self.housing_rate.value.replace('%', '')
            rate = int(rate_str) / 100.0
            
            result = calc_all(
                basic_salary=float(self.basic_salary.value or 0),
                social_base=float(self.social_base.value or 0),
                housing_base=float(self.housing_base.value or 0),
                housing_rate=rate,
                weekend_days=float(self.weekend_days.value or 0),
                holiday_days=float(self.holiday_days.value or 0),
                tax_deductions=float(self.tax_deductions.value or 0),
            )
            self.current_result = result
            
            # 更新结果
            self.result_income.value = f"¥{result['basic_salary']:,.2f}"
            self.result_daily.value = f"¥{result['daily_wage']:,.2f}"
            ot = result['overtime']
            ot_text = f"¥{ot['total']:,.2f} (周末{ot['weekend_amount']:,.2f} + 节假日{ot['holiday_amount']:,.2f})"
            self.result_overtime.value = ot_text
            self.result_gross.value = f"¥{result['gross_salary']:,.2f}"
            
            ins = result['insurance']
            self.result_pension.value = f"¥{ins['pension']:,.2f}"
            self.result_medical.value = f"¥{ins['medical']:,.2f}"
            self.result_unemployment.value = f"¥{ins['unemployment']:,.2f}"
            self.result_housing.value = f"¥{ins['housing_fund']:,.2f}"
            self.result_insurance_total.value = f"¥{ins['total']:,.2f}"
            
            self.result_tax.value = f"¥{result['tax']:,.2f}"
            self.result_net.value = f"¥{result['net_salary']:,.2f}"
            
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"输入有误: {ex}"))
            self.page.snack_bar.open = True
            self.page.update()
    
    def on_save(self, e=None):
        """保存当前参数和结果到数据库"""
        self.on_calculate()
        if not self.current_result:
            return
        
        import datetime
        now = datetime.datetime.now()
        ym = now.strftime("%Y-%m")
        
        from data.storage import save_monthly_record
        record = {
            'year_month': ym,
            'basic_salary': float(self.basic_salary.value or 0),
            'weekend_overtime_days': float(self.weekend_days.value or 0),
            'holiday_overtime_days': float(self.holiday_days.value or 0),
            'social_insurance_base': float(self.social_base.value or 0),
            'housing_fund_base': float(self.housing_base.value or 0),
            'housing_fund_rate': float(self.housing_rate.value.replace('%', '')) / 100,
            'tax_deductions': float(self.tax_deductions.value or 0),
            'actual_necessary': 0,
            'actual_flexible': 0,
            'actual_savings': 0,
            'notes': '',
        }
        save_monthly_record(record)
        
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"✅ {ym} 工资记录已保存"),
            bgcolor=ft.Colors.GREEN_100,
        )
        self.page.snack_bar.open = True
        self.page.update()
