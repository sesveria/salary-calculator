"""数据备份模块测试"""
import os

import pytest

from data.backup import backup_db, _cleanup_old, KEEP_DAYS


class TestBackup:
    def test_backup_creates_file(self, tmp_path):
        # 创建假数据库
        db = tmp_path / "salary.db"
        db.write_text("fake sqlite content")
        backup_dir = str(tmp_path / "backups")

        result = backup_db(str(db), backup_dir)
        assert result is not None
        assert os.path.exists(result)
        # 备份内容一致
        assert open(result).read() == "fake sqlite content"

    def test_backup_missing_db(self, tmp_path):
        result = backup_db(str(tmp_path / "nonexistent.db"), str(tmp_path / "b"))
        assert result is None

    def test_backup_same_day_overwrites(self, tmp_path):
        db = tmp_path / "salary.db"
        db.write_text("v1")
        backup_dir = str(tmp_path / "backups")
        backup_db(str(db), backup_dir)
        db.write_text("v2")
        backup_db(str(db), backup_dir)
        # 同一天只保留一份
        files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
        assert len(files) == 1
        # 内容是最新
        latest = os.path.join(backup_dir, files[0])
        assert open(latest).read() == "v2"

    def test_cleanup_old(self, tmp_path):
        backup_dir = str(tmp_path)
        # 创建 5 个假备份（不同日期）
        for i in range(5):
            p = os.path.join(backup_dir, f"salary-2026010{i}.db")
            open(p, "w").write(str(i))
        _cleanup_old(backup_dir, keep=2)
        remaining = sorted(f for f in os.listdir(backup_dir) if f.startswith('salary-'))
        assert len(remaining) == 2
        # 保留的是最新的（日期最大）
        assert remaining == ['salary-20260103.db', 'salary-20260104.db']
