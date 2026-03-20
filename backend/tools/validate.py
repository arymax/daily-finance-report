"""
validate.py — 驗證 portfolio.json 是否符合 portfolio_schema.json 規格

用法：
    python validate.py                  # 驗證預設 portfolio.json
    python validate.py --fix-hints      # 額外顯示欄位修正建議
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Windows terminal UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import jsonschema
    from jsonschema import Draft7Validator
except ImportError:
    print("❌ 缺少套件，請執行：uv pip install jsonschema")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
SCHEMA_FILE = BASE_DIR / "portfolio_schema.json"
PORTFOLIO_FILE = BASE_DIR / "portfolio.json"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(portfolio_path: Path = PORTFOLIO_FILE) -> bool:
    schema = load_json(SCHEMA_FILE)
    portfolio = load_json(portfolio_path)

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(portfolio), key=lambda e: list(e.absolute_path))

    if not errors:
        print(f"✅  portfolio.json 驗證通過（0 錯誤）")
        _print_summary(portfolio)
        return True

    print(f"❌  發現 {len(errors)} 個驗證錯誤：\n")
    for i, err in enumerate(errors, 1):
        path = " → ".join(str(p) for p in err.absolute_path) or "（根層）"
        print(f"  {i}. [{path}]")
        print(f"     {err.message}")
        print()
    return False


def _print_summary(portfolio: dict) -> None:
    """驗證通過後印出資產概覽。"""
    cash = portfolio.get("cash", {}).get("total_twd", 0)
    lt   = len(portfolio.get("long_term", {}).get("positions", []))
    ta   = len(portfolio.get("tactical", {}).get("positions", []))
    cr   = len(portfolio.get("crypto", {}).get("positions", []))
    wl   = len(portfolio.get("watchlist", []))
    ev   = len(portfolio.get("strategy", {}).get("key_upcoming_events", []))

    print()
    print("  資產概覽")
    print(f"  ├─ 現金：{cash:>10,} TWD")
    print(f"  ├─ 長期配置：{lt} 筆持倉")
    print(f"  ├─ 波段投資：{ta} 筆持倉")
    print(f"  ├─ 加密貨幣：{cr} 筆持倉")
    print(f"  ├─ 觀察清單：{wl} 筆")
    print(f"  └─ 近期關鍵事件：{ev} 筆")


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio JSON Schema 驗證工具")
    parser.add_argument("--file", type=Path, default=PORTFOLIO_FILE,
                        help="指定 portfolio JSON 路徑（預設 portfolio.json）")
    args = parser.parse_args()

    print(f"驗證：{args.file}")
    print(f"Schema：{SCHEMA_FILE}\n")

    success = validate(args.file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
