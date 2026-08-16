"""CSV 导出测试"""
import csv
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data import storage


@pytest.fixture
def db(tmp_path):
    db = str(tmp_path / "test.db")
    storage.init_db(db)
    rec = {
        'year_month': '2026-03',
        'basic_salary': 15000,
        'gross_salary': 17000,
        'tax_amount': 651,
        'insurance_total': 2785,
        'net_salary': 13564,
        'extra_income': 500,
        'actual_necessary': 3000,
        'actual_flexible': 2000,
        'actual_savings': 1500,
        'total_expense': 6500,
        'save_rate': 11.06,
        'opening_balance': 1000,
        'closing_balance': 8564,
        'notes': '测试备注',
    }
    storage.save_monthly_record(rec, db)
    return db


class TestExportCSV:
    def test_export_creates_file(self, db, tmp_path):
        out = str(tmp_path / "records.csv")
        count = storage.export_records_csv(out, db)
        assert count == 1
        assert os.path.exists(out)

    def test_export_content(self, db, tmp_path):
        out = str(tmp_path / "records.csv")
        storage.export_records_csv(out, db)

        with open(out, newline='', encoding='utf-8-sig') as f:
            rows = list(csv.reader(f))
        # 表头 + 1 行数据
        assert len(rows) == 2
        header = rows[0]
        assert 'year_month' in header
        assert 'net_salary' in header
        assert 'closing_balance' in header
        # 数据正确（REAL 读出带 .0 后缀）
        data = dict(zip(header, rows[1]))
        assert data['year_month'] == '2026-03'
        assert float(data['net_salary']) == 13564.0
        assert float(data['extra_income']) == 500.0
        assert data['notes'] == '测试备注'

    def test_export_utf8_bom(self, db, tmp_path):
        out = str(tmp_path / "records.csv")
        storage.export_records_csv(out, db)
        # 文件以 BOM 开头（Excel 打开不乱码）
        with open(out, 'rb') as f:
            head = f.read(3)
        assert head == b'\xef\xbb\xbf'

    def test_export_empty_db(self, tmp_path):
        db = str(tmp_path / "empty.db")
        storage.init_db(db)
        out = str(tmp_path / "empty.csv")
        count = storage.export_records_csv(out, db)
        assert count == 0
