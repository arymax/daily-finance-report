# 每日財經報告 Daily Finance Report

每天自動爬取個股與市場新聞、查詢即時股價，透過 **Claude Code CLI** 生成持倉分析與市場總覽報告，並透過 **GitHub Pages** 提供即時互動式儀表板。

🔗 **Live Dashboard**：[arymax.github.io/daily-finance-report](https://arymax.github.io/daily-finance-report)

---

## 功能特色

- **持倉儀表板**：即時股價（US / TW / Crypto）、損益、資產分配圓餅圖、歷史走勢
- **持倉分析**：成本損益計算、操作建議（Claude 生成）
- **市場總覽**：RSS 市場新聞 + 重要個股新聞、強弱板塊、風險提示
- **觀察清單**：優先級評分、進場條件追蹤、主題對齊
- **Thesis 管理**：個股深度研究文件、自動更新、產業板塊分類
- **主題催化劑**：跨標的主題追蹤（AI / 液冷 / 核電等）
- **記憶功能**：保留近 N 日分析摘要，確保分析連貫性
- **GitHub 同步**：執行後自動 push，GitHub Pages 自動部署

---

## 前置需求

| 工具 | 說明 |
|------|------|
| Python 3.10+ | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 套件管理（必要）|
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) | `claude` 指令需可執行 |
| Git | 同步用 |

---

## 快速開始

### 1. Clone repo

```bash
git clone https://github.com/arymax/daily-finance-report.git
cd daily-finance-report
```

### 2. 安裝套件

```bash
uv sync
```

### 3. 設定個人持倉

```bash
cp portfolio.example.json portfolio.json
```

編輯 `portfolio.json`，填入 ticker、持股數量、成本（TWD）等欄位。
驗證格式：

```bash
uv run python main.py --validate
```

### 4. 安裝 pre-commit hook（必做）

**作用**：每次 commit `portfolio.json` 時，自動重生成 `docs/data.json` 並加入同一個 commit，確保儀表板與持倉資料永遠同步。

在 `.git/hooks/pre-commit` 建立以下內容的檔案：

```sh
#!/bin/sh
# 跳過方式：SKIP_DASHBOARD=1 git commit -m "..."
if [ "${SKIP_DASHBOARD}" = "1" ]; then
  exit 0
fi

if git diff --cached --name-only | grep -q "^portfolio\.json$"; then
  echo "[pre-commit] portfolio.json 已變動，自動重生成 docs/data.json..."
  uv run python main.py --dashboard --session morning
  if [ $? -ne 0 ]; then
    echo "[pre-commit] ❌ dashboard 生成失敗，commit 中止"
    exit 1
  fi
  git add docs/data.json docs/history.json
  echo "[pre-commit] ✅ docs/data.json 已更新並加入 commit"
fi
exit 0
```

接著確保檔案有執行權限（macOS / Linux）：
```bash
chmod +x .git/hooks/pre-commit
```

> ⚠️ `.git/hooks/` 不受 git 版本控制，**換電腦或重新 clone 後需重新建立此檔案**。

**跳過 hook（緊急 commit 時）：**
```bash
SKIP_DASHBOARD=1 git commit -m "緊急修正"
```

### 5. 調整設定（可選）

編輯 `config.json`：

```json
{
  "claude_model": "",
  "claude_timeout_seconds": 300,
  "max_articles_per_stock": 5,
  "max_market_articles": 20,
  "sync": {
    "enabled": true,
    "auto_pull": true,
    "auto_push": true
  },
  "memory": {
    "enabled": true,
    "context_days": 5
  }
}
```

### 6. （可選）設定 Finnhub API Key

Finnhub 為 US 股票提供更即時的報價（儀表板不需要也能運作，Yahoo Finance 為主要來源）。

