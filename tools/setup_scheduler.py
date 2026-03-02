"""
setup_scheduler.py — 用 Windows Task Scheduler 設定每日兩個時段自動執行
  早盤 07:00 — 台股盤前／美股盤後  (--session morning)
  收盤 18:00 — 台股盤後／美股盤前  (--session evening)

適用環境：Git Bash、CMD、PowerShell 皆可執行

用法：
    python setup_scheduler.py          # 建立/更新兩個排程任務
    python setup_scheduler.py --remove # 刪除兩個排程任務
    python setup_scheduler.py --status # 查詢兩個任務狀態
"""

import argparse
import io
import shutil
import subprocess
import sys
from pathlib import Path

# Windows terminal UTF-8 support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

TASKS = [
    {"name": "DailyFinanceReport_Morning", "time": "07:00", "session": "morning", "label": "台股盤前／美股盤後"},
    {"name": "DailyFinanceReport_Evening", "time": "18:00", "session": "evening", "label": "台股盤後／美股盤前"},
]

BASE_DIR = Path(__file__).parent.parent.resolve()
MAIN_PY  = BASE_DIR / "main.py"


def _oem_encoding() -> str:
    """偵測 Windows OEM code page（繁中為 cp950），供 schtasks 輸出解碼用。"""
    if sys.platform == "win32":
        try:
            import ctypes
            cp = ctypes.windll.kernel32.GetOEMCP()
            return f"cp{cp}"
        except Exception:
            pass
    return "utf-8"


def _run(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding=_oem_encoding(),
        errors="replace",
        check=check,
    )


def find_python() -> str:
    """
    優先使用 uv run（若 uv 已安裝且 pyproject.toml 存在）。
    否則 fallback 到 .venv/Scripts/python.exe，最後才用 sys.executable。
    """
    uv_exe = shutil.which("uv")
    if uv_exe and (BASE_DIR / "pyproject.toml").exists():
        return uv_exe  # caller 以 "uv run python main.py --session X" 形式組裝指令

    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _build_action(session: str) -> tuple[str, str]:
    """回傳 (action 指令字串, 執行模式說明)"""
    python_or_uv = find_python()
    uv_exe = shutil.which("uv")
    if uv_exe and python_or_uv == uv_exe:
        action = f'"{uv_exe}" run python "{MAIN_PY}" --session {session}'
        mode = "uv run"
    else:
        action = f'"{python_or_uv}" "{MAIN_PY}" --session {session}'
        mode = ".venv python"
    return action, mode


def create_tasks() -> None:
    all_ok = True
    for task in TASKS:
        action, mode = _build_action(task["session"])
        print(f"  任務名稱  : {task['name']}")
        print(f"  執行時間  : 每日 {task['time']}（{task['label']}）")
        print(f"  執行方式  : {mode}")
        print(f"  指令      : {action}")
        print()

        # 先刪除舊任務（若存在），忽略失敗
        _run(["schtasks", "/delete", "/tn", task["name"], "/f"], check=False)

        result = _run([
            "schtasks", "/create",
            "/tn", task["name"],
            "/tr", action,
            "/sc", "DAILY",
            "/st", task["time"],
            "/f",
        ], check=False)

        if result.returncode == 0:
            print(f"OK  排程任務「{task['name']}」建立成功")
        else:
            print(f"NG  排程任務「{task['name']}」建立失敗")
            print(result.stderr or result.stdout)
            all_ok = False
        print()

    if all_ok:
        print("所有排程任務建立成功！")
        print()
        status()
    else:
        print("部分任務建立失敗，請確認：")
        print("  1. 以「系統管理員身分」開啟終端機後再執行此腳本")
        print("  2. 系統時區已設為 Asia/Taipei（UTC+8）")
        sys.exit(1)


def remove_tasks() -> None:
    for task in TASKS:
        result = _run(["schtasks", "/delete", "/tn", task["name"], "/f"], check=False)
        if result.returncode == 0:
            print(f"已刪除任務「{task['name']}」")
        else:
            print(f"找不到任務「{task['name']}」或刪除失敗")
            print(result.stderr)


def status() -> None:
    for task in TASKS:
        result = _run(["schtasks", "/query", "/tn", task["name"], "/fo", "LIST"], check=False)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"找不到任務「{task['name']}」，請先執行 setup_scheduler.py 建立任務。")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Windows Task Scheduler 設定工具（雙時段）")
    parser.add_argument("--remove", action="store_true", help="刪除兩個排程任務")
    parser.add_argument("--status", action="store_true", help="查詢兩個任務狀態")
    args = parser.parse_args()

    print("=" * 55)
    print("  Daily Finance Report - Scheduler Setup")
    print("=" * 55)
    print()

    if args.remove:
        remove_tasks()
    elif args.status:
        status()
    else:
        create_tasks()


if __name__ == "__main__":
    main()
