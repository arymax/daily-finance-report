# Marvell Technology Inc.（MRVL）｜研究報告

**產業：** 半導體（自訂 AI 晶片 / 資料中心網路 / 光學）
**市場：** US
**主題：** AI ASIC 週期最直接受益者——為超大型雲端客戶設計專屬推論晶片，深度繫結 Google、Amazon 等 Hyperscaler 資本支出浪潮
**研究日期：** 2026-03-06
**研究觸發：** Q4 財報雙超預期（EPS $0.80、營收 $2.22B YoY +22.1%），管理層確認 Google/Amazon 等超大型雲端 AI 定制晶片需求「強勁」，盤後跳漲，為 AI ASIC 週期延伸最直接受益標的

---

### 核心業務與商業模式

#### 賣什麼：產品結構

Marvell 是一家純矽智財（Fabless）半導體公司，產品可分為四大支柱：

| 業務 | 主要產品 | FY2026 佔比（估） |
|------|---------|----------------|
| **資料中心**（核心引擎） | 客製 AI ASIC、PAM4 DSP、光電子晶片、乙太網路交換器 | ~74% |
| **運營商基礎設施** | 5G 基頻 ASIC、網路處理器 | ~11% |
| **企業網路** | 乙太網路 PHY、交換器 IC | ~8% |
| **汽車 / 工業** | 車用乙太網路、安全處理器 | ~7% |

**最核心產品：Custom AI ASIC（自訂推論晶片）**
這是當前最大的成長引擎。Marvell 以「晶片設計代工」模式，替 Google（TPU 系列）、Amazon（Trainium/Inferentia）等客戶設計專屬 AI 加速器。客戶提供架構需求，Marvell 負責 RTL 設計、IP 整合、流片（台積電代工），最終交付 ASIC。

**光互連晶片（Electro-Optic DSP）**
Marvell 的 PAM4 DSP（數位訊號處理器）是資料中心高速光纖互連的關鍵元件，每台 AI 伺服器機架均需大量使用，這是相對低調但黏性極高的業務。

#### 怎麼賣：商業模式

- **NRE（Non-Recurring Engineering）+ 量產授權**：前期向客戶收取晶片設計費，量產後按晶片銷售量收取授權費/出貨利潤，現金流前低後高。
- **長週期設計合作**：一個 ASIC 專案從設計到量產通常耗時 18–36 個月，一旦 tape-out（設計定案）後極難替換。
- **直銷為主**：Hyperscaler 客戶直接對接 Marvell 工程與業務團隊，無分銷商介入，毛利保留較完整。

#### 賣給誰：客戶輪廓

- **Google**：TPU 設計夥伴（長期合作超過 10 年），是最大單一客戶，佔比估計 15–20%
- **Amazon AWS**：Trainium 2/3、Inferentia 系列 ASIC 協助設計
- **Microsoft**：傳聞中的 Maia AI 晶片供應鏈夥伴
- **Meta / 其他 Hyperscaler**：光互連 DSP 廣泛供貨
- **Tier-1 電信商**：AT&T、Verizon、中國電信等（5G 基頻 ASIC）

---

### 競爭護城河與市場地位

#### 護城河分析

**1. 深度技術整合（最強護城河）**
Marvell 替 Hyperscaler 設計的 ASIC 高度客製，IP、封裝方式、介面設計均與客戶 AI 框架深度整合。替換成本極高——換供應商意味著重新設計晶片、重新訓練 SW 工具鏈，周期 2–3 年，成本逾億美元。

**2. 獨家 IP 庫**
Marvell 擁有豐富的半導體 IP，涵蓋 SerDes（高速序列介面）、PCIe、HBM 記憶體介面、光互連 DSP 等，這些 IP 在 ASIC 設計中是必不可少的模組，Hyperscaler 自行開發的成本遠高於採用 Marvell 方案。

**3. 台積電先進製程優先排程**
多年合作關係讓 Marvell 在台積電 3nm/2nm 產能取得優先地位，對於急於推出下一代 AI 晶片的 Hyperscaler 而言，這是無法輕易繞開的瓶頸。

**4. 多客戶 ASIC 平台規模效應**
同時服務多家 Hyperscaler，讓 Marvell 的 ASIC 設計流程、EDA 工具鏈持續優化，形成設計效率護城河——競爭者（如 Broadcom）也有此能力，但新進者難以追趕。

#### 主要競爭對手

| 競爭對手 | 重疊領域 | Marvell 優勢 |
|---------|---------|------------|
| **Broadcom（AVGO）** | Custom ASIC（Google TPU、Meta）、網路晶片 | Marvell 更專注 AI ASIC，AVGO 更大但更分散 |
| **Intel（IFS/Habana）** | AI 加速器 | Marvell 無晶圓廠包袱，更靈活 |
| **Nvidia（GB200 NVLink）** | GPU 互連 | 不同層次：Marvell 做基礎設施，Nvidia 做計算 |
| **Arm / Cadence（IP 供應）** | IP 授權 | Marvell 整合服務更完整 |

