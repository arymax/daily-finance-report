# 每日財經報告 Daily Finance Report

每天早晨自動爬取個股與市場新聞、查詢即時股價，透過 **Claude Code CLI** 生成持倉分析與市場總覽報告，並儲存至 GitHub 供跨裝置使用。

## 功能特色

- **持倉分析**：即時股價、成本損益、操作建議
- **市場總覽**：RSS 市場新聞 + 重要個股（NVDA、AAPL 等）新聞確保不漏接財報
- **記憶功能**：自動保留近 N 日分析摘要，提示決策連貫性
- **GitHub 同步**：執行後自動 push，跨裝置皆可取得最新報告
- **Windows 排程**：Task Scheduler 每日自動執行

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

這會自動根據 `pyproject.toml` 與 `uv.lock` 建立 `.venv` 並安裝所有依賴。

### 3. 設定個人持倉

複製範例並填入自己的持倉資料：
```bash
cp portfolio.example.json portfolio.json
```

編輯 `portfolio.json`，填入 ticker、持股數量、成本（TWD）等欄位。
格式說明請參考 `portfolio.example.json` 與 `portfolio_schema.json`。

驗證格式是否正確：
```bash
uv run python main.py --validate
```

### 4. 調整設定（可選）

編輯 `config.json`：

```json
{
  "claude_model": "",               // 留空使用預設模型，或指定如 "claude-opus-4-5"
  "claude_timeout_seconds": 300,
  "max_articles_per_stock": 5,
  "max_market_articles": 20,
  "news_sources": {
    "market_extra_tickers": ["NVDA", "AAPL", "MSFT", ...]  // 保證抓到的重要個股
  },
  "memory": {
    "enabled": true,
    "context_days": 5               // 記憶天數
  },
  "sync": {
    "enabled": false,               // 設為 true 以啟用 GitHub 自動同步
    "auto_pull": true,
    "auto_push": true
  }
}
```

### 5. 執行

```bash
uv run python main.py
```

報告生成在 `reports/` 目錄。

---

## 指令選項

```bash
uv run python main.py              # 完整報告（持倉分析 + 市場總覽）
uv run python main.py --portfolio  # 只執行持倉分析
uv run python main.py --market     # 只執行市場總覽
uv run python main.py --validate   # 只驗證 portfolio.json 格式，不生成報告
```

---

## GitHub 同步設定

若要啟用跨裝置同步，在 `config.json` 設定：
```json
"sync": { "enabled": true, "auto_pull": true, "auto_push": true }
```

確認本機 git remote 已設定：
```bash
git remote add origin https://github.com/<你的帳號>/<repo>.git
```

每次執行完畢後，程式會自動將 `reports/`、`memory/`、`portfolio.json` push 到 GitHub。

---

## 每日自動排程

本專案使用 **Python `schedule` 套件**，不依賴 Windows Task Scheduler，無需管理員權限。

### 手動啟動（當次有效）
```bash
# 有 console 視窗
uv run python scheduler_daemon.py

# 背景靜默執行（無視窗）
start "" .venv\Scripts\pythonw.exe scheduler_daemon.py
```

### 開機自動啟動（永久生效，不需管理員）
```bash
uv run python tools/install_startup.py
```

查詢狀態 / 移除：
```bash
uv run python tools/install_startup.py --status
uv run python tools/install_startup.py --remove
```

| 時段 | 時間 | 說明 |
|------|------|------|
| morning | 07:00 | 台股盤前／美股盤後分析 |
| evening | 18:00 | 台股盤後／美股盤前預備 |

---

## 專案結構

```
daily-finance-report/
├── main.py                   # 主程式入口
├── config.json               # 設定檔
├── portfolio.json            # 個人持倉（自行建立，勿 commit 敏感資料）
├── portfolio.example.json    # 持倉格式範例
├── portfolio_schema.json     # portfolio 欄位 schema（格式驗證用）
├── pyproject.toml            # 專案設定與依賴（uv init）
├── uv.lock                   # 精確版本鎖定檔
│
├── core/                     # 核心模組
│   ├── config.py             # 設定載入 + 日誌初始化
│   ├── portfolio.py          # 持倉載入 + schema 驗證
│   ├── news.py               # 個股 + 市場新聞抓取
│   ├── prices.py             # 即時股價 + 匯率查詢
│   ├── prompts.py            # Claude prompt 建構
│   ├── memory.py             # 跨日記憶摘要
│   └── sync.py               # Git 同步封裝
│
├── tools/                    # 獨立工具腳本
│   ├── validate.py           # portfolio schema 驗證 CLI
│   └── install_startup.py    # 開機自動啟動設定（不需管理員）
│
├── reports/                  # 每日報告（自動生成）
│   └── YYYYMMDD_*.md
│
└── memory/                   # 每日記憶摘要（自動生成）
    └── YYYYMMDD.md
```

---

## 新聞來源

| 類型 | 來源 |
|------|------|
| 個股新聞 | yfinance API + Yahoo Finance RSS |
| 市場新聞 | Yahoo Finance / Reuters / MarketWatch / CNBC RSS |
| 重要個股 | NVDA, AAPL, MSFT, META, GOOGL, AMZN, TSLA, AMD, TSM, SMCI（可在 config.json 調整）|
| 股價 | yfinance fast_info（TW / US / Crypto）|
| 匯率 | yfinance（USD/TWD）|

---

## License

MIT
