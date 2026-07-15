# 工资计算器 — 任务清单

## 任务

### [x] Task 1: 项目初始化
- [x] Git 仓库初始化
- [x] Comet / OpenSpec 安装
- [x] 创建 change: salary-calculator
- [x] 创建 proposal.md、design.md、tasks.md

### [ ] Task 2: 核心计算引擎
- [ ] 实现 `core/salary_calc.py` — 基本工资 + 加班费计算
  - [ ] `calc_daily_wage(basic_salary)` → 日工资 = 基本工资 / 21.75
  - [ ] `calc_overtime(daily_wage, weekend_days, holiday_days)` → 周末2倍/节假日3倍
  - [ ] `calc_gross(basic_salary, overtime_amount)` → 应发工资
- [ ] 实现 `core/tax.py` — 五险一金 + 个税
  - [ ] `calc_insurance(social_base, housing_base, housing_rate)` → 五险一金明细
  - [ ] `calc_tax(taxable_income)` → 个税（累计预扣法）
  - [ ] `calc_net(gross_salary, insurance_total, tax)` → 实发工资
- [ ] 实现 `core/budget.py` — 预算分配
  - [ ] 50/30/20、631、333 等分配方案
  - [ ] `allocate(net_income, scheme)` → 各项预算金额
  - [ ] `validate(budget_items, net_income)` → 预算校验

### [ ] Task 3: 数据层
- [ ] 实现 `data/storage.py`
  - [ ] SQLite 数据库初始化（建表）
  - [ ] `save_monthly_record(data)` → 保存月度记录
  - [ ] `get_monthly_record(year_month)` → 查询
  - [ ] `list_all_records()` → 历史列表
  - [ ] `save_budget_template(template)` → 预算模板 CRUD
  - [ ] `save_budget_items(items)` → 预算细项 CRUD

### [ ] Task 4: Flet GUI — 工资计算 Tab
- [ ] 实现 `gui/app.py` — 主窗口 + Tab 布局
- [ ] 实现 `gui/salary_tab.py`
  - [ ] 基本工资输入（TextField）
  - [ ] 社保/公积金基数（TextField）
  - [ ] 周末/节假日加班天数（Dropdown + 默认1天）
  - [ ] 专项附加扣除（可展开）
  - [ ] 结果展示区（卡片式布局）
    - [ ] 加班费明细
    - [ ] 五险一金明细
    - [ ] 个税
    - [ ] 实发工资（高亮）
  - [ ] 保存按钮 → SQLite

### [ ] Task 5: Flet GUI — 预算分配 Tab
- [ ] 实现 `gui/budget_tab.py`
  - [ ] 分配方案选择（Dropdown: 50/30/20 / 631 / 333 / 自定义）
  - [ ] 必要支出明细编辑（可增删行）
  - [ ] 弹性支出明细编辑
  - [ ] 储蓄投资明细编辑
  - [ ] 预算校验指示器（绿/红）
  - [ ] 保存/加载模板

### [ ] Task 6: Flet GUI — 月度记录 Tab
- [ ] 实现 `gui/record_tab.py`
  - [ ] 月份选择器
  - [ ] 实际收支表单
  - [ ] 月结余 / 累计结余展示
  - [ ] 储蓄率展示（进度条/环形图）
  - [ ] 历史记录列表（DataTable）
  - [ ] 年度汇总

### [ ] Task 7: 打包与分发
- [ ] `requirements.txt` 整理
- [ ] `build.bat` Windows 打包脚本
- [ ] `flet pack` 测试
- [ ] README.md 编写

### [ ] Task 8: 测试与验证
- [ ] 核心计算单元测试（pytest）
  - [ ] 工资计算测试
  - [ ] 个税计算测试
  - [ ] 预算分配测试
- [ ] GUI 手动测试（三个 Tab 流程）
- [ ] Windows 打包测试
