"""
scheduler_daemon.py — 每日財務報告背景排程

每日兩個時段自動觸發 main.py：
  07:00 — 早盤（台股盤前／美股盤後）
  18:00 — 收盤（台股盤後／美股盤前）

啟動方式：
  python scheduler_daemon.py          # 前景執行（有 console）
  pythonw scheduler_daemon.py         # 背景靜默執行（無 console）

開機自動啟動（不需管理員）：
  python tools/install_startup.py     # 將背景啟動捷徑加入 Windows 開機啟動
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import schedule

BASE_DIR = Path(__file__).parent
TST = timezone(timedelta(hours=8))

# ── Logging ────────────────────────────────────────────────
logs_dir = BASE_DIR / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / f"scheduler_{datetime.now(TST).strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ── 讀取排程開關 ───────────────────────────────────────────
def _is_enabled() -> bool:
    """每次觸發前即時讀取 config.json，讓使用者可隨時關閉排程而無需重啟 daemon。"""
    try:
        with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("scheduler", {}).get("enabled", True)
    except Exception as e:
        logger.warning(f"讀取 config.json 失敗，預設啟用：{e}")
        return True


# ── Python 執行檔路徑 ──────────────────────────────────────
def _find_python() -> str:
    """優先使用 .venv/Scripts/python.exe，找不到才用 sys.executable。"""
    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


# ── 觸發 main.py ───────────────────────────────────────────
def _trigger(session: str) -> None:
    if not _is_enabled():
        now = datetime.now(TST).strftime("%Y-%m-%d %H:%M")
        logger.info(f"[{now}] 排程已停用（scheduler.enabled=false），略過 {session}")
        return

    now = datetime.now(TST).strftime("%Y-%m-%d %H:%M")
    logger.info(f"[{now}] 觸發 main.py --session {session}")
    try:
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(
            [_find_python(), str(BASE_DIR / "main.py"), "--session", session],
            cwd=str(BASE_DIR),
            **kwargs,
        )
    except Exception as e:
        logger.error(f"觸發失敗：{e}")


# ── 排程設定 ───────────────────────────────────────────────
schedule.every().day.at("07:00").do(_trigger, session="morning")
schedule.every().day.at("18:00").do(_trigger, session="evening")
schedule.every().day.at("23:05").do(_trigger, session="evening")


# ── 主迴圈 ────────────────────────────────────────────────
def main() -> None:
    logger.info("=" * 50)
    logger.info("  Daily Finance Report Scheduler 啟動")
    logger.info("  07:00 → morning  |  18:00 → evening")
    logger.info("=" * 50)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
