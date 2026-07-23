"""工资计算 Tab — 支持加班基数、按天计算、入职日期"""
import datetime
import flet as ft
from core.tax import calc_all
from data.storage import get_setting, set_setting
from gui.logger import get_logger

log = get_logger()


class SalaryTab:
    def __init__(self, page: ft.Page):
        self.page = page

        now = datetime.datetime.now()
        current_ym = now.strftime("%Y-%m")

        # 月份选择
        self.month_picker = ft.TextField(
            label="月份", value=current_ym, width=140,
            prefix_icon=ft.Icons.CALENDAR_MONTH, hint_text="YYYY-MM（可改其他月）",
        )

        # 基本参数
        self.basic_salary = ft.TextField(
            label="基本工资（元）", value="15000", width=180,
            prefix_icon=ft.Icons.MONETIZATION_ON, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.overtime_base = ft.TextField(
            label="加班基数（元）", value="15000", width=180,
            prefix_icon=ft.Icons.WORK, keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="默认为基本工资",
        )
        self.social_base = ft.TextField(
            label="社保基数", value="15000", width=180,
            prefix_icon=ft.Icons.SECURITY, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.housing_base = ft.TextField(
            label="公积金基数", value="15000", width=180,
            prefix_icon=ft.Icons.HOME, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.housing_rate = ft.Dropdown(
            label="公积金比例", value="8%", width=140,
            options=[ft.dropdown.Option(f"{i}%") for i in range(5, 13)],
        )
        self.weekend_days = ft.TextField(
            label="周末加班（天）", value="1", width=140,
            prefix_icon=ft.Icons.WEEKEND, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.holiday_days = ft.TextField(
            label="节假日加班（天）", value="0", width=140,
            prefix_icon=ft.Icons.CELEBRATION, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.tax_deductions = ft.TextField(
            label="专项附加扣除（元）", value="0", width=180,
            prefix_icon=ft.Icons.REMOVE, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.critical_illness = ft.TextField(
            label="大病医疗保险（元）", value="10", width=140,
            prefix_icon=ft.Icons.MEDICAL_SERVICES, keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="默认10元",
        )
        self.pay_day = ft.Dropdown(
            label="发薪日", value="15", width=140,
            options=[ft.dropdown.Option(str(d)) for d in [1, 5, 8, 10, 12, 15, 20, 25, 28]],
        )

        # 按天计算模式
        self.daily_mode_switch = ft.Switch(
            label="按天计算（首月/离职）", value=False,
            on_change=self._on_daily_toggle,
        )
        self.daily_fields = ft.Column(
            visible=False,
            spacing=10,
            controls=[
                ft.Text("—— 首月工资 ——", size=12, color=ft.Colors.GREY_500),
                ft.TextField(
                    label="入职日期", value="", width=200,
                    prefix_icon=ft.Icons.CALENDAR_MONTH, hint_text="YYYY-MM-DD",
                ),
                ft.ResponsiveRow([
                    ft.TextField(
                        label="当月工作日数", value="", width=140,
                        prefix_icon=ft.Icons.WORK, keyboard_type=ft.KeyboardType.NUMBER,
                        hint_text="自动计算",
                    ),
                    ft.TextField(
                        label="实际出勤天数", value="", width=140,
                        prefix_icon=ft.Icons.PEOPLE, keyboard_type=ft.KeyboardType.NUMBER,
                        hint_text="自动计算",
                    ),
                ]),
                ft.Button(
                    content=ft.Text("📅 自动计算工作日"),
                    icon=ft.Icons.AUTO_FIX_HIGH,
                    on_click=self._auto_calc_workdays,
                ),
            ],
        )
        self._entry_date_field = self.daily_fields.controls[1]
        self._month_days_field = self.daily_fields.controls[2].controls[0]
        self._actual_days_field = self.daily_fields.controls[2].controls[1]

        # 结果字段
        self.result_income = ft.Text("—", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.result_daily = ft.Text("—")
        self.result_overtime = ft.Text("—")

        self.result_gross = ft.Text("—")
        self.result_pension = ft.Text("—")
        self.result_medical = ft.Text("—")
        self.result_unemployment = ft.Text("—")
        self.result_housing = ft.Text("—")
        self.result_critical_illness = ft.Text("—")
        self.result_insurance_total = ft.Text("—")
        self.result_tax = ft.Text("—")
        self.result_net = ft.Text("—", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)

        self.current_result = None

        # 加载上次设置
        self._load_settings()
        # 加载数据库中最新的记录
        self._load_last_record()

    def _load_settings(self):
        """加载全局设置"""
        saved_pay_day = get_setting("pay_day", "15")
        self.pay_day.value = saved_pay_day

    def _load_last_record(self):
        """从数据库加载最新的工资记录，预填到输入框"""
        from data.storage import list_records
        records = list_records()
        if not records:
            return
        rec = records[0]
        ym = rec['year_month']
        self.month_picker.value = ym
        self.basic_salary.value = str(rec.get('basic_salary', 0) or 0)
        self.overtime_base.value = str(rec.get('overtime_base', 0) or 0)
        self.social_base.value = str(rec.get('social_insurance_base', 0) or 0)
        self.housing_base.value = str(rec.get('housing_fund_base', 0) or 0)
        rate_pct = int((rec.get('housing_fund_rate', 0.08) or 0.08) * 100)
        self.housing_rate.value = f"{rate_pct}%"
        self.weekend_days.value = str(rec.get('weekend_overtime_days', 0) or 0)
        self.holiday_days.value = str(rec.get('holiday_overtime_days', 0) or 0)
        self.tax_deductions.value = str(rec.get('tax_deductions', 0) or 0)
        self.critical_illness.value = str(rec.get('insurance_critical_illness', 10) or 10)
        self.pay_day.value = str(rec.get('pay_day', 15) or 15)
        log.info(f"工资Tab: 从 {ym} 恢复数据")

    def _save_settings(self):
        """保存全局设置"""
        set_setting("pay_day", self.pay_day.value)

    def _on_daily_toggle(self, e=None):
        self.daily_fields.visible = self.daily_mode_switch.value
        self.page.update()

    def _auto_calc_workdays(self, e=None):
        from holiday import get_workdays_in_month, get_workdays_between
        import datetime

        date_str = self._entry_date_field.value.strip()
        if not date_str:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("请先填写入职日期"),
                bgcolor=ft.Colors.AMBER_100,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        try:
            entry = datetime.date.fromisoformat(date_str)
        except ValueError:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("日期格式错误，请使用 YYYY-MM-DD"),
                bgcolor=ft.Colors.RED_100,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        month_days = get_workdays_in_month(entry.year, entry.month)
        if entry.month == 12:
            last_day = datetime.date(entry.year, 12, 31)
        else:
            last_day = datetime.date(entry.year, entry.month + 1, 1) - datetime.timedelta(days=1)

        actual_days = get_workdays_between(entry, last_day)

        self._month_days_field.value = str(month_days)
        self._actual_days_field.value = str(actual_days)
        self.page.update()

        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"✅ 当月工作日: {month_days}天, 出勤: {actual_days}天"),
            bgcolor=ft.Colors.GREEN_100,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📥 输入参数", size=16, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            ft.Row([
                                self.month_picker,
                                ft.VerticalDivider(width=1),
                                self.pay_day,
                            ]),
                            ft.Row([
                                self.basic_salary,
                                ft.VerticalDivider(width=1),
                                self.overtime_base,
                            ]),
                            ft.Row([
                                self.social_base,
                                ft.VerticalDivider(width=1),
                                self.housing_base,
                            ]),
                            ft.Row([
                                self.housing_rate,
                                ft.VerticalDivider(width=1),
                                self.critical_illness,
                            ]),
                            ft.Row([
                                self.weekend_days,
                                ft.VerticalDivider(width=1),
                                self.holiday_days,
                            ]),
                            ft.Row([
                                self.tax_deductions,
                            ]),
                            ft.Divider(height=1, color=ft.Colors.GREY_300),
                            self.daily_mode_switch,
                            self.daily_fields,
                            ft.Divider(),
                            ft.Row([
                                ft.Button(content=ft.Text("🧮 计算"),
                                          icon=ft.Icons.CALCULATE,
                                          on_click=self.on_calculate),
                                ft.Button(content=ft.Text("💾 保存"),
                                          icon=ft.Icons.SAVE,
                                          on_click=self.on_save),
                            ]),
                        ], expand=True, scroll=ft.ScrollMode.AUTO),
                        padding=ft.Padding(left=20, top=20, right=20, bottom=20),
                        expand=1,
                        border=ft.Border(
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                        ),
                        border_radius=10,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📊 计算结果", size=16, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self._mk_row("基本工资", self.result_income),
                            self._mk_row("日工资", self.result_daily),
                            self._mk_row("加班费合计", self.result_overtime),
                            ft.Divider(),
                            self._mk_row("应发工资", self.result_gross, True),
                            ft.Divider(),
                            ft.Text("— 五险一金 —", size=12, color=ft.Colors.GREY_500),
                            self._mk_row("  养老保险", self.result_pension),
                            self._mk_row("  医疗保险", self.result_medical),
                            self._mk_row("  失业保险", self.result_unemployment),
                            self._mk_row("  住房公积金", self.result_housing),
                            self._mk_row("  大病医疗保险", self.result_critical_illness),
                            self._mk_row("  五险一金合计", self.result_insurance_total, True),
                            ft.Divider(),
                            self._mk_row("应缴个税", self.result_tax),
                            ft.Divider(height=2, color=ft.Colors.GREEN_700),
                            self._mk_row("★ 实发工资", self.result_net, True),
                        ], expand=True, scroll=ft.ScrollMode.AUTO),
                        padding=ft.Padding(left=20, top=20, right=20, bottom=20),
                        expand=1,
                        border=ft.Border(
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                            ft.BorderSide(1, ft.Colors.GREY_300),
                        ),
                        border_radius=10,
                    ),
                ]),
            ], expand=True, scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding(left=15, top=15, right=15, bottom=15),
            expand=True,
        )

    def _mk_row(self, label, value_field, bold=False):
        return ft.Row([
            ft.Text(label, size=14 if not bold else 16,
                    weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL),
            ft.Container(expand=True),
            value_field,
        ])

    def on_calculate(self, e=None):
        try:
            rate_str = self.housing_rate.value.replace('%', '')
            rate = int(rate_str) / 100.0 if rate_str else 0.08

            basic = float(self.basic_salary.value or 0)
            ot_base = float(self.overtime_base.value or 0) or basic
            social = float(self.social_base.value or 0)
            housing = float(self.housing_base.value or 0)
            weekend = float(self.weekend_days.value or 0)
            holiday = float(self.holiday_days.value or 0)
            deductions = float(self.tax_deductions.value or 0)
            ci = float(self.critical_illness.value or 10)

            daily_mode = self.daily_mode_switch.value
            actual_days = 0
            month_days = 0
            if daily_mode:
                try:
                    actual_days = float(self._actual_days_field.value or 0)
                    month_days = float(self._month_days_field.value or 0)
                except ValueError:
                    pass

            # 累计计税：查询本年已有记录
            ym = self.month_picker.value.strip()
            from data.storage import get_cumulative_tax_info
            cum = get_cumulative_tax_info(ym)

            result = calc_all(
                basic_salary=basic,
                social_base=social,
                housing_base=housing,
                housing_rate=rate,
                weekend_days=weekend,
                holiday_days=holiday,
                tax_deductions=deductions,
                overtime_base=ot_base,
                daily_mode=daily_mode,
                actual_work_days=actual_days,
                month_work_days=month_days,
                critical_illness_amount=ci,
                cum_ytd_gross=cum['ytd_gross'],
                cum_ytd_insurance=cum['ytd_insurance'],
                cum_months=cum['months_count'],
                cum_ytd_deductions=cum['ytd_deductions'],
                cum_tax_paid=cum['ytd_tax'],
            )
            self.current_result = result

            self.result_income.value = f"¥{result['basic_salary']:,.2f}"
            self.result_daily.value = f"¥{result['daily_wage']:,.2f}"
            ot = result['overtime']
            self.result_overtime.value = f"¥{ot['total']:,.2f} (周末{ot['weekend_amount']:,.2f} + 节假日{ot['holiday_amount']:,.2f})"
            self.result_gross.value = f"¥{result['gross_salary']:,.2f}"

            ins = result['insurance']
            self.result_pension.value = f"¥{ins['pension']:,.2f}"
            self.result_medical.value = f"¥{ins['medical']:,.2f}"
            self.result_unemployment.value = f"¥{ins['unemployment']:,.2f}"
            self.result_housing.value = f"¥{ins['housing_fund']:,.2f}"
            self.result_critical_illness.value = f"¥{ins['critical_illness']:,.2f}"
            self.result_insurance_total.value = f"¥{ins['total']:,.2f}"
            self.result_tax.value = f"¥{result['tax']:,.2f}"
            self.result_net.value = f"¥{result['net_salary']:,.2f}"

            # 显示累计计税信息
            if cum['months_count'] > 0:
                tax_info = (f"（累计预扣: 年累计应税 ¥{cum['ytd_gross']+result['gross_salary']:,.2f}, "
                           f"本月预扣 ¥{result['tax']:,.2f}）")
            else:
                tax_info = ""
            self.result_tax.tooltip = tax_info or "单月计算（首月）"

            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"❌ 输入有误: {ex}"),
                bgcolor=ft.Colors.RED_100,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def on_save(self, e=None):
        self.on_calculate()
        if not self.current_result:
            return

        ym = self.month_picker.value.strip()
        if not ym or len(ym) != 7 or '-' not in ym:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("❌ 月份格式错误，请使用 YYYY-MM"),
                bgcolor=ft.Colors.RED_100,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        basic = float(self.basic_salary.value or 0)
        ot_base = float(self.overtime_base.value or 0) or basic

        # 按天模式信息
        daily_mode = 1 if self.daily_mode_switch.value else 0
        entry_date = self._entry_date_field.value.strip() if daily_mode else ""
        actual_days = float(self._actual_days_field.value or 0) if daily_mode else 0
        month_days = float(self._month_days_field.value or 0) if daily_mode else 0

        # 工作月份：如果按天模式有入职日期，工作月取入职月
        work_ym = ym
        if entry_date:
            try:
                ed = datetime.date.fromisoformat(entry_date)
                work_ym = ed.strftime("%Y-%m")
            except ValueError:
                pass

        from data.storage import save_monthly_record, get_opening_balance, reconcile_balances

        result = self.current_result
        net_salary = result['net_salary']
        opening = get_opening_balance(ym)
        closing = round(opening + net_salary, 2)

        log.info(f"保存工资记录: {ym}, 净收入={net_salary:.2f}, 期初={opening:.2f}")

        ot = result['overtime']
        ins = result['insurance']

        record = {
            'year_month': ym,
            'basic_salary': basic,
            'overtime_base': ot_base,
            'weekend_overtime_days': float(self.weekend_days.value or 0),
            'holiday_overtime_days': float(self.holiday_days.value or 0),
            'social_insurance_base': float(self.social_base.value or 0),
            'housing_fund_base': float(self.housing_base.value or 0),
            'housing_fund_rate': float(self.housing_rate.value.replace('%', '')) / 100,
            'tax_deductions': float(self.tax_deductions.value or 0),
            'daily_mode': daily_mode,
            'entry_date': entry_date,
            'actual_work_days': actual_days,
            'month_work_days': month_days,
            'pay_day': int(self.pay_day.value or 15),
            'work_year_month': work_ym,
            # 基准值
            'pension_rate': 0.08,
            'medical_rate': 0.02,
            'unemployment_rate': 0.005,
            'tax_free_threshold': 5000,
            # 计算结果
            'gross_salary': result['gross_salary'],
            'daily_wage': result['daily_wage'],
            'overtime_weekend': ot['weekend_amount'],
            'overtime_holiday': ot['holiday_amount'],
            'overtime_total': ot['total'],
            'insurance_pension': ins['pension'],
            'insurance_medical': ins['medical'],
            'insurance_unemployment': ins['unemployment'],
            'insurance_housing_fund': ins['housing_fund'],
            'insurance_critical_illness': ins['critical_illness'],
            'insurance_total': ins['total'],
            'tax_amount': result['tax'],
            'net_salary': net_salary,
            # 预算/实际（初始为 0）
            'actual_necessary': 0,
            'actual_flexible': 0,
            'actual_savings': 0,
            'budget_necessary': 0,
            'budget_flexible': 0,
            'budget_savings': 0,
            # 结余
            'opening_balance': opening,
            'closing_balance': closing,
            'total_available': round(opening + net_salary, 2),
            'total_expense': 0,
            'save_rate': 0,
            'notes': '',
        }
        save_monthly_record(record)
        self._save_settings()

        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"✅ {ym} 工资记录已保存"),
            bgcolor=ft.Colors.GREEN_100,
        )
        self.page.snack_bar.open = True
        self.page.update()
