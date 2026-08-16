"""年度汇总 Tab — 按年聚合收入、税、储蓄、结余"""
import datetime
import flet as ft
from data.storage import list_records_asc, get_initial_balance
from gui.logger import get_logger

log = get_logger()


def _aggregate_year(year: str) -> dict:
    """聚合指定年份的所有月度记录

    Returns:
        {
            'year': str, 'months': int,
            'gross': float, 'insurance': float, 'tax': float,
            'net': float, 'extra': float,
            'expense': float, 'savings': float,
            'save_rate': float, 'closing': float,
            'monthly': [ {ym, net, extra, sav, expense}, ... ]
        }
    """
    records = list_records_asc()
    agg = {
        'year': year, 'months': 0,
        'gross': 0.0, 'insurance': 0.0, 'tax': 0.0,
        'net': 0.0, 'extra': 0.0,
        'expense': 0.0, 'savings': 0.0,
        'save_rate': 0.0, 'closing': 0.0,
        'monthly': [],
    }
    for rec in records:
        if not rec['year_month'].startswith(year):
            continue
        gross = rec.get('gross_salary', 0) or 0
        insurance = rec.get('insurance_total', 0) or 0
        tax = rec.get('tax_amount', 0) or 0
        net = rec.get('net_salary', 0) or 0
        extra = rec.get('extra_income', 0) or 0
        nec = rec.get('actual_necessary', 0) or 0
        flex = rec.get('actual_flexible', 0) or 0
        sav = rec.get('actual_savings', 0) or 0
        expense = nec + flex + sav

        agg['months'] += 1
        agg['gross'] += gross
        agg['insurance'] += insurance
        agg['tax'] += tax
        agg['net'] += net
        agg['extra'] += extra
        agg['expense'] += expense
        agg['savings'] += sav
        agg['closing'] = rec.get('closing_balance', 0) or 0  # 最后一条覆盖
        agg['monthly'].append({
            'ym': rec['year_month'],
            'net': net, 'extra': extra, 'sav': sav, 'expense': expense,
        })

    if agg['months'] > 0:
        total_income = agg['net'] + agg['extra']
        agg['save_rate'] = round(agg['savings'] / total_income * 100, 2) if total_income > 0 else 0
    return agg


