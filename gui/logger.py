"""日志工具 — 写入文件用于调试"""
import logging
import os
import sys

LOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(LOG_DIR, 'app.log')

_logger = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger('salary_calc')
    _logger.setLevel(logging.DEBUG)

    # 文件处理器
    fh = logging.FileHandler(LOG_PATH, mode='a', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    fh.setFormatter(fmt)
    _logger.addHandler(fh)

    # 控制台也输出（给开发者看）
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    _logger.addHandler(ch)

    return _logger
