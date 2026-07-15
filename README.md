# 💰 工资计算器

一个漂亮的本地桌面工资计算应用，帮你算清每个月该拿多少钱。

## 功能

| 功能 | 说明 |
|------|------|
| 🧮 **工资计算** | 基本工资 + 加班费（周末2倍/节假日3倍），日工资按21.75天折算 |
| 📊 **五险一金 + 个税** | 自动计算扣款，税后到手一目了然 |
| 📋 **预算分配** | 支持 50/30/20、631、333 等多种方案 |
| 📅 **月度记录** | 记录每月实际收支，跟踪结余和储蓄率 |
| 💾 **本地存储** | SQLite 持久化，历史数据随时回溯 |
| 🪟 **跨平台** | Windows / macOS / Linux 均可运行 |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

## Windows 打包

```bash
# 双击 build.bat
# 或手动执行
flet pack main.py --name 工资计算器
```

输出：`dist/工资计算器.exe`，双击即可运行。

## 项目结构

```
salary-calculator/
├── main.py                 # 入口
├── core/                   # 核心逻辑
│   ├── salary_calc.py      # 工资 + 加班计算
│   ├── tax.py              # 五险一金 + 个税
│   └── budget.py           # 预算分配
├── gui/                    # 界面
│   ├── app.py              # 主窗口
│   ├── salary_tab.py       # 工资计算 Tab
│   ├── budget_tab.py       # 预算分配 Tab
│   └── record_tab.py       # 月度记录 Tab
├── data/                   # 数据层
│   └── storage.py          # SQLite CRUD
├── tests/                  # 测试
│   └── test_calc.py        # 核心计算测试
├── requirements.txt
├── build.bat
└── README.md
```

## 技术栈

- **GUI**: Flet (Flutter 引擎)
- **语言**: Python 3.11+
- **存储**: SQLite
- **打包**: flet pack → .exe
