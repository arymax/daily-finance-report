"""
portfolio.py — 持倉資料載入與 schema 驗證
"""

import json
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
logger = logging.getLogger(__name__)


def load_portfolio(path: Path) -> dict:
    if not path.exists():
        logger.error(f"找不到 portfolio.json：{path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_portfolio(portfolio_path: Path) -> None:
    """
    用 jsonschema 驗證 portfolio.json。
    驗證失敗時記錄錯誤並退出。
    """
    try:
        import jsonschema
        from jsonschema import Draft7Validator
    except ImportError:
        logger.warning("jsonschema 未安裝，跳過驗證（建議：uv pip install jsonschema）")
        return

    schema_path = BASE_DIR / "portfolio_schema.json"
    if not schema_path.exists():
        logger.warning("找不到 portfolio_schema.json，跳過驗證")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    portfolio = load_portfolio(portfolio_path)

    errors = sorted(
        Draft7Validator(schema).iter_errors(portfolio),
        key=lambda e: list(e.absolute_path),
    )
    if errors:
        logger.error(f"portfolio.json schema 驗證失敗，發現 {len(errors)} 個錯誤：")
        for err in errors:
            path = " → ".join(str(p) for p in err.absolute_path) or "根層"
            logger.error(f"  [{path}] {err.message}")
        sys.exit(1)
    logger.info("✅ portfolio.json schema 驗證通過")