**市場地位：Custom AI ASIC 領域與 Broadcom 並列前二。**
光互連 DSP 領域，Marvell 是全球市佔最高的獨立廠商（估計 ~50%+）。

---

### 行業 KPI 與公司表現

#### 半導體 AI 基礎設施行業關鍵 KPI

| KPI | 行業意義 | Marvell 表現 |
|-----|---------|------------|
| **資料中心營收 YoY 成長率** | 核心 AI 業務動能 | FY2026 Q4：+78% YoY（創紀錄） |
| **Design Win 數量與規模** | 未來 2–3 年訂單能見度 | FY2026 創下歷史新高（管理層明確表述） |
| **毛利率趨勢** | 產品組合升級程度 | 51.0%（Non-GAAP 接近 60%），逐年改善 |
| **客戶集中度（Top 客戶）** | 風險與議價能力指標 | Google/Amazon 佔比高，為雙刃劍 |
| **NRE 收入比例** | 設計管線健康度 | 持續增加，表示新設計案流入 |
| **FY2027 營收指引** | 管理層能見度 | 接近 $11B，YoY +30%（超越市場預期） |
| **AI TAM 成長率** | 市場天花板 | IDC 預測 AI ASIC 市場 2025–2028 CAGR >45% |

**亮點數據：**
- FY2026 全年資料中心營收佔總營收 74%，且此比例仍在上升
- FY2026 Q4 EPS（Non-GAAP）$0.80，超出指引上限
- 管理層首次明確 FY2027 指引：接近 $11B 營收，隱含 30%+ 成長

---

### 成長驅動力

#### 未來 2–3 年核心成長引擎

**1. Hyperscaler AI ASIC 訂單加速（最大驅動力，2026–2028）**

Google TPU v6/v7、Amazon Trainium 3/4 的量產週期已進入 Marvell 設計管線。
管理層預估 AI ASIC 可定址市場（TAM）從 2025 年的約 $75B 成長至 2028 年的 $150B+。
FY2026 已創下 Design Win 記錄，這些 Design Win 對應的量產收入將在 FY2027–2028 集中實現。

**2. 光互連 DSP 需求爆發（2025–2027）**

每個 GPU / AI 加速器集群需要大量 800G/1.6T 光收發器模組，Marvell 的 PAM4 DSP 是不可或缺的核心元件。
隨著 Nvidia GB200 NVL72 機架密度提升，光互連需求呈非線性增長。
Marvell 預計此業務在未來兩年維持 40%+ 年增長。

**3. 乙太網路交換 IC（AI 集群網路）（2026–2027）**

InfiniBand 主導地位受到 Ultra Ethernet Consortium（Marvell 為創始成員之一）挑戰。
Marvell 的 Teralynx 系列乙太網路交換晶片定位為替代 InfiniBand 的低成本方案，受 Meta、AWS 青睞。

**4. 5G / 運營商基礎設施復甦（2027 候補）**

受 5G 建設放緩拖累，此業務目前處於低谷，一旦全球電信商進入 5G-Advanced 建設週期，Marvell 的基頻 ASIC 和網路處理器將迎來補庫週期。

**FY2027 財務路線圖預覽：**
- 營收指引：接近 $11B（YoY +30%）
- Non-GAAP EPS 共識：約 $5.44（較研究撰寫時 $4.72 上修，YoY +77%+）
- 毛利率目標：Non-GAAP 接近 62%

---

### 財務數據概覽

| 指標 | 數值 | 備註 |
|------|------|------|
| **股價** | $87.86 | 2026-03-16 |
| **市值** | $76.74B | |
| **FY2026 Q4 營收** | $2.22B | YoY +22.1%，QoQ +7% |
| **FY2026 全年營收** | ~$7.97B | YoY +36.8% |
| **FY2027 營收指引** | ~$11B | YoY +30%+ |
| **EPS（TTM，GAAP）** | $3.07 | |
| **EPS（Non-GAAP FY2026 Q4）** | $0.80 | 超出指引 |
| **預期 EPS（FY2027 Non-GAAP）** | $5.44 | YoY +77%+（較原 $4.72 上修） |
| **毛利率（GAAP）** | 51.0% | Non-GAAP ~60% |
| **營業利益率（GAAP）** | 18.7% | Non-GAAP ~35% |
| **Trailing P/E** | 28.62x | 基於 GAAP EPS |
| **Forward P/E** | 16.14x | 基於 FY2027 Non-GAAP EPS |
| **P/B** | 5.20x | |
| **P/S（FY2027E）** | ~6.0x | 基於 ~$11B 營收指引 |
| **分析師目標均價** | $120.28 | 追蹤分析師 40 人 |
| **隱含上漲空間** | ~+37% | 相對現價 $87.86 |

