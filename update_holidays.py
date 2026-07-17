#!/usr/bin/env python3
"""
节假日库更新工具 —— 检测并升级 chinese-calendar。

用法:
  python update_holidays.py               # 检查并升级（交互式）
  python update_holidays.py --check       # 仅检查，不升级
  python update_holidays.py --auto        # 静默升级（供 GUI 调用）
  python update_holidays.py --check-json  # 输出 JSON 供程序解析（给 app.py 调用）

返回码:
  0 = 已是最新 / 无需操作
  1 = 已升级 / 有可用更新
  2 = 出错
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request

PACKAGE = "chinese-calendar"
PYPI_JSON = "https://pypi.org/pypi/chinese-calendar/json"
MIRROR_JSON = "https://pypi.tuna.tsinghua.edu.cn/pypi/chinese-calendar/json"
TIMEOUT = 20


def _get_installed_version() -> str | None:
    """获取当前安装版本"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", PACKAGE],
            capture_output=True, text=True, timeout=15,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def _get_latest_version() -> str | None:
    """从 PyPI 查询最新版本号"""
    for url in (PYPI_JSON, MIRROR_JSON):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "update-chinese-calendar/1.0"},
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
            return data["info"]["version"]
        except Exception:
            continue
    return None


def _version_tuple(v: str) -> tuple:
    """版本号转可比较元组"""
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def _do_upgrade() -> tuple[bool, str]:
    """执行升级，返回 (成功?, 日志)"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE],
            capture_output=True, text=True, timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        success = result.returncode == 0
        message = output.splitlines()[-1] if output else ("升级成功" if success else "升级失败")
        return success, message
    except subprocess.TimeoutExpired:
        return False, "升级超时（>120秒）"
    except Exception as e:
        return False, f"升级出错: {e}"


def cmd_check():
    """仅检查"""
    installed = _get_installed_version()
    latest = _get_latest_version()

    if not installed:
        print(f"❌ 未安装 {PACKAGE}，请先执行: pip install {PACKAGE}")
        return 2

    if not latest:
        print("❌ 无法连接 PyPI，请检查网络")
        return 2

    if _version_tuple(installed) >= _version_tuple(latest):
        print(f"✅ {PACKAGE} 已是最新版本: v{installed}")
        return 0
    else:
        print(f"📦 {PACKAGE} v{installed} → v{latest} 可用")
        print(f"   执行 'python update_holidays.py' 升级")
        return 1


def cmd_auto():
    """静默升级（供 GUI 等程序调用）"""
    installed = _get_installed_version()
    latest = _get_latest_version()

    if not installed:
        print(f"❌ {PACKAGE} 未安装")
        return 2

    if not latest:
        print("❌ 无法连接 PyPI")
        return 2

    if _version_tuple(installed) >= _version_tuple(latest):
        print(f"✅ {PACKAGE} v{installed} 已是最新")
        return 0

    print(f"📦 {PACKAGE} v{installed} → v{latest} 开始升级...")
    ok, msg = _do_upgrade()
    if ok:
        print(f"✅ 升级完成: v{latest}")
        return 1
    else:
        print(f"❌ 升级失败: {msg}")
        return 2


def cmd_interactive():
    """交互式升级"""
    installed = _get_installed_version()
    latest = _get_latest_version()

    if not installed:
        print(f"📦 {PACKAGE} 未安装，正在安装...")
        ok, msg = _do_upgrade()
        print(f"   {'✅' if ok else '❌'} {msg}")
        return 0 if ok else 2

    if not latest:
        print("❌ 无法连接 PyPI，请检查网络")
        return 2

    if _version_tuple(installed) >= _version_tuple(latest):
        print(f"✅ {PACKAGE} 已是最新版本: v{installed}")
        return 0
    else:
        print(f"📦 发现新版本: {PACKAGE} v{installed} → v{latest}")
        try:
            answer = input("   是否升级？(Y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        if answer in ("", "y", "yes"):
            ok, msg = _do_upgrade()
            print(f"   {'✅' if ok else '❌'} {msg}")
            return 0 if ok else 2
        else:
            print("   已跳过")
            return 1


def cmd_check_json():
    """JSON 输出模式（供 app.py 调用）"""
    installed = _get_installed_version()
    latest = _get_latest_version()

    result = {
        "installed": installed,
        "latest": latest,
        "uptodate": True,
        "error": None,
    }

    if not installed:
        result["error"] = f"{PACKAGE} 未安装"
        result["uptodate"] = False
    elif not latest:
        result["error"] = "无法连接 PyPI"
        result["uptodate"] = False
    else:
        result["uptodate"] = _version_tuple(installed) >= _version_tuple(latest)

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("uptodate") and not result.get("error") else 1


def main():
    parser = argparse.ArgumentParser(description="节假日库更新工具")
    parser.add_argument("--check", action="store_true", help="仅检查版本")
    parser.add_argument("--auto", action="store_true", help="静默升级（无交互）")
    parser.add_argument("--check-json", action="store_true", help="JSON 输出（供 GUI 调用）")
    args = parser.parse_args()

    if args.check:
        return cmd_check()
    elif args.auto:
        return cmd_auto()
    elif args.check_json:
        return cmd_check_json()
    else:
        return cmd_interactive()


if __name__ == "__main__":
    sys.exit(main())
