---
change: salary-calculator
design-doc: docs/superpowers/specs/2026-07-15-salary-calculator-design.md
base-ref: 1b78142a9073ceda4d6b226815bbd933f4daff87
---

# 工资计算器 — 实施计划

## 任务分解

### Task 1: 核心计算引擎
- [x] 1.1 创建 `core/__init__.py`
- [x] 1.2 实现 `core/salary_calc.py`
- [x] 1.3 实现 `core/tax.py`
- [x] 1.4 实现 `core/budget.py`
- [x] 1.5 单元测试 `tests/test_calc.py`（pytest 19 passed）

### Task 2: SQLite 数据层
- [x] 2.1 创建 `data/__init__.py`、`data/storage.py`
- [x] 2.2 数据库初始化（建表：settings、monthly_records、budget_items）
- [x] 2.3 实现 CRUD：save/load/list 月度记录
- [x] 2.4 预算模板 CRUD + 预算细项 CRUD

### Task 3: Flet GUI — 工资计算 Tab
- [x] 3.1 创建 `main.py` 入口 + `gui/__init__.py`
- [x] 3.2 实现 `gui/app.py`（主窗口 + 3个Tab）
- [x] 3.3 实现 `gui/salary_tab.py`

### Task 4: Flet GUI — 预算分配 Tab
- [x] 4.1 实现 `gui/budget_tab.py`

### Task 5: Flet GUI — 月度记录 Tab
- [x] 5.1 实现 `gui/record_tab.py`

### Task 6: 收尾
- [x] 6.1 `requirements.txt`
- [x] 6.2 `build.bat`（Windows 打包脚本）
- [x] 6.3 README.md
- [x] 6.4 全流程手动测试