**估值評析：**
Forward P/E 16x 對一家 AI ASIC 核心受益公司而言明顯低估——同業 Broadcom 目前交易在 25–28x Forward P/E。若以 Broadcom 倍數套用，Marvell 合理股價區間為 $100–$120，與分析師共識目標價吻合。EPS 成長率 77%（FY2027E）對應 16x PE 的 PEG 僅 0.21，具有顯著安全邊際。

---

### 即時市場指標（自動更新）
<!-- snapshot:start -->
*最後更新：2026-03-20 07:01 TST*

| 指標 | 數值 |
|------|------|
| 本益比（Trailing P/E） | 29.16 |
| 預期本益比（Forward P/E） | 16.46 |
| EPS（TTM） | 3.07 USD |
| 預期 EPS | 5.44 USD |
| 股價淨值比（P/B） | 5.30 |
| 毛利率（最新季） | 51.0% |
| 營業利益率 | 18.7% |
| 營收成長率（YoY） | 22.1% |
| 自由現金流（FCF，TTM） | 1.44 B USD |
| 市值 | 78.28 B USD |
| 分析師目標均價 | 120.50 USD |
| 追蹤分析師數 | 40 |
| 毛利率趨勢（近4季） | 2026-Q1:51.7% → 2025-Q4:51.6% → 2025-Q3:50.4% → 2025-Q2:50.3% |
<!-- snapshot:end -->

---

### 主要風險

**1. 客戶集中度風險（最核心結構性風險）**

Google 和 Amazon 合計佔 Marvell 營收估計 35–45%。若任一主要客戶策略轉向——例如 Google 決定完全自研 TPU（完全繞開 Marvell），或 Amazon 選擇競爭對手——將對 Marvell 造成結構性衝擊。此風險在技術上可行（Google 內部有強大的 IC 設計能力），但實際執行需 3–5 年過渡期，短期可控，中期需持續監控。

**2. ASIC vs. GPU 技術路徑競爭（週期性風險）**

若 Nvidia 在 GPU 效率上持續突破（Blackwell 後的下一代架構），Hyperscaler 可能重新評估自研 ASIC 的 ROI，轉而增加 GPU 採購而非委託 Marvell 設計 ASIC。此風險在 2025 年有所升溫（Nvidia B200 性價比提升），但 Marvell 管理層強調 ASIC 在特定推論任務的 TCO 優勢持續存在，且 Design Win 管線未見減少。

**3. 台積電先進製程產能與地緣政治風險**

Marvell 所有先進晶片均委由台積電代工（主要在 5nm/3nm/2nm）。台灣地緣政治風險、台積電產能分配、或美中貿易制裁升級均可能衝擊供應鏈。此外，若台積電先進製程產能被 Nvidia 等大客戶優先佔用，Marvell 的 Hyperscaler 訂單交期可能延誤，影響短期營收確認時間點。

---

### 買入邏輯初步評估

### 買入邏輯初步評估

> **AI ASIC 週期最直接的純股票受益者，Forward P/E 16x 對應 77% EPS 成長明顯低估。**
>
> Marvell FY2026 Q4 財報（3/6）雙超預期，FY2027 指引接近 $11B（YoY +30%）確認 AI ASIC 週期進入加速收割階段。Design Win 歷史新高代表 FY2027–2028 量產收入能見度強。Nvidia GTC 確認 Blackwell Ultra 路線圖，直接印證 Marvell 光互連 DSP 與 ASIC 需求剛性。**Nvidia 宣布向 Amazon 銷售 100 萬顆 GPU（至 2027 年底，3/19）進一步確認 Amazon AI CapEx 持續強勁，直接強化 MRVL Amazon Trainium/Inferentia ASIC 設計管線的訂單能見度。**
>
> Forward P/E 16x 對照同業 Broadcom 25–28x，以及 PEG 僅 0.21（77% EPS 成長），估值折價顯著。折價反映客戶集中度風險（Google/Amazon 合計 35–45%），但管理層 Design Win 管線無縮減信號，短中期此風險可控。
>
> **目前持倉為負浮盈（-3.6%）**，股價 $89.53 已回升至 $85–$88 關鍵支撐區之上，支撐守穩為正面技術信號，持倉維持，觀察能否進一步突破 $90–$95 阻力區。
>
> **主要風險：** ① Google/Amazon 訂單集中；② Nvidia GPU 效率持續提升壓縮 ASIC ROI；③ 台積電先進製程地緣政治風險；④ FOMC 偏鷹壓制估值。
<!-- last_updated: 2026-03-20 -->
