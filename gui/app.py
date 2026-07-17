"""工资计算器 - 主窗口 (flet 0.86.0 compatible)"""
import flet as ft
from gui.salary_tab import SalaryTab
from gui.budget_tab import BudgetTab
from gui.record_tab import RecordTab
from data.storage import init_db
from holiday import is_library_available, get_library_version
import json
import subprocess
import sys
import threading
import os


def _check_update_async(page: ft.Page):
    """后台检查节假日库版本（非阻塞）"""

    def check():
        script = os.path.join(os.path.dirname(__file__), "..", "update_holidays.py")
        script = os.path.abspath(script)
        try:
            result = subprocess.run(
                [sys.executable, script, "--check-json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                data = json.loads(result.stdout)
                if data.get("error"):
                    return
                installed = data.get("installed")
                latest = data.get("latest")
                if installed and latest and installed != latest:
                    # 有更新 → 在主线程弹出通知
                    def notify():
                        page.snack_bar = ft.SnackBar(
                            content=ft.Row([
                                ft.Text(f"节假日库有更新: v{installed} → v{latest}"),
                                ft.Container(expand=True),
                                ft.Button(
                                    content=ft.Text("更新"),
                                    on_click=lambda e: _do_update(page, script),
                                ),
                            ]),
                            bgcolor=ft.Colors.BLUE_50,
                            duration=None,  # 不自动消失
                        )
                        page.snack_bar.open = True
                        page.update()
                    page.add(notify)  # 安全地调度到主线程
        except Exception:
            pass

    threading.Thread(target=check, daemon=True).start()


def _do_update(page: ft.Page, script: str):
    """执行更新"""
    if page.snack_bar:
        page.snack_bar.open = False
    page.snack_bar = ft.SnackBar(
        content=ft.Text("正在更新节假日数据..."),
        bgcolor=ft.Colors.AMBER_100,
    )
    page.snack_bar.open = True
    page.update()

    def upgrade():
        try:
            result = subprocess.run(
                [sys.executable, script, "--auto"],
                capture_output=True, text=True, timeout=120,
            )
            def done():
                if result.returncode in (0, 1):
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("✅ 节假日库已更新，重启应用生效"),
                        bgcolor=ft.Colors.GREEN_100,
                    )
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("⚠️ 更新失败，请手动运行: python update_holidays.py"),
                        bgcolor=ft.Colors.RED_100,
                    )
                page.snack_bar.open = True
                page.update()
            page.add(done)
        except Exception:
            pass

    threading.Thread(target=upgrade, daemon=True).start()


def _backfill_if_needed():
    """旧数据回填 + 结余重算"""
    from data.storage import reconcile_balances
    reconcile_balances()


def main(page: ft.Page):
    page.title = "💰 工资计算器"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1100
    page.window.height = 800
    page.window.min_width = 900
    page.window.min_height = 650
    page.padding = 0

    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ft.Colors.BLUE_700,
            primary_container=ft.Colors.BLUE_100,
            secondary=ft.Colors.GREEN_700,
            surface=ft.Colors.GREY_50,
        ),
    )

    init_db()

    # 迁移旧数据：补全全量快照字段
    _backfill_if_needed()

    # 后台检查节假日库更新（非阻塞，不影响启动速度）
    _check_update_async(page)

    salary_tab = SalaryTab(page)
    budget_tab = BudgetTab(page)
    record_tab = RecordTab(page)

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        content=ft.Column([
            ft.TabBar(
                tabs=[
                    ft.Tab(label="  \u5de5\u8d44\u8ba1\u7b97  ", icon=ft.Icons.CALCULATE),
                    ft.Tab(label="  \u9884\u7b97\u5206\u914d  ", icon=ft.Icons.ACCOUNT_BALANCE),
                    ft.Tab(label="  \u6708\u5ea6\u8bb0\u5f55  ", icon=ft.Icons.DATE_RANGE),
                ],
            ),
            ft.TabBarView(
                expand=True,
                controls=[
                    salary_tab.build(),
                    budget_tab.build(),
                    record_tab.build(),
                ],
            ),
        ], expand=True),
        length=3,
        expand=True,
    )

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ACCOUNT_BALANCE, size=28, color=ft.Colors.BLUE_700),
                        ft.Text("\u5de5\u8d44\u8ba1\u7b97\u5668", size=22,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                    ]),
                    padding=ft.Padding(left=20, top=10, right=0, bottom=5),
                ),
                ft.Divider(height=1),
                tabs,
            ]),
            expand=True,
        )
    )


if __name__ == '__main__':
    ft.app(target=main)
