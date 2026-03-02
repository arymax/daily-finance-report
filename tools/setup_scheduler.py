"""
setup_scheduler.py — 用 Windows Task Scheduler 設定每日 07:00 自動執行
適用環境：Git Bash、CMD、PowerShell 皆可執行

用法：
    python setup_scheduler.py          # 建立/更新排程任務
    python setup_scheduler.py --remove # 刪除排程任務
    python setup_scheduler.py --status # 查詢任務狀態
"""

import argparse
import subprocess
import sys
from pathlib import Path

TASK_NAME = "DailyFinanceReport"
BASE_DIR = Path(__file__).parent.parent.resolve()
MAIN_PY = BASE_DIR / "main.py"


def _run(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def find_python() -> str:
    """
    優先使用 uv run（若 uv 已安裝且 pyproject.toml 存在）。
    否則 fallback 到 .venv/Scripts/python.exe，最後才用 sys.executable。
    """
    import shutil

    uv_exe = shutil.which("uv")
    if uv_exe and (BASE_DIR / "pyproject.toml").exists():
        return uv_exe  # caller 會以 "uv run python main.py" 形式組裝指令

    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def create_task() -> None:
    python_or_uv = find_python()
    script_path = str(MAIN_PY)

    # 若取得的是 uv，使用 "uv run python main.py"（uv init 架構）
    import shutil
    uv_exe = shutil.which("uv")
    if uv_exe and python_or_uv == uv_exe:
        action = f'"{uv_exe}" run python "{script_path}"'
        mode = "uv run"
    else:
        action = f'"{python_or_uv}" "{script_path}"'
        mode = ".venv python"

    print(f"  執行方式  : {mode}")
    print(f"  指令      : {action}")
    print(f"  任務名稱  : {TASK_NAME}")
    print(f"  執行時間  : 每日 07:00（台灣時間）")
    print()

    # 先刪除舊任務（若存在），忽略失敗
    _run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"], check=False)

    # 建立新排程任務
    result = _run([
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", action,
        "/sc", "DAILY",
        "/st", "07:00",
        "/rl", "HIGHEST",
        "/f",
    ], check=False)

    if result.returncode == 0:
        print("✅ 排程任務建立成功！")
        print()
        status()
    else:
        print("❌ 建立失敗！")
        print(result.stderr or result.stdout)
        print()
        print("請確認：")
        print("  1. 以「系統管理員身分」開啟終端機後再執行此腳本")
        print("  2. 系統時區已設為 Asia/Taipei（UTC+8）")
        sys.exit(1)


def remove_task() -> None:
    result = _run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"], check=False)
    if result.returncode == 0:
        print(f"✅ 任務「{TASK_NAME}」已刪除。")
    else:
        print(f"找不到任務「{TASK_NAME}」或刪除失敗。")
        print(result.stderr)


def status() -> None:
    result = _run(["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"], check=False)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"找不到任務「{TASK_NAME}」，請先執行 setup_scheduler.py 建立任務。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Windows Task Scheduler 設定工具")
    parser.add_argument("--remove", action="store_true", help="刪除排程任務")
    parser.add_argument("--status", action="store_true", help="查詢任務狀態")
    args = parser.parse_args()

    print("=" * 50)
    print("  Daily Finance Report — 排程設定")
    print("=" * 50)

    if args.remove:
        remove_task()
    elif args.status:
        status()
    else:
        create_task()


if __name__ == "__main__":
    main()
