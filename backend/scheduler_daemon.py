"""
scheduler_daemon.py — 每日財務報告背景排程（含系統匣圖示）

每日兩個時段自動觸發 main.py：
  07:00 — 早盤（台股盤前／美股盤後）
  18:00 — 收盤（台股盤後／美股盤前）
  21:15 — 盤前晨檢（美股開盤前 5 分鐘晨檢）

啟動方式：
  python scheduler_daemon.py          # 前景執行（有 console）
  pythonw scheduler_daemon.py         # 背景靜默執行（系統匣圖示）

開機自動啟動（不需管理員）：
  python tools/install_startup.py     # 將背景啟動捷徑加入 Windows 開機啟動
"""

import json
import logging
import os
import subprocess
import sys
import threading
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

_handlers: list[logging.Handler] = [
    logging.FileHandler(log_file, encoding="utf-8"),
]
try:
    if sys.stdout:
        _handlers.append(logging.StreamHandler(sys.stdout))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=_handlers,
)
logger = logging.getLogger(__name__)


# ── 讀取排程開關 ───────────────────────────────────────────
def _is_enabled() -> bool:
    """每次觸發前即時讀取 config.json，讓使用者可隨時關閉排程。"""
    try:
        with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("scheduler", {}).get("enabled", True)
    except Exception as e:
        logger.warning(f"讀取 config.json 失敗，預設啟用：{e}")
        return True


def _set_enabled(value: bool) -> None:
    """將 scheduler.enabled 寫回 config.json。"""
    try:
        with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        config.setdefault("scheduler", {})["enabled"] = value
        with open(BASE_DIR / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"寫入 config.json 失敗：{e}")


# ── Python 執行檔路徑 ──────────────────────────────────────
def _find_python() -> str:
    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


# ── 觸發 main.py ───────────────────────────────────────────
def _trigger(session: str) -> None:
    if not _is_enabled():
        now = datetime.now(TST).strftime("%Y-%m-%d %H:%M")
        logger.info(f"[{now}] 排程已停用，略過 {session}")
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


def _trigger_premarket() -> None:
    if not _is_enabled():
        now = datetime.now(TST).strftime("%Y-%m-%d %H:%M")
        logger.info(f"[{now}] 排程已停用，略過 premarket")
        return

    now = datetime.now(TST).strftime("%Y-%m-%d %H:%M")
    logger.info(f"[{now}] 觸發 main.py --premarket")
    try:
        # 不使用 CREATE_NO_WINDOW，保留 pywebview 視窗可見
        subprocess.Popen(
            [_find_python(), str(BASE_DIR / "main.py"), "--premarket"],
            cwd=str(BASE_DIR),
        )
    except Exception as e:
        logger.error(f"盤前晨檢觸發失敗：{e}")


# ── 排程設定 ───────────────────────────────────────────────
schedule.every().day.at("07:00").do(_trigger, session="morning")
schedule.every().day.at("18:00").do(_trigger, session="evening")
schedule.every().day.at("21:15").do(_trigger_premarket)


# ── 系統匣圖示 ─────────────────────────────────────────────
def _run_tray() -> None:
    """建立並執行系統匣圖示（主執行緒）。"""
    try:
        from PIL import Image, ImageDraw
        import pystray
    except ImportError:
        logger.warning("pystray / Pillow 未安裝，略過系統匣圖示；排程仍正常運行。")
        return

    # ── 圖示繪製 ──────────────────────────────────────────
    def _make_image(enabled: bool) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 外圓：綠色（啟用）/ 灰色（停用）
        bg = (34, 197, 94) if enabled else (150, 150, 150)
        draw.ellipse([2, 2, 62, 62], fill=bg)
        # 時鐘面
        draw.ellipse([14, 14, 50, 50], fill=(255, 255, 255, 220))
        # 時針 & 分針
        draw.line([32, 32, 32, 20], fill=(30, 30, 30), width=3)
        draw.line([32, 32, 42, 38], fill=(30, 30, 30), width=2)
        return img

    # ── Tooltip 文字 ──────────────────────────────────────
    def _tooltip() -> str:
        enabled = _is_enabled()
        nxt = schedule.next_run()
        nxt_str = nxt.strftime("%m/%d %H:%M") if nxt else "—"
        tag = "ON" if enabled else "OFF"
        return f"Daily Finance Report [{tag}]\n下次執行：{nxt_str}"

    # ── 選單動作 ──────────────────────────────────────────
    def _toggle(icon, item):
        new_val = not _is_enabled()
        _set_enabled(new_val)
        icon.icon = _make_image(new_val)
        icon.title = _tooltip()
        logger.info(f"排程已{'啟用' if new_val else '停用'}（來自系統匣）")

    def _open_log(icon, item):
        log = logs_dir / f"scheduler_{datetime.now(TST).strftime('%Y%m%d')}.log"
        if log.exists():
            os.startfile(str(log))
        else:
            logger.info("今日 log 尚不存在")

    def _open_reports(icon, item):
        reports_dir = BASE_DIR / "reports"
        if reports_dir.exists():
            os.startfile(str(reports_dir))

    def _quit(icon, item):
        icon.stop()

    # ── 建立圖示 ──────────────────────────────────────────
    icon = pystray.Icon(
        "daily-finance",
        _make_image(_is_enabled()),
        _tooltip(),
        menu=pystray.Menu(
            pystray.MenuItem("Daily Finance Report", None, enabled=False),
            pystray.MenuItem("07:00 早盤  ·  18:00 收盤  ·  21:15 盤前晨檢", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("啟用／停用排程", _toggle),
            pystray.MenuItem("查看今日 Log", _open_log),
            pystray.MenuItem("開啟報告資料夾", _open_reports),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("結束", _quit),
        ),
    )

    # 每 60 秒更新 tooltip & 圖示顏色
    def _refresh():
        while True:
            time.sleep(60)
            try:
                icon.icon = _make_image(_is_enabled())
                icon.title = _tooltip()
            except Exception:
                break

    threading.Thread(target=_refresh, daemon=True).start()

    logger.info("系統匣圖示已啟動")
    icon.run()  # 阻塞主執行緒，直到使用者點「結束」


# ── 主流程 ────────────────────────────────────────────────
def main() -> None:
    logger.info("=" * 50)
    logger.info("  Daily Finance Report Scheduler 啟動")
    logger.info("  07:00 → morning  |  18:00 → evening  |  21:15 → premarket")
    logger.info("=" * 50)

    # 排程迴圈在背景執行緒
    def _loop():
        while True:
            schedule.run_pending()
            time.sleep(30)

    threading.Thread(target=_loop, daemon=True).start()

    # 系統匣在主執行緒（pystray 要求）
    # 若無 pystray，_run_tray() 直接 return，改用簡單迴圈維持行程存活
    _run_tray()

    # 若系統匣未啟動（無 pystray），保持行程運行
    logger.info("（無系統匣模式）排程持續運行中，Ctrl+C 可結束")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler 已停止")


if __name__ == "__main__":
    main()
