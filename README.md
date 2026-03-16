# NoFOMO - Trade Journal & FOMO Analysis

[中文版本](#中文版)

## Overview

**NoFOMO** is a stock and crypto trading journal that helps you learn from FOMO (Fear of Missing Out) decisions. Instead of predicting markets, it focuses on what matters: **recording your trades and reflecting on your emotional state** to avoid repeating the same mistakes.

### Core Philosophy

- 📝 **Record everything**: Every BUY, SELL, and trade entry point
- 😱 **Tag your emotions**: Was this FOMO? Or a planned trade?
- 📊 **Analyze patterns**: See how many trades were FOMO vs. planned, and compare their returns
- 🎯 **Learn & improve**: Post-trade reflection to build better trading habits

## Key Features

### 1. **Trade Journal with Reflection**
- Record trades via natural language chat: "I bought 100 MU at $150"
- Edit/delete trades anytime
- Post-trade review form (after closing the position):
  - **Motivation**: Planned entry, breakout, heard from others, FOMO, etc.
  - **Emotion**: Calm, slightly rushed, extreme FOMO
  - **Lesson**: What did you learn?
  - **Next time**: How will you handle similar situations differently?

### 2. **Auto-Prompt for Reflection**
- When you record a SELL trade, the app automatically prompts: "Want to review your BUY entry for this ticker?"
- Helps you capture insights while fresh

### 3. **FOMO Analytics Dashboard**
- **FOMO Rate**: % of BUY trades tagged as extreme FOMO
- **Emotion Distribution**: Calm vs. Rushed vs. FOMO breakdown
- **Motivation Patterns**: Most common reasons you buy
- See at a glance: Are you habitual FOMOer? Or mostly disciplined?

### 4. **Portfolio Management**
- Real-time holdings, P&L, and allocation
- Multi-currency support (USD, TWD, JPY, HKD, KRW, VND)
- Multi-market tracking (US, Taiwan, Hong Kong, Japan, South Korea, Vietnam, Crypto)
- Technical indicators (RSI, MACD, Moving Averages) at trade entry

### 5. **Natural Language Chat Interface**
- Buy/sell via chat: "Bought 10 TSLA at $250"
- Deposit/withdraw cash
- Query portfolio value
- Multi-language support (English & Traditional Chinese)

## Project Structure

```
nofomo/
├── src/                          # Backend (Python/Flask)
│   ├── api.py                   # Main API (Flask endpoints)
│   ├── portfolio.py             # Portfolio calculations & trade management
│   ├── database.py              # SQLite setup & migrations
│   ├── models.py                # SQLAlchemy models (Trade, Settings, etc.)
│   ├── chat_service.py          # NLP intent parsing & trade processing
│   ├── parser_rule.py           # Rule-based NLP parser
│   ├── market_data.py           # Stock/crypto price fetching
│   ├── analyzer.py              # Technical analysis
│   ├── ai_agent.py              # AI-powered trade enrichment
│   └── utils.py                 # Utilities
├── ui/                           # Frontend (Bootstrap 5 + Vanilla JS)
│   ├── public/
│   │   └── index.html           # Single-page app (React components in script)
│   ├── package.json
│   └── vite.config.ts
├── data/                         # Local data storage
│   ├── nofomo.db               # SQLite database
│   ├── portfolio.json
│   ├── watchlist.json
│   └── trades/                  # Trade records
├── tests/                        # Unit tests
├── requirements.txt              # Python dependencies
└── README.md
```

## Setup & Running

### Prerequisites
- Python 3.8+
- Node.js 16+ (for Vite dev server)
- pip / npm

### Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API server (Flask)
python src/api.py
```
Backend runs at **http://localhost:5001**

### Frontend Setup

```bash
cd ui

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Frontend runs at **http://localhost:5174**

Open http://localhost:5174/index.html in your browser.

## API Endpoints

### Trades
- `GET /api/trades` - Fetch all trades with reflection data
- `POST /api/trades` - Add a new trade
- `PUT /api/trades/<id>` - Edit trade details
- `PUT /api/trades/<id>/review` - Save post-trade reflection
- `DELETE /api/trades/<id>` - Delete a trade

### Portfolio
- `GET /api/portfolio/summary` - Total holdings, P&L, allocation
- `GET /api/portfolio/history` - Historical portfolio snapshots
- `GET /api/portfolio/performance` - Performance metrics

### Analysis
- `GET /api/trades/analysis` - Trade statistics + FOMO report
- `GET /api/risk-assessment` - Concentration risk & win rate

### Market Data
- `GET /api/quote?ticker=TSLA` - Stock/crypto current price
- `GET /api/batch-quote?tickers=TSLA,MU` - Multiple quotes
- `GET /api/analyze?ticker=TSLA` - Technical indicators (RSI, MACD, MA)

### Chat
- `POST /api/chat` - Process natural language trade commands

## Configuration

Edit settings via the **Settings** tab in the app:
- **LLM Provider**: OpenAI, Google Gemini, or Rule-based (free, local)
- **API Keys**: For LLM services (optional)
- **Model**: Select which model to use

Settings are stored in SQLite database.

## Database Schema

### Trade Model
```python
- id: unique ID
- date: trade date (YYYY-MM-DD)
- action: BUY, SELL, DEPOSIT, WITHDRAW, VALUATION
- ticker, price, quantity, amount, currency
- market: US, TW, JP, HK, KR, VN, CRYPTO
- Technical: rsi, trend, ma5, ma20, macd
- **Review fields (NoFOMO)**:
  - motivation: 計劃布局, 突破追買, 看別人買, 聽消息, 其他
  - emotion: 冷靜, 有點急, 非常FOMO
  - lesson: free text (what you learned)
  - next_action: free text (how you'll act differently next time)
  - reviewed_at: timestamp of when reflection was saved
```

## Features Roadmap

- [ ] Multi-account support
- [ ] Advanced charting with TradingView integration
- [ ] Backtesting engine
- [ ] Strategy simulation
- [ ] Mobile app
- [ ] Cloud sync
- [ ] Social features (share learnings anonymously)

## Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

## Contributing

Pull requests welcome! Please ensure:
1. Code passes `pytest`
2. Follows existing code style
3. Includes test coverage for new features

## License

MIT License - feel free to use for personal trading analysis.

## Disclaimer

**NoFOMO is a learning tool, not financial advice.** Past performance does not guarantee future results. Always do your own research and consult a financial advisor before making investment decisions.

---

# 中文版

## 概述

**NoFOMO** 是一個股票和加密貨幣交易日誌應用，幫助你從 FOMO（害怕錯過）決策中學習。與其預測市場，不如專注於最重要的事：**記錄你的交易並反思你的情緒狀態**，以避免重複同樣的錯誤。

### 核心理念

- 📝 **記錄一切**：每次 BUY、SELL 和進場點位
- 😱 **標記情緒**：這是 FOMO 嗎？還是計劃中的交易？
- 📊 **分析模式**：看你有多少交易是 FOMO vs. 計劃，比較它們的報酬率
- 🎯 **學習改進**：事後反思幫助你建立更好的交易習慣

## 主要功能

### 1. **交易日誌 + 復盤系統**
- 用聊天自然語言記錄交易：「我以 $150 買進 100 股 MU」
- 隨時編輯/刪除交易
- 平倉後的復盤表單：
  - **買入動機**：計劃布局、突破追買、聽消息、FOMO 等
  - **當時情緒**：冷靜、有點急、非常 FOMO
  - **學到什麼**：這筆交易給你什麼啟發？
  - **下次怎麼做**：遇到類似情況會如何應對？

### 2. **自動復盤提醒**
- 記錄 SELL 時，app 自動提示：「要對這支股票的買入做復盤嗎？」
- 幫助你趁著記憶新鮮時立刻捕捉洞察

### 3. **NoFOMO 分析儀表板**
- **FOMO 率**：被標記為「非常 FOMO」的買入佔比
- **情緒分布**：冷靜 vs. 有點急 vs. 非常 FOMO 的比例
- **買入動機分布**：你最常見的買進原因是什麼
- 一眼看出：你是慣性 FOMO 者？還是大多時候紀律良好？

### 4. **投資組合管理**
- 實時持倉、損益、資產配置
- 多幣種支援（台幣、美金、日圓、港幣、韓幣、越南盾）
- 多市場追蹤（美國、台灣、香港、日本、南韓、越南、加密貨幣）
- 進場時的技術指標（RSI、MACD、均線）

### 5. **自然語言聊天介面**
- 聊天買賣：「買進 10 股 TSLA，$250」
- 存入/提取現金
- 查詢投資組合價值
- 支援多語言（英文和繁體中文）

## 專案結構

```
nofomo/
├── src/                          # 後端 (Python/Flask)
│   ├── api.py                   # Flask API 主入口
│   ├── portfolio.py             # 投資組合計算與交易管理
│   ├── database.py              # SQLite 設定與遷移
│   ├── models.py                # SQLAlchemy 資料模型
│   ├── chat_service.py          # NLP 意圖解析與交易處理
│   ├── parser_rule.py           # 規則型 NLP 解析器
│   ├── market_data.py           # 股票/加密貨幣價格抓取
│   ├── analyzer.py              # 技術分析
│   ├── ai_agent.py              # AI 強化交易資料
│   └── utils.py                 # 工具函數
├── ui/                           # 前端 (Bootstrap 5 + Vanilla JS)
│   ├── public/
│   │   └── index.html           # 單頁應用 (React 元件在 script 中)
│   ├── package.json
│   └── vite.config.ts
├── data/                         # 本地資料存儲
│   ├── nofomo.db               # SQLite 資料庫
│   ├── portfolio.json
│   ├── watchlist.json
│   └── trades/                  # 交易記錄
├── tests/                        # 單元測試
├── requirements.txt              # Python 套件
└── README.md
```

## 安裝與執行

### 系統要求
- Python 3.8+
- Node.js 16+ (用於 Vite)
- pip / npm

### 後端設定

```bash
# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt

# 運行 API 伺服器
python src/api.py
```
後端運行於 **http://localhost:5001**

### 前端設定

```bash
cd ui

# 安裝套件
npm install

# 啟動 Vite 開發伺服器
npm run dev
```
前端運行於 **http://localhost:5174**

在瀏覽器打開 http://localhost:5174/index.html

## API 端點

### 交易
- `GET /api/trades` - 取得所有交易（含復盤資料）
- `POST /api/trades` - 新增交易
- `PUT /api/trades/<id>` - 編輯交易
- `PUT /api/trades/<id>/review` - 儲存交易復盤
- `DELETE /api/trades/<id>` - 刪除交易

### 投資組合
- `GET /api/portfolio/summary` - 投資組合摘要、損益、配置
- `GET /api/portfolio/history` - 歷史投資組合快照
- `GET /api/portfolio/performance` - 績效指標

### 分析
- `GET /api/trades/analysis` - 交易統計 + FOMO 報告
- `GET /api/risk-assessment` - 集中度風險與勝率

### 市場資料
- `GET /api/quote?ticker=TSLA` - 單支股票/加密貨幣現價
- `GET /api/batch-quote?tickers=TSLA,MU` - 批量報價
- `GET /api/analyze?ticker=TSLA` - 技術指標 (RSI, MACD, MA)

### 聊天
- `POST /api/chat` - 處理自然語言交易命令

## 設定

在應用程式的「設定」頁籤調整：
- **LLM 提供者**：OpenAI、Google Gemini 或規則型（免費、本地）
- **API Key**：用於 LLM 服務（選擇性）
- **模型選擇**：選擇要使用的模型

設定儲存在 SQLite 資料庫。

## 資料庫結構

### Trade 模型
```python
- id: 唯一識別碼
- date: 交易日期 (YYYY-MM-DD)
- action: BUY, SELL, DEPOSIT, WITHDRAW, VALUATION
- ticker, price, quantity, amount, currency
- market: US, TW, JP, HK, KR, VN, CRYPTO
- 技術指標: rsi, trend, ma5, ma20, macd
- **復盤欄位 (NoFOMO)**:
  - motivation: 計劃布局、突破追買、看別人買、聽消息、其他
  - emotion: 冷靜、有點急、非常FOMO
  - lesson: 自由文本（你學到什麼）
  - next_action: 自由文本（下次怎麼做）
  - reviewed_at: 復盤保存的時間戳
```

## 功能規劃

- [ ] 多帳戶支援
- [ ] 高階圖表與 TradingView 整合
- [ ] 回測引擎
- [ ] 策略模擬
- [ ] 行動應用
- [ ] 雲端同步
- [ ] 社群功能（匿名分享學習）

## 測試

```bash
# 運行測試
pytest tests/

# 含覆蓋率
pytest --cov=src tests/
```

## 貢獻

歡迎提交 Pull Request！請確保：
1. 程式通過 `pytest`
2. 遵循既有程式風格
3. 新功能包含測試覆蓋

## 授權

MIT License - 自由用於個人交易分析

## 免責聲明

**NoFOMO 是學習工具，不構成投資建議。** 過去績效不保證未來結果。投資前請自行研究並諮詢財務顧問。
