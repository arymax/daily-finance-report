"""
config.py — 設定載入 + 日誌初始化
"""

import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TST = timezone(timedelta(hours=8))


def load_config() -> dict:
    path = BASE_DIR / "config.json"
    if not path.exists():
        print("❌ 找不到 config.json")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_logging(logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{datetime.now(TST).strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
