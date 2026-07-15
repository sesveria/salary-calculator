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

### 2. 核心计算逻辑

#### 工资计算

```
日工资 = 基本工资 ÷ 21.75

周末加班费 = 日工资 × 2 × 周末加班天数
节假日加班费 = 日工资 × 3 × 节假日加班天数

应发工资 = 基本工资 + 周末加班费 + 节假日加班费
```

#### 五险一金

```
养老保险 = 社保基数 × 8%
医疗保险 = 社保基数 × 2%
失业保险 = 社保基数 × 0.5%
公积金   = 公积金基数 × (5%~12%)
五险一金合计 = 养老 + 医疗 + 失业 + 公积金
```

#### 个税（累计预扣法）

```
应纳税所得额 = 应发工资 - 五险一金 - 5000 - 专项附加扣除

税率（月度）：
  ≤3000    → 3%
  ≤12000   → 10%  (速算扣除 210)
  ≤25000   → 20%  (速算扣除 1410)
  ≤35000   → 25%  (速算扣除 2660)
  ≤55000   → 30%  (速算扣除 4410)
  ≤80000   → 35%  (速算扣除 7160)
  >80000   → 45%  (速算扣除 15160)

应缴个税 = 应纳税所得额 × 税率 - 速算扣除数
实发工资 = 应发工资 - 五险一金 - 个税
```

### 3. 数据层 (SQLite)

```sql
-- 每月工资记录
CREATE TABLE monthly_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year_month TEXT NOT NULL UNIQUE,    -- "2026-07"
    basic_salary REAL,                  -- 基本工资
    weekend_overtime_days REAL,         -- 周末加班天数
    holiday_overtime_days REAL,         -- 节假日加班天数
    social_insurance_base REAL,         -- 社保基数
    housing_fund_base REAL,             -- 公积金基数
    housing_fund_rate REAL,             -- 公积金比例
    tax_deductions REAL,                -- 专项附加扣除
    actual_expenses_necessary REAL,     -- 实际必要支出
    actual_expenses_flexible REAL,      -- 实际弹性支出
    actual_savings REAL,                -- 实际储蓄投资
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 预算模板
CREATE TABLE budget_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    necessary_ratio REAL,
    flexible_ratio REAL,
    savings_ratio REAL,
    is_active INTEGER DEFAULT 0
);

-- 预算细项
CREATE TABLE budget_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER REFERENCES budget_templates(id),
    category TEXT NOT NULL,              -- necessary/flexible/savings
    name TEXT NOT NULL,
    budget_amount REAL,
    sort_order INTEGER
);
```

### 4. 项目结构

```
~/salary-calculator/
├── main.py                 # 入口
├── config.py               # 全局配置
├── gui/
│   ├── __init__.py
│   ├── app.py              # Flet App 主窗口
│   ├── salary_tab.py       # 工资计算 Tab
│   ├── budget_tab.py       # 预算分配 Tab
│   └── record_tab.py       # 月度记录 Tab
├── core/
│   ├── __init__.py
│   ├── salary_calc.py      # 工资+加班计算
│   ├── tax.py              # 五险一金+个税
│   └── budget.py           # 预算分配逻辑
├── data/
│   ├── __init__.py
│   └── storage.py          # SQLite CRUD
├── requirements.txt
├── build.bat               # Windows 打包脚本
└── README.md
```

### 5. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| GUI 框架 | Flet | Flutter 引擎，现代美观，跨平台，纯 Python |
| 存储 | SQLite | 零配置，单文件，Python 内置支持 |
| 打包 | flet pack / PyInstaller | 生成单文件 .exe，Windows 双击运行 |
| 状态管理 | Flet 内置状态 | 不需要复杂状态管理库 |
| 输入验证 | 前端 + 后端双重校验 | 防误输入 |

### 6. 数据流

```
用户输入参数 → Flet 控件 → Python 回调
    → core/salary_calc.py 计算
    → data/storage.py 持久化
    → Flet UI 更新展示
```

## 验收场景

### 核心场景：完整工资计算
1. 用户输入基本工资 15000
2. 社保基数 15000，公积金基数 15000，比例 8%
3. 周末加班 1 天，节假日加班 0 天
4. 点击计算
5. 结果：日工资 689.66，周末加班费 1379.31，五险一金 1575，个税约 651，实发约 14153