1. 到 [finnhub.io](https://finnhub.io/) 免費註冊取得 API Key
2. 在 `config.json` 加入：

```json
{
  "finnhub_api_key": "你的_API_KEY"
}
```

執行 `main.py` 後會自動生成 `docs/config.js`（已 gitignored，僅本機有效）。

### 7. 執行

```bash
uv run python main.py
```

報告生成在 `reports/`，儀表板資料更新至 `docs/data.json`。

---

## 指令選項

```bash
uv run python main.py                        # 完整報告（持倉分析 + 市場總覽）
uv run python main.py --portfolio            # 只執行持倉分析（Task 1）
uv run python main.py --market               # 只執行市場總覽（Task 2）
uv run python main.py --validate             # 只驗證 portfolio.json 格式
uv run python main.py --dashboard            # 快速重生成儀表板（不呼叫 Claude）
uv run python main.py --update-thesis        # 單獨執行 thesis 自動更新（Task 4）
uv run python main.py --research             # 單獨執行自動研究新標的（Task 5）
uv run python main.py --enrich-thesis        # 對所有 thesis 補充深度質化分析
uv run python main.py --enrich-ticker NET    # 只補充指定 ticker 的 thesis
uv run python main.py --premarket            # 執行美股開盤前晨檢
uv run python main.py --session evening      # 指定時段（預設 morning）
uv run python main.py --force                # 強制執行（忽略週末跳過邏輯）
```

### 更新持倉後同步儀表板的完整流程

```bash
# 1. 編輯 portfolio.json（手動或由 Claude 協助）
# 2. Commit（pre-commit hook 自動重生成 data.json）
git add portfolio.json
git commit -m "portfolio: 更新說明"
# 3. Push（GitHub Pages 自動部署）
git push
```

或手動觸發儀表板重建（不 commit）：

```bash
uv run python main.py --dashboard
```

---

## 儀表板即時報價來源

儀表板每 15 秒自動更新價格，**所有來源皆免費、無需 API Key**：

| 資產 | 主要來源 | Fallback |
|------|---------|---------|
| US 股票 | Yahoo Finance（via corsproxy.io） | Finnhub（若有本機 key） |
| TW 股票 | TWSE API（via corsproxy.io） | — |
| 加密貨幣 | Binance ticker API | CoinGecko（via corsproxy.io） |
| USD/TWD | open.er-api.com | — |

> TW 股票在非交易時段（平日 13:30 後、週末）顯示昨收價。  
> GitHub Pages 上 Finnhub 不可用（`config.js` 為 gitignored 本機檔案），以 Yahoo Finance 為主。

---

## 每日自動排程

```bash
# 手動啟動排程（前景）
uv run python scheduler_daemon.py

# 開機自動啟動（不需管理員）
uv run python tools/install_startup.py

# 查詢狀態 / 移除
uv run python tools/install_startup.py --status
uv run python tools/install_startup.py --remove
```

| 時段 | 時間 | 說明 |
|------|------|------|
| morning | 07:00 | 台股盤前／美股盤後 |
| evening | 18:00 | 台股盤後／美股盤前 |

---

## 專案結構

```
daily-finance-report/
├── main.py                   # 主程式入口
├── scheduler_daemon.py       # 每日自動排程
├── config.json               # 設定檔
├── portfolio.json            # 個人持倉（自行建立，gitignored）
├── portfolio.example.json    # 持倉格式範例
├── portfolio_schema.json     # 欄位 schema（格式驗證用）
├── pyproject.toml
├── uv.lock
│
├── core/                     # 核心模組
│   ├── config.py             # 設定載入 + 日誌初始化
│   ├── portfolio.py          # 持倉載入 + schema 驗證
│   ├── news.py               # 個股 + 市場新聞抓取
│   ├── prices.py             # 即時股價 + 匯率查詢（yfinance）
│   ├── prompts.py            # Claude prompt 建構
│   ├── memory.py             # 跨日記憶摘要
│   ├── sync.py               # Git 同步封裝
│   ├── dashboard.py          # docs/data.json 生成
│   ├── thesis.py             # Thesis 管理與更新
│   ├── themes_updater.py     # 主題催化劑追蹤
│   ├── fundamentals.py       # 基本面資料抓取
│   ├── research.py           # 自動研究新標的
│   └── premarket.py          # 盤前晨檢
│
├── docs/                     # GitHub Pages 儀表板
│   ├── index.html            # 儀表板前端
│   ├── data.json             # 持倉快照（由 --dashboard 生成）
│   ├── history.json          # 歷史資產走勢
│   ├── config.js             # 本機 API Key（gitignored）
│   ├── reports/              # 報告 markdown（同步自 reports/）
│   ├── thesis/               # Thesis markdown（同步自 thesis/）
│   └── themes/               # 主題文件（同步自 themes/）
│
├── reports/                  # 每日報告（自動生成）
├── thesis/                   # 個股深度研究文件
├── themes/                   # 主題催化劑文件
└── memory/                   # 跨日記憶摘要
```

---

## License

MIT
