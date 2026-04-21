# 📈 TDCC 股市散戶監測儀 (Stock Screener)

一款專為台灣股市設計的籌碼面量化分析系統。透過追蹤 **TDCC 集保股權分散數據**，自動找出大戶增持、散戶減持且股價位於合理位階的投資標的。

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)
![FastAPI](https://img.shields.io/badge/Framework-FastAPI-red.svg)

---

## ✨ 核心亮點

- **籌碼集中追蹤**：動態分析大戶持股與散戶人數變化，精準鎖定籌碼集中標的。
- **智能化量化篩選**：整合「量比」、「20MA 股價位階」與「籌碼趨勢」的多維度篩選模型。
- **獨家評分系統**：根據大戶與散戶的增減比例，自動產出 0-100 分的投資參考權重。
- **實時 ETA 預估**：採用流式計算預計剩餘時間，大數據下載不再盲目等待。
- **動態視覺化**：整合 Plotly.js，網頁內建股價 K 線與均線走勢圖。

## 🚀 快速開始

### 1. 環境準備
建議使用 Python 虛擬環境：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 啟動伺服器
```bash
python backend/main.py
```
打開瀏覽器訪問 `http://127.0.0.1:8001` 即可使用。

## 📊 篩選指標說明

| 指標 | 說明 |
| :--- | :--- |
| **評分 (Score)** | 結合籌碼變動幅度的綜合指標，分數愈高代表籌碼集中愈顯著。 |
| **量比** | 當日成交量與 MA5 均量的比例，> 1.0 代表出現爆量啟動。 |
| **20MA 距離** | 股價離 20 日線的百分比，協助判斷當前是否過度乖離。 |

## 🛠️ 技術架構

- **Backend**: FastAPI, SQLAlchemy (SQLite), yfinance, Pandas
- **Frontend**: Vanilla JS (ES6+), CSS3 Glassmorphism, Plotly.js
- **Deployment**: 具備良好的 Raspberry Pi 4 移植性與 Git 版本管理支持。

## 📝 聲明
本工具僅供學術與技術研究參考，不構成任何投資建議。投資有風險，入市需謹慎。

---
© 2026 TDCC 股市散戶監測儀 開發小組
