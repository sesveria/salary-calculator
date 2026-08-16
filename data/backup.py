"""数据自动备份 — 启动时快照 salary.db 到 backups/

策略：
  - 每天最多一份（同名覆盖当天）
  - 保留最近 KEEP_DAYS 天的备份
  - 备份失败不影响应用启动（静默降级）
"""
import os
import shutil
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'salary.db')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backups')
KEEP_DAYS = 30


def backup_db(db_path: str = DB_PATH, backup_dir: str = BACKUP_DIR) -> str | None:
    """快照数据库到备份目录，返回备份文件路径（失败返回 None）

    每天一份：backups/salary-YYYYMMDD.db
    """
    if not os.path.exists(db_path):
        return None
    try:
        os.makedirs(backup_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        target = os.path.join(backup_dir, f'salary-{date_str}.db')
        shutil.copy2(db_path, target)
        _cleanup_old(backup_dir)
        return target
    except OSError:
        return None


def _cleanup_old(backup_dir: str, keep: int = KEEP_DAYS):
    """删除超过保留天数的备份文件"""
    try:
        files = [f for f in os.listdir(backup_dir)
                 if f.startswith('salary-') and f.endswith('.db')]
        files.sort()  # 按文件名（日期）排序，最旧在前
        while len(files) > keep:
            old = os.path.join(backup_dir, files.pop(0))
            try:
                os.remove(old)
            except OSError:
                pass
    except OSError:
        pass
