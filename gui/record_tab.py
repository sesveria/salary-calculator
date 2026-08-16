"""月度记录 Tab — 选月份 → 加载 → 编辑 → 保存"""

import datetime
import os
import flet as ft
from data.storage import (
    list_records, get_monthly_record, save_monthly_record, delete_record,
    get_budget_items, reconcile_balances, export_records_csv,
)
from core.budget import CATEGORY_LABELS
from gui.logger import get_logger

log = get_logger()


class RecordTab:
    def __init__(self, page: ft.Page):
        self.page = page

        now = datetime.datetime.now()
        default_ym = now.strftime("%Y-%m")

        # 月份选择（编辑区用）
        self.edit_month_selector = ft.Dropdown(
            label="选择月份", value=default_ym, width=180,
            options=[],
            on_select=self._on_edit_month_changed,
        )

        # ---- 编辑区字段（仅实际支出） ----
        self.edit_actual_necessary = ft.TextField(label="实际必要支出", value="0", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        self.edit_actual_flexible = ft.TextField(label="实际弹性支出", value="0", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        self.edit_actual_savings = ft.TextField(label="实际储蓄", value="0", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        self.edit_notes = ft.TextField(label="备注", value="", width=300, multiline=True, min_lines=1, max_lines=3)

        self._current_edit_ym = ""

        # 历史记录表（只读，无操作按钮）
        self.table = ft.DataTable(
            column_spacing=8,
            columns=[
                ft.DataColumn(ft.Text("月份", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("税前", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("税后", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("期初", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("总可用", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("支出", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("月末", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("储蓄率", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.Border(
                ft.BorderSide(1, ft.Colors.GREY_300), ft.BorderSide(1, ft.Colors.GREY_300),
                ft.BorderSide(1, ft.Colors.GREY_300), ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            vertical_lines=ft.BorderSide(1, ft.Colors.GREY_200),
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
            heading_row_color=ft.Colors.BLUE_50,
            expand=True,
        )

        # 汇总
        self.summary_net = ft.Text("¥0", size=18, weight=ft.FontWeight.BOLD)
        self.summary_save = ft.Text("¥0", size=18, weight=ft.FontWeight.BOLD)
        self.summary_rate = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.summary_closing = ft.Text("¥0", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
        self.summary_consumption = ft.Text("¥0", size=16)

    # ──── 构建 UI ────

    def build(self):
        return ft.Container(
            content=ft.Column([
                # 顶栏
                ft.Row([
                    ft.Text("📅 月度记录", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Button(content=ft.Text("📤 导出CSV"), icon=ft.Icons.DOWNLOAD,
                              on_click=self._export_csv),
                    ft.Button(content=ft.Text("🔄 刷新"), icon=ft.Icons.REFRESH, on_click=self.refresh),
                ]),
                ft.Divider(),

                # 编辑区
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            self.edit_month_selector,
                            ft.Button(content=ft.Text("💾 保存"), icon=ft.Icons.SAVE, on_click=self._save_edit),
                        ]),
                        ft.Divider(height=1, color=ft.Colors.GREY_300),
                        ft.Text("实际支出（修改后点保存）", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                        ft.ResponsiveRow([
                            self.edit_actual_necessary, self.edit_actual_flexible,
                            self.edit_actual_savings, self.edit_notes,
                        ], run_spacing=5),
                    ]),
                    padding=ft.Padding(left=10, top=10, right=10, bottom=10),
                    border=ft.Border(
                        ft.BorderSide(1, ft.Colors.BLUE_200), ft.BorderSide(1, ft.Colors.BLUE_200),
                        ft.BorderSide(1, ft.Colors.BLUE_200), ft.BorderSide(1, ft.Colors.BLUE_200),
                    ),
                    border_radius=8,
                    bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Divider(),

                # 资金概览
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 资金概览（累计）", size=14, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.ResponsiveRow([
                            ft.Column([ft.Text("税后收入", size=11), self.summary_net]),
                            ft.Column([ft.Text("消费支出", size=11), self.summary_consumption]),
                            ft.Column([ft.Text("储蓄投资", size=11), self.summary_save]),
                            ft.Column([ft.Text("储蓄率", size=11), self.summary_rate]),
                            ft.VerticalDivider(),
                            ft.Column([
                                ft.Text("💰 月末余额", size=11, color=ft.Colors.BLUE_700),
                                self.summary_closing,
                            ]),
                        ], run_spacing=8),
                    ]),
                    padding=ft.Padding(left=10, top=10, right=10, bottom=10),
                    border=ft.Border(
                        ft.BorderSide(1, ft.Colors.BLUE_200), ft.BorderSide(1, ft.Colors.BLUE_200),
                        ft.BorderSide(1, ft.Colors.BLUE_200), ft.BorderSide(1, ft.Colors.BLUE_200),
                    ),
                    border_radius=8,
                    bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Divider(),

                # 历史记录表（只读）
                ft.Text("历史记录", size=14, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "💡 在上方选择月份 → 加载数据 → 修改 → 保存",
                    size=11, color=ft.Colors.GREY_500,
                ),
                ft.Container(
                    content=ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
                    expand=True,
                    border=ft.Border(
                        ft.BorderSide(1, ft.Colors.GREY_200), ft.BorderSide(1, ft.Colors.GREY_200),
                        ft.BorderSide(1, ft.Colors.GREY_200), ft.BorderSide(1, ft.Colors.GREY_200),
                    ),
                    border_radius=8,
                ),
            ], scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding(left=15, top=15, right=15, bottom=15),
            expand=True,
        )

    # ──── 月份选择 → 加载数据 ────

    def _on_edit_month_changed(self, e=None):
        """编辑区的月份下拉框变化 → 加载该月数据"""
        ym = self.edit_month_selector.value
        if not ym:
            return
        rec = get_monthly_record(ym)
        if rec:
            self._load_record_to_form(rec)
            self._current_edit_ym = ym
            log.info(f"记录Tab: 加载 {ym} 数据")
        else:
            self._clear_form()
            self._current_edit_ym = ""

    def _load_record_to_form(self, rec: dict):
        """将一条月度记录的实际支出加载到编辑表单"""
        self.edit_actual_necessary.value = str(rec.get('actual_necessary', 0) or 0)
        self.edit_actual_flexible.value = str(rec.get('actual_flexible', 0) or 0)
        self.edit_actual_savings.value = str(rec.get('actual_savings', 0) or 0)
        self.edit_notes.value = rec.get('notes', '') or ''
        self.page.update()

    def _clear_form(self):
        """清空编辑表单"""
        self.edit_actual_necessary.value = "0"
        self.edit_actual_flexible.value = "0"
        self.edit_actual_savings.value = "0"
        self.edit_notes.value = ""
        self.page.update()

    # ──── 保存 ────

    def _save_edit(self, e=None):
        """保存当前编辑的月份实际支出"""
        ym = self.edit_month_selector.value
        if not ym:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("请先选择月份"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        rec = get_monthly_record(ym)
        if not rec:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"未找到 {ym} 的记录，请先在工资Tab保存"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        def _f(v):
            try:
                return float(v or 0)
            except ValueError:
                return 0

        rec['actual_necessary'] = _f(self.edit_actual_necessary.value)
        rec['actual_flexible'] = _f(self.edit_actual_flexible.value)
        rec['actual_savings'] = _f(self.edit_actual_savings.value)
        rec['notes'] = self.edit_notes.value or ''

        save_monthly_record(dict(rec))
        reconcile_balances()
        self.refresh()

        self.page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ {ym} 实际支出已更新"), bgcolor=ft.Colors.GREEN_100)
        self.page.snack_bar.open = True
        self.page.update()
        log.info(f"记录保存: {ym}")

    # ──── 导出 CSV ────

    def _export_csv(self, e=None):
        """导出全部月度记录为 CSV 到项目 exports/ 目录"""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            export_dir = os.path.join(project_root, 'exports')
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, f"records-{datetime.datetime.now().strftime('%Y%m%d')}.csv")

            count = export_records_csv(filepath)
            if count == 0:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("⚠️ 暂无记录可导出，请先保存工资数据"),
                    bgcolor=ft.Colors.AMBER_100,
                )
            else:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"✅ 已导出 {count} 条记录 → {filepath}"),
                    bgcolor=ft.Colors.GREEN_100,
                )
            self.page.snack_bar.open = True
            self.page.update()
            log.info(f"CSV 导出: {filepath} ({count} 条)")
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"❌ 导出失败: {ex}"),
                bgcolor=ft.Colors.RED_100,
            )
            self.page.snack_bar.open = True
            self.page.update()

    # ──── 删除 ────

    def _confirm_delete(self, e=None):
        """确认后删除当前选中月份的记录"""
        ym = self.edit_month_selector.value
        if not ym:
            return
        rec = get_monthly_record(ym)
        if not rec:
            return

        def do_delete(e):
            delete_record(ym)
            # 删除中间月份后必须重建结余链，否则后续月份期初/期末余额全错
            reconcile_balances()
            if self._confirm_dialog:
                self._confirm_dialog.open = False
            self.refresh()
            self._clear_form()
            self._current_edit_ym = ""
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"🗑️ {ym} 已删除"), bgcolor=ft.Colors.RED_100)
            self.page.snack_bar.open = True
            self.page.update()
            log.info(f"记录删除: {ym}")

        def cancel(e):
            if self._confirm_dialog:
                self._confirm_dialog.open = False
            self.page.update()

        self._confirm_dialog = ft.AlertDialog(
            title=ft.Text(f"确认删除 {ym}？"),
            content=ft.Text("该操作不可恢复，关联的预算细项也会一并删除。"),
            actions=[
                ft.TextButton("取消", on_click=cancel),
                ft.FilledButton("🗑️ 确认删除", on_click=do_delete, color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_700),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = self._confirm_dialog
        self._confirm_dialog.open = True
        self.page.update()

    # ──── 刷新 ────

    def refresh(self, e=None):
        """刷新月份下拉框、历史表和资金概览"""
        records = list_records()
        rows_data = []
        total_net = 0
        total_consumption = 0
        total_save = 0

        # 刷新编辑区的月份下拉框
        options = []
        for r in records:
            ym = r['year_month']
            options.append(ft.dropdown.Option(ym, f"{ym} (¥{r.get('net_salary', 0):,.0f})"))
        if not options:
            options.append(ft.dropdown.Option(datetime.datetime.now().strftime("%Y-%m")))
        self.edit_month_selector.options = options

        from core.tax import calc_all

        log.info(f"记录Tab刷新: {len(records)} 条记录")

        for rec in records:
            ym_val = rec['year_month']
            # 所有值直接从数据库读取（保存时已算好）
            gross = rec.get('gross_salary', 0) or 0
            net = rec.get('net_salary', 0) or 0
            total_net += net
            nec = rec.get('actual_necessary', 0) or 0
            flex = rec.get('actual_flexible', 0) or 0
            savings = rec.get('actual_savings', 0) or 0
            total_save += savings
            total_consumption += (nec + flex)
            opening = rec.get('opening_balance', 0) or 0
            closing = rec.get('closing_balance', 0) or 0
            total_available = rec.get('total_available', 0) or round(opening + net, 2)
            total_expense = rec.get('total_expense', 0) or (nec + flex + savings)
            save_rate = rec.get('save_rate', 0) or 0
            rows_data.append((ym_val, gross, net, opening, total_available, total_expense, closing, save_rate))

        # 构建只读历史表
        table_rows = []
        for ym, g, n, op, av, ta, cl, sr in rows_data:
            table_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(ym, size=13)),
                ft.DataCell(ft.Text(f"¥{g:,.0f}", size=13)),
                ft.DataCell(ft.Text(f"¥{n:,.0f}", size=13)),
                ft.DataCell(ft.Text(f"¥{op:,.0f}", size=13)),
                ft.DataCell(ft.Text(f"¥{av:,.0f}", size=13)),
                ft.DataCell(ft.Text(f"¥{ta:,.0f}", size=13)),
                ft.DataCell(ft.Text(f"¥{cl:,.0f}", size=13, color=ft.Colors.BLUE_700 if cl >= 0 else ft.Colors.RED_700)),
                ft.DataCell(ft.Text(f"{sr:.1f}%", size=13)),
            ]))
        self.table.rows = table_rows

        # 资金概览
        self.summary_net.value = f"¥{total_net:,.0f}"
        self.summary_consumption.value = f"¥{total_consumption:,.0f}"
        self.summary_save.value = f"¥{total_save:,.0f}"
        self.summary_rate.value = f"{total_save / total_net * 100:.1f}%" if total_net > 0 else "0%"
        self.summary_closing.value = f"¥{rows_data[0][6]:,.0f}" if rows_data else "¥0"

        self.page.update()

        # 刷新后自动加载当前选中月份的数据
        self._on_edit_month_changed()
