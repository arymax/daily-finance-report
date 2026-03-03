"""
install_startup.py — 將排程 daemon 加入 Windows 開機自動啟動（不需管理員）

原理：在 %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\ 放置 .bat 檔，
Windows 每次登入時會自動執行該資料夾內的所有程式。

用法：
    python tools/install_startup.py           # 安裝開機啟動
    python tools/install_startup.py --remove  # 移除開機啟動
    python tools/install_startup.py --status  # 查詢目前狀態
"""

import argparse
import io
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR      = Path(__file__).parent.parent.resolve()
DAEMON_PY     = BASE_DIR / "scheduler_daemon.py"
VENV_PYTHONW  = BASE_DIR / ".venv" / "Scripts" / "pythonw.exe"
STARTUP_DIR   = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
BAT_FILE      = STARTUP_DIR / "DailyFinanceReport.bat"


def _pythonw() -> str:
    """回傳 pythonw.exe 路徑（靜默執行，不顯示 console）。"""
    if VENV_PYTHONW.exists():
        return str(VENV_PYTHONW)
    # fallback：把 python.exe 換成 pythonw.exe
    return str(Path(sys.executable).with_name("pythonw.exe"))


def install() -> None:
    pythonw = _pythonw()
    bat_content = (
        f'@echo off\n'
        f'start "" "{pythonw}" "{DAEMON_PY}"\n'
    )
    BAT_FILE.write_text(bat_content, encoding="utf-8")
    print(f"✅ 開機啟動已安裝：{BAT_FILE}")
    print(f"   執行檔：{pythonw}")
    print(f"   Daemon：{DAEMON_PY}")
    print()
    print("下次登入 Windows 後，scheduler_daemon.py 將自動在背景執行。")
    print("若要立即啟動，請執行：")
    print(f'  start "" "{pythonw}" "{DAEMON_PY}"')


def remove() -> None:
    if BAT_FILE.exists():
        BAT_FILE.unlink()
        print(f"✅ 已移除開機啟動：{BAT_FILE}")
    else:
        print("找不到開機啟動設定，可能尚未安裝。")


def status() -> None:
    if BAT_FILE.exists():
        print(f"✅ 開機啟動已安裝：{BAT_FILE}")
        print()
        print("--- 內容 ---")
        print(BAT_FILE.read_text(encoding="utf-8"))
    else:
        print("❌ 尚未安裝開機啟動。")
        print(f"   執行 python tools/install_startup.py 來安裝。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Finance Report 開機啟動管理")
    parser.add_argument("--remove", action="store_true", help="移除開機啟動")
    parser.add_argument("--status", action="store_true", help="查詢目前狀態")
    args = parser.parse_args()

    print("=" * 50)
    print("  Daily Finance Report - 開機啟動設定")
    print("=" * 50)
    print()

    if args.remove:
        remove()
    elif args.status:
        status()
    else:
        install()


if __name__ == "__main__":
    main()
