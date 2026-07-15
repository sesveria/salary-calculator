# Comet Design Handoff

- Change: salary-calculator
- Phase: design
- Mode: compact
- Context hash: 81eb704e95123f9a0a49c2010ccc5efdf82d6151aeefd5b6f1df077bee97df0a

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/salary-calculator/proposal.md

- Source: openspec/changes/salary-calculator/proposal.md
- Lines: 1-48
- SHA256: edc7ae5594f1083830ac03d0f46ebd37c862d21d0e0a63308ac1e28cca20c084

```md
# 工资计算器 (Salary Calculator)

## 问题背景

用户目前用 Excel 表格管理工资计算和预算分配，但存在以下痛点：

1. **Excel 公式易出错** — 跨表引用、列引用错误导致结果不准
2. **加班计算复杂** — 周末2倍工资（按21.75天折算日工资）、节假日3倍，Excel 难以清晰表达
3. **数据散乱** — 每月需要手动复制粘贴，缺乏统一的数据管理
4. **界面不够直观** — Excel 的表格形式对非技术用户不够友好

## 目标

开发一个本地桌面工资计算应用：

- **工资计算**：基本工资 + 加班费（周末2倍、节假日3倍）
- **五险一金 + 个税**：自动计算扣款，到手一目了然
- **预算分配**：支持 50/30/20、631、333 等多种方案
- **月度跟踪**：记录每月实际收支，统计结余和储蓄率
- **本地存储**：数据持久化，随时回溯历史
- **跨平台**：在 Windows 上也能运行（打包为 .exe）
- **美观界面**：现代化 UI 设计

## 范围

### 包含
- 核心工资计算引擎（基本工资 + 加班）
- 五险一金 + 个税计算
- 预算分配模块
- 月度收支记录
- SQLite 本地数据存储
- Flet 图形界面
- Windows 打包（.exe）
- Git 版本管理

### 不包含
- Web 版本
- 多用户/权限管理
- 联网同步/云存储
- 导出发票/工资单 PDF
- 银行 API 对接

## 角色与用户场景

### 主要用户：上班族
- 每月发薪后记录工资和各项支出
- 查看预算执行情况，调整消费习惯
- 追踪储蓄进度和财务目标
```

## openspec/changes/salary-calculator/design.md

- Source: openspec/changes/salary-calculator/design.md
- Lines: 1-215
- SHA256: 02140ebf9e90d2f595aaa172935190926d53774df805be3d0d841c5ee004b253

[TRUNCATED]

```md
# 工资计算器 — 技术设计

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    Flet GUI                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ 工资Tab  │  │ 预算Tab  │  │ 月度记录Tab      │   │
│  │ 输入参数  │  │ 分配方案  │  │ 实际收支/结余    │   │
│  │ 展示结果  │  │ 预算明细  │  │ 年度汇总        │   │
│  └────┬─────┘  └────┬─────┘  └───────┬──────────┘   │
│       │              │                │              │
└───────┼──────────────┼────────────────┼──────────────┘
        │              │                │
        ▼              ▼                ▼
┌─────────────────────────────────────────────────────┐
│              Python 核心逻辑层                       │
│                                                     │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────┐  │
│  │ salary_calc  │  │   tax      │  │   budget    │  │
│  │ · 基本工资    │  │ · 五险一金  │  │ · 分配方案   │  │
│  │ · 加班费     │  │ · 个税     │  │ · 预算校验   │  │
│  │ · 21.75天    │  │ · 累计预扣  │  │ · 结余跟踪   │  │
│  └──────┬───────┘  └─────┬──────┘  └──────┬──────┘  │
│         │                │                 │         │
└─────────┼────────────────┼─────────────────┼─────────┘
          │                │                 │
          ▼                ▼                 ▼
┌─────────────────────────────────────────────────────┐
│                  Data Layer (SQLite)                 │
│                                                     │
│  Tables:                                             │
│  · monthly_records  — 每月工资/支出记录              │
│  · budget_templates — 预算方案模板                   │
│  · settings         — 用户偏好/参数                  │
└─────────────────────────────────────────────────────┘
```

## 详细设计

### 1. GUI 层 (Flet)

使用 Flet 构建三 Tab 界面：

```
AppBar: 💰 工资计算器
├── Tab 1: 工资计算
│   ├── 输入区（卡片）
│   │   ├── 基本工资输入框
│   │   ├── 社保基数 + 公积金基数
│   │   ├── 周末加班天数（默认1天）
│   │   ├── 节假日加班天数（默认0）
│   │   └── 专项附加扣除
│   ├── 结果区（卡片）
│   │   ├── 加班费明细（周末/节假日分开）
│   │   ├── 应发工资
│   │   ├── 五险一金扣款
│   │   ├── 个税
│   │   └── 实发到手 ← 高亮
│   └── 保存按钮
│
├── Tab 2: 预算分配
│   ├── 分配方案选择（下拉框：50/30/20 / 631 / 333 / 自定义）
│   ├── 预算明细编辑（可展开列表）
│   │   ├── 必要支出（房租/水电/伙食/交通…）
│   │   ├── 弹性支出（外食/购物/娱乐…）
│   │   └── 储蓄投资（应急金/保险/基金…）
│   └── 预算校验（自动检查 支出+储蓄=收入）
│
├── Tab 3: 月度记录
│   ├── 月份选择
│   ├── 实际收入/支出填入
│   ├── 月结余 / 累计结余
│   ├── 储蓄率
│   └── 历史记录列表

└── BottomBar: 状态栏 / 年度汇总
```

```

Full source: openspec/changes/salary-calculator/design.md

## openspec/changes/salary-calculator/tasks.md

- Source: openspec/changes/salary-calculator/tasks.md
- Lines: 1-78
- SHA256: 3d47fc01e98581995ce8f086a59be38c77c54a5777fbeab77964006ff5f3efd3

```md
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
```

