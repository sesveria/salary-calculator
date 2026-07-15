"""工资计算器 - 主窗口"""
import flet as ft
from gui.salary_tab import SalaryTab
from gui.budget_tab import BudgetTab
from gui.record_tab import RecordTab
from data.storage import init_db


def main(page: ft.Page):
    page.title = "💰 工资计算器"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1000
    page.window.height = 750
    page.window.min_width = 800
    page.window.min_height = 600
    page.padding = 0
    
    # 主题色
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ft.Colors.BLUE_700,
            primary_container=ft.Colors.BLUE_100,
            secondary=ft.Colors.GREEN_700,
            surface=ft.Colors.GREY_50,
        ),
    )
    
    # 初始化数据库
    init_db()
    
    salary_tab = SalaryTab(page)
    budget_tab = BudgetTab(page)
    record_tab = RecordTab(page)
    
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="  工资计算  ",
                icon=ft.icons.CALCULATE,
                content=salary_tab.build(),
            ),
            ft.Tab(
                text="  预算分配  ",
                icon=ft.icons.ACCOUNT_BALANCE_WALLET,
                content=budget_tab.build(),
            ),
            ft.Tab(
                text="  月度记录  ",
                icon=ft.icons.DATE_RANGE,
                content=record_tab.build(),
            ),
        ],
        expand=True,
    )
    
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.ACCOUNT_BALANCE, size=28, color=ft.Colors.BLUE_700),
                        ft.Text("工资计算器", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                    ]),
                    padding=ft.padding.only(left=20, top=10, bottom=5),
                ),
                ft.Divider(height=1),
                tabs,
            ]),
            expand=True,
        )
    )


if __name__ == '__main__':
    ft.app(target=main)