class SummaryTab:
    def __init__(self, page: ft.Page):
        self.page = page
        now = datetime.datetime.now()
        current_year = now.strftime("%Y")

        # 年份选择
        self.year_selector = ft.Dropdown(
            label="选择年份", value=current_year, width=160,
            options=[],
            on_select=self._on_year_changed,
        )

        # 指标显示
        self.stat_months = ft.Text("—", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
        self.stat_gross = ft.Text("—", size=20, weight=ft.FontWeight.BOLD)
        self.stat_insurance = ft.Text("—", size=20, weight=ft.FontWeight.BOLD)
        self.stat_tax = ft.Text("—", size=20, weight=ft.FontWeight.BOLD)
        self.stat_net = ft.Text("—", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.stat_extra = ft.Text("—", size=18)
        self.stat_expense = ft.Text("—", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)
        self.stat_savings = ft.Text("—", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.stat_save_rate = ft.Text("—", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
        self.stat_closing = ft.Text("—", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700)

        # 月度明细表
        self.detail_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("月份", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("实发工资", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("额外收入", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("总支出", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("储蓄", weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=[],
            expand=True,
        )

        self._load_years(current_year)

    def _load_years(self, current_year: str):
        """从数据库加载所有年份到选择器"""
        records = list_records_asc()
        years = sorted({r['year_month'][:4] for r in records}, reverse=True)
        if current_year not in years:
            years.insert(0, current_year)
        if not years:
            years = [current_year]
        self.year_selector.options = [ft.dropdown.Option(y) for y in years]

    def _on_year_changed(self, e=None):
        year = self.year_selector.value
        if not year:
            return
        self.refresh(year)

    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📈 年度汇总", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self.year_selector,
                    ft.Button(content=ft.Text("🔄 刷新"), icon=ft.Icons.REFRESH,
                              on_click=self.on_refresh),
                ]),
                ft.Divider(),
                # 指标卡片
                ft.Row([
                    self._stat_card("📅 记录月数", self.stat_months, ft.Colors.BLUE_700),
                    self._stat_card("💰 应发合计", self.stat_gross, ft.Colors.GREY_700),
                    self._stat_card("🛡️ 五险一金", self.stat_insurance, ft.Colors.ORANGE_700),
                    self._stat_card("🧾 个税合计", self.stat_tax, ft.Colors.RED_700),
                ]),
                ft.Row([
                    self._stat_card("💵 实发合计", self.stat_net, ft.Colors.GREEN_700),
                    self._stat_card("➕ 额外收入", self.stat_extra, ft.Colors.BLUE_700),
                    self._stat_card("💸 总支出", self.stat_expense, ft.Colors.RED_700),
                    self._stat_card("🏦 储蓄合计", self.stat_savings, ft.Colors.GREEN_700),
                ]),
                ft.Row([
                    self._stat_card("📊 储蓄率", self.stat_save_rate, ft.Colors.BLUE_700),
                    self._stat_card("🔚 年末结余", self.stat_closing, ft.Colors.PURPLE_700),
                ]),
                ft.Divider(),
                ft.Text("月度明细", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column([self.detail_table], scroll=ft.ScrollMode.AUTO),
                    expand=True,
                ),
            ], expand=True, scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding(left=15, top=15, right=15, bottom=15),
            expand=True,
        )

    def _stat_card(self, label, value_field, color):
        return ft.Container(
            content=ft.Column([
                ft.Text(label, size=12, color=ft.Colors.GREY_600),
                value_field,
            ], spacing=4),
            bgcolor=ft.Colors.GREY_50,
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            border_radius=8,
            expand=True,
            border=ft.Border(
                ft.BorderSide(1, ft.Colors.GREY_300),
                ft.BorderSide(1, ft.Colors.GREY_300),
                ft.BorderSide(1, ft.Colors.GREY_300),
                ft.BorderSide(1, ft.Colors.GREY_300),
            ),
        )

    def refresh(self, year: str = None):
        """刷新指定年份的汇总（默认当前选中）"""
        year = year or self.year_selector.value
        if not year:
            return
        agg = _aggregate_year(year)

        self.stat_months.value = f"{agg['months']} 个月"
        self.stat_gross.value = f"¥{agg['gross']:,.0f}"
        self.stat_insurance.value = f"¥{agg['insurance']:,.0f}"
        self.stat_tax.value = f"¥{agg['tax']:,.0f}"
        self.stat_net.value = f"¥{agg['net']:,.0f}"
        self.stat_extra.value = f"¥{agg['extra']:,.0f}"
        self.stat_expense.value = f"¥{agg['expense']:,.0f}"
        self.stat_savings.value = f"¥{agg['savings']:,.0f}"
        self.stat_save_rate.value = f"{agg['save_rate']}%"
        self.stat_closing.value = f"¥{agg['closing']:,.0f}"

        # 月度明细表
        rows = []
        for m in agg['monthly']:
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(m['ym'], size=13)),
                ft.DataCell(ft.Text(f"¥{m['net']:,.0f}", size=13)),
                ft.DataCell(ft.Text(f"¥{m['extra']:,.0f}", size=13)),
                ft.DataCell(ft.Text(f"¥{m['expense']:,.0f}", size=13)),
                ft.DataCell(ft.Text(f"¥{m['sav']:,.0f}", size=13)),
            ]))
        self.detail_table.rows = rows
        log.info(f"年度汇总刷新: {year}, {agg['months']} 个月")
        self.page.update()

    def on_refresh(self, e=None):
        self._load_years(self.year_selector.value or datetime.datetime.now().strftime("%Y"))
        self.refresh()
