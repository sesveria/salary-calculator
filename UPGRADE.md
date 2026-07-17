# 升级指南

## 如何保留数据升级版本

所有数据保存在 `salary.db` 文件中。升级版本时：

### 完整升级步骤

1. **备份** — 把旧的 `salary.db` 复制到安全位置

2. **替换代码** — 解压新版压缩包到项目目录（覆盖除 salary.db 外的所有文件）

3. **运行** — `pip install -r requirements.txt && python main.py`

   新版启动时会自动检测旧数据库结构，补充缺少的字段，不需要手动迁移。

### 常见场景

| 场景 | 做法 |
|------|------|
| 第一次安装 | 解压 → pip install → python main.py（数据为空，需手动录入） |
| 已有数据想升级 | 保留 salary.db，覆盖其他文件 → pip install → python main.py |
| 换电脑 | 把整个文件夹（含 salary.db）复制过去 → pip install → python main.py |
| 只想传数据 | 只复制 salary.db 到新版项目目录即可 |
