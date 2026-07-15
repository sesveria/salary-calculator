---
comet_change: salary-calculator
role: technical-design
canonical_spec: openspec
---

# 工资计算器 — 设计文档

## 1. 技术栈

| 层面 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 用户环境已有，生态成熟 |
| GUI | Flet | Flutter 引擎，现代美观，跨平台（Win/Mac/Linux），纯 Python |
| 存储 | SQLite (sqlite3) | 零配置，单文件，Python 内置 |
| 打包 | `flet pack` | 生成单文件 .exe，Windows 双击运行 |
| 版本管理 | Git | 用户要求 |

## 2. 项目结构

```
~/salary-calculator/
├── main.py                 # 入口
├── config.py               # 全局配置
├── requirements.txt        # 依赖
├── build.bat               # Windows 打包
├── README.md
├── gui/
│   ├── __init__.py
│   ├── app.py              # 主窗口 + Tab 布局
│   ├── salary_tab.py       # 工资计算 Tab
│   ├── budget_tab.py       # 预算分配 Tab
│   └── record_tab.py       # 月度记录 Tab
├── core/
│   ├── __init__.py
│   ├── salary_calc.py      # 工资 + 加班计算
│   ├── tax.py              # 五险一金 + 个税
│   └── budget.py           # 预算分配逻辑
└── data/
    ├── __init__.py
    └── storage.py          # SQLite CRUD
```

## 3. 核心计算

### 3.1 工资计算 (salary_calc.py)

```
日工资 = 基本工资 / 21.75
周末加班费 = 日工资 × 2 × 周末加班天数
节假日加班费 = 日工资 × 3 × 节假日加班天数
应发工资 = 基本工资 + 周末加班费 + 节假日加班费
```

### 3.2 五险一金 + 个税 (tax.py)

```
养老保险 = 社保基数 × 8%
医疗保险 = 社保基数 × 2%
失业保险 = 社保基数 × 0.5%
住房公积金 = 公积金基数 × 公积金比例 (5%~12% 可配置)
五险一金合计 = 养老 + 医疗 + 失业 + 公积金

应纳税所得额 = 应发工资 - 五险一金 - 5000 - 专项附加扣除
个税 = 应纳税所得额 × 适用税率 - 速算扣除数 (≥0)

实发工资 = 应发工资 - 五险一金 - 个税
```

### 3.3 预算分配 (budget.py)

支持 50/30/20、631、333 三种预设方案 + 自定义：
- 给定税后收入和分配比例 → 计算出各项预算金额
- 预算校验：支出合计 + 储蓄 = 税后收入

## 4. 数据库设计

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE monthly_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year_month TEXT NOT NULL UNIQUE,
    basic_salary REAL DEFAULT 0,
    weekend_overtime_days REAL DEFAULT 1,
    holiday_overtime_days REAL DEFAULT 0,
    social_insurance_base REAL DEFAULT 0,
    housing_fund_base REAL DEFAULT 0,
    housing_fund_rate REAL DEFAULT 0.08,
    tax_deductions REAL DEFAULT 0,
    actual_necessary REAL DEFAULT 0,
    actual_flexible REAL DEFAULT 0,
    actual_savings REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE budget_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year_month TEXT NOT NULL,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    budget_amount REAL DEFAULT 0,
    actual_amount REAL DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);
```

## 5. GUI 设计

### 5.1 整体布局

```
┌──────────────────────────────────────────────┐
│  AppBar: 💰 工资计算器                         │
├──────────────────────────────────────────────┤
│                                              │
│  [Tab: 工资计算] [Tab: 预算分配] [Tab: 月度记录] │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │             Tab 内容区                   │  │
│  │                                         │  │
│  │  (卡片式布局，圆角，浅色主题)              │  │
│  │                                         │  │
│  └────────────────────────────────────────┘  │
│                                              │
├──────────────────────────────────────────────┤
│  BottomBar: 快捷操作 / 状态                   │
└──────────────────────────────────────────────┘
```

### 5.2 工资计算 Tab
- 左侧输入区：基本工资、社保基线、公积金基数和比例、加班天数、专项附加扣除
- 右侧结果区：加班费明细、五险一金明细、个税 → 实发工资（绿色高亮）
- 底部：保存按钮

### 5.3 预算分配 Tab
- 顶部：方案选择下拉框
- 中部：三个分类卡片（必要/弹性/储蓄），每类可添加/编辑细项
- 底部：预算校验条（绿色通过/红色超出）

### 5.4 月度记录 Tab
- 月份选择器
- 实际收支表单
- 月结余 + 累计结余 + 储蓄率（进度条）
- 历史记录表格

## 6. 数据流

```
用户操作 → Flet 控件事件 → Python 回调函数
  → core/ 模块计算 → data/storage.py 读写 SQLite
  → Flet UI 更新（set_state 刷新）
```

## 7. 状态管理

使用 Flet 内置状态管理：
- 每个 Tab 维护自己的 state（输入值、计算结果）
- 跨 Tab 共享数据通过 `app.state` 或重新查询 SQLite
- 保存后自动刷新相关 Tab

## 8. 测试策略

- core/ 模块：pytest 单元测试，覆盖边界条件
- gui/ 模块：手动测试，验证三个 Tab 交互流程
- 数据层：单元测试 CRUD 操作
- 打包：在 Windows 上测试 flet pack 生成的 .exe

## 9. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 加班默认值 | 全局配置（settings 表） | 用户设置一次，每月自动加载 |
| 个税算法 | 月度预扣（非累计） | 简化实现，月度误差小 |
| 预算细项 | 持久化到 budget_items 表 | 用户一次配置，每月复用 |
| GUI 框架 | Flet | 纯 Python + Flutter 引擎，无需前端经验 |
| 打包方式 | flet pack → .exe | 官方支持，一键打包 |
