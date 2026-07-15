---
change: salary-calculator
design-doc: docs/superpowers/specs/2026-07-15-salary-calculator-design.md
base-ref: 1b78142a9073ceda4d6b226815bbd933f4daff87
---

# 工资计算器 — 实施计划

## 任务分解

### Task 1: 核心计算引擎
- [ ] 1.1 创建 `core/__init__.py`
- [ ] 1.2 实现 `core/salary_calc.py`
  - `calc_daily_wage(basic_salary)` → 基本工资/21.75
  - `calc_overtime(daily_wage, weekend_days, holiday_days)` → 加班费
  - `calc_gross(basic_salary, overtime)` → 应发
- [ ] 1.3 实现 `core/tax.py`
  - `calc_insurance(base, rate)` → 五险一金明细
  - `calc_tax(taxable_income)` → 个税（分段累进）
  - `calc_net(gross, insurance, tax)` → 实发
- [ ] 1.4 实现 `core/budget.py`
  - `calc_allocation(net_income, scheme)` → 按方案分配
  - `validate(items, total)` → 校验和为0
- [ ] 1.5 单元测试 `tests/test_calc.py`（pytest）

### Task 2: SQLite 数据层
- [ ] 2.1 创建 `data/__init__.py`、`data/storage.py`
- [ ] 2.2 数据库初始化（建表：settings、monthly_records、budget_items）
- [ ] 2.3 实现 CRUD：save/load/list 月度记录
- [ ] 2.4 预算模板 CRUD + 预算细项 CRUD

### Task 3: Flet GUI — 工资计算 Tab
- [ ] 3.1 创建 `main.py` 入口 + `gui/__init__.py`
- [ ] 3.2 实现 `gui/app.py`（主窗口 + 3个Tab）
- [ ] 3.3 实现 `gui/salary_tab.py`
  - 输入区：基本工资、社保/公积金基数和比例、加班天数、专项附加
  - 结果区：加班费明细、五险一金、个税、实发工资（高亮）
  - 保存按钮

### Task 4: Flet GUI — 预算分配 Tab
- [ ] 4.1 实现 `gui/budget_tab.py`
  - 方案选择下拉框
  - 三类预算明细（可编辑）
  - 预算校验指示器

### Task 5: Flet GUI — 月度记录 Tab
- [ ] 5.1 实现 `gui/record_tab.py`
  - 月份选择
  - 实际收支表单
  - 月结余/累计结余/储蓄率
  - 历史记录表格

### Task 6: 收尾
- [ ] 6.1 `requirements.txt`
- [ ] 6.2 `build.bat`（Windows 打包脚本）
- [ ] 6.3 README.md
- [ ] 6.4 全流程手动测试
